---
name: elections
description: Guides mailbox-backed elections for assigning agents to roles. Use when the group needs to pick a leader, reviewer, coordinator, or other single role-holder from a candidate set.
---

Use this skill when agents need to elect one of several agents to a role.

## Preferred runtime

When an AInbox checkout is available locally, run `source ./scripts/ensure-mailbox.sh` on Linux/macOS or `.\scripts\ensure-mailbox.ps1` in PowerShell before using `mailbox`.

## Best fit

- electing a leader
- choosing a reviewer or coordinator
- assigning a temporary owner for a task

## Minimal workflow

```bash
mailbox create-election --role leader --candidate worker-agent --candidate reviewer-agent --participant worker-agent --participant reviewer-agent --participant coordinator-agent
mailbox vote-election --id <election-id> --candidate reviewer-agent
mailbox show-election --id <election-id>
```

## Rules worth remembering

- votes are public
- elections reject self-votes
- participants receive mailbox notifications when they are supplied

## Source checkout variations

```bash
# Rust CLI from source
cargo run -- create-election --role leader --candidate worker-agent --candidate reviewer-agent

# Python compatibility CLI from source
python -m ainbox.cli create-election --role leader --candidate worker-agent --candidate reviewer-agent
```
