import { LinkIcon } from 'lucide-react'

import { formatDateTime, timeAgo } from '@/lib/time'
import type { Source } from '@/types/api'

function hostOf(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function SourceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null
  return (
    <section aria-label="Sources" className="flex flex-col gap-1.5">
      <h4 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Sources</h4>
      <ol className="flex flex-col gap-1 text-sm">
        {sources.map((source, index) => (
          <li key={source.url} className="flex min-w-0 items-baseline gap-2">
            <span className="text-xs text-muted-foreground tabular-nums">{index + 1}.</span>
            <div className="min-w-0">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium break-words text-primary underline-offset-2 hover:underline"
              >
                {source.title || hostOf(source.url)}
              </a>
              <span className="text-xs text-muted-foreground">
                {' '}
                <LinkIcon className="inline size-3" aria-hidden="true" /> {hostOf(source.url)} ·{' '}
                {source.via === 'fetch_page' ? 'read' : 'found'}{' '}
                <time dateTime={source.retrieved_at ?? undefined} title={formatDateTime(source.retrieved_at)}>
                  {timeAgo(source.retrieved_at)}
                </time>
              </span>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
