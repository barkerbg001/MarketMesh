import { useId, useMemo, useState, type FormEvent } from 'react'
import {
  AlertCircleIcon,
  Loader2Icon,
  MessageSquareTextIcon,
  PackageSearchIcon,
  SearchIcon,
  TriangleAlertIcon,
} from 'lucide-react'

import { ProductCard, ProductCardSkeleton } from '@/components/store/product-card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useCart } from '@/hooks/use-cart'
import { postJson } from '@/lib/api'
import { ALL_RETAILER_IDS, RETAILERS, retailerLabel, type Retailer } from '@/lib/retailers'
import { formatDateTime } from '@/lib/time'
import type { ProductSearchRequest, ProductSearchResponse } from '@/types/store'

const EXAMPLE_QUERIES = ['full cream milk', 'bread', 'coffee', 'chicken breast']
const MAX_QUERY_LENGTH = 200
const RESULTS_PER_RETAILER = 8

type RetailerFilter = Retailer | 'all'

export function ProductSearch() {
  const inputId = useId()
  const errorId = useId()
  const [query, setQuery] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [activeRetailer, setActiveRetailer] = useState<RetailerFilter>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchResult, setSearchResult] = useState<ProductSearchResponse | null>(null)
  const { addProduct, keys } = useCart()

  const visibleProducts = useMemo(() => {
    if (!searchResult) return []
    if (activeRetailer === 'all') return searchResult.products
    return searchResult.products.filter((product) => product.retailer === activeRetailer)
  }, [searchResult, activeRetailer])

  const partialErrors = searchResult ? Object.entries(searchResult.errors) : []

  async function runSearch(searchQuery: string) {
    const trimmed = searchQuery.trim()
    if (!trimmed) {
      setValidationError('Enter a product to search for.')
      return
    }
    if (loading) return

    setQuery(trimmed)
    setValidationError(null)
    setLoading(true)
    setError(null)
    setSearchResult(null)
    setActiveRetailer('all')

    try {
      const payload: ProductSearchRequest = {
        query: trimmed,
        retailers: ALL_RETAILER_IDS,
        max_results: RESULTS_PER_RETAILER,
      }
      setSearchResult(
        await postJson<ProductSearchResponse>('/api/products/search', payload, 'Product search failed'),
      )
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
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2 text-center sm:py-4">
        <p className="text-sm font-medium text-primary">Live retailer search</p>
        <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Search South African retailers directly
        </h1>
        <p className="mx-auto max-w-2xl text-muted-foreground text-pretty">
          Prices are read live from Takealot, Checkers, Woolworths, and Pick n Pay. Add options to your
          research cart, or <a href="#/chat" className="font-medium text-primary underline underline-offset-2">ask the agents</a> to
          research other stores and regions.
        </p>
      </section>

      <section className="mx-auto flex w-full max-w-2xl flex-col gap-3">
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-1.5">
          <label className="sr-only" htmlFor={inputId}>
            Search products
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <SearchIcon
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                id={inputId}
                type="search"
                value={query}
                maxLength={MAX_QUERY_LENGTH}
                onChange={(event) => {
                  setQuery(event.target.value)
                  if (validationError) setValidationError(null)
                }}
                placeholder="Search groceries, electronics, household…"
                className="h-10 pl-9 text-base md:text-sm"
                aria-invalid={validationError ? true : undefined}
                aria-describedby={validationError ? errorId : undefined}
                autoComplete="off"
              />
            </div>
            <Button type="submit" size="lg" className="h-10 px-4" disabled={loading}>
              {loading ? (
                <Loader2Icon className="animate-spin" data-icon="inline-start" aria-hidden="true" />
              ) : (
                <SearchIcon data-icon="inline-start" aria-hidden="true" />
              )}
              {loading ? 'Searching' : 'Search'}
            </Button>
          </div>
          {validationError && (
            <p id={errorId} className="text-sm text-destructive">
              {validationError}
            </p>
          )}
        </form>

        {!searchResult && !loading && !error && (
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="text-sm text-muted-foreground">Popular searches:</span>
            {EXAMPLE_QUERIES.map((example) => (
              <Button
                key={example}
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={() => void runSearch(example)}
              >
                {example}
              </Button>
            ))}
          </div>
        )}
      </section>

      <p className="sr-only" aria-live="polite">
        {loading
          ? 'Searching retailers…'
          : searchResult
            ? `${searchResult.products.length} products found for ${searchResult.query}`
            : ''}
      </p>

      {error && (
        <Alert variant="destructive" className="mx-auto max-w-2xl">
          <AlertCircleIcon aria-hidden="true" />
          <AlertTitle>Search failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && (
        <section aria-busy="true" aria-label="Loading products" className="flex flex-col gap-3">
          <p className="text-center text-sm text-muted-foreground">
            Scraping live prices from four stores — this can take a minute or two.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }, (_, index) => (
              <ProductCardSkeleton key={index} />
            ))}
          </div>
        </section>
      )}

      {!loading && searchResult && (
        <section className="flex flex-col gap-4" aria-label="Search results">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <p className="text-sm text-muted-foreground">
              Showing <strong className="text-foreground">{visibleProducts.length}</strong> results for
              &ldquo;{searchResult.query}&rdquo;, retrieved {formatDateTime(searchResult.retrieved_at)}
            </p>
            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              value={activeRetailer}
              onValueChange={(value) => {
                if (value) setActiveRetailer(value as RetailerFilter)
              }}
              aria-label="Filter by retailer"
              className="flex-wrap"
            >
              {[{ id: 'all' as const, label: 'All stores' }, ...RETAILERS].map((retailer) => {
                const count =
                  retailer.id === 'all'
                    ? searchResult.products.length
                    : searchResult.products.filter((product) => product.retailer === retailer.id).length
                return (
                  <ToggleGroupItem key={retailer.id} value={retailer.id}>
                    {retailer.label}
                    <span className="text-xs text-muted-foreground tabular-nums">{count}</span>
                  </ToggleGroupItem>
                )
              })}
            </ToggleGroup>
          </div>

          {partialErrors.length > 0 && (
            <Alert>
              <TriangleAlertIcon aria-hidden="true" />
              <AlertTitle>Some stores could not be searched</AlertTitle>
              <AlertDescription>
                <ul className="list-inside list-disc">
                  {partialErrors.map(([retailer, message]) => (
                    <li key={retailer}>
                      <span className="font-medium text-foreground">{retailerLabel(retailer)}:</span>{' '}
                      {message}
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {visibleProducts.length === 0 ? (
            <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed p-10 text-center">
              <PackageSearchIcon className="size-10 text-muted-foreground/60" aria-hidden="true" />
              <h2 className="font-medium">No products found</h2>
              <p className="text-sm text-muted-foreground">
                Try another search term or switch retailer filters.
              </p>
            </div>
          ) : (
            <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {visibleProducts.map((product) => (
                <li key={product.key}>
                  <ProductCard
                    product={product}
                    inCart={keys.has(product.key)}
                    onAdd={(item) => void addProduct(item)}
                  />
                </li>
              ))}
            </ul>
          )}
          <p className="flex items-center justify-center gap-2 text-center text-sm text-muted-foreground">
            <MessageSquareTextIcon className="size-4" aria-hidden="true" />
            Want a comparison or other stores? <a href="#/chat" className="font-medium text-primary underline underline-offset-2">Ask the research team</a>.
          </p>
        </section>
      )}
    </div>
  )
}
