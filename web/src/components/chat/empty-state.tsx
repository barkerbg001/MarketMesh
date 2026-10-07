import { SparklesIcon } from 'lucide-react'

import { AgentAvatar } from '@/components/agents/agent-avatar'
import { Button } from '@/components/ui/button'
import type { Agent } from '@/types/api'

const RETAILER_PROMPTS = [
  'Find the cheapest 2L full cream milk across Checkers, Pick n Pay and Woolworths.',
  '@scout Find prices for Huggies size 4 nappies at South African retailers.',
  'I need a cordless drill under R1500. Find options on Takealot and compare the top three.',
  '@atlas Who are the main air fryer brands in South Africa and how are they positioned on price?',
]

const WEB_PROMPTS = [
  'What are the best noise-cancelling headphones under $300 right now?',
  '@atlas How is the robot vacuum market split between budget and premium brands?',
  'Compare the current Kindle models and tell me which one is the best value.',
  '@scout Find three popular standing desks with their prices and warranty terms.',
]

export function EmptyState({
  agents,
  region,
  onPrompt,
  disabled,
}: {
  agents: Agent[]
  region: string | undefined
  onPrompt: (prompt: string) => void
  disabled: boolean
}) {
  const prompts = region === 'za-en' ? RETAILER_PROMPTS : WEB_PROMPTS
  const handles = new Set(agents.map((agent) => agent.handle))
  const usable = prompts.filter((prompt) => {
    const mention = /^@(\w+)/.exec(prompt)
    return !mention || handles.has(mention[1])
  })

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 py-8">
      <div className="flex flex-col gap-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">What are you researching?</h1>
        <p className="text-muted-foreground">
          Ask the team. Mesh answers and brings in specialists. Type <kbd className="rounded border px-1 text-xs">@</kbd>{' '}
          to talk to one directly.
        </p>
      </div>

      <ul className="grid gap-3 sm:grid-cols-2" aria-label="Research team">
        {agents.map((agent) => (
          <li key={agent.id} className="flex gap-3 rounded-lg border p-3">
            <AgentAvatar agent={agent} size="md" />
            <div className="min-w-0">
              <p className="text-sm">
                <span className="font-semibold">{agent.name}</span>{' '}
                <span className="text-muted-foreground">@{agent.handle}</span>
              </p>
              <p className="text-xs text-muted-foreground">{agent.role}</p>
              <p className="mt-1 text-sm">{agent.intro}</p>
            </div>
          </li>
        ))}
      </ul>

      <section aria-label="Suggested prompts" className="flex flex-col gap-2">
        <h2 className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
          <SparklesIcon className="size-4" aria-hidden="true" />
          Try one of these
        </h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {usable.map((prompt) => (
            <Button
              key={prompt}
              variant="outline"
              className="h-auto justify-start py-2.5 text-left whitespace-normal"
              disabled={disabled}
              onClick={() => onPrompt(prompt)}
            >
              {prompt}
            </Button>
          ))}
        </div>
      </section>
    </div>
  )
}
