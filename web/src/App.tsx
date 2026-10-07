import { useEffect, useState } from 'react'

import { CartProvider } from '@/components/cart/cart-provider'
import { CartSheet } from '@/components/cart/cart-sheet'
import { ChatPage } from '@/components/chat/chat-page'
import { AppHeader } from '@/components/layout/app-header'
import { WorkspaceProvider } from '@/components/layout/workspace-provider'
import { SettingsPage } from '@/components/settings/settings-page'
import { ProductSearch } from '@/components/store/product-search'
import { TooltipProvider } from '@/components/ui/tooltip'
import { routeHref, useRoute } from '@/hooks/use-route'
import { CONVERSATIONS_CHANGED_EVENT } from '@/lib/api'

const TITLES = { chat: 'Chat', search: 'Search', settings: 'Settings' } as const

function App() {
  const route = useRoute()
  // The chat stays mounted on other views so a running answer keeps streaming; remember which one was open.
  const [chatId, setChatId] = useState<string | null>(null)
  const routeChatId = route.view === 'chat' ? route.conversationId : undefined
  if (routeChatId !== undefined && routeChatId !== chatId) setChatId(routeChatId)
  const activeChatId = routeChatId === undefined ? chatId : routeChatId

  useEffect(() => {
    const clear = () => setChatId(null)
    window.addEventListener(CONVERSATIONS_CHANGED_EVENT, clear)
    return () => window.removeEventListener(CONVERSATIONS_CHANGED_EVENT, clear)
  }, [])

  useEffect(() => {
    document.title = `${TITLES[route.view]} · MarketMesh`
  }, [route.view])

  return (
    <WorkspaceProvider>
      <CartProvider>
        <TooltipProvider>
          <div className="flex h-dvh flex-col">
            <AppHeader view={route.view} chatHref={routeHref({ view: 'chat', conversationId: activeChatId })} />
            <main className="min-h-0 flex-1">
              <div hidden={route.view !== 'chat'} className="h-full">
                <ChatPage conversationId={activeChatId} active={route.view === 'chat'} />
              </div>
              <div hidden={route.view !== 'search'} className="h-full overflow-y-auto">
                <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-10">
                  <ProductSearch />
                </div>
              </div>
              {route.view === 'settings' && (
                <div className="h-full overflow-y-auto">
                  <SettingsPage section={route.section} />
                </div>
              )}
            </main>
          </div>
          <CartSheet />
        </TooltipProvider>
      </CartProvider>
    </WorkspaceProvider>
  )
}

export default App
