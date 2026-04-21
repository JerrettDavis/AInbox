# Claude Command: Mailbox Read

Use this command to read the next inbox item or a specific message by ID.

Examples assume the latest native `mailbox` binary from the platform-specific release is already on `PATH`.

## Start with the usual flow

```bash
mailbox sync --pull-only
mailbox list
mailbox read --id <message-id>
```

## Reach for the short form when you already know the queue

```bash
mailbox read
```

Without `--id`, AInbox reads the first unread inbox message.

## Remember

- reading sets `read_at`
- the message moves from `.mailbox/inbox/` to `.mailbox/archive/`
- use `mailbox archive --id <message-id>` when you want to skip without printing the message

## Source checkout variations

```bash
# Rust CLI from source
cargo run -- read --id <message-id>

# Python compatibility CLI from source
python -m ainbox.cli read --id <message-id>
```

## If you need more detail

```bash
mailbox read --help
```
