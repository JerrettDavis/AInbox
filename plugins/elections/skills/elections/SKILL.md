# Elections

Use this skill when agents need to elect one of several agents to a role.

## Best fit

- electing a leader
- choosing a reviewer or coordinator
- assigning a temporary owner for a task

## Core commands

```bash
mailbox create-election --role leader --candidate worker-agent --candidate reviewer-agent --participant worker-agent --participant reviewer-agent --participant coordinator-agent
mailbox list-elections --status open
mailbox vote-election --id <election-id> --candidate reviewer-agent
mailbox show-election --id <election-id>
mailbox close-election --id <election-id>
```

## Rules

- votes are public
- candidates cannot vote for themselves
- if participants are supplied, the creator automatically sends mailbox notifications
