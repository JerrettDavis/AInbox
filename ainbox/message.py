"""Message parsing and serialization."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from .util import parse_utc_timestamp


class Message:
    """Represents a mailbox message (markdown + frontmatter)."""

    def __init__(
        self,
        msg_id: str,
        to: str,
        from_: str,
        subject: str,
        sent_at: str,
        received_at: Optional[str] = None,
        read_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
        expires_at: Optional[str] = None,
        body: str = "",
        **extra_fields,
    ):
        self.id = msg_id
        self.to = to
        self.from_ = from_
        self.subject = subject
        self.sent_at = sent_at
        self.received_at = received_at
        self.read_at = read_at
        self.correlation_id = correlation_id
        if expires_at:
            parse_utc_timestamp(expires_at)
        self.expires_at = expires_at
        self.body = body
        self.extra_fields = extra_fields

    def to_markdown(self) -> str:
        """Serialize message to markdown with frontmatter."""
        frontmatter = self._build_frontmatter()
        return f"{frontmatter}\n\n{self.body}".rstrip() + "\n"

    def _build_frontmatter(self) -> str:
        """Build YAML frontmatter."""
        def _sanitize_field(value: str) -> str:
            """Reject strings with embedded newlines to prevent frontmatter injection."""
            if not isinstance(value, str):
                value = str(value)
            if "\n" in value or "\r" in value:
                raise ValueError(f"Field values cannot contain newlines: {repr(value[:50])}")
            return value
        
        lines = ["---"]
        lines.append(f"id: {_sanitize_field(self.id)}")
        lines.append(f"to: {_sanitize_field(self.to)}")
        lines.append(f"from: {_sanitize_field(self.from_)}")
        lines.append(f"subject: {_sanitize_field(self.subject)}")
        lines.append(f"sent_at: {_sanitize_field(self.sent_at)}")
        lines.append(f"received_at: {_sanitize_field(self.received_at or 'null')}")
        lines.append(f"read_at: {_sanitize_field(self.read_at or 'null')}")
        if self.correlation_id:
            lines.append(f"correlation_id: {_sanitize_field(self.correlation_id)}")
        if self.expires_at:
            lines.append(f"expires_at: {_sanitize_field(self.expires_at)}")
        for key, value in self.extra_fields.items():
            if isinstance(value, str):
                lines.append(f"{key}: {_sanitize_field(value)}")
            elif isinstance(value, list):
                lines.append(f"{key}: {value}")
            elif value is None:
                lines.append(f"{key}: null")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, content: str) -> "Message":
        """Parse markdown + frontmatter into Message."""
        # Split on line-delimited --- markers only
        # Frontmatter must start with --- on line 1 and close with --- on some later line
        lines = content.split("\n")
        if len(lines) < 3 or lines[0].strip() != "---":
            raise ValueError("Invalid message format: missing frontmatter markers")
        
        # Find closing --- delimiter (must be second occurrence of --- on its own line)
        closing_idx = None
        found_first = True  # We already know line 0 is ---
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_idx = i
                break
        
        if closing_idx is None:
            raise ValueError("Invalid message format: missing closing --- delimiter")
        
        frontmatter_str = "\n".join(lines[1:closing_idx]).strip()
        # For body: everything after closing --- (which includes the empty separator line)
        # Reconstruct and strip trailing whitespace to match to_markdown() which does .rstrip() + "\n"
        body_lines = lines[closing_idx + 1:]
        # Skip exactly one empty line if present (the separator between frontmatter and body)
        if body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]
        body = "\n".join(body_lines).rstrip()
        
        # Parse frontmatter (simple key: value format)
        fields = {}
        optional_nullable = {"received_at", "read_at", "correlation_id", "expires_at"}
        required = {"id", "to", "from", "subject", "sent_at"}
        
        for line in frontmatter_str.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            
            # Handle null: only for optional nullable fields, treat "null" as None
            # Required fields preserve the literal string "null"
            if value.lower() == "null" and key in optional_nullable:
                fields[key] = None
            else:
                fields[key] = value
        
        # Extract required fields
        missing = required - set(fields.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            msg_id=fields["id"],
            to=fields["to"],
            from_=fields["from"],
            subject=fields["subject"],
            sent_at=fields["sent_at"],
            received_at=fields.get("received_at"),
            read_at=fields.get("read_at"),
            correlation_id=fields.get("correlation_id"),
            expires_at=fields.get("expires_at"),
            body=body,
            **{k: v for k, v in fields.items() if k not in required and k not in optional_nullable},
        )

    def is_expired(self) -> bool:
        """Return whether the message has reached its expiry time."""
        if not self.expires_at:
            return False
        return parse_utc_timestamp(self.expires_at) <= datetime.now(timezone.utc)

    @classmethod
    def from_file(cls, path: Path) -> "Message":
        """Load message from file."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return cls.from_markdown(content)

    def to_file(self, path: Path) -> None:
        """Save message to file (atomic write)."""
        import tempfile
        import os
        
        content = self.to_markdown()
        
        # Atomic write: write to temp file, then replace
        temp_dir = path.parent
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=temp_dir,
            delete=False,
            suffix=".tmp",
        ) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            os.replace(temp_path, path)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise
