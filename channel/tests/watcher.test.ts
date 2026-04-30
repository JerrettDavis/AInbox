import { describe, expect, test, beforeEach, afterEach } from 'bun:test'
import path from 'node:path'
import os from 'node:os'
import fs from 'node:fs/promises'
import { startWatcher, diffTick, type ChannelEvent } from '../lib/watcher.ts'
import { emptyState } from '../lib/state.ts'

function buildMessage(opts: {
  id: string
  from: string
  to: string
  subject: string
  sent_at: string
  received_at?: string
  read_at?: string
  correlation_id?: string
  body: string
}): string {
  const lines = ['---']
  lines.push(`id: ${opts.id}`)
  lines.push(`to: ${opts.to}`)
  lines.push(`from: ${opts.from}`)
  lines.push(`subject: ${opts.subject}`)
  lines.push(`sent_at: ${opts.sent_at}`)
  lines.push(`received_at: ${opts.received_at ?? 'null'}`)
  lines.push(`read_at: ${opts.read_at ?? 'null'}`)
  if (opts.correlation_id) lines.push(`correlation_id: ${opts.correlation_id}`)
  lines.push('---', '', opts.body)
  return lines.join('\n') + '\n'
}

let workspace: string
let statePath: string

beforeEach(async () => {
  workspace = await fs.mkdtemp(path.join(os.tmpdir(), 'ainbox-watcher-'))
  await fs.mkdir(path.join(workspace, '.mailbox', 'inbox'), { recursive: true })
  await fs.mkdir(path.join(workspace, '.mailbox', 'sent'), { recursive: true })
  await fs.mkdir(path.join(workspace, '.mailbox', 'archive'), { recursive: true })
  statePath = path.join(workspace, 'channel-state.json')
})

afterEach(async () => {
  await fs.rm(workspace, { recursive: true, force: true })
})

describe('diffTick', () => {
  test('emits received event for new inbox message', async () => {
    const file = '20260430T120000Z_msg1.md'
    await fs.writeFile(
      path.join(workspace, '.mailbox', 'inbox', file),
      buildMessage({
        id: 'msg1',
        from: 'alice',
        to: 'bob',
        subject: 'hello',
        sent_at: '2026-04-30T12:00:00Z',
        body: 'hi there',
      }),
    )
    const state = emptyState(workspace)
    const { events, nextState } = await diffTick({ cwd: workspace, state, allowlist: null, maxFilesPerFolder: 1000 })
    expect(events).toHaveLength(1)
    expect(events[0]?.event).toBe('received')
    expect(events[0]?.msg.id).toBe('msg1')
    expect(events[0]?.bodyPreview).toBe('hi there')
    expect(nextState.folders.inbox).toContain(file)
  })

  test('does not re-emit known messages', async () => {
    const file = '20260430T120000Z_msg1.md'
    await fs.writeFile(
      path.join(workspace, '.mailbox', 'inbox', file),
      buildMessage({
        id: 'msg1',
        from: 'alice',
        to: 'bob',
        subject: 'hello',
        sent_at: '2026-04-30T12:00:00Z',
        body: 'hi',
      }),
    )
    const state = emptyState(workspace)
    state.folders.inbox = [file]
    const { events } = await diffTick({ cwd: workspace, state, allowlist: null, maxFilesPerFolder: 1000 })
    expect(events).toHaveLength(0)
  })

  test('archive without read_at does not emit read event', async () => {
    const file = '20260430T120000Z_msg2.md'
    await fs.writeFile(
      path.join(workspace, '.mailbox', 'archive', file),
      buildMessage({
        id: 'msg2',
        from: 'a',
        to: 'b',
        subject: 's',
        sent_at: '2026-04-30T12:00:00Z',
        body: 'b',
      }),
    )
    const state = emptyState(workspace)
    const { events } = await diffTick({ cwd: workspace, state, allowlist: null, maxFilesPerFolder: 1000 })
    expect(events).toHaveLength(0)
  })

  test('archive with read_at emits read event', async () => {
    const file = '20260430T120000Z_msg2.md'
    await fs.writeFile(
      path.join(workspace, '.mailbox', 'archive', file),
      buildMessage({
        id: 'msg2',
        from: 'a',
        to: 'b',
        subject: 's',
        sent_at: '2026-04-30T12:00:00Z',
        read_at: '2026-04-30T12:05:00Z',
        body: 'b',
      }),
    )
    const state = emptyState(workspace)
    const { events } = await diffTick({ cwd: workspace, state, allowlist: null, maxFilesPerFolder: 1000 })
    expect(events).toHaveLength(1)
    expect(events[0]?.event).toBe('read')
  })

  test('sent folder emits sent event', async () => {
    const file = '20260430T120000Z_msg3.md'
    await fs.writeFile(
      path.join(workspace, '.mailbox', 'sent', file),
      buildMessage({
        id: 'msg3',
        from: 'me',
        to: 'them',
        subject: 'x',
        sent_at: '2026-04-30T12:00:00Z',
        body: 'sent body',
      }),
    )
    const state = emptyState(workspace)
    const { events } = await diffTick({ cwd: workspace, state, allowlist: null, maxFilesPerFolder: 1000 })
    expect(events).toHaveLength(1)
    expect(events[0]?.event).toBe('sent')
  })

  test('allowlist filters inbox events', async () => {
    const file = '20260430T120000Z_msg4.md'
    await fs.writeFile(
      path.join(workspace, '.mailbox', 'inbox', file),
      buildMessage({
        id: 'msg4',
        from: 'stranger',
        to: 'me',
        subject: 'hi',
        sent_at: '2026-04-30T12:00:00Z',
        body: 'b',
      }),
    )
    const state = emptyState(workspace)
    const allowed = new Set(['friend'])
    const { events } = await diffTick({ cwd: workspace, state, allowlist: allowed, maxFilesPerFolder: 1000 })
    expect(events).toHaveLength(0)
  })
})

describe('startWatcher', () => {
  test('runs initial tick and persists state', async () => {
    const file = '20260430T120000Z_msg-watch.md'
    await fs.writeFile(
      path.join(workspace, '.mailbox', 'inbox', file),
      buildMessage({
        id: 'msg-watch',
        from: 'alice',
        to: 'bob',
        subject: 'wake up',
        sent_at: '2026-04-30T12:00:00Z',
        body: 'rise and shine',
      }),
    )
    const events: ChannelEvent[] = []
    const handle = await startWatcher({
      cwd: workspace,
      pollIntervalMs: 100000,
      statePath,
      onEvent: e => {
        events.push(e)
      },
    })
    await handle.tickOnce()
    await handle.stop()
    expect(events.length).toBeGreaterThan(0)
    const stateRaw = await fs.readFile(statePath, 'utf-8')
    expect(stateRaw).toContain('msg-watch')
  })
})
