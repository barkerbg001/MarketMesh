import { BotIcon, CpuIcon, DatabaseIcon, GlobeIcon, KeyRoundIcon, PaletteIcon, SlidersHorizontalIcon } from 'lucide-react'

import { AgentsSection } from '@/components/settings/agents-section'
import { AppearanceSection } from '@/components/settings/appearance-section'
import { DataSection } from '@/components/settings/data-section'
import { GenerationSection } from '@/components/settings/generation-section'
import { ModelsSection } from '@/components/settings/models-section'
import { OpenRouterSection } from '@/components/settings/openrouter-section'
import { ResearchSection } from '@/components/settings/research-section'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { routeHref } from '@/hooks/use-route'
import { useWorkspace } from '@/hooks/use-workspace'
import { cn } from '@/lib/utils'

const SECTIONS = [
  { id: 'openrouter', label: 'OpenRouter', icon: KeyRoundIcon, render: () => <OpenRouterSection /> },
  { id: 'models', label: 'Models', icon: CpuIcon, render: () => <ModelsSection /> },
  { id: 'generation', label: 'Generation', icon: SlidersHorizontalIcon, render: () => <GenerationSection /> },
  { id: 'region', label: 'Region & currency', icon: GlobeIcon, render: () => <ResearchSection /> },
  { id: 'appearance', label: 'Appearance', icon: PaletteIcon, render: () => <AppearanceSection /> },
  { id: 'agents', label: 'Agents', icon: BotIcon, render: () => <AgentsSection /> },
  { id: 'data', label: 'Data', icon: DatabaseIcon, render: () => <DataSection /> },
] as const

export function SettingsPage({ section }: { section: string | null }) {
  const { settings, settingsError, refreshSettings } = useWorkspace()
  const current = SECTIONS.find((entry) => entry.id === section) ?? SECTIONS[0]
  const needsServer = current.id !== 'appearance'

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 md:grid-cols-[13rem_1fr]">
      <div className="flex min-w-0 flex-col gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <nav aria-label="Settings sections">
          <ul className="flex gap-1 overflow-x-auto md:flex-col">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <li key={id}>
                <a
                  href={routeHref({ view: 'settings', section: id })}
                  aria-current={current.id === id ? 'page' : undefined}
                  className={cn(
                    'flex items-center gap-2 rounded-md px-3 py-2 text-sm whitespace-nowrap hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none',
                    current.id === id && 'bg-accent font-medium',
                  )}
                >
                  <Icon className="size-4" aria-hidden="true" />
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <p className="hidden text-xs text-muted-foreground md:block">
          MarketMesh is single-user: anyone who can reach this API shares these settings, cart and history.
        </p>
      </div>

      <div className="flex min-w-0 flex-col gap-4">
        {needsServer && settingsError && !settings ? (
          <Alert variant="destructive">
            <AlertTitle>Settings could not be loaded</AlertTitle>
            <AlertDescription>
              <p>{settingsError}</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => void refreshSettings()}>
                Try again
              </Button>
            </AlertDescription>
          </Alert>
        ) : needsServer && !settings ? (
          <div className="flex flex-col gap-3" aria-label="Loading settings">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          current.render()
        )}
      </div>
    </div>
  )
}
