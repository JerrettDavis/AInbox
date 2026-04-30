import fs from 'node:fs/promises'
import path from 'node:path'
import { parseFrontmatter, bodyPreview, type ParsedMessage } from './frontmatter.ts'
import { loadStateOutcome, saveState, emptyState, type ChannelState, STATE_FILE } from './state.ts'

export type ChannelEventKind = 'received' | 'sent' | 'read'

export interface ChannelEvent {
  event: ChannelEventKind
  msg: ParsedMessage
  bodyPreview: string
}

export type Folder = 'inbox' | 'sent' | 'archive'

export interface WatcherOptions {
  cwd?: string
  pollIntervalMs?: number
  autoSyncIntervalMs?: number
  allowlist?: Set<string> | null
  statePath?: string
  onEvent: (e: ChannelEvent) => void | Promise<void>
  onSync?: () => void | Promise<void>
  log?: (msg: string) => void
  maxFilesPerFolder?: number
}

export interface WatcherHandle {
  stop(): Promise<void>
  tickOnce(): Promise<void>
}

const FOLDERS: Folder[] = ['inbox', 'sent', 'archive']

const FOLDER_TO_EVENT: Record<Folder, ChannelEventKind> = {
  inbox: 'received',
  sent: 'sent',
  archive: 'read',
}

export async function listMessageFiles(dir: string, max: number): Promise<string[]> {
  let entries: string[]
  try {
    entries = await fs.readdir(dir)
  } catch (err) {
    const e = err as NodeJS.ErrnoException
    if (e.code === 'ENOENT') return []
    throw err
  }
  const md = entries.filter(n => n.endsWith('.md'))
  md.sort()
  if (md.length > max) return md.slice(md.length - max)
  return md
}

export async function readMessage(filePath: string): Promise<ParsedMessage | null> {
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    return parseFrontmatter(content)
  } catch {
    return null
  }
}

export async function diffTick(args: {
  cwd: string
  state: ChannelState
  allowlist: Set<string> | null
  maxFilesPerFolder: number
}): Promise<{ events: ChannelEvent[]; nextState: ChannelState }> {
  const { cwd, state, allowlist, maxFilesPerFolder } = args
  const localMailbox = path.join(cwd, '.mailbox')

  const nextFolders: ChannelState['folders'] = { inbox: [], sent: [], archive: [] }
  const events: ChannelEvent[] = []

  for (const folder of FOLDERS) {
    const dir = path.join(localMailbox, folder)
    const current = await listMessageFiles(dir, maxFilesPerFolder)
    nextFolders[folder] = current

    const known = new Set(state.folders[folder])
    for (const name of current) {
      if (known.has(name)) continue
      const fp = path.join(dir, name)
      const msg = await readMessage(fp)
      if (!msg) continue
      if (folder === 'archive' && msg.read_at == null) continue
      if (folder === 'inbox' && allowlist && !allowlist.has(msg.from)) continue
      events.push({
        event: FOLDER_TO_EVENT[folder],
        msg,
        bodyPreview: bodyPreview(msg.body),
      })
    }
  }

  const nextState: ChannelState = {
    version: state.version,
    project: cwd,
    folders: nextFolders,
    lastTickAt: new Date().toISOString(),
  }
  return { events, nextState }
}

export async function startWatcher(opts: WatcherOptions): Promise<WatcherHandle> {
  const cwd = opts.cwd ?? process.cwd()
  const pollIntervalMs = opts.pollIntervalMs ?? 2000
  const autoSyncIntervalMs = opts.autoSyncIntervalMs ?? 0
  const allowlist = opts.allowlist ?? null
  const statePath = opts.statePath ?? STATE_FILE
  const log = opts.log ?? (() => {})
  const maxFilesPerFolder = opts.maxFilesPerFolder ?? 5000

  const outcome = await loadStateOutcome(cwd, statePath)
  let state: ChannelState
  if (outcome.kind === 'mismatched' || outcome.kind === 'corrupt') {
    state = await primeStateFromFilesystem(cwd, maxFilesPerFolder)
    await saveState(state, statePath)
    log(`channel state ${outcome.kind}; primed from filesystem to avoid replay`)
  } else {
    state = outcome.state
  }

  let stopped = false
  let inflight: Promise<void> | null = null

  const runTick = async (): Promise<void> => {
    if (stopped) return
    try {
      const { events, nextState } = await diffTick({ cwd, state, allowlist, maxFilesPerFolder })
      state = nextState
      await saveState(state, statePath)
      for (const e of events) {
        try {
          await opts.onEvent(e)
        } catch (err) {
          log(`channel onEvent error: ${(err as Error).message}`)
        }
      }
    } catch (err) {
      log(`watcher tick error: ${(err as Error).message}`)
    }
  }

  const tick = async (): Promise<void> => {
    if (inflight) {
      await inflight
      return
    }
    const p = runTick().finally(() => {
      inflight = null
    })
    inflight = p
    await p
  }

  const pollTimer = setInterval(() => {
    void tick()
  }, pollIntervalMs)

  let syncTimer: ReturnType<typeof setInterval> | null = null
  if (autoSyncIntervalMs > 0 && opts.onSync) {
    syncTimer = setInterval(() => {
      void (async () => {
        try {
          await opts.onSync!()
        } catch (err) {
          log(`watcher sync error: ${(err as Error).message}`)
        }
      })()
    }, autoSyncIntervalMs)
  }

  void tick()

  return {
    async stop() {
      stopped = true
      clearInterval(pollTimer)
      if (syncTimer) clearInterval(syncTimer)
    },
    async tickOnce() {
      await tick()
    },
  }
}

async function primeStateFromFilesystem(cwd: string, max: number): Promise<ChannelState> {
  const localMailbox = path.join(cwd, '.mailbox')
  const folders: ChannelState['folders'] = { inbox: [], sent: [], archive: [] }
  for (const folder of FOLDERS) {
    folders[folder] = await listMessageFiles(path.join(localMailbox, folder), max)
  }
  return {
    version: emptyState(cwd).version,
    project: cwd,
    folders,
    lastTickAt: new Date().toISOString(),
  }
}
