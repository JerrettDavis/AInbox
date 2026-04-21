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
