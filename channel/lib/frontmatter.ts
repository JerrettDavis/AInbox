export interface ParsedMessage {
  id: string
  to: string
  from: string
  subject: string
  sent_at: string
  received_at: string | null
  read_at: string | null
  correlation_id: string | null
  expires_at: string | null
  body: string
}

const REQUIRED = ['id', 'to', 'from', 'subject', 'sent_at'] as const
const NULLABLE = new Set(['received_at', 'read_at', 'correlation_id', 'expires_at'])

export class FrontmatterError extends Error {}

export function parseFrontmatter(content: string): ParsedMessage {
  const lines = content.split(/\r?\n/)
  if (lines.length < 3 || lines[0]?.trim() !== '---') {
    throw new FrontmatterError('Missing opening --- delimiter')
  }
  let closingIdx = -1
  for (let i = 1; i < lines.length; i++) {
    if (lines[i]?.trim() === '---') {
      closingIdx = i
      break
    }
  }
  if (closingIdx < 0) {
    throw new FrontmatterError('Missing closing --- delimiter')
  }

  const fields = new Map<string, string | null>()
  for (let i = 1; i < closingIdx; i++) {
    const raw = lines[i] ?? ''
    const line = raw.trim()
    if (!line || line.startsWith('#')) continue
    const colonIdx = line.indexOf(':')
    if (colonIdx < 0) continue
    const key = line.slice(0, colonIdx).trim()
    const value = line.slice(colonIdx + 1).trim()
    if (value.toLowerCase() === 'null' && NULLABLE.has(key)) {
      fields.set(key, null)
    } else {
      fields.set(key, value)
    }
  }

  for (const k of REQUIRED) {
    if (!fields.has(k) || fields.get(k) === null) {
      throw new FrontmatterError(`Missing required field: ${k}`)
    }
  }

  const bodyLines = lines.slice(closingIdx + 1)
  if (bodyLines.length > 0 && bodyLines[0]?.trim() === '') {
    bodyLines.shift()
  }
  const body = bodyLines.join('\n').replace(/\s+$/, '')

  return {
    id: fields.get('id') as string,
    to: fields.get('to') as string,
    from: fields.get('from') as string,
    subject: fields.get('subject') as string,
    sent_at: fields.get('sent_at') as string,
    received_at: (fields.get('received_at') ?? null) as string | null,
    read_at: (fields.get('read_at') ?? null) as string | null,
    correlation_id: (fields.get('correlation_id') ?? null) as string | null,
    expires_at: (fields.get('expires_at') ?? null) as string | null,
    body,
  }
}

export function bodyPreview(body: string, max = 280): string {
  const collapsed = body.replace(/\s+/g, ' ').trim()
  if (collapsed.length <= max) return collapsed
  return collapsed.slice(0, max - 1).trimEnd() + '…'
}
