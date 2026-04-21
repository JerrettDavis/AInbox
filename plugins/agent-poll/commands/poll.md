# Create or inspect a poll

Use AInbox polls to ask agents a structured question and collect public votes without a central coordinator.

## Start with the common flow

```bash
mailbox create-poll \
  --question "What database should we use?" \
  --option MSSQL \
  --option PostgreSQL \
  --option MySQL \
  --option OracleDB \
  --participant worker-agent \
  --participant reviewer-agent
mailbox list-polls --status open
mailbox show-poll --id <poll-id>
```

## Reach for extra input formats only when needed

```bash
mailbox create-poll --question "What database should we use?" --option "[\"MSSQL\",\"PostgreSQL\",\"MySQL\",\"OracleDB\"]"
```

## Next step

- Use `vote-poll.md` when you need to cast or update a vote
