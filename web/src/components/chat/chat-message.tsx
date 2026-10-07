import { memo } from 'react'
import { CornerDownRightIcon, Loader2Icon, ScaleIcon, ShoppingCartIcon, SquareIcon } from 'lucide-react'

import { AgentAvatar } from '@/components/agents/agent-avatar'
import { ActivityList } from '@/components/chat/activity-list'
import { ComparisonTable } from '@/components/chat/comparison-table'
import { Markdown } from '@/components/chat/markdown'
import { ProviderErrorAlert } from '@/components/chat/provider-error'
import { SourceList } from '@/components/chat/source-list'
import { ProductCard } from '@/components/store/product-card'
import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/time'
import type { Agent, ChatMessage, Product } from '@/types/api'

type ChatMessageProps = {
  message: ChatMessage
  agent: Agent | undefined
  agentById: (id: string) => Agent | undefined
  liveTool?: string
  inCart: (key: string) => boolean
  onAdd: (product: Product) => void
}

function UserMessage({ message }: { message: ChatMessage }) {
  const compared = message.payload.cart_item_ids?.length ?? 0
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-primary-foreground">
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
      </div>
      {compared > 0 && (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <ScaleIcon className="size-3" aria-hidden="true" />
          Comparing {compared} cart item{compared === 1 ? '' : 's'}
        </span>
      )}
    </div>
  )
}

export const ChatMessageView = memo(function ChatMessageView({
  message,
  agent,
  agentById,
  liveTool,
  inCart,
  onAdd,
}: ChatMessageProps) {
  if (message.role === 'user') return <UserMessage message={message} />

  const { payload } = message
  const streaming = message.status === 'streaming'
  const products = payload.products ?? []
  const comparisonKeys = new Set(payload.comparison?.product_keys ?? [])
  const cardProducts = products.filter((product) => !comparisonKeys.has(product.key))
  const requested = (payload.requested ?? []).map((id) => agentById(id)?.name).filter(Boolean)
  const name = agent?.name ?? 'Agent'

  return (
    <article className="flex gap-3" aria-label={`${name}${agent ? `, ${agent.role}` : ''}`}>
      {agent ? <AgentAvatar agent={agent} /> : <div className="size-8 shrink-0 rounded-full bg-muted" />}
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <header className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="font-semibold">{name}</span>
          {agent && <span className="text-xs text-muted-foreground">{agent.role}</span>}
          <time className="text-xs text-muted-foreground" dateTime={message.created_at}>
            {formatDateTime(message.created_at)}
          </time>
          {streaming && (
            <Badge variant="secondary">
              <Loader2Icon className="animate-spin" aria-hidden="true" />
              Working
            </Badge>
          )}
          {message.status === 'cancelled' && (
            <Badge variant="outline">
              <SquareIcon aria-hidden="true" />
              Stopped
            </Badge>
          )}
        </header>

        {payload.task && (
          <p className="flex items-start gap-1.5 rounded-md bg-muted px-2.5 py-1.5 text-xs text-muted-foreground">
            <CornerDownRightIcon className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            <span>
              <span className="font-medium text-foreground">Task from {agentById('orchestrator')?.name ?? 'Mesh'}:</span>{' '}
              {payload.task}
            </span>
          </p>
        )}
        {requested.length > 0 && (
          <p className="text-xs text-muted-foreground">You asked for {requested.join(' and ')}.</p>
        )}

        <ActivityList activity={payload.activity ?? []} live={liveTool} />

        {message.content ? (
          <div className="text-[length:var(--chat-text)]">
            <Markdown>{message.content}</Markdown>
          </div>
        ) : (
          streaming && !liveTool && (
            <p className="text-sm text-muted-foreground" role="status">
              Thinking…
            </p>
          )
        )}

        {payload.comparison && (
          <ComparisonTable comparison={payload.comparison} inCart={inCart} onAdd={onAdd} />
        )}

        {cardProducts.length > 0 && (
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Products found">
            {cardProducts.slice(0, 12).map((product) => (
              <li key={product.key}>
                <ProductCard product={product} compact inCart={inCart(product.key)} onAdd={onAdd} />
              </li>
            ))}
          </ul>
        )}

        {(payload.cart_actions ?? []).length > 0 && (
          <ul className="flex flex-col gap-1 text-xs text-muted-foreground">
            {payload.cart_actions!.map((action) => (
              <li key={`${action.action}:${action.key}`} className="flex items-center gap-1.5">
                <ShoppingCartIcon className="size-3.5" aria-hidden="true" />
                {action.action === 'added' && <>Added <strong className="text-foreground">{action.title}</strong> to your cart</>}
                {action.action === 'already_in_cart' && <><strong className="text-foreground">{action.title}</strong> was already in your cart</>}
                {action.action === 'removed' && <>Removed <strong className="text-foreground">{action.title}</strong> from your cart</>}
              </li>
            ))}
          </ul>
        )}

        <SourceList sources={payload.sources ?? []} />

        {payload.error && <ProviderErrorAlert error={payload.error} />}
      </div>
    </article>
  )
})
