---
name: agent-poll
description: Guides simple public polls between agents. Use when a team needs a lightweight shared vote on a question, shortlist, or preference without electing a single agent to a role.
---

Use this skill when agents need a simple shared vote on a question.

## Best fit

- selecting an approach or tool
- confirming a team preference
- choosing between a short list of options

## Minimal workflow

```bash
mailbox create-poll --question "What database should we use?" --option MSSQL --option PostgreSQL --option MySQL --participant worker-agent --participant reviewer-agent
mailbox vote-poll --id <poll-id> --option PostgreSQL
mailbox show-poll --id <poll-id>
```

## Rules worth remembering

- votes are public
- each voter can update their vote while the poll is open
- participants receive mailbox notifications when they are supplied
