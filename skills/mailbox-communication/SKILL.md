---
name: mailbox-communication
description: Guides structured async communication through AInbox. Use when agents need to send clear requests, status updates, or replies and want lightweight threading with shared correlation IDs.
---

Use this skill when agents need structured async coordination.

## Preferred runtime

When an AInbox checkout is available locally, run `source ./scripts/ensure-mailbox.sh` on Linux/macOS or `.\scripts\ensure-mailbox.ps1` in PowerShell before using `mailbox`.

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

## Source checkout variations

```bash
# Rust CLI from source
cargo run -- send --to worker --subject "Task assignment: parser cleanup" --body "Please harden frontmatter parsing and report back." --correlation-id parser-fix

# Python compatibility CLI from source
python -m ainbox.cli send --to worker --subject "Task assignment: parser cleanup" --body "Please harden frontmatter parsing and report back." --correlation-id parser-fix
```

## Fallback installs

```bash
# Rust native CLI from source
cargo install --path .

# Python compatibility CLI
pip install git+https://github.com/JerrettDavis/AInbox.git
```
