import { describe, expect, it } from 'vitest'

import { applyStreamEvent } from '@/components/chat/chat-events'
import type { ChatMessage, Conversation } from '@/types/api'

const message = (id: number, overrides: Partial<ChatMessage> = {}): ChatMessage => ({
  id,
  conversation_id: 'c1',
  role: 'assistant',
  agent: 'orchestrator',
  content: '',
  status: 'streaming',
  payload: {},
  created_at: '2026-10-06T10:00:00Z',
  ...overrides,
})

const conversation = (messages: ChatMessage[]): Conversation => ({
  id: 'c1',
  title: 'New conversation',
  created_at: '2026-10-06T10:00:00Z',
  updated_at: '2026-10-06T10:00:00Z',
  running: false,
  messages,
  product_count: 0,
  source_count: 0,
})

describe('applyStreamEvent', () => {
  it('replaces the optimistic user message with the saved one and adopts the new title', () => {
    const pending = message(-1, { role: 'user', agent: null, content: 'Find kettles', status: 'complete' })
    const saved = { ...pending, id: 10 }
    const next = applyStreamEvent(
      conversation([pending]),
      {
        type: 'run',
        run_id: 'r1',
        conversation: { id: 'c1', title: 'Find kettles', created_at: '', updated_at: '', running: true },
        user_message: saved,
      },
      -1,
    )
    expect(next.title).toBe('Find kettles')
    expect(next.messages.map((entry) => entry.id)).toEqual([10])
  })

  it('appends tokens and activity to the right message', () => {
    let state = conversation([message(1), message(2, { agent: 'researcher' })])
    state = applyStreamEvent(state, { type: 'token', message_id: 2, text: 'Hel' })
    state = applyStreamEvent(state, { type: 'token', message_id: 2, text: 'lo' })
    state = applyStreamEvent(state, {
      type: 'tool_end',
      message_id: 2,
      tool: 'web_search',
      label: 'Searched the web',
      ok: true,
      summary: '5 results',
    })
    expect(state.messages[0].content).toBe('')
    expect(state.messages[1].content).toBe('Hello')
    expect(state.messages[1].payload.activity).toEqual([
      { tool: 'web_search', label: 'Searched the web', ok: true, summary: '5 results' },
    ])
  })

  it('does not duplicate a started message and replaces it with the final version', () => {
    let state = conversation([message(1)])
    state = applyStreamEvent(state, { type: 'agent_start', message: message(1) })
    expect(state.messages).toHaveLength(1)
    state = applyStreamEvent(state, { type: 'message', message: message(1, { content: 'Done', status: 'complete' }) })
    expect(state.messages).toEqual([message(1, { content: 'Done', status: 'complete' })])
  })

  it('removes an empty orchestrator segment', () => {
    const state = applyStreamEvent(conversation([message(1), message(2)]), { type: 'message_removed', message_id: 1 })
    expect(state.messages.map((entry) => entry.id)).toEqual([2])
  })

  it('ignores events that do not change messages', () => {
    const state = conversation([message(1)])
    expect(applyStreamEvent(state, { type: 'ping' })).toBe(state)
    expect(applyStreamEvent(state, { type: 'cart_changed' })).toBe(state)
  })
})
