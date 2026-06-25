import { useMemo, useState, type FormEvent } from 'react'

import { CartProvider, displayPrice, formatPrice, useCart } from '../hooks/useCart'
import type { ProductSearchResponse, Retailer, ScrapedProduct } from '../types/store'

const RETAILERS: { id: Retailer | 'all'; label: string }[] = [
  { id: 'all', label: 'All stores' },
  { id: 'takealot', label: 'Takealot' },
  { id: 'checkers', label: 'Checkers' },
  { id: 'woolworths', label: 'Woolworths' },
  { id: 'picknpay', label: 'Pick n Pay' },
]

const EXAMPLE_QUERIES = ['full cream milk', 'bread', 'coffee', 'chicken breast']

const RETAILER_LABELS: Record<string, string> = {
  takealot: 'Takealot',
  checkers: 'Checkers',
  woolworths: 'Woolworths',
  picknpay: 'Pick n Pay',
}

function retailerBadgeClass(retailer: string) {
  return `retailer-badge retailer-${retailer}`
}

function ProductCard({
  product,
  onAdd,
}: {
  product: ScrapedProduct
  onAdd: (product: ScrapedProduct) => void
}) {
  const outOfStock = product.in_stock === false

  return (
    <article className="product-card">
      <div className="product-image">
        <span className="product-image-placeholder" aria-hidden="true">
          {product.title.slice(0, 1).toUpperCase()}
        </span>
        <span className={retailerBadgeClass(product.retailer)}>
          {RETAILER_LABELS[product.retailer] ?? product.retailer}
        </span>
      </div>

      <div className="product-body">
        <h3 className="product-title">{product.title}</h3>
        <div className="product-meta">
          <span className="product-price">{displayPrice(product.price)}</span>
          {product.rating && <span className="product-rating">★ {product.rating}</span>}
        </div>
        {outOfStock && <span className="stock-badge out-of-stock">Out of stock</span>}
        {product.in_stock === true && <span className="stock-badge in-stock">In stock</span>}
      </div>

      <div className="product-actions">
        <a href={product.url} target="_blank" rel="noreferrer" className="btn btn-ghost">
          View
        </a>
        <button
          type="button"
          className="btn btn-primary"
          disabled={outOfStock}
          onClick={() => onAdd(product)}
        >
          Add to cart
        </button>
      </div>
    </article>
  )
}

function CartDrawer() {
  const { items, itemCount, subtotal, isOpen, setIsOpen, removeItem, updateQuantity, clearCart } =
    useCart()

  if (!isOpen) return null

  return (
    <>
      <button
        type="button"
        className="cart-backdrop"
        aria-label="Close cart"
        onClick={() => setIsOpen(false)}
      />
      <aside className="cart-drawer" aria-label="Shopping cart">
        <header className="cart-header">
          <div>
            <h2>Your cart</h2>
            <p>{itemCount} item{itemCount === 1 ? '' : 's'}</p>
          </div>
          <button type="button" className="icon-btn" onClick={() => setIsOpen(false)} aria-label="Close">
            ×
          </button>
        </header>

        {items.length === 0 ? (
          <div className="cart-empty">
            <p>Your cart is empty.</p>
            <p className="cart-empty-hint">Search for products and add them here.</p>
          </div>
        ) : (
          <>
            <ul className="cart-items">
              {items.map((item) => (
                <li key={item.cartId} className="cart-item">
                  <div className="cart-item-info">
                    <span className={retailerBadgeClass(item.retailer)}>
                      {RETAILER_LABELS[item.retailer] ?? item.retailer}
                    </span>
                    <strong>{item.title}</strong>
                    <span className="cart-item-price">{displayPrice(item.price)}</span>
                  </div>
                  <div className="cart-item-controls">
                    <div className="qty-controls">
                      <button
                        type="button"
                        className="qty-btn"
                        aria-label="Decrease quantity"
                        onClick={() => updateQuantity(item.cartId, item.quantity - 1)}
                      >
                        −
                      </button>
                      <span>{item.quantity}</span>
                      <button
                        type="button"
                        className="qty-btn"
                        aria-label="Increase quantity"
                        onClick={() => updateQuantity(item.cartId, item.quantity + 1)}
                      >
                        +
                      </button>
                    </div>
                    <button
                      type="button"
                      className="link-btn"
                      onClick={() => removeItem(item.cartId)}
                    >
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>

            <footer className="cart-footer">
              <div className="cart-subtotal">
                <span>Subtotal</span>
                <strong>{formatPrice(subtotal)}</strong>
              </div>
              <p className="cart-note">
                Prices are scraped live from each retailer. Checkout happens on the retailer&apos;s
                site.
              </p>
              <button type="button" className="btn btn-primary btn-block" disabled>
                Checkout (coming soon)
              </button>
              <button type="button" className="btn btn-ghost btn-block" onClick={clearCart}>
                Clear cart
              </button>
            </footer>
          </>
        )}
      </aside>
    </>
  )
}

export function Store() {
  const [query, setQuery] = useState('')
  const [activeRetailer, setActiveRetailer] = useState<Retailer | 'all'>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchResult, setSearchResult] = useState<ProductSearchResponse | null>(null)
  const { itemCount, setIsOpen, addItem } = useCart()

  const visibleProducts = useMemo(() => {
    if (!searchResult) return []
    if (activeRetailer === 'all') return searchResult.products
    return searchResult.products.filter((product) => product.retailer === activeRetailer)
  }, [searchResult, activeRetailer])

  async function runSearch(searchQuery: string) {
    const trimmed = searchQuery.trim()
    if (!trimmed || loading) return

    setQuery(trimmed)
    setLoading(true)
    setError(null)
    setSearchResult(null)

    try {
      const response = await fetch('/api/products/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmed,
          retailers: ['takealot', 'checkers', 'woolworths', 'picknpay'],
          max_results: 8,
        }),
      })

      const data = (await response.json()) as ProductSearchResponse | { detail?: unknown }

      if (!response.ok) {
        const detail = typeof data === 'object' && data && 'detail' in data ? data.detail : null
        if (typeof detail === 'string') throw new Error(detail)
        if (typeof detail === 'object' && detail && 'message' in detail) {
          throw new Error(String((detail as { message: string }).message))
        }
        throw new Error('Product search failed')
      }

      setSearchResult(data as ProductSearchResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Product search failed')
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void runSearch(query)
  }

  return (
    <div className="store-shell">
      <header className="store-header">
        <div className="store-brand">
          <span className="hero-badge">Price comparison store</span>
          <h1>MarketMesh</h1>
          <p>Search Takealot, Checkers, Woolworths, and Pick n Pay — add the best deals to your cart.</p>
        </div>
        <button type="button" className="cart-toggle" onClick={() => setIsOpen(true)}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M6 6h15l-1.5 9h-12L6 6Z"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
            <path d="M6 6 5 3H2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="9" cy="20" r="1.5" fill="currentColor" />
            <circle cx="18" cy="20" r="1.5" fill="currentColor" />
          </svg>
          Cart
          {itemCount > 0 && <span className="cart-count">{itemCount}</span>}
        </button>
      </header>

      <section className="search-panel store-search">
        <form onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="product-query">
            Search products
          </label>
          <div className={`input-wrap${loading ? ' loading' : ''}`}>
            <input
              id="product-query"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search groceries, electronics, household…"
              disabled={loading}
            />
            <button type="submit" disabled={loading || !query.trim()} aria-label="Search products">
              {loading ? (
                <span className="spinner" aria-hidden="true" />
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M21 21l-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              )}
            </button>
          </div>
        </form>

        {!searchResult && !loading && !error && (
          <div className="examples">
            <span className="examples-label">Popular searches</span>
            <div className="example-chips">
              {EXAMPLE_QUERIES.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="chip"
                  onClick={() => void runSearch(example)}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {searchResult && (
        <div className="retailer-tabs" role="tablist" aria-label="Filter by retailer">
          {RETAILERS.map((retailer) => {
            const count =
              retailer.id === 'all'
                ? searchResult.products.length
                : searchResult.products.filter((product) => product.retailer === retailer.id).length
            return (
              <button
                key={retailer.id}
                type="button"
                role="tab"
                aria-selected={activeRetailer === retailer.id}
                className={`retailer-tab${activeRetailer === retailer.id ? ' active' : ''}`}
                onClick={() => setActiveRetailer(retailer.id)}
              >
                {retailer.label}
                <span className="tab-count">{count}</span>
              </button>
            )
          })}
        </div>
      )}

      {error && (
        <div className="alert alert-error" role="alert">
          <strong>Search failed</strong>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <section className="product-grid loading-grid" aria-live="polite" aria-busy="true">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="product-card skeleton-card">
              <div className="skeleton product-skeleton-image" />
              <div className="skeleton" />
              <div className="skeleton short" />
            </div>
          ))}
        </section>
      )}

      {!loading && searchResult && visibleProducts.length > 0 && (
        <section className="results-summary">
          <p>
            Showing <strong>{visibleProducts.length}</strong> results for &ldquo;
            {searchResult.query}&rdquo;
          </p>
          {Object.keys(searchResult.errors).length > 0 && (
            <p className="partial-errors">
              Some stores could not be searched:{' '}
              {Object.entries(searchResult.errors)
                .map(([retailer, message]) => `${RETAILER_LABELS[retailer] ?? retailer}: ${message}`)
                .join(' · ')}
            </p>
          )}
        </section>
      )}

      {!loading && searchResult && visibleProducts.length === 0 && (
        <div className="empty-state">
          <h2>No products found</h2>
          <p>Try another search term or switch retailer tabs.</p>
        </div>
      )}

      {!loading && visibleProducts.length > 0 && (
        <section className="product-grid">
          {visibleProducts.map((product) => (
            <ProductCard key={`${product.retailer}:${product.url}`} product={product} onAdd={addItem} />
          ))}
        </section>
      )}

      <CartDrawer />
    </div>
  )
}

export function StoreWithCart() {
  return (
    <CartProvider>
      <Store />
    </CartProvider>
  )
}
