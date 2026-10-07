import { MessagesSquareIcon, SearchIcon, SettingsIcon, ShoppingBagIcon, ShoppingCartIcon } from 'lucide-react'

import { ThemeToggle } from '@/components/layout/theme-toggle'
import { Button } from '@/components/ui/button'
import { useCart } from '@/hooks/use-cart'
import type { Route } from '@/hooks/use-route'

type NavItem = { view: Route['view']; href: string; label: string; icon: typeof ShoppingBagIcon }

export function AppHeader({ view, chatHref }: { view: Route['view']; chatHref: string }) {
  const { cart, setIsOpen } = useCart()
  const itemCount = cart.item_count
  const items: NavItem[] = [
    { view: 'chat', href: chatHref, label: 'Chat', icon: MessagesSquareIcon },
    { view: 'search', href: '#/search', label: 'Search', icon: SearchIcon },
    { view: 'settings', href: '#/settings', label: 'Settings', icon: SettingsIcon },
  ]

  return (
    <header className="z-40 shrink-0 border-b bg-background/80 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-2 px-4 sm:gap-4 sm:px-6">
        <a
          href="#/chat"
          className="flex items-center gap-2 rounded-md font-semibold tracking-tight outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShoppingBagIcon className="size-4" aria-hidden="true" />
          </span>
          <span className="hidden sm:inline">MarketMesh</span>
        </a>

        <nav aria-label="Main" className="flex items-center gap-1">
          {items.map((item) => {
            const active = item.view === view
            const Icon = item.icon
            return (
              <Button key={item.view} variant={active ? 'secondary' : 'ghost'} asChild>
                <a href={item.href} aria-current={active ? 'page' : undefined} aria-label={item.label}>
                  <Icon data-icon="inline-start" aria-hidden="true" />
                  <span className="hidden sm:inline">{item.label}</span>
                </a>
              </Button>
            )
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <Button
            variant="outline"
            onClick={() => setIsOpen(true)}
            aria-label={`Open cart, ${itemCount} item${itemCount === 1 ? '' : 's'}`}
          >
            <ShoppingCartIcon data-icon="inline-start" aria-hidden="true" />
            <span className="hidden sm:inline">Cart</span>
            {itemCount > 0 && (
              <span className="ml-0.5 inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground tabular-nums">
                {itemCount}
              </span>
            )}
          </Button>
        </div>
      </div>
    </header>
  )
}
