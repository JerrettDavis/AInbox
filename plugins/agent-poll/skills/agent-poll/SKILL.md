# Agent Poll

Use this skill when agents need a simple shared vote on a question.

## Best fit

- selecting a technology or approach
- confirming a team preference
- choosing between a short list of options

## Core commands

```bash
mailbox create-poll --question "What database should we use?" --option MSSQL --option PostgreSQL --option MySQL --participant worker-agent --participant reviewer-agent
mailbox list-polls --status open
mailbox vote-poll --id <poll-id> --option PostgreSQL
mailbox show-poll --id <poll-id>
mailbox close-poll --id <poll-id>
```

## Rules

- votes are public
- each voter has one vote file and can update their vote while the poll is open
- if participants are supplied, the creator automatically sends mailbox notifications
