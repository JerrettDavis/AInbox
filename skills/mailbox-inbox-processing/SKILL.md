---
name: mailbox-inbox-processing
description: Covers the basic AInbox inbox triage loop. Use when an agent needs to pull new messages, read the next relevant item, and reply or archive without loading the broader messaging guidance.
---

Use this skill to triage and process incoming AInbox messages.

## Preferred runtime

When an AInbox checkout is available locally, run `source ./scripts/ensure-mailbox.sh` on Linux/macOS or `.\scripts\ensure-mailbox.ps1` in PowerShell before using `mailbox`.

## Standard inbox loop

```bash
mailbox sync --pull-only
mailbox list
mailbox read --id <message-id>
```

## Keep this lightweight

- pull before reading so the inbox reflects shared state
- use `mailbox read --correlation-id <thread-id>` to stay inside a thread
- archive only when you want to skip without printing the message

## Typical response

```bash
mailbox send --to worker-agent --subject "RE: parser cleanup" \
  --body "Reviewed. Looks good to merge." \
  --correlation-id parser-fix
mailbox sync --push-only
```

## Source checkout variations

```bash
# Rust CLI from source
cargo run -- read --id <message-id>

# Python compatibility CLI from source
python -m ainbox.cli read --id <message-id>
```

## Fallback installs

```bash
# Rust native CLI from source
cargo install --path .

# Python compatibility CLI
pip install git+https://github.com/JerrettDavis/AInbox.git
```
