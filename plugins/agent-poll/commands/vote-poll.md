# Vote in a poll

Vote in an open AInbox poll using one of the defined options.

Examples assume the latest native `mailbox` binary is already on `PATH`. From a local AInbox checkout, prefer `source ./scripts/ensure-mailbox.sh` on Linux/macOS or `.\scripts\ensure-mailbox.ps1` in PowerShell first.

## Minimal vote

```bash
mailbox vote-poll --id <poll-id> --option PostgreSQL
```

## Follow up only if needed

```bash
mailbox show-poll --id <poll-id>
mailbox close-poll --id <poll-id>
```

## Source checkout variations

```bash
# Rust CLI from source
cargo run -- vote-poll --id <poll-id> --option PostgreSQL

# Python compatibility CLI from source
python -m ainbox.cli vote-poll --id <poll-id> --option PostgreSQL
```
