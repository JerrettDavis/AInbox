import fs from 'node:fs/promises'
import path from 'node:path'
import os from 'node:os'

export interface ChannelConfig {
  enabled: boolean
  pollIntervalMs: number
  autoSyncIntervalMs: number
  allowlistEnforced: boolean
  allowlist: string[]
}

export const DEFAULT_CONFIG: ChannelConfig = {
  enabled: true,
  pollIntervalMs: 2000,
  autoSyncIntervalMs: 0,
  allowlistEnforced: false,
  allowlist: [],
}

const HOME_MAILBOX = path.join(os.homedir(), '.mailbox')
export const CONFIG_FILE = path.join(HOME_MAILBOX, 'channel-config.yaml')

export async function loadConfig(configPath = CONFIG_FILE): Promise<ChannelConfig> {
  let raw: string
  try {
    raw = await fs.readFile(configPath, 'utf-8')
  } catch {
    return { ...DEFAULT_CONFIG }
  }
  return parseConfig(raw)
}

export async function saveConfig(config: ChannelConfig, configPath = CONFIG_FILE): Promise<void> {
  await fs.mkdir(path.dirname(configPath), { recursive: true })
  const yaml = serializeConfig(config)
  // tmp is placed in the same directory as the target so fs.rename is always
  // an intra-volume move. This invariant prevents EXDEV on single-drive setups.
  // If the OS still raises EXDEV (e.g. bind-mounts or cross-drive TEMP), fall
  // back to copy + unlink rather than leaving a stale tmp file.
  const tmp = `${configPath}.${process.pid}.${Date.now()}.tmp`
  await fs.writeFile(tmp, yaml, 'utf-8')
  try {
    await fs.rename(tmp, configPath)
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === 'EXDEV') {
      await fs.copyFile(tmp, configPath)
      await fs.unlink(tmp)
    } else {
      throw err
    }
  }
}

export function parseConfig(yaml: string): ChannelConfig {
  const cfg: ChannelConfig = { ...DEFAULT_CONFIG, allowlist: [] }
  const lines = yaml.split(/\r?\n/)
  let inAllowlist = false
  for (const rawLine of lines) {
    if (rawLine.startsWith('#')) continue
    if (rawLine.trim() === '') {
      inAllowlist = false
      continue
    }
    if (inAllowlist && /^\s*-\s+/.test(rawLine)) {
      const item = rawLine.replace(/^\s*-\s+/, '').trim().replace(/^["']|["']$/g, '')
      if (item) cfg.allowlist.push(item)
      continue
    }
    inAllowlist = false
    const colonIdx = rawLine.indexOf(':')
    if (colonIdx < 0) continue
    const key = rawLine.slice(0, colonIdx).trim()
    const value = rawLine.slice(colonIdx + 1).trim()
    switch (key) {
      case 'enabled':
        cfg.enabled = parseBool(value, cfg.enabled)
        break
      case 'pollIntervalMs':
        cfg.pollIntervalMs = parseInt(value, 10) || cfg.pollIntervalMs
        break
      case 'autoSyncIntervalMs':
        cfg.autoSyncIntervalMs = parseInt(value, 10) || 0
        break
      case 'allowlistEnforced':
        cfg.allowlistEnforced = parseBool(value, cfg.allowlistEnforced)
        break
      case 'allowlist':
        if (value === '' || value === '[]') {
          inAllowlist = value === ''
        } else if (value.startsWith('[') && value.endsWith(']')) {
          const inner = value.slice(1, -1).trim()
          if (inner) {
            cfg.allowlist = inner
              .split(',')
              .map(s => s.trim().replace(/^["']|["']$/g, ''))
              .filter(Boolean)
          }
        }
        break
    }
  }
  return cfg
}

export function serializeConfig(config: ChannelConfig): string {
  const lines: string[] = []
  lines.push(`enabled: ${config.enabled}`)
  lines.push(`pollIntervalMs: ${config.pollIntervalMs}`)
  lines.push(`autoSyncIntervalMs: ${config.autoSyncIntervalMs}`)
  lines.push(`allowlistEnforced: ${config.allowlistEnforced}`)
  if (config.allowlist.length === 0) {
    lines.push('allowlist: []')
  } else {
    lines.push('allowlist:')
    for (const item of config.allowlist) {
      lines.push(`  - ${item}`)
    }
  }
  return lines.join('\n') + '\n'
}

function parseBool(value: string, fallback: boolean): boolean {
  const v = value.toLowerCase()
  if (v === 'true' || v === 'yes' || v === '1') return true
  if (v === 'false' || v === 'no' || v === '0') return false
  return fallback
}
