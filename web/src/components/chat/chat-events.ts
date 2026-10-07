import type { ChatMessage, Conversation, StreamEvent } from '@/types/api'

/** Apply one streamed event to a conversation. Pure, so it can be unit tested. */
export function applyStreamEvent(conversation: Conversation, event: StreamEvent, pendingUserId?: number): Conversation {
  const messages = conversation.messages
  const update = (id: number, change: (message: ChatMessage) => ChatMessage) => ({
    ...conversation,
    messages: messages.map((message) => (message.id === id ? change(message) : message)),
  })

  switch (event.type) {
    case 'run': {
      const withoutPending = messages.filter((message) => message.id !== pendingUserId)
      return {
        ...conversation,
        ...event.conversation,
        messages: [...withoutPending.filter((m) => m.id !== event.user_message.id), event.user_message],
      }
    }
    case 'agent_start':
      if (messages.some((message) => message.id === event.message.id)) return conversation
      return { ...conversation, messages: [...messages, event.message] }
    case 'token':
      return update(event.message_id, (message) => ({ ...message, content: message.content + event.text }))
    case 'tool_end':
      return update(event.message_id, (message) => ({
        ...message,
        payload: {
          ...message.payload,
          activity: [
            ...(message.payload.activity ?? []),
            { tool: event.tool, label: event.label, ok: event.ok, summary: event.summary },
          ],
        },
      }))
    case 'message':
      if (!messages.some((message) => message.id === event.message.id)) {
        return { ...conversation, messages: [...messages, event.message] }
      }
      return update(event.message.id, () => event.message)
    case 'message_removed':
      return { ...conversation, messages: messages.filter((message) => message.id !== event.message_id) }
    default:
      return conversation
  }
}
