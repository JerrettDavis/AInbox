"""Core mailbox operations."""

import os
from pathlib import Path
from typing import List, Optional

from .util import (
    get_local_mailbox,
    get_home_mailbox,
    get_shared_outbox,
    get_agent_id,
    generate_id,
    generate_timestamp,
    make_message_filename,
    extract_id_from_filename,
)
from .message import Message


class Mailbox:
    """Main mailbox operations."""

    DLQ_AGENT_ID = "dlq"
    EXPIRY_AGENT_ID = "mailbox-expiry"
    EXPIRY_MESSAGE_TYPE = "expired"

    def __init__(self):
        self.local_mailbox = get_local_mailbox()
        self.shared_outbox = get_shared_outbox()
        self.agent_id = get_agent_id()

    def init(self) -> None:
        """Initialize local mailbox structure."""
        folders = ["inbox", "outbox", "sent", "archive", "draft"]
        for folder in folders:
            (self.local_mailbox / folder).mkdir(parents=True, exist_ok=True)
        print(f"Initialized mailbox at {self.local_mailbox}")

    def send(
        self,
        to: str,
        subject: str,
        body: str = "",
        correlation_id: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> str:
        """Create and send a message."""
        msg_id = generate_id()
        timestamp = generate_timestamp()
        
        message = Message(
            msg_id=msg_id,
            to=to,
            from_=self.agent_id,
            subject=subject,
            sent_at=timestamp,
            correlation_id=correlation_id,
            expires_at=expires_at,
            body=body,
        )
        
        # Create outbox folder if needed
        outbox = self.local_mailbox / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        
        # Save to outbox
        filename = make_message_filename(msg_id)
        filepath = outbox / filename
        message.to_file(filepath)
        
        return str(filepath)

    def list_inbox(self, limit: int = 10) -> List[Message]:
        """List messages in inbox."""
        self._expire_inbox_messages()
        inbox = self.local_mailbox / "inbox"
        if not inbox.exists():
            return []
        
        messages = []
        files = sorted(inbox.glob("*.md"), reverse=True)[:limit]
        
        for file in files:
            try:
                msg = Message.from_file(file)
                messages.append(msg)
            except Exception as e:
                print(f"Warning: Could not parse {file}: {e}")
        
        return messages

    def read_message(self, msg_id: Optional[str] = None, correlation_id: Optional[str] = None) -> Optional[Message]:
        """Read a message and mark as read.
        
        Args:
            msg_id: Specific message ID to read
            correlation_id: Filter by correlation ID (reads first matching)
        """
        self._expire_inbox_messages()
        inbox = self.local_mailbox / "inbox"
        if not inbox.exists():
            return None
        
        if msg_id:
            # Find by ID
            for file in inbox.glob("*.md"):
                if extract_id_from_filename(file.name) == msg_id:
                    return self._mark_and_read(file)
        elif correlation_id:
            # Find first message with matching correlation_id
            for file in sorted(inbox.glob("*.md")):
                try:
                    msg = Message.from_file(file)
                    if msg.correlation_id == correlation_id:
                        return self._mark_and_read(file)
                except Exception:
                    continue
        else:
            # Read first message
            files = sorted(inbox.glob("*.md"))
            if files:
                return self._mark_and_read(files[0])
        
        return None

    def _mark_and_read(self, filepath: Path) -> Message:
        """Read a message and move to archive."""
        message = Message.from_file(filepath)
        
        # Update read_at timestamp
        message.read_at = generate_timestamp()
        
        # Move to archive
        archive = self.local_mailbox / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        
        archive_path = archive / filepath.name
        message.to_file(archive_path)
        
        # Remove from inbox
        os.unlink(filepath)
        
        return message

    def archive_message(self, msg_id: str) -> bool:
        """Archive a message by ID."""
        self._expire_inbox_messages()
        inbox = self.local_mailbox / "inbox"
        if not inbox.exists():
            return False
        
        for file in inbox.glob("*.md"):
            if extract_id_from_filename(file.name) == msg_id:
                return self._mark_and_read(file) is not None
        
        return False

    def sync(self, push_only: bool = False, pull_only: bool = False) -> tuple:
        """Sync mailbox (push and/or pull)."""
        pushed = 0
        pulled = 0

        self._expire_inbox_messages()
        
        if not pull_only:
            pushed = self._sync_push()
        
        if not push_only:
            pulled = self._sync_pull()
        
        return pushed, pulled

    def _sync_push(self) -> int:
        """Push messages from local outbox to shared outbox."""
        outbox = self.local_mailbox / "outbox"
        if not outbox.exists():
            return 0
        
        count = 0
        sent = self.local_mailbox / "sent"
        sent.mkdir(parents=True, exist_ok=True)
        
        self.shared_outbox.mkdir(parents=True, exist_ok=True)
        
        for file in outbox.glob("*.md"):
            try:
                message = Message.from_file(file)
                if message.is_expired():
                    self._route_expired_message(message, source="outbox")
                    os.unlink(file)
                    continue

                dest = self.shared_outbox / file.name
                message.to_file(dest)
                
                # Move original to sent
                sent_path = sent / file.name
                message.to_file(sent_path)
                
                # Remove from outbox
                os.unlink(file)
                count += 1
            except Exception as e:
                print(f"Warning: Could not push {file.name}: {e}")
        
        return count

    def _sync_pull(self) -> int:
        """Pull messages from shared outbox to local inbox."""
        if not self.shared_outbox.exists():
            return 0
        
        inbox = self.local_mailbox / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        
        # Track IDs already locally (inbox, archive, sent) to avoid re-importing
        existing_ids = set()
        for folder in ["inbox", "archive", "sent"]:
            folder_path = self.local_mailbox / folder
            if folder_path.exists():
                for file in folder_path.glob("*.md"):
                    msg_id = extract_id_from_filename(file.name)
                    if msg_id:
                        existing_ids.add(msg_id)
        
        count = 0
        for file in self.shared_outbox.glob("*.md"):
            try:
                message = Message.from_file(file)

                if message.to != self.DLQ_AGENT_ID and message.is_expired():
                    self._route_expired_message(message, source="shared-outbox")
                    os.unlink(file)
                    continue
                
                # Only pull if addressed to us and not already locally
                if message.to == self.agent_id and message.id not in existing_ids:
                    # Set received_at timestamp on pull
                    if not message.received_at:
                        message.received_at = generate_timestamp()
                    
                    inbox_path = inbox / file.name
                    message.to_file(inbox_path)
                    existing_ids.add(message.id)
                    count += 1
                    
                    # Clean up shared outbox after successful pull
                    # V1 pragmatic strategy: remove file after pulling
                    # This prevents unbounded growth while preserving correctness for point-to-point model
                    try:
                        os.unlink(file)
                    except Exception as e:
                        print(f"Warning: Could not delete {file.name} from shared outbox: {e}")
            except Exception as e:
                print(f"Warning: Could not pull {file.name}: {e}")
        
        return count

    def _expire_inbox_messages(self) -> None:
        """Route expired local inbox messages to the DLQ."""
        inbox = self.local_mailbox / "inbox"
        if not inbox.exists():
            return

        for file in list(inbox.glob("*.md")):
            try:
                message = Message.from_file(file)
                if message.to != self.DLQ_AGENT_ID and message.is_expired():
                    self._route_expired_message(message, source="inbox")
                    os.unlink(file)
            except Exception as e:
                print(f"Warning: Could not process expiry for {file.name}: {e}")

    def _route_expired_message(self, message: Message, source: str) -> None:
        """Write an expiry notification to the DLQ mailbox."""
        self.shared_outbox.mkdir(parents=True, exist_ok=True)

        expired = Message(
            msg_id=generate_id(),
            to=self.DLQ_AGENT_ID,
            from_=self.EXPIRY_AGENT_ID,
            subject=f"Expired: {message.subject}",
            sent_at=generate_timestamp(),
            correlation_id=message.correlation_id or f"expired:{message.id}",
            body=(
                "This message expired and was routed to the dlq mailbox.\n\n"
                f"source: {source}\n"
                f"original_id: {message.id}\n"
                f"original_to: {message.to}\n"
                f"original_from: {message.from_}\n"
                f"original_subject: {message.subject}\n"
                f"original_expires_at: {message.expires_at}\n\n"
                "Original message:\n\n"
                f"{message.to_markdown()}"
            ),
            message_type=self.EXPIRY_MESSAGE_TYPE,
            original_id=message.id,
            original_to=message.to,
            original_from=message.from_,
            original_subject=message.subject,
            original_expires_at=message.expires_at or "",
        )
        expired.to_file(self.shared_outbox / make_message_filename(expired.id))
