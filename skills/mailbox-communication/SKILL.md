# Mailbox Communication

Use this skill when agents need structured async coordination.

## Good message patterns

- Clear subject lines: `PR review complete - ready to merge`
- Specific asks: say what the recipient should do next
- Shared `--correlation-id` values for related updates

## Examples

```bash
mailbox send --to worker --subject "Task assignment: parser cleanup" \
  --body "Please harden frontmatter parsing and report back." \
  --correlation-id parser-fix

mailbox send --to reviewer --subject "Review request: parser cleanup" \
  --body "Implementation is ready for review." \
  --correlation-id parser-fix
```

## Recommended cadence

1. Send the message
2. Sync immediately to push it
3. Sync before checking inbox
4. Read and reply using the same correlation ID when the conversation is related

## Install prerequisite

```bash
pip install git+https://github.com/JerrettDavis/AInbox.git
```
