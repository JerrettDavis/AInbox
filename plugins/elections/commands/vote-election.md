# Vote in an election

Vote for an eligible candidate in an open election.

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

## Runtime variations

```bash
# Rust CLI from source
cargo run -- vote-election --id <election-id> --candidate reviewer-agent

# Python compatibility CLI from source
python -m ainbox.cli vote-election --id <election-id> --candidate reviewer-agent
```
