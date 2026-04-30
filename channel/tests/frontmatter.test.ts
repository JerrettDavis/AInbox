import { describe, expect, test } from 'bun:test'
import path from 'node:path'
import { parseFrontmatter, bodyPreview, FrontmatterError } from '../lib/frontmatter.ts'

const FIXTURES = path.join(import.meta.dir, 'fixtures')

describe('parseFrontmatter', () => {
  test('parses fixture with body containing ---', async () => {
    const content = await Bun.file(path.join(FIXTURES, 'sample.md')).text()
    const msg = parseFrontmatter(content)
    expect(msg.id).toBe('abc123')
    expect(msg.to).toBe('claude-agent')
    expect(msg.from).toBe('worker-agent')
    expect(msg.subject).toBe('PR ready for review')
    expect(msg.sent_at).toBe('2026-04-15T22:31:00Z')
    expect(msg.received_at).toBe('2026-04-15T22:32:00Z')
    expect(msg.read_at).toBeNull()
    expect(msg.correlation_id).toBe('thread-42')
    expect(msg.expires_at).toBeNull()
    expect(msg.body).toContain('not a frontmatter delimiter')
    expect(msg.body).toContain('Hey Claude,')
  })

  test('handles missing optional correlation_id', () => {
    const content = [
      '---',
      'id: m1',
      'to: a',
      'from: b',
      'subject: s',
      'sent_at: 2026-04-30T12:00:00Z',
      '---',
      '',
      'body',
      '',
    ].join('\n')
    const msg = parseFrontmatter(content)
    expect(msg.correlation_id).toBeNull()
    expect(msg.received_at).toBeNull()
    expect(msg.read_at).toBeNull()
    expect(msg.body).toBe('body')
  })

  test('null literal in nullable field becomes null', () => {
    const content = [
      '---',
      'id: m1',
      'to: a',
      'from: b',
      'subject: s',
      'sent_at: 2026-04-30T12:00:00Z',
      'received_at: null',
      'read_at: null',
      'correlation_id: null',
      '---',
      '',
      'hi',
    ].join('\n')
    const msg = parseFrontmatter(content)
    expect(msg.received_at).toBeNull()
    expect(msg.read_at).toBeNull()
    expect(msg.correlation_id).toBeNull()
  })

  test('throws on missing opening delimiter', () => {
    expect(() => parseFrontmatter('no frontmatter here')).toThrow(FrontmatterError)
  })

  test('throws on missing closing delimiter', () => {
    const content = '---\nid: x\nto: a\nfrom: b\nsubject: s\nsent_at: 2026-04-30T12:00:00Z\n'
    expect(() => parseFrontmatter(content)).toThrow(FrontmatterError)
  })

  test('throws on missing required field', () => {
    const content = '---\nid: m1\nto: a\nfrom: b\nsubject: s\n---\nbody'
    expect(() => parseFrontmatter(content)).toThrow(FrontmatterError)
  })

  test('handles CRLF line endings', () => {
    const content =
      '---\r\nid: m1\r\nto: a\r\nfrom: b\r\nsubject: s\r\nsent_at: 2026-04-30T12:00:00Z\r\n---\r\n\r\nbody\r\n'
    const msg = parseFrontmatter(content)
    expect(msg.id).toBe('m1')
    expect(msg.body).toBe('body')
  })
})

describe('bodyPreview', () => {
  test('collapses newlines to spaces', () => {
    expect(bodyPreview('line one\nline two\n\nline three')).toBe('line one line two line three')
  })

  test('truncates over max', () => {
    const long = 'a'.repeat(500)
    const out = bodyPreview(long, 280)
    expect(out.length).toBe(280)
    expect(out.endsWith('…')).toBe(true)
  })

  test('preserves short body verbatim', () => {
    expect(bodyPreview('short', 280)).toBe('short')
  })
})
