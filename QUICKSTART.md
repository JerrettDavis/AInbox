# QUICKSTART.md – AInbox Quick Reference

## Installation (Pick One)

```bash
# Option 1: Direct pip install (all platforms)
pip install -e .

# Option 2: Bash (macOS/Linux)
bash scripts/install.sh

# Option 3: PowerShell (Windows)
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

## Set Your Agent Identity (Once)

```bash
export MAILBOX_AGENT_ID=my-agent
# or
echo "agent_id: my-agent" > ~/.mailbox/config.yaml
```

## Basic Workflow

### 1. Initialize (First Time)

```bash
mailbox init
# Creates: .mailbox/inbox, outbox, sent, archive, draft
```

### 2. Send a Message

```bash
mailbox send --to recipient-agent --subject "My message" --body "Hello!"

# Or pipe multi-line:
echo "Multi-line message body" | mailbox send --to recipient-agent --subject "..."
```

### 3. Sync to Push

```bash
mailbox sync
# Output: Sync complete: 1 pushed, 0 pulled
```

### 4. Recipient Pulls

```bash
mailbox sync
# Output: Sync complete: 0 pushed, 1 pulled
```

### 5. List Inbox

```bash
mailbox list
# Shows: ID, from, subject, sent timestamp
```

### 6. Read a Message

```bash
mailbox read --id MESSAGE_ID
# Message is automatically archived after reading
```

### 7. Send Reply

```bash
mailbox send --to original-sender --subject "RE: ..." --body "Your response"
mailbox sync  # Push reply
```

## All Commands

| Command | Purpose |
| --- | --- |
| `mailbox --version` | Show version |
| `mailbox init` | Initialize mailbox |
| `mailbox send --to X --subject "Y"` | Send message |
| `mailbox list [--limit 10]` | List inbox messages |
| `mailbox read [--id ID]` | Read and archive message |
| `mailbox archive --id ID` | Archive a message |
| `mailbox sync [--push-only\|--pull-only]` | Push/pull messages |
| `mailbox config --list` | Show agent ID and paths |
| `mailbox help` | Show help |

## Common Scenarios

### Send with Threading

```bash
# Start conversation
mailbox send --to agent --subject "Feature X" --body "..." --correlation-id feat-x

# Follow-up related message
mailbox send --to agent --subject "Feature X – update" --body "..." --correlation-id feat-x
```

### Read First Message

```bash
mailbox read  # No --id = reads first message
```

### List as JSON

```bash
mailbox list --format json
```

### Push Only (Don't Pull)

```bash
mailbox sync --push-only
```

### Pull Only (Don't Push)

```bash
mailbox sync --pull-only
```

## Troubleshooting

### "Agent ID not found"

```bash
export MAILBOX_AGENT_ID=my-agent
# or add to ~/.mailbox/config.yaml:
# agent_id: my-agent
```

### Message not received

1. Sender: `mailbox sync` (to push)
2. Recipient: `mailbox sync` (to pull)
3. Verify recipient ID is spelled correctly

### Already read a message by mistake

```bash
# Check archive
ls .mailbox/archive
```

## File Locations

- **Local mailbox**: `.mailbox/` (in current directory)
- **Shared mailbox**: `~/.mailbox/shared/outbox/` (home directory)
- **Config**: `~/.mailbox/config.yaml` (optional, global)

## Environment Variables

- `MAILBOX_AGENT_ID` – Your agent name (overrides config)
- `MAILBOX_SHARED` – Custom shared mailbox path (overrides default)

## Integration with Agents

### Claude Code

Commands available in `.claude/commands/`:
- `mailbox-read.md` – How to read messages
- `mailbox-send.md` – How to send messages
- `mailbox-sync.md` – How to sync

### Copilot CLI

Skills available in `.copilot/skills/`:
- `mailbox-basics.md` – Concepts and setup
- `mailbox-communication.md` – Communication patterns
- `mailbox-inbox-processing.md` – Managing inbox

## Tips

1. **Always sync after sending** – Messages won't reach recipients until you sync
2. **Sync before reading** – Pull latest messages with sync first
3. **Use correlation-id for threads** – Group related messages with `--correlation-id`
4. **Archives are automatic** – Reading a message moves it to `.mailbox/archive/`
5. **Multi-line bodies** – Use stdin with `|` or heredoc for complex content

## For Developers

### Test Locally

```bash
# Set agent ID
export MAILBOX_AGENT_ID=test-agent-1

# Initialize
mailbox init

# Send test message
mailbox send --to another-agent --subject "Test" --body "Hello"

# Sync
mailbox sync

# List
mailbox list
```

### Check Message Format

```bash
cat .mailbox/outbox/*.md
# Shows: frontmatter (YAML) + body (markdown)
```

### Debug Sync

```bash
ls ~/.mailbox/shared/outbox/  # See shared messages
ls .mailbox/sent/             # See sent messages
ls .mailbox/inbox/            # See inbox messages
ls .mailbox/archive/          # See read messages
```

## Next Steps

- [Read full README](README.md) for installation & usage
- [Read PLAN.md](PLAN.md) for architecture & design
- [Read AGENTS.md](AGENTS.md) for multi-agent coordination
- [Read CLAUDE.md](CLAUDE.md) for Claude Code setup
- [Read IMPLEMENTATION.md](IMPLEMENTATION.md) for technical details

---

**Questions?** Check the documentation or inspect `.mailbox/` folder structure directly (all messages are readable markdown).
