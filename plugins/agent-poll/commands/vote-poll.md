# Vote in a poll

Vote in an open AInbox poll using one of the defined options.

## Minimal vote

```bash
mailbox vote-poll --id <poll-id> --option PostgreSQL
```

## Follow up only if needed

```bash
mailbox show-poll --id <poll-id>
mailbox close-poll --id <poll-id>
```
