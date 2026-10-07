import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import { CartContext, EMPTY_CART, type CompareRequest } from '@/hooks/use-cart'
import { navigate } from '@/hooks/use-route'
import { deleteJson, errorMessage, getJson, patchJson, postJson } from '@/lib/api'
import type { CartItem, CartState, Product } from '@/types/api'

/** Key used by the browser-only cart of earlier versions; imported once, then removed. */
const LEGACY_CART_KEY = 'marketmesh-cart'

type LegacyEntry = { title: string; url: string; retailer?: string; price?: string | null; quantity?: number }

function readLegacyCart(): LegacyEntry[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(LEGACY_CART_KEY) ?? 'null')
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((item): item is LegacyEntry =>
        typeof item?.title === 'string' && typeof item?.url === 'string' && /^https?:\/\//.test(item.url))
      .map((item) => ({
        title: item.title.slice(0, 500),
        url: item.url,
        retailer: typeof item.retailer === 'string' ? item.retailer : '',
        price: typeof item.price === 'string' ? item.price : null,
        quantity: Math.min(Math.max(Number(item.quantity) || 1, 1), 99),
      }))
  } catch {
    return []
  }
}

type AddResponse = { created: boolean; duplicate: boolean; item: CartItem; cart: CartState }

export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<CartState>(EMPTY_CART)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [compareRequest, setCompareRequest] = useState<CompareRequest | null>(null)
  const compareRef = useRef<CompareRequest | null>(null)

  const refresh = useCallback(async () => {
    try {
      setCart(await getJson<CartState>('/api/cart', 'Could not load the cart'))
      setError(null)
    } catch (err) {
      setError(errorMessage(err, 'Could not load the cart'))
    } finally {
      setLoading(false)
    }
  }, [])

  const startedRef = useRef(false)

  useEffect(() => {
    // StrictMode runs effects twice; importing twice would double legacy quantities.
    if (startedRef.current) return
    startedRef.current = true
    const legacy = readLegacyCart()
    if (legacy.length === 0) {
      void refresh()
      return
    }
    postJson<{ imported: number; cart: CartState }>('/api/cart/import', { items: legacy }, 'Import failed')
      .then((result) => {
        localStorage.removeItem(LEGACY_CART_KEY)
        setCart(result.cart)
        setLoading(false)
        toast.success(`Moved ${result.imported} item(s) from your old browser cart into your research cart.`)
      })
      .catch(() => void refresh())
  }, [refresh])

  const addProduct = useCallback(async (product: Product, conversationId?: string | null) => {
    try {
      const result = await postJson<AddResponse>('/api/cart', {
        product: {
          title: product.title,
          url: product.url,
          seller: product.seller,
          source: product.source,
          image_url: product.image_url,
          price: product.price,
          price_amount: product.price_amount,
          currency: product.currency,
          specs: product.specs,
          retrieved_at: product.retrieved_at,
        },
        conversation_id: conversationId ?? null,
      }, 'Could not add to cart')
      setCart(result.cart)
      if (result.duplicate) {
        toast.info('Already in your cart', {
          description: result.item.title,
          action: { label: 'Add another', onClick: () => void patchJson<{ cart: CartState }>(
            `/api/cart/${result.item.id}`, { quantity: Math.min(result.item.quantity + 1, 99) }, 'Update failed',
          ).then((next) => setCart(next.cart)) },
        })
      } else {
        toast.success('Added to cart', {
          description: result.item.title,
          action: { label: 'View cart', onClick: () => setIsOpen(true) },
        })
      }
    } catch (err) {
      toast.error(errorMessage(err, 'Could not add to cart'))
    }
  }, [])

  const updateItem = useCallback(async (id: number, changes: { quantity?: number; notes?: string }) => {
    try {
      setCart((await patchJson<{ cart: CartState }>(`/api/cart/${id}`, changes, 'Could not update the item')).cart)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not update the item'))
    }
  }, [])

  const removeItem = useCallback(async (id: number) => {
    try {
      setCart(await deleteJson<CartState>(`/api/cart/${id}`, 'Could not remove the item'))
    } catch (err) {
      toast.error(errorMessage(err, 'Could not remove the item'))
    }
  }, [])

  const clearCart = useCallback(async () => {
    try {
      setCart(await deleteJson<CartState>('/api/cart', 'Could not clear the cart', { confirm: 'CLEAR' }))
      toast.success('Cart cleared')
    } catch (err) {
      toast.error(errorMessage(err, 'Could not clear the cart'))
    }
  }, [])

  const requestCompare = useCallback((items: CartItem[]) => {
    const request = { itemIds: items.map((item) => item.id), titles: items.map((item) => item.title) }
    compareRef.current = request
    setCompareRequest(request)
    setIsOpen(false)
    navigate({ view: 'chat', conversationId: null })
  }, [])

  const takeCompareRequest = useCallback(() => {
    const request = compareRef.current
    compareRef.current = null
    setCompareRequest(null)
    return request
  }, [])

  const keys = useMemo(() => new Set(cart.items.map((item) => item.product_key)), [cart.items])

  const value = useMemo(
    () => ({
      cart, loading, error, isOpen, setIsOpen, keys, addProduct, updateItem, removeItem, clearCart, refresh,
      compareRequest, requestCompare, takeCompareRequest,
    }),
    [cart, loading, error, isOpen, keys, addProduct, updateItem, removeItem, clearCart, refresh,
      compareRequest, requestCompare, takeCompareRequest],
  )

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}
