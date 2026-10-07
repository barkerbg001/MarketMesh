type Priced = { price: string | null; price_amount: string | null; currency: string | null }

const formatters = new Map<string, Intl.NumberFormat>()

function formatterFor(currency: string) {
  let formatter = formatters.get(currency)
  if (!formatter) {
    try {
      formatter = new Intl.NumberFormat(undefined, { style: 'currency', currency, minimumFractionDigits: 2 })
    } catch {
      formatter = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
    formatters.set(currency, formatter)
  }
  return formatter
}

/** Format a decimal string in its own currency. Amounts are never converted. */
export function formatMoney(amount: string, currency: string) {
  const value = Number(amount)
  if (!Number.isFinite(value)) return `${currency} ${amount}`
  return formatterFor(currency).format(value)
}

/** The price as retrieved: formatted when amount and currency are known, else the raw text, else unknown. */
export function displayPrice(product: Priced) {
  if (product.price_amount && product.currency) return formatMoney(product.price_amount, product.currency)
  if (product.price) return product.price
  return 'Price unknown'
}

export function hasKnownPrice(product: Priced) {
  return Boolean(product.price_amount && product.currency)
}

/** Order subtotals with the preferred currency first; others follow alphabetically. */
export function orderSubtotals<T extends { currency: string }>(subtotals: T[], preferred: string) {
  return [...subtotals].sort((a, b) => {
    if (a.currency === preferred) return -1
    if (b.currency === preferred) return 1
    return a.currency.localeCompare(b.currency)
  })
}
