# AGENTS.md – Integration with GitHub Copilot CLI and Other Assistants

This document explains how to integrate AInbox with **GitHub Copilot CLI**, **Claude Code**, and other coding assistants.

## Overview

AInbox is agent-agnostic. It provides:

1. **CLI tool** (`mailbox` command) – The single source of truth
2. **Wrapper scripts** – Thin shells for each platform (Bash, PowerShell)
3. **Skills/Commands** – Instruction files teaching agents how to use the mailbox
4. **Config** – Environment variables and config files for agent identity

Each assistant system integrates via its own skill/command mechanism while calling the same underlying `mailbox` CLI.

## Copilot CLI

### Setup

1. Install AInbox:
   ```bash
   pip install -e .
   ```

   Or install directly from GitHub:
   ```bash
   pip install git+https://github.com/JerrettDavis/AInbox.git
   ```

2. Add the marketplace and install the plugin:
   ```bash
   copilot plugin marketplace add JerrettDavis/AInbox
   copilot plugin install ainbox@ainbox-marketplace
   ```

3. Add skills to your Copilot workspace:
   - `.copilot/skills/mailbox-basics.md`
   - `.copilot/skills/mailbox-communication.md`
   - `.copilot/skills/mailbox-inbox-processing.md`

4. Set agent identity:
   ```bash
   export MAILBOX_AGENT_ID=copilot-worker
   ```

### Included Subagents

Installing the core `ainbox` plugin also provides:

- `orchestrator` - mailbox-first coordinator that delegates work and runs elections when multiple agents need a leader
- `project-manager` - active leader that participates directly while routing most coordination through the mailbox

### Usage in Copilot

Once skills are registered, you can ask:

- "List my mailbox inbox"
- "Send a message to the reviewer asking for feedback"
- "Read my latest message"
- "Sync my mailbox"

The assistant will translate these into `mailbox` CLI commands.

### Skills

See `.copilot/skills/` for detailed skill definitions.

## Claude Code

### Setup

1. Install AInbox:
   ```bash
   pip install -e .
   ```

   Or install directly from GitHub:
   ```bash
   pip install git+https://github.com/JerrettDavis/AInbox.git
   ```

2. Add the marketplace and install the plugin:
   ```text
   /plugin marketplace add JerrettDavis/AInbox
   /plugin install ainbox@ainbox-marketplace
   ```

3. Add commands to your Claude workspace:
   - `.claude/commands/mailbox-read.md`
   - `.claude/commands/mailbox-send.md`
   - `.claude/commands/mailbox-sync.md`

4. Set agent identity:
   ```bash
   export MAILBOX_AGENT_ID=claude-reviewer
   ```

### Included Subagents

Installing the core `ainbox` plugin also provides:

- `orchestrator` - orchestration-only coordinator that delegates through subagents and mailbox workflows
- `project-manager` - active leader that helps directly while keeping multi-agent coordination organized through AInbox

### Usage in Claude

Once commands are registered, Claude can:

- Execute `mailbox list` to see inbox messages
- Execute `mailbox read --id <id>` to read a message
- Execute `mailbox send --to <agent> --subject "..." --body "..."` to send messages
- Execute `mailbox sync` to push/pull messages

## Custom Agents

For any other agent system:

1. Ensure the `mailbox` command is in PATH:
   ```bash
   pip install -e .
   ```

2. Pass agent identity via environment variable:
   ```bash
   export MAILBOX_AGENT_ID=my-custom-agent
   ```

3. Call the CLI directly:
   ```bash
   mailbox list
   mailbox send --to recipient --subject "..." --body "..."
   mailbox read --id <id>
   mailbox sync
   ```

## Multi-Agent Scenario

Here's how two agents coordinate:

### Agent 1 (Worker)

```bash
export MAILBOX_AGENT_ID=worker
mailbox init
mailbox send --to reviewer --subject "Code review needed" --body "I've completed the implementation."
mailbox sync  # Push message to shared mailbox
```

### Agent 2 (Reviewer)

```bash
export MAILBOX_AGENT_ID=reviewer
mailbox init
mailbox sync  # Pull messages from shared mailbox
mailbox list  # See worker's message
mailbox read --id <id>  # Read and archive the message
# Compose a reply
mailbox send --to worker --subject "Review complete" --body "Looks good, merging now."
mailbox sync  # Push reply to shared mailbox
```

### Agent 1 (Worker) – Again

```bash
mailbox sync  # Pull reviewer's reply
mailbox list  # See the reply
mailbox read --id <id>  # Read and archive
```

## Configuration Files

### Local Config (`.mailbox/config.yaml`)

```yaml
agent_id: my-agent
```

### Global Config (`~/.mailbox/config.yaml`)

```yaml
agent_id: default-agent
shared_mailbox_path: /path/to/shared/mailbox
```

### Environment Variables

Priority (highest to lowest):

1. `MAILBOX_AGENT_ID` – Agent identity
2. `MAILBOX_SHARED` – Shared mailbox path
3. Config files
4. Defaults

## Message Anatomy

All messages are markdown files in `.mailbox/` folders:

```markdown
---
id: unique-id
to: recipient-agent
from: sender-agent
subject: Message title
sent_at: 2026-04-15T22:31:00Z
received_at: 2026-04-15T22:32:00Z (set on pull)
read_at: 2026-04-15T22:35:00Z (set on read)
correlation_id: optional-thread-id
---

Message body in markdown format.

Can be multi-line.
```

Fields:
- `id` – Unique message ID (generated)
- `to` – Recipient agent ID
- `from` – Sender agent ID
- `subject` – Subject line
- `sent_at` – ISO 8601 timestamp (UTC)
- `received_at` – When pulled (set by system)
- `read_at` – When read (set by system)
- `correlation_id` – Optional grouping (for threading)

## Tips for Agent Integration

1. **List before read**: Always call `mailbox list` first to see message IDs, then `mailbox read --id <id>` to read specific messages.

2. **Sync regularly**: Call `mailbox sync` before listing and after sending to ensure messages are propagated.

3. **Set agent ID early**: Do this once per session. The identity is then cached or used from env/config.

4. **Handle stdin**: The `--body` parameter can be omitted to read from stdin:
   ```bash
   echo "Compose message body" | mailbox send --to agent-id --subject "..."
   ```

5. **JSON output**: Use `mailbox list --format json` for machine-readable inbox (useful for structured processing).

## Troubleshooting

### "Agent ID not found"

Set `MAILBOX_AGENT_ID`:
```bash
export MAILBOX_AGENT_ID=my-agent
```

Or add to `~/.mailbox/config.yaml`:
```yaml
agent_id: my-agent
```

### Messages not appearing in recipient inbox

1. Sender must run `mailbox sync` (pushes outbox to shared)
2. Recipient must run `mailbox sync` (pulls from shared into inbox)
3. Check that recipient ID in message matches recipient's agent ID
4. Verify shared mailbox path is correct (defaults to `~/.mailbox/shared`)

### File permission errors

Ensure write access to:
- `.mailbox/` (local mailbox)
- `~/.mailbox/` (shared mailbox)

## Next Steps

- See [CLAUDE.md](CLAUDE.md) for Claude-specific setup
- See [PLAN.md](PLAN.md) for detailed architecture
- See `.copilot/skills/` for Copilot skill definitions
- See `.claude/commands/` for Claude command definitions
