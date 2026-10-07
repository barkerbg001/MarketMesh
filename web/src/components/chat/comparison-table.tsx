import { CheckIcon, ShoppingCartIcon, TrophyIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDateTime } from '@/lib/time'
import { cn } from '@/lib/utils'
import type { Comparison, Product } from '@/types/api'

export function ComparisonTable({
  comparison,
  inCart,
  onAdd,
}: {
  comparison: Comparison
  inCart: (key: string) => boolean
  onAdd: (product: Product) => void
}) {
  const products = comparison.product_keys
    .map((key) => comparison.products.find((product) => product.key === key))
    .filter((product): product is Product => Boolean(product))

  return (
    <section aria-label={comparison.title} className="flex flex-col gap-2 rounded-lg border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-medium">{comparison.title}</h4>
        <span className="text-xs text-muted-foreground">Built {formatDateTime(comparison.created_at)}</span>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-32">Criterion</TableHead>
            {products.map((product) => (
              <TableHead key={product.key} className="min-w-40 align-top whitespace-normal">
                <a href={product.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline">
                  {product.title}
                </a>
                <div className="text-xs font-normal text-muted-foreground">{product.seller || product.source}</div>
                {comparison.best_pick_key === product.key && (
                  <Badge className="mt-1">
                    <TrophyIcon aria-hidden="true" />
                    Best pick
                  </Badge>
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {comparison.rows.map((row) => (
            <TableRow key={row.name}>
              <TableCell className="font-medium whitespace-normal">
                {row.name}
                {row.derived && <span className="block text-xs font-normal text-muted-foreground">from sources</span>}
              </TableCell>
              {products.map((product) => {
                const value = row.values[product.key] ?? 'Unknown'
                const winner = row.verdict === product.key
                return (
                  <TableCell
                    key={product.key}
                    className={cn(
                      'whitespace-normal',
                      value === 'Unknown' && 'text-muted-foreground italic',
                      winner && 'bg-primary/10 font-medium',
                    )}
                  >
                    {value}
                    {winner && <span className="sr-only"> (best for {row.name})</span>}
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
          <TableRow>
            <TableCell className="text-muted-foreground">Shortlist</TableCell>
            {products.map((product) => (
              <TableCell key={product.key}>
                <Button
                  size="sm"
                  variant={inCart(product.key) ? 'secondary' : 'outline'}
                  onClick={() => onAdd(product)}
                  aria-label={inCart(product.key) ? `${product.title} is in your cart` : `Add ${product.title} to cart`}
                >
                  {inCart(product.key) ? (
                    <CheckIcon data-icon="inline-start" aria-hidden="true" />
                  ) : (
                    <ShoppingCartIcon data-icon="inline-start" aria-hidden="true" />
                  )}
                  {inCart(product.key) ? 'In cart' : 'Add'}
                </Button>
              </TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>
      {comparison.summary && <p className="text-sm">{comparison.summary}</p>}
    </section>
  )
}
