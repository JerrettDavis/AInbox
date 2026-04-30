import fs from 'node:fs/promises'
import path from 'node:path'
import os from 'node:os'

export interface ChannelState {
  version: number
  project: string
  folders: {
    inbox: string[]
    sent: string[]
    archive: string[]
  }
  lastTickAt: string | null
}

export const STATE_VERSION = 1

const HOME_MAILBOX = path.join(os.homedir(), '.mailbox')
export const STATE_FILE = path.join(HOME_MAILBOX, 'channel-state.json')

export function emptyState(project: string): ChannelState {
  return {
    version: STATE_VERSION,
    project,
    folders: { inbox: [], sent: [], archive: [] },
    lastTickAt: null,
  }
}

export type LoadOutcome =
  | { kind: 'fresh'; state: ChannelState }
  | { kind: 'matched'; state: ChannelState }
  | { kind: 'mismatched'; state: ChannelState }
  | { kind: 'corrupt'; state: ChannelState }

export async function loadStateOutcome(project: string, statePath = STATE_FILE): Promise<LoadOutcome> {
  let raw: string
  try {
    raw = await fs.readFile(statePath, 'utf-8')
  } catch {
    return { kind: 'fresh', state: emptyState(project) }
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return { kind: 'corrupt', state: emptyState(project) }
  }
  if (!isChannelState(parsed)) return { kind: 'corrupt', state: emptyState(project) }
  if (parsed.project !== project) return { kind: 'mismatched', state: emptyState(project) }
  return { kind: 'matched', state: parsed }
}

export async function loadState(project: string, statePath = STATE_FILE): Promise<ChannelState> {
  const outcome = await loadStateOutcome(project, statePath)
  return outcome.state
}

export async function saveState(state: ChannelState, statePath = STATE_FILE): Promise<void> {
  await fs.mkdir(path.dirname(statePath), { recursive: true })
  // tmp is placed in the same directory as the target so fs.rename is always
  // an intra-volume move. This invariant prevents EXDEV on single-drive setups.
  // If the OS still raises EXDEV (e.g. bind-mounts or cross-drive TEMP), fall
  // back to copy + unlink rather than leaving a stale tmp file.
  const tmp = `${statePath}.${process.pid}.${Date.now()}.tmp`
  await fs.writeFile(tmp, JSON.stringify(state, null, 2), 'utf-8')
  try {
    await fs.rename(tmp, statePath)
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === 'EXDEV') {
      await fs.copyFile(tmp, statePath)
      await fs.unlink(tmp)
    } else {
      throw err
    }
  }
}

function isChannelState(v: unknown): v is ChannelState {
  if (!v || typeof v !== 'object') return false
  const o = v as Record<string, unknown>
  if (typeof o.version !== 'number') return false
  if (typeof o.project !== 'string') return false
  if (!o.folders || typeof o.folders !== 'object') return false
  const f = o.folders as Record<string, unknown>
  for (const k of ['inbox', 'sent', 'archive']) {
    if (!Array.isArray(f[k])) return false
    if (!(f[k] as unknown[]).every(x => typeof x === 'string')) return false
  }
  return true
}
