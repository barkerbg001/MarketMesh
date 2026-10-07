import { useCallback, useEffect, useRef, useState } from 'react'

import { applyStreamEvent } from '@/components/chat/chat-events'
import { useCart } from '@/hooks/use-cart'
import { navigate } from '@/hooks/use-route'
import { errorMessage, getJson, postJson } from '@/lib/api'
import { streamMessage } from '@/lib/stream'
import type { ChatMessage, Conversation, ConversationSummary, ProviderError } from '@/types/api'

type Run = { conversationId: string; runId: string | null; controller: AbortController }

let pendingIds = -1

export function useChat(conversationId: string | null, onConversationsChanged: () => void) {
  const { refresh: refreshCart } = useCart()
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [liveTools, setLiveTools] = useState<Record<number, string>>({})
  const [turnError, setTurnError] = useState<ProviderError | null>(null)
  const runRef = useRef<Run | null>(null)
  const loadedIdRef = useRef<string | null>(null)

  useEffect(() => {
    setTurnError(null)
    if (!conversationId) {
      loadedIdRef.current = null
      setConversation(null)
      setLoadError(null)
      return
    }
    if (loadedIdRef.current === conversationId) return
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    getJson<Conversation>(`/api/conversations/${conversationId}`, 'Could not open this conversation')
      .then((data) => {
        if (cancelled) return
        loadedIdRef.current = data.id
        setConversation(data)
      })
      .catch((err) => {
        if (cancelled) return
        setConversation(null)
        setLoadError(errorMessage(err, 'Could not open this conversation'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [conversationId])

  const send = useCallback(async (content: string, cartItemIds: number[] = []) => {
    if (runRef.current) return false
    setTurnError(null)

    let target = conversation
    if (!target) {
      try {
        target = await postJson<Conversation>('/api/conversations', {}, 'Could not start a conversation')
      } catch (err) {
        setTurnError({ code: 'request_failed', message: errorMessage(err, 'Could not start a conversation') })
        return false
      }
      loadedIdRef.current = target.id
      setConversation(target)
      navigate({ view: 'chat', conversationId: target.id })
    }

    const targetId = target.id
    const pendingId = pendingIds--
    const pending: ChatMessage = {
      id: pendingId,
      conversation_id: targetId,
      role: 'user',
      agent: null,
      content,
      status: 'complete',
      payload: cartItemIds.length ? { cart_item_ids: cartItemIds } : {},
      created_at: new Date().toISOString(),
    }
    const applyTo = (change: (current: Conversation) => Conversation) =>
      setConversation((current) => (current && current.id === targetId ? change(current) : current))
    applyTo((current) => ({ ...current, messages: [...current.messages, pending] }))

    const controller = new AbortController()
    runRef.current = { conversationId: targetId, runId: null, controller }
    setRunningId(targetId)
    setLiveTools({})

    let sent = true
    try {
      await streamMessage(targetId, { content, cart_item_ids: cartItemIds }, {
        signal: controller.signal,
        onEvent: (event) => {
          switch (event.type) {
            case 'run':
              if (runRef.current) runRef.current.runId = event.run_id
              onConversationsChanged()
              break
            case 'tool_start':
              setLiveTools((tools) => ({ ...tools, [event.message_id]: event.label }))
              return
            case 'tool_end':
            case 'message':
            case 'message_removed': {
              const id = event.type === 'message' ? event.message.id : event.message_id
              setLiveTools(({ [id]: _removed, ...rest }) => rest)
              break
            }
            case 'cart_changed':
              void refreshCart()
              return
            case 'error':
              setTurnError(event.error)
              return
            default:
              break
          }
          applyTo((current) => applyStreamEvent(current, event, pendingId))
        },
      })
    } catch (err) {
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        applyTo((current) => ({ ...current, messages: current.messages.filter((m) => m.id !== pendingId) }))
        setTurnError({ code: 'request_failed', message: errorMessage(err, 'The message could not be sent') })
        sent = false
      }
    } finally {
      runRef.current = null
      setRunningId(null)
      setLiveTools({})
      onConversationsChanged()
    }
    return sent
  }, [conversation, onConversationsChanged, refreshCart])

  const stop = useCallback(async () => {
    const run = runRef.current
    if (!run) return
    if (!run.runId) {
      run.controller.abort()
      return
    }
    try {
      await postJson(`/api/runs/${run.runId}/cancel`, {}, 'Could not stop the agents')
    } catch {
      run.controller.abort()
    }
  }, [])

  const renameLocal = useCallback((summary: ConversationSummary) => {
    setConversation((current) => (current && current.id === summary.id ? { ...current, title: summary.title } : current))
  }, [])

  return {
    conversation,
    loading,
    loadError,
    running: runningId !== null && runningId === conversation?.id,
    busy: runningId !== null,
    liveTools,
    turnError,
    dismissError: () => setTurnError(null),
    send,
    stop,
    renameLocal,
  }
}
