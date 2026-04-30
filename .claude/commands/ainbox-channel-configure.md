# Claude Command: AInbox Channel Configure

Manage the AInbox push channel. Updates `~/.mailbox/channel-config.yaml`.

The channel ships disabled-by-default at the session level (you must pass `--channels`), so this command only tunes runtime behaviour: poll interval, auto-sync, and the optional sender allowlist.

## Subcommands

```bash
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" enable
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" disable
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" set-poll-interval 2000
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" set-auto-sync 0
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" enforce-allowlist on
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" enforce-allowlist off
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" set-allowlist add some-agent
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" set-allowlist remove some-agent
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" set-allowlist show
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" status
bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" reset
```

`set-poll-interval` accepts ms in the range `[250, 60000]`. `set-auto-sync 0` disables periodic `mailbox sync`. The allowlist filters inbound `received` events; outbound `sent`/`read` are always emitted.

## Command

bun "${CLAUDE_PLUGIN_ROOT}/channel/scripts/configure.ts" $ARGS
