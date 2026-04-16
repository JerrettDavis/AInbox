# AInbox – Filesystem-Based Async Mailbox for Coding Agents

A minimal, cross-platform Python CLI and package that enables **decentralized agent communication** via structured markdown messages and a shared filesystem.

**No broker. No orchestrator. Just files and conventions.**

## Quick Start

### Installation

```bash
# Linux/macOS
bash scripts/install.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\install.ps1

# Or directly from the repo checkout
pip install -e .

# Or from GitHub
pip install git+https://github.com/JerrettDavis/AInbox.git
```

Verify:
```bash
mailbox --version
```

### Plugin Marketplace Installation

**Claude Code**

```bash
claude plugin marketplace add JerrettDavis/AInbox
claude plugin install ainbox@ainbox-marketplace
```

**GitHub Copilot CLI**

```bash
copilot plugin marketplace add JerrettDavis/AInbox
copilot plugin install ainbox@ainbox-marketplace
```

The marketplace installs the AInbox command/skill plugin metadata. Install the Python CLI as shown above so the `mailbox` executable is available on `PATH`.

### Basic Usage

```bash
# Initialize local mailbox
mailbox init

# Send a message to another agent
mailbox send --to reviewer-agent --subject "PR ready for review" --body "Please check my implementation."

# Or pipe the body
echo "Review this PR" | mailbox send --to reviewer-agent --subject "Code review needed"

# List inbox
mailbox list

# Read a message
mailbox read --id <message-id>

# Sync with shared mailbox (push local outbox, pull incoming)
mailbox sync
```

## Architecture

### Mailbox Folders

**Local (.mailbox/)**:
- `inbox/` – Received messages
- `outbox/` – Messages ready to send
- `sent/` – Delivered messages
- `archive/` – Read/processed messages

**Shared (~/.mailbox/shared/outbox)**:
- Global exchange point for all agents

### Message Format

Messages are markdown files with YAML frontmatter:

```markdown
---
id: abc123def456
to: reviewer-agent
from: worker-agent
subject: PR needs validation
sent_at: 2026-04-15T22:31:00Z
received_at: null
read_at: null
correlation_id: task-12345
---

I've completed the implementation. Please review and validate.

- Worker
```

**Frontmatter Field Constraints**:
- All string fields (id, to, from, subject, correlation_id) must be single-line
- Embedded newlines in frontmatter fields are rejected during message creation to prevent parsing corruption
- The message body (after the closing `---`) can contain multiple lines

### Workflow

1. **Send**: `mailbox send` → message in `.mailbox/outbox/`
2. **Sync (push)**: `mailbox sync` → copy to `~/.mailbox/shared/outbox/`, move original to `.mailbox/sent/`
3. **Sync (pull)**: `mailbox sync` → other agents pull from shared outbox into their `.mailbox/inbox/`
4. **Read**: `mailbox read --id <id>` → message moved to `.mailbox/archive/`, `read_at` updated

## Commands

| Command | Purpose |
| --- | --- |
| `mailbox init` | Initialize local mailbox |
| `mailbox send --to AGENT --subject "..."` | Create and send message |
| `mailbox list [--limit 10]` | List inbox messages (unread) |
| `mailbox read [--id ID]` | Read message and archive |
| `mailbox read --correlation-id THREAD_ID` | Read first message in thread |
| `mailbox archive --id ID` | Archive a message |
| `mailbox sync` | Push/pull messages |
| `mailbox config --list` | Show configuration |
| `mailbox help` | Show command help |

## Agent Identity

Agent ID is resolved in order:

1. `MAILBOX_AGENT_ID` environment variable
2. `agent_id` in `.mailbox/config.yaml` (local)
3. `agent_id` in `~/.mailbox/config.yaml` (global)
4. Current directory name

Set it once:
```bash
export MAILBOX_AGENT_ID=my-agent
# or
echo "agent_id: my-agent" > ~/.mailbox/config.yaml
```

## Integration with Coding Assistants

### Claude Code

See [CLAUDE.md](CLAUDE.md), `.claude-plugin/plugin.json`, and `.claude/commands/` for Claude-specific setup and plugin metadata.

### Copilot CLI

See [AGENTS.md](AGENTS.md), `.github/plugin/marketplace.json`, and `.github/plugin/plugin.json` for Copilot marketplace integration.

### Custom Agents

Wrapper scripts are provided:

```bash
# Linux/macOS
bash scripts/mailbox.sh send --to agent-id --subject "..."

# Windows (PowerShell)
powershell scripts\mailbox.ps1 send --to agent-id --subject "..."
```

Or simply use the `mailbox` command directly after installation.

## Configuration

**Local config** (`.mailbox/config.yaml`):
```yaml
agent_id: my-agent
shared_mailbox_path: ~/shared-mailbox  # Optional: override default shared mailbox location
```

**Global config** (`~/.mailbox/config.yaml`):
```yaml
agent_id: default-agent
shared_mailbox_path: ~/shared-mailbox  # Optional: override default shared mailbox location
```

**Environment variables**:
- `MAILBOX_AGENT_ID` – Agent identity (overrides config)
- `MAILBOX_SHARED` – Shared mailbox path (overrides config and default)

## Use Cases

- **Multi-agent workflows**: Agents coordinate without a central broker
- **Task handoff**: Worker completes task → sends message → reviewer receives and processes
- **Async coordination**: Agents poll at their own pace, no tight coupling
- **Debugging**: All communication is in plain markdown files, fully inspectable

## Roadmap

**v1.0** (current):
- Core messaging (send, read, sync)
- Markdown + frontmatter format
- File-based transport
- CLI + wrapper scripts

**v2.0**:
- Pre-turn hooks for agent systems
- Message search/indexing
- Batch operations

**v3.0**:
- Real-time watchers
- Optional message encryption
- Broadcast messaging

## For Developers

### Structure

```
ainbox/
  __init__.py       # Package metadata
  cli.py            # Command handlers
  mailbox.py        # Core operations (send, sync, etc.)
  message.py        # Message parsing/serialization
  util.py           # Paths, IDs, timestamps
setup.py            # Package configuration
scripts/            # Wrapper scripts (.sh, .ps1)
```

### Testing Locally

```bash
# Install in development mode
pip install -e .

# Create two test agents
MAILBOX_AGENT_ID=agent1 mailbox init
mkdir test2 && cd test2
MAILBOX_AGENT_ID=agent2 mailbox init
cd ..

# Send message from agent1 to agent2
MAILBOX_AGENT_ID=agent1 mailbox send --to agent2 --subject "Test" --body "Hello!"

# Sync (push from agent1)
MAILBOX_AGENT_ID=agent1 mailbox sync

# Sync (pull in agent2)
cd test2
MAILBOX_AGENT_ID=agent2 mailbox sync
mailbox list

# Read the message
mailbox read --id <id-from-list>
```

### Design Principles

- **Minimal dependencies**: Stdlib only where possible
- **Cross-platform**: Windows (PowerShell), macOS/Linux (Bash), all via Python pathlib
- **Atomic writes**: Temp file + `os.replace()` for robustness
- **Convention over config**: Standard folders, file naming, message schema
- **Pluggable**: Works with any agent system via skills and scripts

## License

MIT

## Contributing

Issues and pull requests welcome. Keep it minimal and focused on the core mailbox functionality.
