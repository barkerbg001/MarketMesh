import { useState } from 'react'
import {
  DownloadIcon,
  ExternalLinkIcon,
  MinusIcon,
  PlusIcon,
  ScaleIcon,
  ShoppingCartIcon,
  Trash2Icon,
} from 'lucide-react'

import { SourceBadge } from '@/components/store/retailer-badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { useCart } from '@/hooks/use-cart'
import { useWorkspace } from '@/hooks/use-workspace'
import { downloadExport } from '@/lib/api'
import { displayPrice, formatMoney, orderSubtotals } from '@/lib/price'
import { formatDateTime, timeAgo } from '@/lib/time'
import type { CartItem } from '@/types/api'

const MAX_COMPARE = 6

function NotesField({ item, onSave }: { item: CartItem; onSave: (notes: string) => void }) {
  const [draft, setDraft] = useState(item.notes)
  return (
    <Textarea
      value={draft}
      maxLength={1000}
      rows={2}
      placeholder="Notes (why it's on the list, what to check)…"
      aria-label={`Notes for ${item.title}`}
      className="min-h-0 resize-y text-sm"
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => {
        if (draft !== item.notes) onSave(draft)
      }}
    />
  )
}

function CartRow({
  item,
  selected,
  onSelect,
}: {
  item: CartItem
  selected: boolean
  onSelect: (checked: boolean) => void
}) {
  const { updateItem, removeItem } = useCart()
  return (
    <li className="flex gap-3 p-4">
      <Checkbox
        checked={selected}
        onCheckedChange={(checked) => onSelect(checked === true)}
        aria-label={`Select ${item.title} for comparison`}
        className="mt-1"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <SourceBadge source={item.source} seller={item.seller} />
          </div>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="line-clamp-2 font-medium leading-snug hover:underline"
          >
            {item.title}
            <ExternalLinkIcon className="ml-1 inline size-3 text-muted-foreground" aria-hidden="true" />
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          <p className="text-sm tabular-nums">
            {displayPrice(item)}
            {item.line_total && item.currency && item.quantity > 1 && (
              <span className="text-muted-foreground"> · {formatMoney(item.line_total, item.currency)} total</span>
            )}
          </p>
          <p className="text-xs text-muted-foreground" title={formatDateTime(item.retrieved_at)}>
            {item.retrieved_at ? `Price retrieved ${timeAgo(item.retrieved_at)}` : 'Retrieval time unknown'}
          </p>
        </div>
        <NotesField key={item.notes} item={item} onSave={(notes) => void updateItem(item.id, { notes })} />
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1" role="group" aria-label={`Quantity for ${item.title}`}>
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Decrease quantity"
              disabled={item.quantity <= 1}
              onClick={() => void updateItem(item.id, { quantity: item.quantity - 1 })}
            >
              <MinusIcon aria-hidden="true" />
            </Button>
            <span className="w-8 text-center tabular-nums" aria-live="polite">
              {item.quantity}
            </span>
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Increase quantity"
              disabled={item.quantity >= 99}
              onClick={() => void updateItem(item.id, { quantity: item.quantity + 1 })}
            >
              <PlusIcon aria-hidden="true" />
            </Button>
          </div>
          <Button variant="ghost" size="sm" onClick={() => void removeItem(item.id)}>
            <Trash2Icon data-icon="inline-start" aria-hidden="true" />
            Remove
          </Button>
        </div>
      </div>
    </li>
  )
}

export function CartSheet() {
  const { cart, error, isOpen, setIsOpen, clearCart, requestCompare } = useCart()
  const { settings } = useWorkspace()
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const selectedItems = cart.items.filter((item) => selected.has(item.id))
  const subtotals = orderSubtotals(cart.subtotals, settings?.currency ?? 'ZAR')

  function toggle(id: number, checked: boolean) {
    setSelected((current) => {
      const next = new Set(current)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetContent
        className="w-full gap-0 sm:max-w-md"
        onInteractOutside={(event) => {
          if (event.target instanceof Element && event.target.closest('[data-sonner-toaster]')) {
            event.preventDefault()
          }
        }}
      >
        <SheetHeader className="border-b pr-12">
          <SheetTitle>Research cart</SheetTitle>
          <SheetDescription>
            A shortlist for comparing options. Nothing here is reserved or purchased.
          </SheetDescription>
        </SheetHeader>

        {error && <p className="border-b px-4 py-2 text-sm text-destructive">{error}</p>}

        {cart.items.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
            <ShoppingCartIcon className="size-10 text-muted-foreground/50" aria-hidden="true" />
            <p className="font-medium">Your cart is empty.</p>
            <p className="text-sm text-muted-foreground">
              Add products from search results or from the agents&apos; product cards.
            </p>
          </div>
        ) : (
          <>
            <ul className="flex-1 divide-y overflow-y-auto" aria-label="Cart items">
              {cart.items.map((item) => (
                <CartRow
                  key={item.id}
                  item={item}
                  selected={selected.has(item.id)}
                  onSelect={(checked) => toggle(item.id, checked)}
                />
              ))}
            </ul>

            <SheetFooter className="gap-3 border-t">
              <div className="flex flex-col gap-1" aria-label="Subtotals by currency">
                {subtotals.map((subtotal) => (
                  <div key={subtotal.currency} className="flex items-center justify-between">
                    <span className="text-sm">
                      Subtotal ({subtotal.currency}, {subtotal.item_count} item{subtotal.item_count === 1 ? '' : 's'})
                    </span>
                    <strong className="tabular-nums">{formatMoney(subtotal.amount, subtotal.currency)}</strong>
                  </div>
                ))}
                {cart.unknown_price_count > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {cart.unknown_price_count} item{cart.unknown_price_count === 1 ? ' has' : 's have'} no known price
                    and {cart.unknown_price_count === 1 ? 'is' : 'are'} not included.
                  </p>
                )}
                {subtotals.length > 1 && (
                  <p className="text-xs text-muted-foreground">
                    Currencies are shown separately; no exchange rates are applied.
                  </p>
                )}
              </div>

              <Button
                disabled={selectedItems.length < 2 || selectedItems.length > MAX_COMPARE}
                onClick={() => {
                  requestCompare(selectedItems)
                  setSelected(new Set())
                }}
              >
                <ScaleIcon data-icon="inline-start" aria-hidden="true" />
                {selectedItems.length < 2
                  ? 'Select 2–6 items to compare'
                  : selectedItems.length > MAX_COMPARE
                    ? `Compare up to ${MAX_COMPARE} items`
                    : `Compare ${selectedItems.length} selected with Tally`}
              </Button>

              <div className="flex gap-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="flex-1">
                      <DownloadIcon data-icon="inline-start" aria-hidden="true" />
                      Export
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuItem onSelect={() => downloadExport('/api/cart/export?format=csv')}>
                      CSV (spreadsheet)
                    </DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => downloadExport('/api/cart/export?format=json')}>
                      JSON
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <ClearCartButton onConfirm={() => void clearCart()} />
              </div>
            </SheetFooter>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

export function ClearCartButton({ onConfirm, disabled }: { onConfirm: () => void; disabled?: boolean }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" className="flex-1 text-destructive" disabled={disabled}>
          <Trash2Icon data-icon="inline-start" aria-hidden="true" />
          Clear cart
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Clear the research cart?</AlertDialogTitle>
          <AlertDialogDescription>
            This removes every item and its notes. Export the cart first if you want a copy.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onConfirm}>
            Clear cart
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
