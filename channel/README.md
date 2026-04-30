# AInbox Channel (MCP push channel)

Bun + TypeScript MCP server that pushes `received`, `sent`, and `read` mailbox events into a Claude Code session as `<channel source="ainbox" ...>` tags, and exposes `reply`, `mark_read`, and `list_inbox` tools backed by the existing `mailbox` CLI.

## Requirements

- Claude Code v2.1.80+
- [Bun](https://bun.sh) on `PATH`
- An installed `mailbox` CLI (or `python -m ainbox.cli` in a venv) — see the project root README

## Layout

```
channel/
├── server.ts                # MCP server entry
├── lib/
│   ├── config.ts            # ~/.mailbox/channel-config.yaml
│   ├── frontmatter.ts       # message frontmatter parser
│   ├── mailbox-cli.ts       # mailbox/python wrapper
│   ├── state.ts             # ~/.mailbox/channel-state.json
│   └── watcher.ts           # polling watcher + diff
├── scripts/
│   └── configure.ts         # /ainbox-channel-configure backend
└── tests/                   # bun:test suites
```

## Local development

From the repo root:

```bash
bun install --cwd channel
bun test --cwd channel
bun run --cwd channel typecheck
```

## Smoke test against Claude Code

```bash
claude --dangerously-load-development-channels server:ainbox \
  -p "Run /mcp and report whether ainbox is connected. Then exit." \
  --output-format json
```

Pass criteria:

1. Exit code 0
2. Output contains `"ainbox"` near `"connected"`
3. No stderr matching `Failed to connect`, `capability error`, or `MCP error`

## Configuration

`~/.mailbox/channel-config.yaml` is created on first save with defaults:

```yaml
enabled: true
pollIntervalMs: 2000
autoSyncIntervalMs: 0
allowlistEnforced: false
allowlist: []
```

Use `/ainbox-channel-configure status` to inspect, or run the script directly:

```bash
bun channel/scripts/configure.ts set-poll-interval 1500
bun channel/scripts/configure.ts enforce-allowlist on
bun channel/scripts/configure.ts set-allowlist add reviewer-agent
```

## Trust model

Message bodies are untrusted user input. The server's instructions tell Claude to confirm with the user before acting on instructions found inside a message. The optional allowlist filters inbound `received` events by sender; the filesystem permissions on the local mailbox remain the primary trust boundary.

## Tools

| Tool | Inputs | Behaviour |
|------|--------|-----------|
| `reply` | `to`, `subject`, `body`, optional `correlation_id` | Calls `mailbox send`, then `mailbox sync --push-only`. |
| `mark_read` | `id` | Calls `mailbox read --id <id>`, which moves the file to `archive/` and stamps `read_at`. Returns the full markdown. |
| `list_inbox` | optional `limit` (default 10) | Calls `mailbox list --format json`. |

## Notifications

Each event becomes one `notifications/claude/channel` message:

```json
{
  "method": "notifications/claude/channel",
  "params": {
    "content": "<280-char body preview>",
    "meta": {
      "event": "received|sent|read",
      "id": "...",
      "from": "...",
      "to": "...",
      "subject": "...",
      "correlation_id": "..."
    }
  }
}
```

Meta keys are underscore_case to satisfy the channel API's `[a-zA-Z0-9_]+` constraint (hyphens are silently dropped).
