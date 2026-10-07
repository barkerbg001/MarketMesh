import { useState } from 'react'
import { CheckIcon, ClockIcon, ExternalLinkIcon, ShoppingCartIcon } from 'lucide-react'

import { SourceBadge } from '@/components/store/retailer-badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { displayPrice, hasKnownPrice } from '@/lib/price'
import { formatDateTime, timeAgo } from '@/lib/time'
import { cn } from '@/lib/utils'
import type { Product } from '@/types/api'

type ProductCardProps = {
  product: Product
  inCart?: boolean
  onAdd?: (product: Product) => void
  compact?: boolean
}

function ProductImage({ product, compact }: { product: Product; compact?: boolean }) {
  const [failed, setFailed] = useState(false)
  const showImage = product.image_url && !failed
  return (
    <div
      className={cn(
        'relative flex items-center justify-center overflow-hidden bg-muted',
        compact ? 'aspect-[2/1]' : 'aspect-[3/1] sm:aspect-[4/3]',
      )}
    >
      {showImage ? (
        <img
          src={product.image_url ?? undefined}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
          className="size-full object-contain p-2 mix-blend-multiply dark:mix-blend-normal"
        />
      ) : (
        <span className="text-4xl font-semibold text-muted-foreground/60" aria-hidden="true">
          {product.title.slice(0, 1).toUpperCase()}
        </span>
      )}
      <div className="absolute top-2 left-2 max-w-[85%]">
        <SourceBadge source={product.source} seller={product.seller} />
      </div>
    </div>
  )
}

export function ProductCard({ product, inCart = false, onAdd, compact = false }: ProductCardProps) {
  const specs = Object.entries(product.specs ?? {}).slice(0, compact ? 3 : 4)
  const outOfStock = product.in_stock === false

  return (
    <Card className="h-full gap-3 overflow-hidden pt-0 pb-3">
      <ProductImage product={product} compact={compact} />

      <CardContent className="flex flex-1 flex-col gap-2 px-3">
        <h3 className="line-clamp-2 text-sm font-medium leading-snug" title={product.title}>
          {product.title}
        </h3>
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span
            className={cn('font-semibold tabular-nums', hasKnownPrice(product) ? 'text-base' : 'text-sm text-muted-foreground')}
          >
            {displayPrice(product)}
          </span>
          {product.currency && <span className="text-xs text-muted-foreground">{product.currency}</span>}
        </div>
        {specs.length > 0 && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-xs">
            {specs.map(([name, value]) => (
              <div key={name} className="contents">
                <dt className="text-muted-foreground">{name}</dt>
                <dd className={cn('truncate', name === 'Availability' && outOfStock && 'text-destructive')} title={value}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        )}
        <p className="mt-auto flex items-center gap-1 text-xs text-muted-foreground" title={formatDateTime(product.retrieved_at)}>
          <ClockIcon className="size-3" aria-hidden="true" />
          Retrieved {timeAgo(product.retrieved_at)}
        </p>
      </CardContent>

      <CardFooter className="gap-2 px-3">
        <Button variant="outline" size="sm" className="flex-1" asChild>
          <a href={product.url} target="_blank" rel="noopener noreferrer">
            <ExternalLinkIcon data-icon="inline-start" aria-hidden="true" />
            Source
            <span className="sr-only"> for {product.title} (opens in a new tab)</span>
          </a>
        </Button>
        {onAdd && (
          <Button
            size="sm"
            className="flex-1"
            variant={inCart ? 'secondary' : 'default'}
            onClick={() => onAdd(product)}
            aria-label={inCart ? `${product.title} is in your cart` : `Add ${product.title} to cart`}
          >
            {inCart ? (
              <CheckIcon data-icon="inline-start" aria-hidden="true" />
            ) : (
              <ShoppingCartIcon data-icon="inline-start" aria-hidden="true" />
            )}
            {inCart ? 'In cart' : 'Add'}
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}

export function ProductCardSkeleton() {
  return (
    <Card className="h-full gap-3 pt-0 pb-3" aria-hidden="true">
      <Skeleton className="aspect-[3/1] rounded-none sm:aspect-[4/3]" />
      <CardContent className="flex flex-col gap-2 px-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="mt-1 h-5 w-24" />
      </CardContent>
      <CardFooter className="gap-2 px-3">
        <Skeleton className="h-7 flex-1" />
        <Skeleton className="h-7 flex-1" />
      </CardFooter>
    </Card>
  )
}
