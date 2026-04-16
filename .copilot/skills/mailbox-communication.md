# Skill: Mailbox Communication Strategy

## Overview

Best practices for using AInbox to coordinate between agents effectively.

## Designing Your Message

### Subjects Should Be Clear

Bad: "Update"  
Good: "PR review complete – ready to merge"

Bad: "Quick question"  
Good: "Need clarification on error handling approach"

### Keep Bodies Focused

- One main topic per message
- Use markdown formatting for readability
- Include context (task IDs, file names, etc.)
- Be specific about what you need from the recipient

### Use Correlation IDs for Related Messages

Group messages in a conversation by task or feature:

```bash
# Initial message
mailbox send --to agent-b --subject "Feature: Auth system" --body "Starting implementation" \
  --correlation-id feat-auth-001

# Follow-up
mailbox send --to agent-b --subject "Feature: Auth system – questions" --body "Need clarification on..." \
  --correlation-id feat-auth-001

# Recipient can filter by correlation_id
mailbox list --format json | grep "feat-auth-001"
```

## Conversation Patterns

### Question/Answer

**Agent A** (asks):
```bash
mailbox send --to agent-b --subject "Implementation Question: Error Handling" \
  --body "How should we handle timeout scenarios?" \
  --correlation-id q-error-handling
```

**Agent B** (responds after reading):
```bash
mailbox send --to agent-a --subject "RE: Implementation Question: Error Handling" \
  --body "Use exponential backoff with max retries..." \
  --correlation-id q-error-handling
```

### Task Assignment

**Manager** (assigns):
```bash
mailbox send --to worker --subject "Task Assignment: API Integration" \
  --body "Complete the payment processor integration. Deadline: Friday." \
  --correlation-id task-pay-api
```

**Worker** (acknowledges):
```bash
mailbox send --to manager --subject "RE: Task Assignment: API Integration" \
  --body "Received. Starting implementation today." \
  --correlation-id task-pay-api

# ... work happens ...

# Later: Status update
mailbox send --to manager --subject "Task Update: API Integration – 50% complete" \
  --body "Schema parsing complete, working on validation layer." \
  --correlation-id task-pay-api
```

### Code Review Flow

**Developer** (submits):
```bash
mailbox send --to reviewer --subject "Code Review: Payment Module" \
  --body "Implementation complete and tested. PR link: https://... Tests: 100% passing." \
  --correlation-id pr-payment
```

**Reviewer** (reviews and responds):
```bash
mailbox sync  # Pull the message
mailbox read --id <id>  # Read it
mailbox send --to developer --subject "RE: Code Review: Payment Module – Approved" \
  --body "Looks great! Minor: rename 'validate()' to 'validate_amount()' for clarity. Otherwise ready to merge." \
  --correlation-id pr-payment
```

**Developer** (makes changes and confirms):
```bash
mailbox send --to reviewer --subject "RE: Code Review: Payment Module – Changes Made" \
  --body "Updated. Renamed function as requested. New PR: https://..." \
  --correlation-id pr-payment
```

## When to Send vs When to Sync

### Send
When you want to create a new message (goes to outbox immediately).

```bash
mailbox send --to agent --subject "..." --body "..."
```

### Sync
When you want to push outgoing or pull incoming.

```bash
mailbox sync       # Both push and pull
mailbox sync --push-only   # Just push (after sending)
mailbox sync --pull-only   # Just pull (before reading)
```

**Workflow**:
```bash
# After creating messages
mailbox send ...
mailbox send ...
mailbox sync  # Push all to shared

# Before reading
mailbox sync  # Pull all from shared
mailbox list
mailbox read --id <id>
```

## Async Coordination Best Practices

### 1. Be Explicit About Expectations

```bash
mailbox send --to agent --subject "Waiting for Code Review" \
  --body "I'm blocked on PR#123. Need your review by EOD Thursday."
```

### 2. Use Timestamps for Urgency

```bash
mailbox send --to agent --subject "URGENT: Production Bug" \
  --body "Critical issue reported 30 mins ago. Investigating now. Can you provide database access?"
```

### 3. Include Context for Handoffs

```bash
mailbox send --to next-agent --subject "Task Handoff: User Auth Implementation" \
  --body """
I've completed the database schema and migration scripts.

Completed:
- User table with proper indexing
- Migration scripts in /db/migrations/
- Unit tests for schema validation

Next steps:
- Implement password hashing in auth service
- Add JWT token generation
- Write integration tests

See /docs/auth-spec.md for full spec.
"""
```

### 4. Acknowledge Receipt

When receiving an important message:
```bash
mailbox read --id <id>
mailbox send --to sender --subject "RE: [Task name]" \
  --body "Received. Starting work now."
```

### 5. Send Status Updates

For long-running tasks:
```bash
# Initial
mailbox send --to coordinator --subject "Task Start: Feature X" \
  --body "Starting implementation." --correlation-id feat-x

# 50% through
mailbox send --to coordinator --subject "Task Update: Feature X – 50% complete" \
  --body "Backend logic done, now working on UI." --correlation-id feat-x

# Complete
mailbox send --to coordinator --subject "Task Complete: Feature X" \
  --body "Ready for review. PR: https://..." --correlation-id feat-x
```

## Handling Message Overload

### Filter by Sender

```bash
# Read only messages from a specific agent
mailbox list --format json | grep '"from": "agent-name"'
```

### Use Correlation IDs to Prioritize

```bash
# List messages, filter by correlation_id
mailbox list --format json | grep "urgent-" | head -5
```

### Archive Old Messages

```bash
# Archive messages older than a week
mailbox list | head -20 | while read line; do
  id=$(echo "$line" | grep "ID:" | awk '{print $NF}')
  mailbox archive --id "$id"
done
```

## Common Mistakes

### ❌ Sending but Not Syncing

```bash
# Wrong: Message stays in outbox
mailbox send --to agent --subject "..." --body "..."

# Right: Sync to push to shared
mailbox send --to agent --subject "..." --body "..."
mailbox sync
```

### ❌ Pulling but Not Reading

```bash
# Wrong: Pull new messages but don't check
mailbox sync
mailbox list  # Never checked

# Right: Pull and then read
mailbox sync
mailbox list
mailbox read --id <important-id>
```

### ❌ Assuming Immediate Delivery

Messages are async. Recipient must explicitly sync to get your message.

```bash
# Don't expect immediate response
mailbox send --to agent --subject "..." --body "..."
# Agent won't see this until they run mailbox sync

# Check in again later
sleep 300  # Wait 5 minutes
mailbox sync  # Pull any responses
```

### ❌ Forgetting Correlation ID for Related Messages

```bash
# Wrong: Can't tell these are related
mailbox send --to agent --subject "Task A" --body "..."
mailbox send --to agent --subject "Task A – update" --body "..."

# Right: Use correlation_id
mailbox send --to agent --subject "Task A" --body "..." --correlation-id task-a
mailbox send --to agent --subject "Task A – update" --body "..." --correlation-id task-a
```

## Tips for Multi-Agent Systems

1. **Establish naming conventions**: Decide on agent IDs upfront (e.g., `worker-1`, `reviewer`, `coordinator`)
2. **Use correlation_ids consistently**: All related messages in a workflow use the same correlation_id
3. **Sync before and after**: `mailbox sync` before reading, after sending
4. **Document expectations**: How often do agents sync? What's the expected response time?
5. **Monitor .mailbox/ folder**: For debugging, check actual files in `.mailbox/inbox/`, `.mailbox/outbox/`, etc.

## Troubleshooting Communication Issues

### Agent Doesn't See My Message

1. Did you call `mailbox sync` after sending? (Required to push to shared)
2. Did the recipient call `mailbox sync`? (Required to pull from shared)
3. Is the recipient ID spelled correctly?
4. Check the message file: `ls .mailbox/outbox/` and `ls .mailbox/sent/`

### Message Content Wrong

Messages are stored as-is. If you made a typo, send a new message with a correction:
```bash
mailbox send --to agent --subject "CORRECTION: Previous message had typo" \
  --body "The correct value is X, not Y."
```

### Too Many Messages

Archive processed ones:
```bash
mailbox read --id <id>  # Archives automatically
# or manually
mailbox archive --id <id>
```

## Next Steps

- [Learn Mailbox Basics (mailbox-basics.md)](#)
- [Learn Inbox Processing (mailbox-inbox-processing.md)](#)
- [See AGENTS.md for integration details](./AGENTS.md)
