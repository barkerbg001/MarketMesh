import { GlobeIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { isRetailer, retailerDotClass, retailerLabel } from '@/lib/retailers'

/** The seller/source of a product: a coloured dot for built-in retailers, a globe for web sources. */
export function SourceBadge({ source, seller }: { source: string; seller?: string | null }) {
  const retailer = isRetailer(source)
  return (
    <Badge variant="outline" className="max-w-full bg-background/90 backdrop-blur-sm">
      {retailer ? (
        <span className={`size-2 shrink-0 rounded-full ${retailerDotClass(source)}`} aria-hidden="true" />
      ) : (
        <GlobeIcon aria-hidden="true" />
      )}
      <span className="truncate">{retailer ? retailerLabel(source) : seller || source}</span>
    </Badge>
  )
}
