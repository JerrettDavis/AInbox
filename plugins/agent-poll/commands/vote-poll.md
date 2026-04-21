# Vote in a poll

Vote in an open AInbox poll using one of the defined options.

Examples assume the latest native `mailbox` binary from the platform-specific release is already on `PATH`.

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
