# Claude Command: Mailbox Send

## Description

Send a message to another agent via the mailbox system. The message is created in the outbox and ready to be synced to the shared mailbox.

## When to Use

- You want to communicate with another agent
- You need to send task updates or requests
- You want to respond to a message

## Command

```bash
mailbox send --to RECIPIENT_ID --subject "SUBJECT" [--body "BODY"] [--correlation-id "THREAD_ID"]
```

## Options

- `--to RECIPIENT_ID` – **Required**. Agent ID of the recipient.
- `--subject "SUBJECT"` – **Required**. Message subject line.
- `--body "BODY"` – Optional. Message body. If omitted or set to `-`, reads from stdin.
- `--correlation-id "THREAD_ID"` – Optional. Correlation ID for threading/grouping related messages.

## Prerequisites

- AInbox must be installed: `pip install -e .`
- Local mailbox must be initialized: `mailbox init`
- Agent ID must be set (via env var, config, or directory name)

## Examples

### Simple message

```bash
mailbox send --to reviewer --subject "Code review needed" --body "Please review my implementation."
```

### Message with stdin (multi-line)

```bash
cat <<EOF | mailbox send --to reviewer --subject "Implementation details"
I've completed the feature with the following approach:

1. Added validation to input handler
2. Integrated error handling for edge cases
3. Updated tests for new functionality

Please review at your convenience.
EOF
```

### Message with correlation ID (for threading)

```bash
mailbox send --to worker --subject "Re: Implementation status" \
  --body "Looks great! Ready to deploy." \
  --correlation-id task-12345
```

## Effects

- Message is created in `.mailbox/outbox/` with unique filename
- Message is NOT immediately visible to recipient
- **Must call `mailbox sync` to push to shared mailbox** (then recipient pulls it)

## Output

```
Message created: .mailbox/outbox/20260415T223100Z_abc123def456.md
```

## Exit Codes

- `0` – Success
- `1` – General error
- `2` – Missing required argument (`--to` or `--subject`)
- `3` – Agent ID not found

## Message Format

Messages are stored as markdown with YAML frontmatter:

```markdown
---
id: unique-id
to: recipient-agent
from: sender-agent
subject: Your subject
sent_at: 2026-04-15T22:31:00Z
received_at: null
read_at: null
correlation_id: optional-thread-id
---

Your message body here.
```

## Related Commands

- `mailbox sync` – **Must run this after sending to push message to shared mailbox**
- `mailbox read --id <id>` – Read a received message
- `mailbox list` – List inbox messages

## Tips

1. **Always sync after sending**: The message won't reach the recipient until you run `mailbox sync`
2. **Use correlation_id for threads**: Group related messages with the same correlation_id
3. **Compose carefully**: Messages are stored as-is; no editing after send
4. **Multi-line body**: Use stdin with `|` or heredoc for complex messages

## Troubleshooting

### "Agent ID not found"

Set agent ID:
```bash
export MAILBOX_AGENT_ID=my-agent
```

### Recipient doesn't see message

1. Did you run `mailbox sync` after sending? (Required to push to shared mailbox)
2. Did recipient run `mailbox sync`? (Required to pull from shared mailbox)
3. Is the recipient ID spelled correctly?
