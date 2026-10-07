import { apiFetch, errorFromResponse } from '@/lib/api'
import type { StreamEvent } from '@/types/api'

/** Splits an NDJSON byte stream into parsed events, tolerating chunks that end mid-line. */
export function createNdjsonParser(onEvent: (event: StreamEvent) => void) {
  const decoder = new TextDecoder()
  let buffer = ''

  function emitLine(line: string) {
    const trimmed = line.trim()
    if (!trimmed) return
    try {
      onEvent(JSON.parse(trimmed) as StreamEvent)
    } catch {
      // A malformed line is skipped rather than ending the whole stream.
    }
  }

  return {
    push(chunk: Uint8Array) {
      buffer += decoder.decode(chunk, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      lines.forEach(emitLine)
    },
    end() {
      buffer += decoder.decode()
      emitLine(buffer)
      buffer = ''
    },
  }
}

export type SendMessageBody = { content: string; cart_item_ids?: number[] }

export async function streamMessage(
  conversationId: string,
  body: SendMessageBody,
  { signal, onEvent }: { signal: AbortSignal; onEvent: (event: StreamEvent) => void },
) {
  const response = await apiFetch(`/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    body,
    signal,
    accept: 'application/x-ndjson',
  })
  if (!response.ok) throw await errorFromResponse(response, 'Could not send the message')
  if (!response.body) throw new Error('The server returned an empty response.')

  const parser = createNdjsonParser(onEvent)
  const reader = response.body.getReader()
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    parser.push(value)
  }
  parser.end()
}
