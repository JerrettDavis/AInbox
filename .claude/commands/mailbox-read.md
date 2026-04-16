# Claude Command: Mailbox Read

## Description

Read a message from the mailbox inbox. This retrieves a message by ID and marks it as read by moving it to the archive folder.

## When to Use

- You want to read a specific message
- You want to view the full content of a message (not just the subject/preview)
- You want to mark a message as processed

## Command

```bash
mailbox read [--id MESSAGE_ID]
```

## Options

- `--id MESSAGE_ID` – Read message with this ID. If omitted, reads the first (oldest) unread message.

## Prerequisites

- AInbox must be installed: `pip install -e .`
- Local mailbox must be initialized: `mailbox init`
- Agent ID must be set (via env var, config, or directory name)

## Example

### List inbox first to get message ID

```bash
$ mailbox list
Inbox: 2 message(s)

1. From: worker-agent
   Subject: PR needs review
   ID: abc123def456
   Sent: 2026-04-15T22:31:00Z

2. From: coordinator
   ...
```

### Read the message

```bash
$ mailbox read --id abc123def456
---
id: abc123def456
to: my-agent
from: worker-agent
subject: PR needs review
sent_at: 2026-04-15T22:31:00Z
received_at: 2026-04-15T22:32:00Z
read_at: 2026-04-15T22:35:00Z
---

I've completed the implementation. Please review the PR.

Thanks!
- Worker
```

### Or read the first message

```bash
$ mailbox read
```

## Effects

- Message is moved from `.mailbox/inbox/` to `.mailbox/archive/`
- `read_at` timestamp is updated in the message
- Message is no longer listed in `mailbox list` (which only shows inbox)

## Output Format

Full markdown document with frontmatter and body:

```markdown
---
id: message-id
to: recipient
from: sender
subject: ...
sent_at: ...
received_at: ...
read_at: ...
correlation_id: optional
---

Message body in markdown.

Can be multi-line.
```

## Exit Codes

- `0` – Success
- `1` – Message not found
- `3` – Agent ID not found

## Related Commands

- `mailbox list` – List inbox messages (without reading)
- `mailbox archive --id <id>` – Archive without reading
- `mailbox send` – Send a message
