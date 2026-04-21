# Create or inspect an election

Use AInbox elections to elect agents into a role such as `leader`, `reviewer`, or `release-manager`.

## Start with the common flow

```bash
mailbox create-election \
  --role leader \
  --candidate worker-agent \
  --candidate reviewer-agent \
  --participant worker-agent \
  --participant reviewer-agent \
  --participant coordinator-agent
mailbox list-elections --status open
mailbox show-election --id <election-id>
```

## Next step

- Use `vote-election.md` when you need to cast a vote
