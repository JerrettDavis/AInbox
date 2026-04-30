import { describe, expect, test, beforeEach, afterEach } from 'bun:test'
import path from 'node:path'
import os from 'node:os'
import fs from 'node:fs/promises'
import { runMailbox, _resetMailboxResolution } from '../lib/mailbox-cli.ts'

let tmpDir: string
let stubPath: string

beforeEach(async () => {
  tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'mailbox-cli-test-'))
  if (process.platform === 'win32') {
    stubPath = path.join(tmpDir, 'mailbox-stub.cmd')
    await fs.writeFile(
      stubPath,
      '@echo off\r\necho ARGS: %*\r\nexit /b 0\r\n',
      'utf-8',
    )
  } else {
    stubPath = path.join(tmpDir, 'mailbox-stub.sh')
    await fs.writeFile(stubPath, '#!/bin/sh\necho "ARGS: $@"\nexit 0\n', 'utf-8')
    await fs.chmod(stubPath, 0o755)
  }
  process.env.MAILBOX_BIN = stubPath
  _resetMailboxResolution()
})

afterEach(async () => {
  delete process.env.MAILBOX_BIN
  _resetMailboxResolution()
  await fs.rm(tmpDir, { recursive: true, force: true })
})

describe('runMailbox', () => {
  test('passes argv to stub and captures stdout', async () => {
    const result = await runMailbox(['send', '--to', 'alice', '--subject', 'hi', '--body', 'yo'])
    expect(result.exitCode).toBe(0)
    expect(result.stdout).toContain('--to')
    expect(result.stdout).toContain('alice')
    expect(result.stdout).toContain('--subject')
    expect(result.stdout).toContain('hi')
    expect(result.stdout).toContain('--body')
    expect(result.stdout).toContain('yo')
  })

  test('sync push-only flag composition', async () => {
    const result = await runMailbox(['sync', '--push-only'])
    expect(result.exitCode).toBe(0)
    expect(result.stdout).toContain('sync')
    expect(result.stdout).toContain('--push-only')
  })

  test('list with json format', async () => {
    const result = await runMailbox(['list', '--limit', '5', '--format', 'json'])
    expect(result.exitCode).toBe(0)
    expect(result.stdout).toContain('--format')
    expect(result.stdout).toContain('json')
  })
})
