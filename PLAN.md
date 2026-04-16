# PLAN.md: AInbox Engineering Specification

## Executive Summary

**AInbox** is a filesystem-based async mailbox for coding agents. It provides a minimal, cross-platform CLI and Python package that enables decentralized agent communication via structured markdown messages. No broker, no orchestrator, no central service—just files, conventions, and scripts.

**Version**: 1.0 (initial scope)  
**Status**: Implementation phase  
**Language**: Python 3.8+ (stdlib-only preferred)  
**Installability**: `pip install -e .` + wrapper scripts for Copilot CLI, Claude Code, etc.

---

## 1. Purpose & Design Principles

### 1.1 Design Goals

- **Decentralized**: No central service or broker. Agents operate independently and poll for messages.
- **File-based**: Filesystem is the transport layer. Markdown is the message format.
- **Convention over configuration**: Standard folder structure, message schema, and state transitions.
- **Cross-platform**: Linux, macOS, Windows via `pathlib` and scripts in Python + Bash + PowerShell.
- **Pluggable**: Works via skills, scripts, and hooks for any agent system.

### 1.2 Core Principles

- **Agents have identity**: Resolved via env var, config, or folder name.
- **Messages are files**: `.md` files with YAML frontmatter + body.
- **Atomic writes**: Use temp file + `os.replace()` for robustness.
- **No broadcasts**: Point-to-point messaging only in v1.
- **Sync is explicit**: Agents call `mailbox sync` to push/pull.

---

## 2. Architecture

### 2.1 Agent Identity Resolution

Priority order:

1. `MAILBOX_AGENT_ID` environment variable
2. `mailbox_agent_id` in local `.mailbox/config.yaml`
3. `mailbox_agent_id` in `~/.mailbox/config.yaml`
4. Basename of parent directory of `.mailbox`

Fail with clear error if identity cannot be resolved.

### 2.2 Mailbox Locations

**Local Mailbox** (project-specific):
```
.mailbox/
  inbox/           # received messages
  outbox/          # messages ready to send
  draft/           # messages being composed (not used in v1)
  sent/            # messages confirmed delivered
  archive/         # messages marked as processed
  config.yaml      # optional local overrides
```

**Shared Mailbox** (global transport):
```
~/.mailbox/                    # default; configurable via MAILBOX_SHARED or config
  shared/
    outbox/                    # global message exchange point
  config.yaml                  # system-wide defaults
```

### 2.3 Configuration

**Files (priority order)**:
1. Environment variables: `MAILBOX_*`
2. Local config: `.mailbox/config.yaml`
3. Global config: `~/.mailbox/config.yaml`
4. Defaults (hardcoded)

**Config example** (`.mailbox/config.yaml`):
```yaml
agent_id: my-agent
shared_mailbox_path: ~/Documents/shared-mailbox
polling_interval: 10
```

---

## 3. Message Lifecycle & State Transitions

### 3.1 States

| State   | Location                    | Description                        |
| ------- | --------------------------- | ---------------------------------- |
| Outbox  | `.mailbox/outbox`           | Ready to send                      |
| Shared  | `~/.mailbox/shared/outbox`  | Global exchange point              |
| Inbox   | `.mailbox/inbox`            | Received (unread by default)       |
| Sent    | `.mailbox/sent`             | Delivered                          |
| Archive | `.mailbox/archive`          | Marked as processed/read           |

### 3.2 Transitions

```
Agent1 creates message
  ↓
.mailbox/outbox (Agent1)
  ↓
mailbox send (or automatic)
  ↓
~/.mailbox/shared/outbox (global)
  ↓
mailbox sync (Agent2)
  ↓
.mailbox/inbox (Agent2)
  ↓
mailbox read or mailbox archive
  ↓
.mailbox/archive (Agent2)
```

### 3.3 Key Behaviors

- **send**: Creates message in outbox. Optional auto-sync.
- **list**: Shows inbox messages. Does NOT mark as read.
- **read**: Displays message content. Marks message as read by moving to archive.
- **archive**: Explicitly moves message from inbox to archive.
- **sync**:
  - **Push**: Copy from `.mailbox/outbox` → `~/.mailbox/shared/outbox`, then move originals to `.mailbox/sent`.
  - **Pull**: Copy from `~/.mailbox/shared/outbox` → `.mailbox/inbox` if `to` matches agent ID. Skip if already in inbox (deduplicate by message ID). Delete pulled messages from shared outbox (v1 pragmatic cleanup for point-to-point messaging).

---

## 4. Message Format & Schema

### 4.1 File Naming

```
{timestamp}_{id}.md
```

Example: `20260415T223100Z_01HZX8KJ92F3Z7Q8A1B2C3D4E5.md`

Where:
- `{timestamp}` = ISO 8601 format `YYYYMMDDTHHMMSSZ`
- `{id}` = Unique ID (e.g., ULID or UUID)

Benefits: Sortable, glob-friendly, unique.

### 4.2 Message Structure

```markdown
---
id: 01HZX8KJ92F3Z7Q8A1B2C3D4E5
to: agent-reviewer
from: agent-worker
subject: PR needs validation
sent_at: 2026-04-15T22:31:00Z
received_at: null
read_at: null
correlation_id: task-12345
---

Hey,

I've completed the implementation for the task. Please review and validate.

- Worker
```

### 4.3 Required Fields

| Field          | Type       | Description                          |
| -------------- | ---------- | ------------------------------------ |
| `id`           | string     | Unique message ID                    |
| `to`           | string     | Recipient agent ID                   |
| `from`         | string     | Sender agent ID                      |
| `subject`      | string     | Message subject                      |
| `sent_at`      | ISO 8601   | When sent (UTC)                      |
| `received_at`  | ISO 8601   | When received by mailbox (pull time) |
| `read_at`      | ISO 8601   | When explicitly read (mark time)     |

### 4.4 Optional Fields

| Field              | Type   | Description           |
| ------------------ | ------ | --------------------- |
| `correlation_id`   | string | Thread/task grouping  |
| `priority`         | string | low/normal/high       |
| `tags`             | list   | Arbitrary tags        |
| `workflow_stage`   | string | Custom workflow state |

All fields after `---` are body (markdown).

---

## 5. CLI Specification

### 5.1 Entry Point

Single entry point: `mailbox`

### 5.2 Commands

#### `mailbox init`

Initialize local mailbox in `.mailbox/` folder.

```bash
mailbox init [--agent-id AGENT_ID]
```

**Behavior**:
- Create `.mailbox/inbox/`, `.mailbox/outbox/`, `.mailbox/sent/`, `.mailbox/archive/`
- Create `.mailbox/config.yaml` if `--agent-id` provided
- Print summary

#### `mailbox send`

Send a message.

```bash
mailbox send --to RECIPIENT --subject "..." [--body "..."] [--correlation-id "..."]
mailbox send --to RECIPIENT --subject "..." < message.txt
echo "message body" | mailbox send --to RECIPIENT --subject "..."
```

**Behavior**:
- Require `--to` and `--subject`
- If `--body` omitted, read from stdin
- Generate unique ID and timestamp
- Set `from` to agent ID
- Create file in `.mailbox/outbox/`
- Print file path
- Optionally auto-sync (configurable)

#### `mailbox list`

List inbox messages.

```bash
mailbox list [--limit 10] [--format json|text]
```

**Behavior**:
- List messages in `.mailbox/inbox/` (unread)
- Show: ID, from, subject, sent_at
- Do NOT mark as read
- Default: 10 most recent
- Output: human-readable or JSON

#### `mailbox read`

Read a message by ID.

```bash
mailbox read [--id ID]
mailbox read [--correlation-id CORR_ID]
```

**Behavior**:
- If `--id` provided, read that message
- If `--correlation-id` provided, list messages in that thread
- If neither provided, read first unread message
- Display full message (frontmatter + body)
- Move message from `.mailbox/inbox/` to `.mailbox/archive/`
- Update `read_at` timestamp

#### `mailbox archive`

Explicitly archive a message.

```bash
mailbox archive --id ID
```

**Behavior**:
- Move message from `.mailbox/inbox/` to `.mailbox/archive/`
- Update `read_at` if not already set

#### `mailbox sync`

Synchronize mailbox.

```bash
mailbox sync [--push-only] [--pull-only]
```

**Behavior**:
- **Push** (default): Copy `.mailbox/outbox/*` → `~/.mailbox/shared/outbox/`, then move originals to `.mailbox/sent/`
- **Pull** (default): Copy from `~/.mailbox/shared/outbox/*` → `.mailbox/inbox/` if `to` matches agent ID. Deduplicate by message ID. Delete pulled messages from shared outbox (v1 pragmatic cleanup for point-to-point messaging).
- `--push-only`: Skip pull
- `--pull-only`: Skip push
- Print summary: X messages pushed, Y messages pulled

#### `mailbox config`

Show or update configuration.

```bash
mailbox config [--list]
mailbox config --set agent_id VALUE
mailbox config --set shared_mailbox_path VALUE
```

#### `mailbox help`

Display help and version.

```bash
mailbox help
mailbox --version
```

### 5.3 Exit Codes

- `0`: Success
- `1`: General error
- `2`: Missing required argument
- `3`: Agent ID not found

---

## 6. Implementation Details

### 6.1 Package Structure

```
ainbox/
  __init__.py           # version
  __main__.py           # entry point
  cli.py                # command handlers
  mailbox.py            # core logic (init, send, list, read, archive, sync)
  config.py             # configuration loader
  message.py            # message parsing/serialization
  fileops.py            # atomic file operations
  util.py               # utilities (paths, ids, timestamps)
```

### 6.2 Key Implementation Points

**Atomic Writes**: Use `tempfile` + `os.replace()` for safety.

```python
import tempfile, os
# Write to temp file in same directory
with tempfile.NamedTemporaryFile(mode='w', dir=target_dir, delete=False) as f:
    f.write(content)
    temp_path = f.name
# Atomic replace
os.replace(temp_path, final_path)
```

**YAML Frontmatter Parsing**:
- Use `yaml.safe_load()` if available; otherwise simple regex split on `---`.
- Keep body as-is (preserve formatting).

**Path Normalization**:
- Use `pathlib.Path` for all paths.
- Expand `~` explicitly before storing.
- Normalize separators.

**ID Generation**:
- Use ULID (timestamp-based unique ID) or UUID4.
- Format as lowercase hex or ULID format.

**Timestamps**:
- ISO 8601 with UTC (e.g., `2026-04-15T22:31:00Z`).

### 6.3 Dependencies

**Preferred**: Stdlib only.

**If needed**:
- `PyYAML` (if parsing complex frontmatter; optional)
- `click` (if CLI becomes more complex; prefer `argparse` in v1)

### 6.4 Python Version

- Minimum: Python 3.8+
- No type hints required (but recommended for future).

---

## 7. Installability & Integration

### 7.1 Package Installation

```bash
pip install -e .
```

Creates `mailbox` command globally available.

### 7.2 Wrapper Scripts

Thin shells around the CLI for agent systems.

**scripts/mailbox.sh** (Bash/Linux/macOS):
```bash
#!/bin/bash
exec mailbox "$@"
```

**scripts/mailbox.ps1** (PowerShell/Windows):
```powershell
param([Parameter(ValueFromRemainingArguments=$true)] $Args)
mailbox @Args
```

**scripts/install.sh** (Linux/macOS):
```bash
pip install -e .
```

**scripts/install.ps1** (PowerShell/Windows):
```powershell
python -m pip install -e .
```

### 7.3 Agent Integration Files

**AGENTS.md**: Instructions for setup in Copilot CLI, Claude Code, etc.

**CLAUDE.md**: Claude-specific skills and setup.

**.claude/commands/mailbox-*.md**: Claude command definitions.

**.copilot/skills/*.md**: Copilot CLI skill definitions.

These are instruction files (not code) that teach agents how to use the mailbox CLI.

---

## 8. Phase 1 Scope (v1.0)

### 8.1 Deliverables

1. ✅ Python package (`ainbox/`)
2. ✅ CLI entry point (`mailbox` command)
3. ✅ Commands: `init`, `send`, `list`, `read`, `archive`, `sync`, `config`, `help`
4. ✅ Message format (markdown + frontmatter)
5. ✅ Folder structure (`.mailbox/inbox/`, `.mailbox/outbox/`, etc.)
6. ✅ Wrapper scripts (`.sh` and `.ps1`)
7. ✅ Integration files (AGENTS.md, CLAUDE.md, etc.)
8. ✅ README (installation + usage)
9. ✅ .gitignore (for `.mailbox/` artifacts)

### 8.2 NOT in Scope (v1)

- Broadcast/group messaging
- Message encryption or signing
- File attachments
- Real-time FS watchers
- Pre-turn hooks (handled externally via skills)
- UI/visualization
- Database indexing
- Message search

---

## 9. Testing Strategy

**Unit tests** (minimal, focused on new behavior):
- Message serialization/deserialization
- Path resolution
- ID generation
- Timestamp handling
- Config loading

**Integration tests** (optional in v1):
- End-to-end send/sync/read flow
- Multi-agent scenario (two local mailboxes)

**Manual validation**:
- Run CLI commands to verify basic flow works
- Test on Windows, macOS, Linux if possible

**No external test framework required** unless scope demands it.

---

## 10. Success Criteria

1. ✅ `pip install -e .` succeeds
2. ✅ `mailbox` command is available globally
3. ✅ `mailbox init` creates folder structure
4. ✅ `mailbox send` creates message file in outbox
5. ✅ `mailbox list` displays inbox messages
6. ✅ `mailbox read` displays and archives message
7. ✅ `mailbox sync` pushes/pulls messages correctly
8. ✅ Wrapper scripts work on Windows (PowerShell) and Unix (Bash)
9. ✅ Integration files are present and clear
10. ✅ README explains installation and basic usage

---

## 11. Roadmap (Future Phases)

**Phase 2**:
- Pre-turn hooks for Claude/Copilot
- Message search
- Batch operations

**Phase 3**:
- Message encryption (optional)
- Real-time watchers
- UI viewer

**Phase 4**:
- Broadcast messaging
- Group conversations
- Workflow orchestration

---

## 12. Summary

AInbox delivers a minimal, working filesystem-based mailbox for agents. It's installable via pip, accessible via CLI, and integrable into any agent system via skills and scripts. Phase 1 focuses on core messaging only—enough to enable decentralized agent coordination without complexity.
