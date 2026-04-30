import { describe, expect, test } from 'bun:test'
import path from 'node:path'

const SERVER_PATH = path.resolve(import.meta.dir, '..', 'server.ts')

interface JsonRpcResponse {
  jsonrpc: '2.0'
  id?: number
  result?: any
  error?: { code: number; message: string }
}

class LineReader {
  private buf = ''
  private iter: AsyncIterableIterator<Uint8Array>
  private decoder = new TextDecoder()

  constructor(stream: AsyncIterable<Uint8Array>) {
    this.iter = stream[Symbol.asyncIterator]() as AsyncIterableIterator<Uint8Array>
  }

  async nextResponseFor(id: number): Promise<JsonRpcResponse> {
    while (true) {
      const newlineIdx = this.buf.indexOf('\n')
      if (newlineIdx >= 0) {
        const line = this.buf.slice(0, newlineIdx).trim()
        this.buf = this.buf.slice(newlineIdx + 1)
        if (!line) continue
        const parsed = JSON.parse(line) as JsonRpcResponse
        if (parsed.id === id) return parsed
        continue
      }
      const next = await this.iter.next()
      if (next.done) throw new Error('server stdout closed before response arrived')
      this.buf += this.decoder.decode(next.value, { stream: true })
    }
  }
}

describe('channel server', () => {
  test('responds to initialize and exposes three tools', async () => {
    const proc = Bun.spawn(['bun', SERVER_PATH], {
      stdin: 'pipe',
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...process.env,
        MAILBOX_BIN: process.platform === 'win32' ? 'cmd.exe' : '/bin/true',
      },
    })

    const stdin = proc.stdin
    if (typeof stdin === 'number') throw new Error('expected piped stdin')

    const stdout = proc.stdout as AsyncIterable<Uint8Array>
    const reader = new LineReader(stdout)

    const writeMessage = async (obj: object): Promise<void> => {
      stdin.write(JSON.stringify(obj) + '\n')
      await stdin.flush()
    }

    try {
      await writeMessage({
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2025-11-25',
          capabilities: {},
          clientInfo: { name: 'test-client', version: '0.0.1' },
        },
      })
      const initResponse = await reader.nextResponseFor(1)
      expect(initResponse.error).toBeUndefined()
      expect(initResponse.result).toBeDefined()
      expect(initResponse.result.serverInfo.name).toBe('ainbox')
      expect(initResponse.result.capabilities.tools).toBeDefined()
      expect(initResponse.result.capabilities.experimental).toBeDefined()
      expect(initResponse.result.capabilities.experimental['claude/channel']).toBeDefined()
      expect(typeof initResponse.result.instructions).toBe('string')
      expect(initResponse.result.instructions).toContain('channel')

      await writeMessage({ jsonrpc: '2.0', method: 'notifications/initialized' })

      await writeMessage({ jsonrpc: '2.0', id: 2, method: 'tools/list' })
      const toolsResponse = await reader.nextResponseFor(2)
      expect(toolsResponse.error).toBeUndefined()
      const tools = toolsResponse.result.tools as Array<{ name: string }>
      expect(tools).toHaveLength(3)
      const names = tools.map(t => t.name).sort()
      expect(names).toEqual(['list_inbox', 'mark_read', 'reply'])
    } finally {
      try {
        stdin.end()
      } catch {}
      proc.kill()
      await proc.exited
    }
  }, 30_000)
})
