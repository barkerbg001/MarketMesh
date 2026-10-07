import { createContext, useContext } from 'react'

import type { CartItem, CartState, Product } from '@/types/api'

export type CompareRequest = { itemIds: number[]; titles: string[] }

export type CartContextValue = {
  cart: CartState
  loading: boolean
  error: string | null
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  /** Product keys currently in the cart, for "In cart" states. */
  keys: Set<string>
  addProduct: (product: Product, conversationId?: string | null) => Promise<void>
  updateItem: (id: number, changes: { quantity?: number; notes?: string }) => Promise<void>
  removeItem: (id: number) => Promise<void>
  clearCart: () => Promise<void>
  refresh: () => Promise<void>
  compareRequest: CompareRequest | null
  requestCompare: (items: CartItem[]) => void
  takeCompareRequest: () => CompareRequest | null
}

export const EMPTY_CART: CartState = { items: [], subtotals: [], unknown_price_count: 0, item_count: 0 }

export const CartContext = createContext<CartContextValue | null>(null)

export function useCart() {
  const context = useContext(CartContext)
  if (!context) throw new Error('useCart must be used within CartProvider')
  return context
}
