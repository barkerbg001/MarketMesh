export type Retailer = 'takealot' | 'checkers' | 'woolworths' | 'picknpay'

export const RETAILERS: { id: Retailer; label: string; dotClass: string }[] = [
  { id: 'takealot', label: 'Takealot', dotClass: 'bg-retailer-takealot' },
  { id: 'checkers', label: 'Checkers', dotClass: 'bg-retailer-checkers' },
  { id: 'woolworths', label: 'Woolworths', dotClass: 'bg-retailer-woolworths' },
  { id: 'picknpay', label: 'Pick n Pay', dotClass: 'bg-retailer-picknpay' },
]

export const ALL_RETAILER_IDS: Retailer[] = RETAILERS.map((retailer) => retailer.id)

export function isRetailer(value: string): value is Retailer {
  return RETAILERS.some((entry) => entry.id === value)
}

export function retailerLabel(retailer: string) {
  return RETAILERS.find((entry) => entry.id === retailer)?.label ?? retailer
}

export function retailerDotClass(retailer: string) {
  return RETAILERS.find((entry) => entry.id === retailer)?.dotClass ?? 'bg-muted-foreground'
}
