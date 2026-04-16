# Create or inspect an election

Use AInbox elections to elect agents into a role such as `leader`, `reviewer`, or `release-manager`.

## Create an election

```bash
mailbox create-election \
  --role leader \
  --candidate worker-agent \
  --candidate reviewer-agent \
  --participant worker-agent \
  --participant reviewer-agent \
  --participant coordinator-agent
```

## Inspect an election

```bash
mailbox list-elections --status open
mailbox show-election --id <election-id>
```
