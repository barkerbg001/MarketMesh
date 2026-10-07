import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { ArrowDownIcon, KeyRoundIcon, Loader2Icon, PanelLeftIcon } from 'lucide-react'
import { toast } from 'sonner'

import { ChatMessageView } from '@/components/chat/chat-message'
import { Composer } from '@/components/chat/composer'
import { ConversationSidebar } from '@/components/chat/conversation-sidebar'
import { EmptyState } from '@/components/chat/empty-state'
import { ProviderErrorAlert } from '@/components/chat/provider-error'
import { useChat } from '@/components/chat/use-chat'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useCart } from '@/hooks/use-cart'
import { navigate } from '@/hooks/use-route'
import { useWorkspace } from '@/hooks/use-workspace'
import { CONVERSATIONS_CHANGED_EVENT, deleteJson, downloadExport, errorMessage, getJson, patchJson } from '@/lib/api'
import type { ConversationSummary, Product } from '@/types/api'

const PIN_THRESHOLD = 120

function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await getJson<{ conversations: ConversationSummary[] }>('/api/conversations', 'Could not load conversations')
      setConversations(data.conversations)
      setError(null)
    } catch (err) {
      setError(errorMessage(err, 'Could not load conversations'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { conversations, setConversations, loading, error, refresh }
}

export function ChatPage({ conversationId, active }: { conversationId: string | null; active: boolean }) {
  const { agents, agentById, settings } = useWorkspace()
  const { keys, addProduct, compareRequest, takeCompareRequest } = useCart()
  const list = useConversations()
  const chat = useChat(conversationId, list.refresh)
  const [draft, setDraft] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const pinnedRef = useRef(true)
  const [showJump, setShowJump] = useState(false)

  const notConfigured = settings !== null && !settings.openrouter.configured
  const noModel = settings !== null && settings.openrouter.configured && !settings.default_model
  const blocked = notConfigured || noModel
  const messages = chat.conversation?.messages ?? []
  const lastMessage = messages.at(-1)

  const inCart = useCallback((key: string) => keys.has(key), [keys])
  const onAdd = useCallback(
    (product: Product) => void addProduct(product, chat.conversation?.id ?? null),
    [addProduct, chat.conversation?.id],
  )
  const { send } = chat

  useEffect(() => {
    if (!active || !compareRequest || chat.busy || blocked) return
    if (conversationId !== null || chat.conversation !== null) return
    const request = takeCompareRequest()
    if (!request) return
    const list = request.titles.map((title, index) => `${index + 1}. ${title}`).join('\n')
    void send(`@tally Compare these shortlisted items from my cart:\n${list}`, request.itemIds)
  }, [active, compareRequest, chat.busy, chat.conversation, conversationId, blocked, takeCompareRequest, send])

  const refreshList = list.refresh
  useEffect(() => {
    const onHistoryChanged = () => {
      void refreshList()
      if (window.location.hash.startsWith('#/chat/')) navigate({ view: 'chat', conversationId: null })
    }
    window.addEventListener(CONVERSATIONS_CHANGED_EVENT, onHistoryChanged)
    return () => window.removeEventListener(CONVERSATIONS_CHANGED_EVENT, onHistoryChanged)
  }, [refreshList])

  const [shownId, setShownId] = useState(conversationId)
  if (shownId !== conversationId) {
    setShownId(conversationId)
    setShowJump(false)
  }
  useEffect(() => {
    pinnedRef.current = true
  }, [conversationId])

  useLayoutEffect(() => {
    const element = scrollRef.current
    if (element && pinnedRef.current) element.scrollTop = element.scrollHeight
  }, [messages.length, lastMessage?.content, lastMessage?.status, chat.liveTools, chat.turnError])

  const handleScroll = () => {
    const element = scrollRef.current
    if (!element) return
    const pinned = element.scrollHeight - element.scrollTop - element.clientHeight < PIN_THRESHOLD
    pinnedRef.current = pinned
    setShowJump(!pinned)
  }

  const jumpToLatest = () => {
    const element = scrollRef.current
    if (!element) return
    pinnedRef.current = true
    setShowJump(false)
    element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
  }

  const sendMessage = useCallback(
    async (text: string) => {
      pinnedRef.current = true
      return send(text)
    },
    [send],
  )

  const startNew = () => {
    setSidebarOpen(false)
    navigate({ view: 'chat', conversationId: null })
  }

  const rename = async (conversation: ConversationSummary, title: string) => {
    try {
      const updated = await patchJson<ConversationSummary>(
        `/api/conversations/${conversation.id}`,
        { title },
        'Could not rename the conversation',
      )
      list.setConversations((items) => items.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)))
      chat.renameLocal(updated)
      return true
    } catch (err) {
      toast.error(errorMessage(err, 'Could not rename the conversation'))
      return false
    }
  }

  const remove = async (conversation: ConversationSummary) => {
    try {
      await deleteJson(`/api/conversations/${conversation.id}`, 'Could not delete the conversation')
      list.setConversations((items) => items.filter((item) => item.id !== conversation.id))
      if (conversation.id === conversationId) navigate({ view: 'chat', conversationId: null })
      toast.success('Conversation deleted')
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete the conversation'))
    }
  }

  const exportConversation = (conversation: ConversationSummary, format: 'markdown' | 'json') =>
    downloadExport(`/api/conversations/${conversation.id}/export?format=${format}`)

  const sidebar = (
    <ConversationSidebar
      conversations={list.conversations}
      loading={list.loading}
      error={list.error}
      activeId={conversationId}
      onNew={startNew}
      onRename={rename}
      onDelete={remove}
      onExport={exportConversation}
      onNavigate={() => setSidebarOpen(false)}
    />
  )

  const disabledReason = notConfigured
    ? 'Add your OpenRouter API key in Settings to start chatting.'
    : noModel
      ? 'Choose a default model in Settings to start chatting.'
      : undefined

  return (
    <div className="mx-auto flex h-full w-full max-w-7xl min-h-0">
      <aside className="hidden w-64 shrink-0 border-r p-3 md:block">{sidebar}</aside>

      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-72 p-3 pt-12">
          <SheetHeader className="sr-only">
            <SheetTitle>Conversations</SheetTitle>
            <SheetDescription>Open, rename, export or delete a research conversation.</SheetDescription>
          </SheetHeader>
          {sidebar}
        </SheetContent>
      </Sheet>

      <section className="relative flex min-w-0 flex-1 flex-col" aria-label="Research chat">
        <div className="flex items-center gap-2 border-b px-3 py-2 md:hidden">
          <Button variant="ghost" size="icon-sm" onClick={() => setSidebarOpen(true)} aria-label="Show conversations">
            <PanelLeftIcon aria-hidden="true" />
          </Button>
          <span className="truncate text-sm font-medium">{chat.conversation?.title ?? 'New conversation'}</span>
        </div>

        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="min-h-0 flex-1 overflow-y-auto px-4"
          aria-live="off"
        >
          {chat.loading ? (
            <div className="flex h-full items-center justify-center text-muted-foreground" role="status">
              <Loader2Icon className="mr-2 size-4 animate-spin" aria-hidden="true" />
              Opening conversation…
            </div>
          ) : chat.loadError ? (
            <div className="mx-auto max-w-xl py-10">
              <Alert variant="destructive">
                <AlertTitle>Could not open this conversation</AlertTitle>
                <AlertDescription>
                  <p>{chat.loadError}</p>
                  <button type="button" className="font-medium underline underline-offset-2" onClick={startNew}>
                    Start a new conversation
                  </button>
                </AlertDescription>
              </Alert>
            </div>
          ) : messages.length === 0 ? (
            <EmptyState
              agents={agents}
              region={settings?.research_region}
              disabled={blocked || chat.busy}
              onPrompt={(prompt) => void sendMessage(prompt)}
            />
          ) : (
            <ol className="mx-auto flex w-full max-w-3xl flex-col gap-[var(--chat-gap)] py-6" aria-label="Messages">
              {messages.map((message) => (
                <li key={message.id}>
                  <ChatMessageView
                    message={message}
                    agent={agentById(message.agent)}
                    agentById={agentById}
                    liveTool={chat.liveTools[message.id]}
                    inCart={inCart}
                    onAdd={onAdd}
                  />
                </li>
              ))}
            </ol>
          )}
        </div>

        {showJump && (
          <Button
            variant="secondary"
            size="sm"
            className="absolute bottom-36 left-1/2 -translate-x-1/2 shadow-md"
            onClick={jumpToLatest}
          >
            <ArrowDownIcon data-icon="inline-start" aria-hidden="true" />
            Latest
          </Button>
        )}

        <div className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-4 pt-2 pb-4">
          {blocked && (
            <Alert>
              <KeyRoundIcon aria-hidden="true" />
              <AlertTitle>{notConfigured ? 'Connect OpenRouter to start' : 'Pick a model to start'}</AlertTitle>
              <AlertDescription>
                <p>
                  {notConfigured
                    ? 'MarketMesh uses your own OpenRouter API key. It is stored encrypted on the API server and never sent to the browser.'
                    : 'Choose the default model the agents should use. You can pick a free model.'}
                </p>
                <a href="#/settings/openrouter" className="font-medium underline underline-offset-2">
                  Open settings
                </a>
              </AlertDescription>
            </Alert>
          )}
          {chat.turnError && <ProviderErrorAlert error={chat.turnError} onDismiss={chat.dismissError} />}
          {chat.busy && !chat.running && (
            <p className="text-xs text-muted-foreground" role="status">
              The agents are still working in another conversation. You can send once they finish.
            </p>
          )}
          <Composer
            agents={agents}
            running={chat.running}
            disabled={blocked || (chat.busy && !chat.running) || chat.loading}
            disabledReason={disabledReason}
            value={draft}
            onChange={setDraft}
            onSend={sendMessage}
            onStop={() => void chat.stop()}
          />
          <p className="text-center text-[11px] text-muted-foreground">
            Agents can be wrong. Prices come from retrieved pages at the time shown; check the source before you buy.
          </p>
        </div>
      </section>
    </div>
  )
}
