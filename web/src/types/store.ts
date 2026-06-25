export type Retailer = 'takealot' | 'checkers' | 'woolworths' | 'picknpay'

export type ScrapedProduct = {
  title: string
  price: string | null
  url: string
  retailer: string
  rating: string | null
  in_stock: boolean | null
}

export type ProductSearchResponse = {
  query: string
  products: ScrapedProduct[]
  errors: Record<string, string>
}

export type CartItem = ScrapedProduct & {
  cartId: string
  quantity: number
}
