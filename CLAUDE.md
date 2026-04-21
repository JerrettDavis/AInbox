# CLAUDE.md – Claude Code Integration

This document explains how to use AInbox with Claude Code.

## Quick Setup

1. **Install AInbox**:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/JerrettDavis/AInbox/main/scripts/install.sh | bash
   ```

   Or from a local AInbox checkout, prefer the safe ensure helpers:
   ```bash
   source ./scripts/ensure-mailbox.sh
   # Windows PowerShell: .\scripts\ensure-mailbox.ps1
   ```

   Or install a specific native release:
   ```bash
   AINBOX_VERSION=vX.Y.Z curl -fsSL https://raw.githubusercontent.com/JerrettDavis/AInbox/main/scripts/install.sh | bash
   ```

   Or use the Python compatibility path:
   ```bash
   pip install git+https://github.com/JerrettDavis/AInbox.git
   ```

2. **Install the marketplace plugin**:
   ```text
   /plugin marketplace add JerrettDavis/AInbox
   /plugin install ainbox@ainbox-marketplace
   ```

   Or, after the native `mailbox` CLI is installed, let AInbox refresh the supported global agent integrations for you:
   ```bash
   mailbox init -g
   ```

3. **Set your agent identity** (do this once):
   ```bash
   export MAILBOX_AGENT_ID=claude-agent
   ```

4. **Initialize mailbox** (first time in a project):
   ```bash
   mailbox init
   ```

## Using AInbox in Claude

Claude can invoke mailbox commands directly. Here are common patterns:

### List Inbox

Ask Claude: "Show me my mailbox inbox"

Claude will execute:
```bash
mailbox list
```

Output:
```
Inbox: 2 message(s)

1. From: worker-agent
   Subject: PR ready for review
   ID: abc123
   Sent: 2026-04-15T22:31:00Z

2. From: coordinator
   Subject: Task assignment
   ID: def456
   Sent: 2026-04-15T22:00:00Z
```

### Read a Message

Ask Claude: "Read message abc123"

Claude will execute:
```bash
mailbox read --id abc123
```

Output:
```markdown
---
id: abc123
to: claude-agent
from: worker-agent
subject: PR ready for review
sent_at: 2026-04-15T22:31:00Z
received_at: 2026-04-15T22:32:00Z
read_at: 2026-04-15T22:35:00Z
---

Hey Claude,

I've completed the implementation for the feature. Could you review the PR and give feedback?

Thanks!
- Worker
```

### Send a Message

Ask Claude: "Send a message to the worker saying the PR looks good"

Claude will execute:
```bash
mailbox send --to worker-agent --subject "PR Review Complete" --body "Looks great! PR approved and ready to merge."
```

Output:
```
Message created: .mailbox/outbox/20260415T223500Z_abc123.md
```

### Sync Mailbox

Ask Claude: "Sync my mailbox"

Claude will execute:
```bash
mailbox sync
```

Output:
```
Sync complete: 1 pushed, 1 pulled
```

## Claude Commands

Commands are defined in `.claude/commands/`:

- `mailbox-read.md` – How to read messages
- `mailbox-send.md` – How to send messages
- `mailbox-sync.md` – How to sync mailbox

Each command file contains:
- Description of what the command does
- When to use it
- Example invocations
- Expected output

See the files for details.

## Running Claude with AInbox subagents

If you want to enforce mailbox-aware orchestration instead of relying on the default agent, launch Claude Code with the AInbox agent explicitly selected:

```bash
claude --agent ainbox:orchestrator "Coordinate this task through mailbox-aware subagents and synthesize the result."
claude --agent ainbox:project-manager "Lead this task with mailbox coordination and delegate bounded work."
```

Use `ainbox:orchestrator` when you want delegation-first coordination and synthesized results. Use `ainbox:project-manager` when you want an active leader that still keeps most coordination flowing through AInbox.

## Multi-Agent Workflow Example

### Scenario

You're Claude, and you're working with a worker agent.

### Step 1: Check Inbox

You: "Show me my mailbox"

Claude executes `mailbox list`:
```
Inbox: 1 message(s)

1. From: worker-agent
   Subject: Implementation ready
   ...
```

### Step 2: Read the Message

You: "Read that message"

Claude executes `mailbox read --id <id>`:
```markdown
---
...
---

I've completed the implementation for feature X. Please review and test.
```

### Step 3: Respond

You: "Send a reply asking for more details on error handling"

Claude executes `mailbox send --to worker-agent --subject "Implementation review" --body "Can you clarify how errors are handled in the retry logic?"`:
```
Message created: .mailbox/outbox/...
```

### Step 4: Sync to Push

You: "Sync my mailbox to send the reply"

Claude executes `mailbox sync`:
```
Sync complete: 1 pushed, 0 pulled
```

The worker agent can now pull the reply with their own `mailbox sync`.

## Tips & Patterns

### Compose Multi-Line Messages

Ask Claude: "Compose a detailed message to the reviewer about the implementation approach"

Claude will write a message with proper formatting and send it:
```bash
mailbox send --to reviewer --subject "Implementation Approach" --body "..."
```

### Handle Correlations

Use `--correlation-id` to group related messages:
```bash
mailbox send --to agent --subject "Task update" --body "..." --correlation-id task-12345
```

This groups messages by task, making conversation threads traceable.

### Filter by Sender

Ask Claude: "Show me messages from worker-agent"

Claude will parse `mailbox list` output and filter:
```bash
mailbox list | grep "worker-agent"
```

### Check Message Status

Ask Claude: "Are there unread messages?"

Claude will check the inbox:
```bash
mailbox list --limit 20 | grep "From:"
```

## Troubleshooting

### "mailbox: command not found"

Install or expose the native CLI:
```bash
source ./scripts/ensure-mailbox.sh
# Windows PowerShell: .\scripts\ensure-mailbox.ps1
# Or use the remote installers from the quick setup section above
```

### "Agent ID not found"

Set the environment variable:
```bash
export MAILBOX_AGENT_ID=my-agent
```

Or add to `~/.mailbox/config.yaml`:
```yaml
agent_id: my-agent
```

### Messages not appearing after sync

1. Did you run `mailbox sync` after sending? (Needed to push to shared mailbox)
2. Did the recipient run `mailbox sync`? (Needed to pull from shared mailbox)
3. Is the recipient ID correct in the message?

## Next Steps

- See [AGENTS.md](AGENTS.md) for multi-agent coordination patterns
- See [README.md](README.md) for the consolidated architecture and installation overview
- See `.claude/commands/` for command definitions
