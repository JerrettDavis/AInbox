# INDEX – AInbox Repository Guide

Welcome to **AInbox**, a filesystem-based async mailbox for coding agents.

This guide helps you navigate the repository.

---

## 🚀 Quick Start (5 minutes)

1. **New to AInbox?** → Read [QUICKSTART.md](QUICKSTART.md)
2. **Want to install?** → Read [README.md](README.md)
3. **Ready to use?** → Run: `mailbox --version`

---

## 📚 Documentation by Role

### For End Users

- **[QUICKSTART.md](QUICKSTART.md)** (5 min)
  - Common commands
  - Basic workflow
  - Troubleshooting quick tips

- **[README.md](README.md)** (15 min)
  - Complete installation guide
  - All commands with examples
  - Multi-agent scenarios
  - Integration with assistants

### For Multi-Agent Coordination

- **[AGENTS.md](AGENTS.md)** (20 min)
  - How agents coordinate
  - Multi-agent patterns
  - Configuration for different agent systems
  - Troubleshooting multi-agent issues

### For Claude Code Users

- **[CLAUDE.md](CLAUDE.md)** (10 min)
  - Claude-specific setup
  - How Claude can use mailbox
  - Example workflows
  - Command reference

### For Developers & Architects

- **[PLAN.md](PLAN.md)** (30 min)
  - Complete engineering specification
  - Architecture & design decisions
  - Configuration system
  - Message format details
  - Sync mechanism
  - Roadmap

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** (30 min)
  - Technical implementation details
  - Code structure
  - Design tradeoffs
  - Testing & validation
  - Known limitations

- **[DELIVERY.md](DELIVERY.md)** (15 min)
  - Summary of what was delivered
  - Feature checklist
  - Design highlights
  - Validation results

---

## 📂 Repository Structure

### Documentation Files

```
QUICKSTART.md        ← Start here (quick reference)
README.md            ← Installation & usage
PLAN.md              ← Architecture & specification
AGENTS.md            ← Multi-agent coordination
CLAUDE.md            ← Claude Code integration
IMPLEMENTATION.md    ← Technical details
DELIVERY.md          ← What was delivered
INDEX.md             ← This file
```

### Code

```
ainbox/              # Main Python package
├── __init__.py      # Package metadata
├── cli.py           # 8 CLI commands
├── mailbox.py       # Core operations
├── message.py       # Message parsing
└── util.py          # Utilities & config

setup.py             # Package setup for pip
```

### Integration & Installation

```
scripts/
├── install.sh       # Bash installer (Linux/macOS)
├── install.ps1      # PowerShell installer (Windows)
├── mailbox.sh       # Bash wrapper
└── mailbox.ps1      # PowerShell wrapper

.claude/commands/
├── mailbox-read.md
├── mailbox-send.md
└── mailbox-sync.md

.copilot/skills/
├── mailbox-basics.md
├── mailbox-communication.md
└── mailbox-inbox-processing.md

.gitignore           # Git ignore rules
```

---

## 🎯 Common Tasks

### I want to...

**...understand what AInbox is**
→ Read: [PLAN.md](PLAN.md) "1. Purpose" section (5 min)

**...install AInbox**
→ Read: [README.md](README.md) "Quick Start" section (5 min)

**...use mailbox from command line**
→ Read: [QUICKSTART.md](QUICKSTART.md) (5 min)

**...send a message to another agent**
→ Read: [QUICKSTART.md](QUICKSTART.md) "Basic Workflow" section

**...set up multi-agent coordination**
→ Read: [AGENTS.md](AGENTS.md) "Multi-Agent Scenario" section

**...use mailbox with Claude Code**
→ Read: [CLAUDE.md](CLAUDE.md) (10 min)

**...use mailbox with Copilot CLI**
→ Read: [AGENTS.md](AGENTS.md) "Copilot CLI" section

**...understand the architecture**
→ Read: [PLAN.md](PLAN.md) "2-4. Architecture sections" (15 min)

**...troubleshoot an issue**
→ Read: [QUICKSTART.md](QUICKSTART.md) "Troubleshooting" section
or [AGENTS.md](AGENTS.md) "Troubleshooting" section

**...see what was delivered**
→ Read: [DELIVERY.md](DELIVERY.md) (10 min)

---

## 📖 Reading Paths by Audience

### New User (15 minutes)

1. [QUICKSTART.md](QUICKSTART.md) – Installation & basic commands
2. [README.md](README.md) – Detailed usage
3. Try it: `mailbox init && mailbox send --to agent --subject "test" --body "hello"`

### Agent Developer (30 minutes)

1. [README.md](README.md) – Overview
2. [AGENTS.md](AGENTS.md) – How agents coordinate
3. [PLAN.md](PLAN.md) – Architecture (sections 2-5)
4. Check: `.claude/commands/` or `.copilot/skills/` for your agent type

### System Architect (1 hour)

1. [PLAN.md](PLAN.md) – Full specification
2. [IMPLEMENTATION.md](IMPLEMENTATION.md) – Technical details & tradeoffs
3. [DELIVERY.md](DELIVERY.md) – What was delivered & validation
4. Review: `ainbox/` code structure

### DevOps / Infrastructure (30 minutes)

1. [README.md](README.md) – Installation section
2. [scripts/](scripts/) – Review installer & wrapper scripts
3. [AGENTS.md](AGENTS.md) – Configuration & environment variables
4. Plan: How to distribute `mailbox` command to your agents

---

## 🔍 Key Concepts

### Message

A markdown file with YAML frontmatter (metadata) and body (content).

```markdown
---
id: unique-id
to: recipient-agent
from: sender-agent
subject: Message title
sent_at: ISO-8601-timestamp
---

Message body in markdown.
```

**Files**: `.mailbox/inbox/`, `.mailbox/outbox/`, `.mailbox/sent/`, `.mailbox/archive/`

### Sync

Two-phase operation:
- **Push**: Copy `.mailbox/outbox/` → `~/.mailbox/shared/outbox/`
- **Pull**: Copy `~/.mailbox/shared/outbox/` → `.mailbox/inbox/` (if addressed to you)

### Agent ID

Unique identifier for each agent. Resolved from (in order):
1. `MAILBOX_AGENT_ID` environment variable
2. `agent_id` in `.mailbox/config.yaml` (local)
3. `agent_id` in `~/.mailbox/config.yaml` (global)
4. Current directory name

### Shared Mailbox

Default location: `~/.mailbox/shared/outbox/`

Global exchange point where all agents can access messages.

---

## 🛠 Available Commands

All commands start with `mailbox`:

```
mailbox --version              # Show version
mailbox init                   # Initialize mailbox
mailbox send                   # Send message
mailbox list                   # List inbox
mailbox read                   # Read message
mailbox archive                # Archive message
mailbox sync                   # Sync (push/pull)
mailbox config                 # Show config
mailbox help                   # Show help
```

See: [QUICKSTART.md](QUICKSTART.md) or [README.md](README.md) for details.

---

## ✅ What's Included

- ✅ Complete Python package (stdlib-only, no dependencies)
- ✅ CLI tool with 8 commands
- ✅ Message format (markdown + YAML frontmatter)
- ✅ Sync mechanism (push/pull with deduplication)
- ✅ Cross-platform support (Windows, macOS, Linux)
- ✅ Integration files (Claude, Copilot)
- ✅ Comprehensive documentation (~50 KB markdown)
- ✅ Installation scripts (Bash & PowerShell)
- ✅ End-to-end validation (tested multi-agent workflow)

---

## ⏭ Next Steps

1. **Install**: Follow [README.md](README.md) installation section
2. **Learn**: Read [QUICKSTART.md](QUICKSTART.md)
3. **Try**: Run `mailbox init` and send a test message
4. **Integrate**: See [CLAUDE.md](CLAUDE.md) or [AGENTS.md](AGENTS.md) for your agent system
5. **Explore**: Check out the code in `ainbox/` for details

---

## 📞 Getting Help

- **"How do I...?"** → Check [QUICKSTART.md](QUICKSTART.md) or [README.md](README.md)
- **"Why is this...?"** → Check [PLAN.md](PLAN.md) or [IMPLEMENTATION.md](IMPLEMENTATION.md)
- **"How do agents coordinate?"** → Check [AGENTS.md](AGENTS.md)
- **"How do I use with Claude?"** → Check [CLAUDE.md](CLAUDE.md)
- **"Something doesn't work"** → Check Troubleshooting sections in docs

---

**Welcome to AInbox!** 🚀

Start with [QUICKSTART.md](QUICKSTART.md) or jump straight to the docs you need above.

Happy messaging!
