# Claude Command: Mailbox Sync

Use this command after sending or before reading so the local mailbox stays aligned with the shared mailbox.

## Start with the default

```bash
mailbox sync
```

## Narrow the operation only when needed

- `mailbox sync --push-only` pushes outbound mail without pulling
- `mailbox sync --pull-only` pulls inbound mail without pushing

## Read the output literally

- `1 pushed` means one outbox message moved to the shared mailbox
- `2 pulled` means two messages were copied into your inbox

## Keep this workflow in mind

```bash
mailbox send --to worker --subject "Task assigned" --body "Please implement feature X"
mailbox sync
mailbox sync --pull-only
mailbox read --id <id>
```

## If you need more detail

```bash
mailbox sync --help
```
