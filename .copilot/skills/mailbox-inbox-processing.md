# Skill: Mailbox Inbox Processing

## Overview

Strategies for efficiently handling incoming mailbox messages and coordinating responses.

## Inbox Triage Workflow

### Step 1: Sync to Get Latest Messages

```bash
mailbox sync  # Pull from shared mailbox
```

### Step 2: List Inbox

```bash
mailbox list
# or with JSON for filtering
mailbox list --format json
```

Example output:
```
Inbox: 3 message(s)

1. From: worker-agent
   Subject: PR review complete
   ID: abc123
   Sent: 2026-04-15T22:31:00Z

2. From: coordinator
   Subject: Task assignment
   ID: def456
   Sent: 2026-04-15T22:00:00Z

3. From: reviewer
   Subject: Implementation approved
   ID: ghi789
   Sent: 2026-04-15T21:30:00Z
```

### Step 3: Prioritize

Look at subjects and sender to determine priority:
- Urgent/blocking → read first
- Assignments from coordinator → read early
- FYI/information → read later

### Step 4: Read and Process

```bash
# Read highest priority
mailbox read --id abc123

# Content displays with frontmatter
---
id: abc123
to: you
from: worker-agent
subject: PR review complete
sent_at: 2026-04-15T22:31:00Z
received_at: 2026-04-15T22:32:00Z
read_at: null
---

Your review was requested. I've addressed all comments and updated the PR.
Ready to merge when you give approval.
```

### Step 5: Respond (if needed)

```bash
mailbox send --to worker-agent --subject "RE: PR review complete" \
  --body "Approved! Merging now." \
  --correlation-id pr-review-task
```

### Step 6: Sync Again

```bash
mailbox sync  # Push response, pull any new messages
```

## Inbox Patterns

### Process All Unread

```bash
# Keep reading until inbox is empty
while [ $(mailbox list | grep "From:" | wc -l) -gt 0 ]; do
  mailbox read  # Read first message (auto-archives)
  # Process the content and respond if needed
  # mailbox send ...
done

mailbox sync  # Final push
```

### Batch Process by Sender

```bash
# See all messages from a specific agent
mailbox list --format json | grep -A5 '"from": "worker-agent"'

# Read only from that agent
for id in $(mailbox list --format json | grep -B1 '"from": "worker-agent"' | grep id | cut -d'"' -f4); do
  mailbox read --id "$id"
done
```

### Filter by Subject

```bash
# Urgent messages first
mailbox list --format json | grep -i "urgent" | jq '.[].id' | while read id; do
  mailbox read --id "$id"
done

# Then normal messages
mailbox list  # Shows remaining
```

## Response Strategies

### Acknowledge Complex Requests

When receiving a detailed request, acknowledge it first:

```bash
# After reading complex request
mailbox send --to sender --subject "RE: [Subject] – Received & Working" \
  --body """
Received your message. I'm currently blocked on [reason].
I'll start work on this after [event/time].
Expected completion: [when].
"""
```

### Request Clarification

If message is unclear:

```bash
mailbox send --to sender --subject "RE: [Subject] – Need Clarification" \
  --body """
Can you clarify:
1. [Point 1 needing clarification]
2. [Point 2]

Otherwise proceeding with [assumption].
"""
```

### Provide Status Updates

For multi-step responses:

```bash
# Initial
mailbox send --to requester --subject "RE: [Task]" \
  --body "Working on it. Initial findings: [...]" \
  --correlation-id task-id

# Later
mailbox send --to requester --subject "RE: [Task] – Update" \
  --body "50% done. Found issue with [X]. Resolving now." \
  --correlation-id task-id

# Final
mailbox send --to requester --subject "RE: [Task] – Complete" \
  --body "Done. Results: [...]" \
  --correlation-id task-id
```

## Managing Message Volume

### Archive Processed Messages

Messages automatically move to archive when you read them:

```bash
mailbox read --id <id>  # Auto-archives
```

Or manually archive if needed:

```bash
mailbox archive --id <id>
```

### Ignore Old Messages

If inbox is full of old messages:

```bash
# Archive the oldest (first ones in list)
mailbox list | tail -20 | grep "ID:" | awk '{print $NF}' | while read id; do
  mailbox archive --id "$id"
done
```

### Set Cleanup Schedule

Periodically clean up archive (if needed for disk space):

```bash
# Option: Delete archived messages (careful!)
rm .mailbox/archive/*.md
```

## Handling Edge Cases

### Message Parsing Error

If a message won't parse:

```bash
# Check the file directly
cat .mailbox/inbox/*.md | head -20

# Manually archive if corrupted
mailbox archive --id <bad-id>

# Ask sender to resend
mailbox send --to sender --subject "Message parsing issue" \
  --body "Couldn't parse your last message. Can you resend?"
```

### Duplicate Messages

If you see the same message twice (rare):

```bash
# Archive the duplicate
mailbox archive --id <duplicate-id>
```

### Message Never Arrives

1. Verify sender synced:
   ```bash
   # Sender must have run: mailbox sync (push-only or full)
   ```

2. Verify you synced:
   ```bash
   mailbox sync  # pull-only or full
   ```

3. Check sender used correct recipient ID:
   ```bash
   # Your agent ID
   echo $MAILBOX_AGENT_ID
   ```

## Inbox Hygiene Tips

### 1. Process Regularly

Don't let inbox pile up:
```bash
# Morning routine
mailbox sync
mailbox list  # See what's new
# Process important ones
```

### 2. Use Correlation IDs to Thread

Group related messages:
```bash
mailbox list --format json | jq '.[] | select(.correlation_id == "task-123")'
```

### 3. Respond Promptly

Async doesn't mean slow:
```bash
# Same day responses
mailbox send --to requester --subject "RE: [...]" \
  --body "Acknowledged. Working on it."
```

### 4. Keep Archive Clean

Old archive can grow large:
```bash
# Optional: Delete very old messages (>30 days)
find .mailbox/archive -name "*.md" -mtime +30 -delete
```

### 5. Monitor Shared Mailbox

Periodically check if shared mailbox is healthy:
```bash
ls -la ~/.mailbox/shared/outbox/ | head
# Should see messages from various agents
```

## Scripting Inbox Processing

### Process All Messages with a Script

```bash
#!/bin/bash
# process_inbox.sh

mailbox sync  # Pull latest

# Process each message
mailbox list --format json | jq -r '.[] | .id' | while read id; do
  msg=$(mailbox read --id "$id")
  
  # Your custom processing
  sender=$(echo "$msg" | grep "from:" | awk '{print $2}')
  subject=$(echo "$msg" | grep "subject:" | cut -d' ' -f2-)
  
  echo "Processing message from $sender: $subject"
  
  # Send acknowledgment
  mailbox send --to "$sender" --subject "RE: $subject" \
    --body "Received and processing."
done

mailbox sync  # Push responses
```

### Batch Archive

```bash
#!/bin/bash
# archive_all.sh

mailbox list --format json | jq -r '.[] | .id' | while read id; do
  mailbox archive --id "$id"
done

echo "All messages archived"
```

## Performance Tips

### Large Inbox (100+ messages)

- Use `mailbox list --limit 10` to see recent only
- Process in batches
- Archive older messages to keep active inbox lean

### Slow Filesystem

- Sync less frequently (batch changes)
- Use `--push-only` or `--pull-only` when possible
- Archive processed messages to reduce directory size

## Monitoring

### Check Inbox Size

```bash
echo "Inbox: $(ls .mailbox/inbox | wc -l) messages"
echo "Archive: $(ls .mailbox/archive | wc -l) messages"
echo "Sent: $(ls .mailbox/sent | wc -l) messages"
```

### Recent Activity

```bash
# Last 10 messages (inbox + archive)
find .mailbox/inbox .mailbox/archive -name "*.md" | sort -r | head -10
```

## Troubleshooting Inbox Issues

### Can't Read a Message

```bash
mailbox read --id <id>
# Error: "No message found"

# Check if it's in archive (already read)
ls .mailbox/archive/*.md | grep <id>

# Or check if it's still in inbox
ls .mailbox/inbox/*.md | grep <id>
```

### Inbox Corrupted

```bash
# Manually check a file
cat .mailbox/inbox/20260415T223100Z_abc123.md

# If corrupted, move to archive
mv .mailbox/inbox/20260415T223100Z_abc123.md .mailbox/archive/
```

### Messages Not Being Pulled

```bash
# Verify agent ID
mailbox config --list

# Sync and check shared mailbox
mailbox sync --pull-only
ls ~/.mailbox/shared/outbox/*.md | head
```

## Next Steps

- [Learn Communication Strategy (mailbox-communication.md)](#)
- [Learn Mailbox Basics (mailbox-basics.md)](#)
- [Check AGENTS.md for setup (./AGENTS.md)](./AGENTS.md)
