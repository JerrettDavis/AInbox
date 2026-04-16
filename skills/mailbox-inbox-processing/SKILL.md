# Mailbox Inbox Processing

Use this skill to triage and process incoming AInbox messages.

## Standard inbox loop

```bash
mailbox sync --pull-only
mailbox list
mailbox read --id <message-id>
```

## Tips

- Pull before reading so inbox reflects the latest shared state
- Use `mailbox read --correlation-id <thread-id>` to process the next message in a thread
- Archive only when you want to skip a message without printing it

## Example response

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
