# Claude Command: Mailbox Sync

## Description

Synchronize the local mailbox with the shared mailbox. This pushes outgoing messages to the shared location and pulls incoming messages addressed to you.

## When to Use

- After sending a message (to push it to shared mailbox)
- Before reading inbox (to pull new messages)
- Periodically to keep mailbox in sync

## Command

```bash
mailbox sync [--push-only] [--pull-only]
```

## Options

- `--push-only` – Only push messages from outbox to shared (skip pull)
- `--pull-only` – Only pull messages from shared to inbox (skip push)
- Default (no options): Push AND pull

## Prerequisites

- AInbox must be installed: `pip install -e .`
- Local mailbox must be initialized: `mailbox init`
- Agent ID must be set (via env var, config, or directory name)
- Shared mailbox path must be writable (defaults to `~/.mailbox/shared/`)

## Example

### Full sync (push + pull)

```bash
$ mailbox sync
Sync complete: 1 pushed, 2 pulled
```

Output means:
- 1 message pushed from `.mailbox/outbox/` to `~/.mailbox/shared/outbox/`
- 2 messages pulled from `~/.mailbox/shared/outbox/` to `.mailbox/inbox/`

### Push only

```bash
$ mailbox sync --push-only
Sync complete: 1 pushed, 0 pulled
```

### Pull only

```bash
$ mailbox sync --pull-only
Sync complete: 0 pushed, 2 pulled
```

## Detailed Behavior

### Push Phase

1. Scans `.mailbox/outbox/` for unsent messages
2. Copies each message to `~/.mailbox/shared/outbox/`
3. Moves original message to `.mailbox/sent/`
4. Removes from outbox

### Pull Phase

1. Scans `~/.mailbox/shared/outbox/` for all messages
2. Checks each message's `to` field
3. If `to` matches agent ID and message not already in inbox:
   - Copies message to `.mailbox/inbox/`
   - Sets `received_at` on the pulled inbox copy
   - Removes the shared copy after successful delivery

## Exit Codes

- `0` – Success
- `1` – General error (permissions, path issues)
- `3` – Agent ID not found

## Typical Workflow

```bash
# 1. Send a message
mailbox send --to worker --subject "Task assigned" --body "Please implement feature X"

# 2. Sync to push it to shared mailbox
mailbox sync
# Output: Sync complete: 1 pushed, 0 pulled

# 3. Worker pulls the message
mailbox sync
# Output: Sync complete: 0 pushed, 1 pulled

# 4. Worker reads it
mailbox list
mailbox read --id <id>

# 5. Worker responds
mailbox send --to reviewer --subject "Re: Task assigned" --body "Implementation complete"

# 6. Worker syncs to push response
mailbox sync
# Output: Sync complete: 1 pushed, 0 pulled

# 7. You pull the response
mailbox sync
# Output: Sync complete: 0 pushed, 1 pulled

# 8. You read the response
mailbox read --id <id>
```

## Configuration

Default shared mailbox location: `~/.mailbox/shared/outbox`

Override with:
```bash
export MAILBOX_SHARED=~/custom/shared/mailbox
```

Or in config file `~/.mailbox/config.yaml`:
```yaml
shared_mailbox_path: ~/custom/shared/mailbox
```

## Related Commands

- `mailbox send` – Create a message (then call sync to push)
- `mailbox list` – List inbox messages (call sync first to pull)
- `mailbox read --id <id>` – Read a message

## Troubleshooting

### "Permission denied" on sync

Check write permissions:
```bash
ls -la ~/.mailbox/
```

### Messages not appearing after sync

1. Verify agent ID is correct: `mailbox config --list`
2. Check that sender's `to` field matches your agent ID
3. Verify both sender and recipient ran sync:
   - Sender: `mailbox sync` (push)
   - You: `mailbox sync` (pull)

### Duplicate messages

Duplicates are prevented by tracking message IDs. If duplicates still appear, check:
- Shared mailbox isn't being manually modified
- Two different agents don't have the same agent ID

## Tips

- Sync early, sync often: Call before reading, after sending
- Use `--push-only` if you're in a read-only shared mailbox
- Use `--pull-only` if you've already pushed and just want updates
