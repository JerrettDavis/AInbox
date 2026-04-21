# Vote in an election

Vote for an eligible candidate in an open election.

Examples assume the latest native `mailbox` binary from the platform-specific release is already on `PATH`.

## Minimal vote

```bash
mailbox vote-election --id <election-id> --candidate reviewer-agent
```

## Important rule

- elections reject self-votes

## Follow up only if needed

```bash
mailbox show-election --id <election-id>
mailbox close-election --id <election-id>
```

## Source checkout variations

```bash
# Rust CLI from source
cargo run -- vote-election --id <election-id> --candidate reviewer-agent

# Python compatibility CLI from source
python -m ainbox.cli vote-election --id <election-id> --candidate reviewer-agent
```
