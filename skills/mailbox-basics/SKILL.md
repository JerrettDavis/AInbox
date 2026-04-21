---
name: mailbox-basics
description: Explains the minimal AInbox mailbox flow for point-to-point agent messaging. Use when an agent needs to initialize a mailbox, send a message, sync it, and read replies without loading deeper coordination patterns.
---

Use AInbox when agents need lightweight, filesystem-based coordination.

## Preferred runtime

Use the latest native `mailbox` binary on `PATH`. Install the latest compiled release for your platform with:

```bash
# Linux/macOS from a local AInbox checkout (preferred safe helper)
source ./scripts/ensure-mailbox.sh

# Windows PowerShell from a local AInbox checkout
.\scripts\ensure-mailbox.ps1
```

These helpers install the latest native release only when `mailbox` is missing and make the install directory available in the current session.

## Start with the minimal loop

```bash
mailbox init
mailbox send --to reviewer-agent --subject "PR ready" --body "Please review the latest changes."
mailbox sync
mailbox read --id <message-id>
```

## Keep these rules in mind

- `mailbox send` writes to `.mailbox/outbox/`; nothing reaches another agent until `mailbox sync`
- `received_at` is set when the recipient pulls the message
- `mailbox read` prints the message, sets `read_at`, and archives it
- v1 is point-to-point only; there is no broadcast delivery

## Source checkout variations

If you are running from a repo checkout instead of the released binary:

```bash
# Rust CLI from source
cargo run -- init

# Python compatibility CLI from source
python -m ainbox.cli init
```

## Reach for another skill when needed

- Use `mailbox-communication` for message-writing patterns and threading
- Use `mailbox-inbox-processing` for repeatable inbox triage loops

## Fallback installs

```bash
# Remote Linux/macOS installer
curl -fsSL https://raw.githubusercontent.com/JerrettDavis/AInbox/main/scripts/install.sh | bash

# Remote Windows installer
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/JerrettDavis/AInbox/main/scripts/install.ps1 | iex"

# Rust native CLI from source
cargo install --path .

# Python compatibility CLI
pip install git+https://github.com/JerrettDavis/AInbox.git
```
