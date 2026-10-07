import { AgentAvatar } from '@/components/agents/agent-avatar'
import { SettingsSection } from '@/components/settings/settings-section'
import { Badge } from '@/components/ui/badge'
import { useWorkspace } from '@/hooks/use-workspace'

export function AgentsSection() {
  const { agents, settings } = useWorkspace()

  return (
    <SettingsSection
      title="The team"
      description={
        <>
          Who answers in chat. Personas live in <code className="text-xs">api/agents/personas.py</code>. Avatars are
          generated in your browser from fixed seeds with DiceBear (Notionists by Zoish, CC0 1.0).
        </>
      }
    >
      <ul className="grid gap-3 lg:grid-cols-2">
        {agents.map((agent) => {
          const model = settings?.agent_models[agent.id] || settings?.default_model
          return (
            <li key={agent.id} className="flex gap-4 rounded-lg border p-4">
              <AgentAvatar agent={agent} size="lg" />
              <div className="flex min-w-0 flex-col gap-1.5">
                <p>
                  <span className="font-semibold">{agent.name}</span>{' '}
                  <span className="text-sm text-muted-foreground">@{agent.handle}</span>
                </p>
                <p className="text-sm text-muted-foreground">{agent.role}</p>
                <p className="text-sm">{agent.intro}</p>
                <p className="text-sm">
                  <span className="font-medium">Quirk:</span> {agent.quirk}
                </p>
                <div className="flex flex-wrap gap-1">
                  {agent.capabilities.map((capability) => (
                    <Badge key={capability} variant="outline">
                      {capability}
                    </Badge>
                  ))}
                </div>
                <p className="truncate text-xs text-muted-foreground">
                  Model: {model ? <code>{model}</code> : 'none selected'}
                  {settings?.agent_models[agent.id] ? ' (override)' : ''}
                </p>
              </div>
            </li>
          )
        })}
      </ul>
    </SettingsSection>
  )
}
