import { describe, expect, test } from 'bun:test'
import { sanitizeMetaValue } from '../server.ts'

describe('sanitizeMetaValue', () => {
  test('passes normal ASCII through unchanged', () => {
    expect(sanitizeMetaValue('hello-world')).toBe('hello-world')
    expect(sanitizeMetaValue('agent@example.com')).toBe('agent@example.com')
    expect(sanitizeMetaValue('Re: Task update')).toBe('Re: Task update')
  })

  test('strips newline characters', () => {
    expect(sanitizeMetaValue('foo\nbar')).toBe('foo bar')
    expect(sanitizeMetaValue('foo\r\nbar')).toBe('foo bar')
    expect(sanitizeMetaValue('foo\rbar')).toBe('foo bar')
    expect(sanitizeMetaValue('a\nb\nc')).toBe('a b c')
  })

  test('strips tab characters', () => {
    expect(sanitizeMetaValue('foo\tbar')).toBe('foo bar')
  })

  test('strips angle brackets', () => {
    expect(sanitizeMetaValue('foo<bar>baz')).toBe('foobarbaz')
    expect(sanitizeMetaValue('<script>alert(1)</script>')).toBe('scriptalert(1)/script')
  })

  test('strips double and single quotes', () => {
    expect(sanitizeMetaValue('say "hello"')).toBe('say hello')
    expect(sanitizeMetaValue("it's fine")).toBe('its fine')
  })

  test('strips backticks', () => {
    expect(sanitizeMetaValue('`code`')).toBe('code')
  })

  test('collapses runs of whitespace to a single space', () => {
    expect(sanitizeMetaValue('foo   bar')).toBe('foo bar')
    expect(sanitizeMetaValue('a\n\nb')).toBe('a b')
  })

  test('trims leading and trailing whitespace', () => {
    expect(sanitizeMetaValue('  hello  ')).toBe('hello')
    expect(sanitizeMetaValue('\n  hello\n')).toBe('hello')
  })

  test('truncates to 256 characters', () => {
    const long = 'a'.repeat(300)
    const result = sanitizeMetaValue(long)
    expect(result.length).toBe(256)
  })

  test('injection attempt: newline + attribute forgery', () => {
    // \n → space, " stripped, then whitespace collapsed → single space
    const evil = 'legit\n" event="malicious'
    const result = sanitizeMetaValue(evil)
    expect(result).not.toContain('\n')
    expect(result).not.toContain('"')
    expect(result).toBe('legit event=malicious')
  })
})
