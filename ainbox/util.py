"""Utility functions for paths, IDs, timestamps."""

import os
from pathlib import Path
from datetime import datetime, timezone
import uuid
import re


def get_home_mailbox() -> Path:
    """Get shared mailbox path (~/.mailbox)."""
    return Path.home() / ".mailbox"


def get_local_mailbox() -> Path:
    """Get local mailbox path (.mailbox)."""
    return Path.cwd() / ".mailbox"


def get_shared_mailbox() -> Path:
    """Get shared mailbox path.
    
    Resolves in order:
    1. MAILBOX_SHARED environment variable
    2. shared_mailbox_path in local .mailbox/config.yaml
    3. shared_mailbox_path in global ~/.mailbox/config.yaml
    4. Default ~/.mailbox
    """
    # 1. Environment variable
    if "MAILBOX_SHARED" in os.environ:
        return normalize_path(os.environ["MAILBOX_SHARED"].strip())
    
    # 2. Local config
    local_config = get_local_mailbox() / "config.yaml"
    if local_config.exists():
        path = _load_config_value(local_config, "shared_mailbox_path")
        if path:
            return normalize_path(path)
    
    # 3. Global config
    global_config = get_home_mailbox() / "config.yaml"
    if global_config.exists():
        path = _load_config_value(global_config, "shared_mailbox_path")
        if path:
            return normalize_path(path)
    
    # 4. Default
    return get_home_mailbox()


def get_shared_outbox() -> Path:
    """Get shared outbox path."""
    return get_shared_mailbox() / "shared" / "outbox"


def normalize_path(path: str) -> Path:
    """Normalize a path string, expanding ~ and converting to Path."""
    return Path(path).expanduser().resolve()


def get_agent_id() -> str:
    """Resolve agent ID from env, config, or folder name."""
    # 1. Environment variable
    if "MAILBOX_AGENT_ID" in os.environ:
        return os.environ["MAILBOX_AGENT_ID"].strip()
    
    # 2. Local config
    local_config = get_local_mailbox() / "config.yaml"
    if local_config.exists():
        agent_id = _load_config_value(local_config, "agent_id")
        if agent_id:
            return agent_id
    
    # 3. Global config
    global_config = get_home_mailbox() / "config.yaml"
    if global_config.exists():
        agent_id = _load_config_value(global_config, "agent_id")
        if agent_id:
            return agent_id
    
    # 4. Folder name fallback
    agent_id = Path.cwd().name
    if agent_id and agent_id != ".":
        return agent_id
    
    raise ValueError(
        "Agent ID not found. Set MAILBOX_AGENT_ID env var, "
        "add 'agent_id' to .mailbox/config.yaml or ~/.mailbox/config.yaml, "
        "or use a named directory."
    )


def _load_config_value(config_path: Path, key: str) -> str:
    """Load a single value from YAML config (simple parser)."""
    try:
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}:"):
                    value = line.split(":", 1)[1].strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    return value
    except Exception:
        pass
    return None


def generate_id() -> str:
    """Generate a unique message ID."""
    return str(uuid.uuid4())[:13]  # Short unique ID


def generate_timestamp() -> str:
    """Generate an ISO 8601 timestamp (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_filename_timestamp() -> str:
    """Generate a timestamp for filename (sortable format)."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_message_filename(msg_id: str) -> str:
    """Create a message filename from ID."""
    ts = generate_filename_timestamp()
    return f"{ts}_{msg_id}.md"


def extract_id_from_filename(filename: str) -> str:
    """Extract message ID from filename."""
    # Format: YYYYMMDDTHHMMSSZ_ID.md
    match = re.match(r"^\d{8}T\d{6}Z_(.+)\.md$", filename)
    if match:
        return match.group(1)
    return None
