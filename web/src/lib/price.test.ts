import { describe, expect, it } from 'vitest'

import { displayPrice, formatMoney, hasKnownPrice, orderSubtotals } from '@/lib/price'

describe('displayPrice', () => {
  it('formats a known amount in its own currency', () => {
    const text = displayPrice({ price: 'R 1,299.00', price_amount: '1299.00', currency: 'ZAR' })
    expect(text).toMatch(/1[\s,.\u00a0\u202f]?299/)
    expect(text).not.toContain('$')
  })

  it('falls back to raw text, then to an explicit unknown label', () => {
    expect(displayPrice({ price: 'From R99', price_amount: null, currency: null })).toBe('From R99')
    expect(displayPrice({ price: null, price_amount: null, currency: null })).toBe('Price unknown')
  })

  it('only treats amount plus currency as a known price', () => {
    expect(hasKnownPrice({ price: 'R99', price_amount: null, currency: 'ZAR' })).toBe(false)
    expect(hasKnownPrice({ price: null, price_amount: '99', currency: 'ZAR' })).toBe(true)
  })
})

describe('formatMoney', () => {
  it('keeps the original text when the amount is not numeric', () => {
    expect(formatMoney('n/a', 'USD')).toBe('USD n/a')
  })
})

describe('orderSubtotals', () => {
  it('puts the preferred currency first and never merges currencies', () => {
    const ordered = orderSubtotals(
      [
        { currency: 'USD', amount: '10.00' },
        { currency: 'EUR', amount: '5.00' },
        { currency: 'ZAR', amount: '100.00' },
      ],
      'ZAR',
    )
    expect(ordered.map((entry) => entry.currency)).toEqual(['ZAR', 'EUR', 'USD'])
  })
})
