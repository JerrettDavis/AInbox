import fs from 'node:fs/promises'
import path from 'node:path'

export interface MailboxResult {
  stdout: string
  stderr: string
  exitCode: number
}

export interface MailboxRunOptions {
  cwd?: string
  env?: Record<string, string | undefined>
  timeoutMs?: number
}

let cachedResolution: ResolvedCommand | null = null

interface ResolvedCommand {
  cmd: string
  prefix: string[]
}

async function fileExists(p: string): Promise<boolean> {
  try {
    const s = await fs.stat(p)
    return s.isFile()
  } catch {
    return false
  }
}

async function findOnPath(name: string): Promise<string | null> {
  const PATH = process.env.PATH ?? ''
  const exts = process.platform === 'win32' ? (process.env.PATHEXT ?? '.EXE;.CMD;.BAT').split(';') : ['']
  for (const dir of PATH.split(path.delimiter)) {
    if (!dir) continue
    for (const ext of exts) {
      const candidate = path.join(dir, name + ext)
      if (await fileExists(candidate)) return candidate
    }
  }
  return null
}

export async function resolveMailboxCommand(): Promise<ResolvedCommand> {
  if (cachedResolution) return cachedResolution
  if (process.env.MAILBOX_BIN) {
    cachedResolution = { cmd: process.env.MAILBOX_BIN, prefix: [] }
    return cachedResolution
  }
  const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT
  if (pluginRoot) {
    const binName = process.platform === 'win32' ? 'mailbox.exe' : 'mailbox'
    const candidate = path.join(pluginRoot, 'bin', binName)
    if (await fileExists(candidate)) {
      cachedResolution = { cmd: candidate, prefix: [] }
      return cachedResolution
    }
  }
  const onPath = await findOnPath(process.platform === 'win32' ? 'mailbox.exe' : 'mailbox')
  if (onPath) {
    cachedResolution = { cmd: onPath, prefix: [] }
    return cachedResolution
  }
  const python = process.platform === 'win32' ? 'python' : 'python3'
  const pythonResolved = await findOnPath(python) ?? (process.platform === 'win32' ? await findOnPath('python.exe') : null)
  if (pythonResolved) {
    cachedResolution = { cmd: pythonResolved, prefix: ['-m', 'ainbox.cli'] }
    return cachedResolution
  }
  throw new Error(
    'mailbox CLI not found. Install via the AInbox plugin, add `mailbox` to PATH, or set MAILBOX_BIN.',
  )
}

export function _resetMailboxResolution(): void {
  cachedResolution = null
}

export async function runMailbox(args: string[], opts: MailboxRunOptions = {}): Promise<MailboxResult> {
  const resolved = await resolveMailboxCommand()
  const argv = [resolved.cmd, ...resolved.prefix, ...args]
  const timeoutMs = opts.timeoutMs ?? 15000

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const proc = Bun.spawn(argv, {
      cwd: opts.cwd ?? process.cwd(),
      env: opts.env ? { ...process.env, ...opts.env } as Record<string, string> : process.env as Record<string, string>,
      stdin: 'ignore',
      stdout: 'pipe',
      stderr: 'pipe',
      signal: controller.signal,
    })
    const [stdout, stderr, exitCode] = await Promise.all([
      new Response(proc.stdout).text(),
      new Response(proc.stderr).text(),
      proc.exited,
    ])
    return { stdout, stderr, exitCode: typeof exitCode === 'number' ? exitCode : -1 }
  } finally {
    clearTimeout(timeout)
  }
}
