import { CheckCircle2Icon, ChevronRightIcon, CircleAlertIcon, Loader2Icon } from 'lucide-react'

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import type { Activity } from '@/types/api'

/** What the agent did (tool calls), with the step in progress shown live. */
export function ActivityList({ activity, live }: { activity: Activity[]; live?: string }) {
  if (activity.length === 0 && !live) return null
  const failures = activity.filter((entry) => !entry.ok).length

  return (
    <Collapsible className="text-xs text-muted-foreground">
      <div className="flex flex-wrap items-center gap-2">
        {activity.length > 0 && (
          <CollapsibleTrigger className="group inline-flex items-center gap-1 rounded-sm hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none">
            <ChevronRightIcon className="size-3.5 transition-transform group-data-[state=open]:rotate-90" aria-hidden="true" />
            {activity.length} step{activity.length === 1 ? '' : 's'}
            {failures > 0 && <span className="text-destructive">, {failures} failed</span>}
          </CollapsibleTrigger>
        )}
        {live && (
          <span className="inline-flex items-center gap-1 text-foreground" role="status">
            <Loader2Icon className="size-3.5 animate-spin" aria-hidden="true" />
            {live}…
          </span>
        )}
      </div>
      <CollapsibleContent>
        <ol className="mt-1.5 flex flex-col gap-1 border-l pl-3">
          {activity.map((entry, index) => (
            <li key={index} className="flex items-start gap-1.5">
              {entry.ok ? (
                <CheckCircle2Icon className="mt-0.5 size-3.5 shrink-0 text-success" aria-hidden="true" />
              ) : (
                <CircleAlertIcon className="mt-0.5 size-3.5 shrink-0 text-destructive" aria-hidden="true" />
              )}
              <span>
                <span className="font-medium text-foreground">{entry.label}</span>
                {entry.summary ? `: ${entry.summary}` : ''}
              </span>
            </li>
          ))}
        </ol>
      </CollapsibleContent>
    </Collapsible>
  )
}
