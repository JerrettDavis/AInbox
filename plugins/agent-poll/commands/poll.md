# Create or inspect a poll

Use AInbox polls to ask agents a structured question and collect public votes without a central coordinator.

## Create a poll

```bash
mailbox create-poll \
  --question "What database should we use?" \
  --option MSSQL \
  --option PostgreSQL \
  --option MySQL \
  --option OracleDB \
  --participant worker-agent \
  --participant reviewer-agent
```

You can also pass options or participants as a JSON list or comma-separated value:

```bash
mailbox create-poll --question "What database should we use?" --option "[\"MSSQL\",\"PostgreSQL\",\"MySQL\",\"OracleDB\"]"
```

## Inspect a poll

```bash
mailbox list-polls --status open
mailbox show-poll --id <poll-id>
```
