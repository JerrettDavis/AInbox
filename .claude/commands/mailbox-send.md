# Claude Command: Mailbox Send

Use this command to create an outbound message for another agent.

Examples assume the latest native `mailbox` binary is already on `PATH`. When the Claude plugin is active, bundled hooks try to bootstrap it silently. From a local AInbox checkout, you can still run `source ./scripts/ensure-mailbox.sh` on Linux/macOS or `.\scripts\ensure-mailbox.ps1` in PowerShell for an explicit setup step.

## Start with the common case

```bash
mailbox send --to reviewer --subject "Code review needed" --body "Please review my implementation."
mailbox sync
```

## Reach for extra flags only when needed

- `--body -` reads a multiline body from stdin
- `--correlation-id <thread-id>` keeps related updates in one thread

## Source checkout variations

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
- keep a `.mailbox/draft/` note for active threads and update it before sending important replies

## If you need more detail

```bash
mailbox send --help
mailbox sync --help
```
