#!/usr/bin/env bun
import { CONFIG_FILE, DEFAULT_CONFIG, loadConfig, saveConfig, type ChannelConfig } from '../lib/config.ts'

interface SubcommandHandler {
  (cfg: ChannelConfig, args: string[]): Promise<{ cfg: ChannelConfig; output: string; save: boolean }>
}

const SUBCOMMANDS: Record<string, SubcommandHandler> = {
  enable: async cfg => ({ cfg: { ...cfg, enabled: true }, output: 'Channel enabled.', save: true }),
  disable: async cfg => ({ cfg: { ...cfg, enabled: false }, output: 'Channel disabled.', save: true }),
  'set-poll-interval': async (cfg, args) => {
    const ms = parseInt(args[0] ?? '', 10)
    if (!Number.isFinite(ms) || ms < 250 || ms > 60000) {
      throw new Error('set-poll-interval expects ms in [250, 60000]')
    }
    return { cfg: { ...cfg, pollIntervalMs: ms }, output: `pollIntervalMs=${ms}`, save: true }
  },
  'set-auto-sync': async (cfg, args) => {
    const ms = parseInt(args[0] ?? '', 10)
    if (!Number.isFinite(ms) || ms < 0) {
      throw new Error('set-auto-sync expects a non-negative ms (0 disables)')
    }
    return { cfg: { ...cfg, autoSyncIntervalMs: ms }, output: `autoSyncIntervalMs=${ms}`, save: true }
  },
  'enforce-allowlist': async (cfg, args) => {
    const flag = args[0]
    if (flag !== 'on' && flag !== 'off') throw new Error('enforce-allowlist expects on|off')
    return {
      cfg: { ...cfg, allowlistEnforced: flag === 'on' },
      output: `allowlistEnforced=${flag === 'on'}`,
      save: true,
    }
  },
  'set-allowlist': async (cfg, args) => {
    const op = args[0]
    if (op === 'show') {
      return {
        cfg,
        output:
          cfg.allowlist.length === 0
            ? 'allowlist is empty'
            : 'allowlist:\n' + cfg.allowlist.map(s => `  - ${s}`).join('\n'),
        save: false,
      }
    }
    const id = args[1]
    if (!id) throw new Error('set-allowlist add|remove requires an agent id')
    if (op === 'add') {
      if (cfg.allowlist.includes(id)) {
        return { cfg, output: `${id} already in allowlist`, save: false }
      }
      return {
        cfg: { ...cfg, allowlist: [...cfg.allowlist, id] },
        output: `Added ${id}`,
        save: true,
      }
    }
    if (op === 'remove') {
      if (!cfg.allowlist.includes(id)) {
        return { cfg, output: `${id} not in allowlist`, save: false }
      }
      return {
        cfg: { ...cfg, allowlist: cfg.allowlist.filter(s => s !== id) },
        output: `Removed ${id}`,
        save: true,
      }
    }
    throw new Error('set-allowlist expects add <id> | remove <id> | show')
  },
  status: async cfg => ({
    cfg,
    output: [
      `Config file: ${CONFIG_FILE}`,
      `enabled: ${cfg.enabled}`,
      `pollIntervalMs: ${cfg.pollIntervalMs}`,
      `autoSyncIntervalMs: ${cfg.autoSyncIntervalMs}`,
      `allowlistEnforced: ${cfg.allowlistEnforced}`,
      `allowlist: ${cfg.allowlist.length === 0 ? '[]' : cfg.allowlist.join(', ')}`,
    ].join('\n'),
    save: false,
  }),
  reset: async () => ({ cfg: { ...DEFAULT_CONFIG, allowlist: [] }, output: 'Config reset to defaults.', save: true }),
}

function printUsage(): void {
  process.stderr.write(
    [
      'Usage: configure <subcommand> [args]',
      '',
      'Subcommands:',
      '  enable',
      '  disable',
      '  set-poll-interval <ms>           (250-60000)',
      '  set-auto-sync <ms>               (0 disables)',
      '  enforce-allowlist on|off',
      '  set-allowlist add <id>',
      '  set-allowlist remove <id>',
      '  set-allowlist show',
      '  status',
      '  reset',
      '',
    ].join('\n'),
  )
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2)
  if (argv.length === 0 || argv[0] === '--help' || argv[0] === '-h') {
    printUsage()
    process.exit(argv.length === 0 ? 2 : 0)
  }
  const [subcommand, ...rest] = argv
  if (!subcommand) {
    printUsage()
    process.exit(2)
  }
  const handler = SUBCOMMANDS[subcommand]
  if (!handler) {
    process.stderr.write(`Unknown subcommand: ${subcommand}\n`)
    printUsage()
    process.exit(2)
  }
  const cfg = await loadConfig()
  try {
    const result = await handler(cfg, rest)
    if (result.save) await saveConfig(result.cfg)
    process.stdout.write(result.output + '\n')
  } catch (err) {
    process.stderr.write(`Error: ${(err as Error).message}\n`)
    process.exit(3)
  }
}

await main()
