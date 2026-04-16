# Mailbox Basics

Use AInbox when you need lightweight, filesystem-based coordination between coding agents.

## What this skill gives you

- A shared mental model for `.mailbox/` folders and message flow
- The core commands to send, sync, list, and read messages
- A repeatable point-to-point workflow for agent handoff

## Core flow

```bash
mailbox init
mailbox send --to reviewer-agent --subject "PR ready" --body "Please review the latest changes."
mailbox sync
mailbox list
mailbox read --id <message-id>
```

## Lifecycle

1. `mailbox send` creates a markdown message in `.mailbox/outbox/`
2. `mailbox sync` pushes local outbox messages to the shared mailbox
3. The recipient runs `mailbox sync` to pull matching messages into `.mailbox/inbox/`
4. `mailbox read` prints the message, sets `read_at`, and archives it

## Important behavior

- `received_at` is set on pull, not on push
- v1 is point-to-point only; no broadcast or group delivery
- pulled messages are removed from the shared outbox after successful delivery
- frontmatter fields are single-line; the body can be multiline markdown

## Install prerequisite

The plugin distributes commands and skills. Install the CLI separately:

```bash
pip install git+https://github.com/JerrettDavis/AInbox.git
```
