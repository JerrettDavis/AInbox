# Skill: Mailbox Basics

## Overview

Understanding the mailbox system and how it enables decentralized agent communication.

## What is AInbox?

AInbox is a **filesystem-based async mailbox** for agents. It allows agents to communicate without a central broker or orchestrator. Messages are stored as markdown files in standardized folders.

### Key Concepts

1. **Decentralized**: No central service. Agents operate independently and poll for messages.
2. **File-based**: Filesystem is the transport layer. Messages are simple markdown files.
3. **Async**: Agents don't need to be running at the same time. They sync when ready.
4. **Convention-based**: Standard folder structure and message format make coordination predictable.

## Folder Structure

Each agent has a local mailbox in `.mailbox/`:

```
.mailbox/
  inbox/        – Received messages (ready to read)
  outbox/       – Messages you've created (ready to send)
  sent/         – Messages you've sent (after sync and recipient read)
  archive/      – Messages you've read (processed)
  draft/        – Messages being composed (not used yet)
```

Plus a shared mailbox (default: `~/.mailbox/shared/outbox`):

```
~/.mailbox/shared/outbox/
                        – Global exchange point (all agents can see)
```

## Message Lifecycle

1. **Create**: You write a message with `mailbox send`
2. **Outbox**: Message sits in `.mailbox/outbox/` (local only)
3. **Sync Push**: You call `mailbox sync` to push to shared outbox
4. **Shared**: Message is now in `~/.mailbox/shared/outbox/` (visible to all)
5. **Sync Pull**: Recipient calls `mailbox sync` to pull into their inbox
6. **Inbox**: Message is now in recipient's `.mailbox/inbox/` (ready to read)
7. **Read**: Recipient calls `mailbox read` to view and archive
8. **Archive**: Message moved to `.mailbox/archive/` (marked as processed)

## Message Format

All messages are markdown files with YAML frontmatter:

```markdown
---
id: 01HZX8KJ92F3Z7Q8A1B2C3D4E5
to: agent-reviewer
from: agent-worker
subject: PR needs validation
sent_at: 2026-04-15T22:31:00Z
received_at: 2026-04-15T22:32:00Z
read_at: null
correlation_id: task-12345
---

Message body in markdown.

Can include multiple lines, formatting, etc.
```

**Key fields**:
- `id` – Unique message identifier
- `to` – Recipient agent ID
- `from` – Sender agent ID
- `subject` – Subject line
- `sent_at` – When sent (ISO 8601 UTC)
- `received_at` – When pulled into inbox (auto-set by system)
- `read_at` – When read (auto-set by system)
- `correlation_id` – Optional thread grouping

## Agent Identity

Each agent has an ID, resolved in order of priority:

1. `MAILBOX_AGENT_ID` environment variable
2. `agent_id` in `.mailbox/config.yaml`
3. `agent_id` in `~/.mailbox/config.yaml`
4. Current directory name

### Set Agent ID

```bash
# Temporary (for this session)
export MAILBOX_AGENT_ID=my-agent

# Permanent (local project)
echo "agent_id: my-agent" > .mailbox/config.yaml

# Permanent (global default)
echo "agent_id: my-agent" > ~/.mailbox/config.yaml
```

## Installation

```bash
# Install the package
pip install -e .

# Verify
mailbox --version
```

## First Steps

### Initialize Mailbox

```bash
mailbox init
```

Creates the folder structure.

### Send a Message

```bash
mailbox send --to reviewer-agent --subject "Code review needed" --body "Check my PR"
```

Creates a message in `.mailbox/outbox/`.

### Sync (Push)

```bash
mailbox sync
```

Pushes message to shared mailbox, moves original to sent folder.

### Recipient Syncs (Pull)

```bash
mailbox sync
```

Pulls messages from shared mailbox into inbox.

### List Inbox

```bash
mailbox list
```

Shows all messages in inbox (without marking as read).

### Read a Message

```bash
mailbox read --id <message-id>
```

Displays message content, moves to archive, sets read_at timestamp.

## Common Patterns

### Send and Forward

1. Send message: `mailbox send --to A --subject "..." --body "..."`
2. Sync: `mailbox sync` (push to shared)
3. Other agent syncs: `mailbox sync` (pull from shared)
4. Other agent reads: `mailbox read --id <id>`

### Thread-Based Conversation

Use `--correlation-id` to group related messages:

```bash
mailbox send --to agent-b --subject "Task update" --body "..." --correlation-id task-123
mailbox send --to agent-b --subject "Task update 2" --body "..." --correlation-id task-123
```

Recipient can identify related messages by correlation_id.

### One-Shot Sync During Task

In a workflow where agent A coordinates with B:

```bash
# Agent A
mailbox send --to B --subject "Start task" --body "..."
mailbox sync  # Push

# Agent B (polls periodically or on demand)
mailbox sync  # Pull
mailbox list
mailbox read --id <id>
# Do work
mailbox send --to A --subject "Task complete" --body "..."
mailbox sync  # Push

# Agent A
mailbox sync  # Pull
mailbox read --id <id>
```

## Design Philosophy

1. **Minimal**: Only essential commands (send, list, read, sync)
2. **Explicit**: No hidden background syncing; you control when to sync
3. **Inspectable**: All messages are readable markdown files
4. **Portable**: Works anywhere with a shared filesystem
5. **Failsafe**: Atomic file operations prevent corruption

## What's Not in Scope

- Broadcast/group messaging (v1 is point-to-point)
- Message encryption (future phase)
- Real-time notifications (async polling only)
- Web UI (CLI only)

## Next Steps

- [Read more about the architecture (PLAN.md)](./PLAN.md)
- [Learn how to integrate with Claude Code (CLAUDE.md)](./CLAUDE.md)
- [Learn how to integrate with Copilot CLI (AGENTS.md)](./AGENTS.md)
- Check `.claude/commands/` for Claude-specific command help
