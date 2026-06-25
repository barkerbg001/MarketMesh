import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import type { CartItem, ScrapedProduct } from '../types/store'

const CART_STORAGE_KEY = 'marketmesh-cart'

type CartContextValue = {
  items: CartItem[]
  itemCount: number
  subtotal: number
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  addItem: (product: ScrapedProduct) => void
  removeItem: (cartId: string) => void
  updateQuantity: (cartId: string, quantity: number) => void
  clearCart: () => void
}

const CartContext = createContext<CartContextValue | null>(null)

function cartIdFor(product: ScrapedProduct) {
  return `${product.retailer}:${product.url}`
}

function readStoredCart(): CartItem[] {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as CartItem[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function parsePrice(price: string | null): number {
  if (!price) return 0
  const digits = price.replace(/[^\d.]/g, '')
  const value = Number.parseFloat(digits)
  return Number.isFinite(value) ? value : 0
}

export function formatPrice(amount: number) {
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: 'ZAR',
    minimumFractionDigits: 2,
  }).format(amount)
}

export function displayPrice(price: string | null) {
  if (!price) return 'Price unavailable'
  return price.startsWith('R') ? price : `R${price}`
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(() => readStoredCart())
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const addItem = useCallback((product: ScrapedProduct) => {
    const cartId = cartIdFor(product)
    setItems((current) => {
      const existing = current.find((item) => item.cartId === cartId)
      if (existing) {
        return current.map((item) =>
          item.cartId === cartId ? { ...item, quantity: item.quantity + 1 } : item,
        )
      }
      return [...current, { ...product, cartId, quantity: 1 }]
    })
    setIsOpen(true)
  }, [])

  const removeItem = useCallback((cartId: string) => {
    setItems((current) => current.filter((item) => item.cartId !== cartId))
  }, [])

  const updateQuantity = useCallback((cartId: string, quantity: number) => {
    if (quantity < 1) {
      setItems((current) => current.filter((item) => item.cartId !== cartId))
      return
    }
    setItems((current) =>
      current.map((item) => (item.cartId === cartId ? { ...item, quantity } : item)),
    )
  }, [])

  const clearCart = useCallback(() => {
    setItems([])
  }, [])

  const itemCount = useMemo(
    () => items.reduce((total, item) => total + item.quantity, 0),
    [items],
  )

  const subtotal = useMemo(
    () => items.reduce((total, item) => total + parsePrice(item.price) * item.quantity, 0),
    [items],
  )

  const value = useMemo(
    () => ({
      items,
      itemCount,
      subtotal,
      isOpen,
      setIsOpen,
      addItem,
      removeItem,
      updateQuantity,
      clearCart,
    }),
    [items, itemCount, subtotal, isOpen, addItem, removeItem, updateQuantity, clearCart],
  )

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  const context = useContext(CartContext)
  if (!context) {
    throw new Error('useCart must be used within CartProvider')
  }
  return context
}
