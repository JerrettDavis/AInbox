---
name: mailbox-inbox-processing
description: Covers the basic AInbox inbox triage loop. Use when an agent needs to pull new messages, read the next relevant item, and reply or archive without loading the broader messaging guidance.
---

Use this skill to triage and process incoming AInbox messages.

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

## Install prerequisite

```bash
pip install git+https://github.com/JerrettDavis/AInbox.git
```
