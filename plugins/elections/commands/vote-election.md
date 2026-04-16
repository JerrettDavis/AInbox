# Vote in an election

Vote for an eligible candidate in an open election.

```bash
mailbox vote-election --id <election-id> --candidate reviewer-agent
```

Important rule:

- elections reject self-votes

Useful follow-ups:

```bash
mailbox show-election --id <election-id>
mailbox close-election --id <election-id>
```
