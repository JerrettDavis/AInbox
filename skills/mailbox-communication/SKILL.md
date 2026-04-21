---
name: mailbox-communication
description: Guides structured async communication through AInbox. Use when agents need to send clear requests, status updates, or replies and want lightweight threading with shared correlation IDs.
---

Use this skill when agents need structured async coordination.

## Prefer this message shape

- clear subject line
- one explicit next action for the recipient
- shared `--correlation-id` for related updates

## Minimal pattern

```bash
mailbox send --to worker --subject "Task assignment: parser cleanup" \
  --body "Please harden frontmatter parsing and report back." \
  --correlation-id parser-fix
mailbox sync
```

## When the conversation continues

- reuse the same correlation ID for replies in the same thread
- sync after sending and before checking inbox
- keep subjects short; put detail in the body

## Install prerequisite

```bash
pip install git+https://github.com/JerrettDavis/AInbox.git
```
