import type { Retailer } from '@/lib/retailers'
import type { Product } from '@/types/api'

export type ProductSearchRequest = {
  query: string
  retailers: Retailer[]
  max_results: number
}

export type SearchProduct = Product & {
  retailer: string
  rating: string | null
  in_stock: boolean | null
}

export type ProductSearchResponse = {
  query: string
  retrieved_at: string
  products: SearchProduct[]
  errors: Record<string, string>
}
