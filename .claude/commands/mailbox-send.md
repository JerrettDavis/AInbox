# Claude Command: Mailbox Send

Use this command to create an outbound message for another agent.

## Start with the common case

```bash
mailbox send --to reviewer --subject "Code review needed" --body "Please review my implementation."
mailbox sync
```

## Reach for extra flags only when needed

- `--body -` reads a multiline body from stdin
- `--correlation-id <thread-id>` keeps related updates in one thread

## Runtime variations

```bash
# Rust CLI from source
cargo run -- send --to reviewer --subject "Code review needed" --body "Please review my implementation."

# Python compatibility CLI from source
python -m ainbox.cli send --to reviewer --subject "Code review needed" --body "Please review my implementation."
```

## Remember

- `mailbox send` writes to `.mailbox/outbox/`
- the recipient will not see the message until someone runs `mailbox sync`
- `mailbox sync` immediately after sending is the normal workflow

## If you need more detail

```bash
mailbox send --help
mailbox sync --help
```
