import { describe, expect, it } from 'vitest'

import { createNdjsonParser } from '@/lib/stream'
import type { StreamEvent } from '@/types/api'

const encode = (text: string) => new TextEncoder().encode(text)

describe('createNdjsonParser', () => {
  it('emits one event per line, including lines split across chunks', () => {
    const events: StreamEvent[] = []
    const parser = createNdjsonParser((event) => events.push(event))
    parser.push(encode('{"type":"ping"}\n{"type":"tok'))
    parser.push(encode('en","message_id":1,"text":"Hi"}\n'))
    parser.end()
    expect(events).toEqual([{ type: 'ping' }, { type: 'token', message_id: 1, text: 'Hi' }])
  })

  it('flushes a final line without a trailing newline', () => {
    const events: StreamEvent[] = []
    const parser = createNdjsonParser((event) => events.push(event))
    parser.push(encode('{"type":"done","status":"complete"}'))
    expect(events).toEqual([])
    parser.end()
    expect(events).toEqual([{ type: 'done', status: 'complete' }])
  })

  it('skips blank and malformed lines without stopping', () => {
    const events: StreamEvent[] = []
    const parser = createNdjsonParser((event) => events.push(event))
    parser.push(encode('\n{not json}\n\n{"type":"ping"}\n'))
    parser.end()
    expect(events).toEqual([{ type: 'ping' }])
  })

  it('handles multi-byte characters split across chunks', () => {
    const events: StreamEvent[] = []
    const parser = createNdjsonParser((event) => events.push(event))
    const bytes = encode('{"type":"token","message_id":2,"text":"R 1 299 – café"}\n')
    const cut = bytes.indexOf(0xc3) + 1
    parser.push(bytes.slice(0, cut))
    parser.push(bytes.slice(cut))
    parser.end()
    expect(events).toEqual([{ type: 'token', message_id: 2, text: 'R 1 299 – café' }])
  })
})
