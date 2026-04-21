---
name: mailbox-basics
description: Explains the minimal AInbox mailbox flow for point-to-point agent messaging. Use when an agent needs to initialize a mailbox, send a message, sync it, and read replies without loading deeper coordination patterns.
---

Use AInbox when agents need lightweight, filesystem-based coordination.

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

## Reach for another skill when needed

- Use `mailbox-communication` for message-writing patterns and threading
- Use `mailbox-inbox-processing` for repeatable inbox triage loops

## Install prerequisite

```bash
pip install git+https://github.com/JerrettDavis/AInbox.git
```
