import { useCallback, useEffect, useState } from 'react'
import { Loader2Icon, RefreshCwIcon } from 'lucide-react'
import { toast } from 'sonner'

import { AgentAvatar } from '@/components/agents/agent-avatar'
import { ModelPicker } from '@/components/settings/model-picker'
import { SettingsSection } from '@/components/settings/settings-section'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useWorkspace } from '@/hooks/use-workspace'
import { errorMessage, getJson, patchJson } from '@/lib/api'
import type { ModelInfo, WorkspaceSettings } from '@/types/api'

export function ModelsSection() {
  const { settings, setSettings, agents } = useWorkspace()
  const [models, setModels] = useState<ModelInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async (refresh = false) => {
    setLoading(true)
    setError(null)
    try {
      const body = await getJson<{ models: ModelInfo[] }>(
        `/api/settings/openrouter/models${refresh ? '?refresh=1' : ''}`,
        'Could not load models from OpenRouter',
      )
      setModels(body.models)
    } catch (err) {
      setError(errorMessage(err, 'Could not load models from OpenRouter'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (!settings) return null

  const save = async (changes: Partial<Pick<WorkspaceSettings, 'default_model' | 'agent_models'>>, message: string) => {
    setSaving(true)
    try {
      setSettings(await patchJson<WorkspaceSettings>('/api/settings', changes, 'Could not save the model'))
      toast.success(message)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not save the model'))
    } finally {
      setSaving(false)
    }
  }

  const setAgentModel = (agentId: string, model: string) => {
    const next = { ...settings.agent_models }
    if (model) next[agentId] = model
    else delete next[agentId]
    void save({ agent_models: next }, model ? 'Agent model saved' : 'Agent now uses the default model')
  }

  return (
    <SettingsSection
      title="Models"
      description="Pick the model the team uses. MarketMesh never picks a model for you and never falls back to a paid one."
    >
      <div className="flex items-center justify-between gap-2 text-sm text-muted-foreground">
        <span>{loading ? 'Loading models from OpenRouter…' : `${models.length} tool-capable models available`}</span>
        <Button variant="ghost" size="sm" onClick={() => void load(true)} disabled={loading}>
          {loading ? (
            <Loader2Icon data-icon="inline-start" className="animate-spin" aria-hidden="true" />
          ) : (
            <RefreshCwIcon data-icon="inline-start" aria-hidden="true" />
          )}
          Refresh list
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Model list unavailable</AlertTitle>
          <AlertDescription>
            {error} Your saved choices still apply; you can pick new ones once the list loads.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Default model</h3>
        <ModelPicker
          label="Default model"
          models={models}
          value={settings.default_model}
          disabled={saving || (loading && models.length === 0)}
          onChange={(model) => void save({ default_model: model }, model ? 'Default model saved' : 'Default model cleared')}
          emptyLabel="No default (agents will not run)"
        />
        {!settings.default_model && (
          <p className="text-sm text-destructive">Choose a default model before chatting.</p>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <h3 className="text-sm font-medium">Per-agent overrides</h3>
          <p className="text-sm text-muted-foreground">
            Optional. For example, give Scout a cheaper model for searching and Mesh a stronger one for the final answer.
          </p>
        </div>
        <ul className="flex flex-col gap-3">
          {agents.map((agent) => (
            <li key={agent.id} className="grid items-center gap-2 sm:grid-cols-[12rem_1fr]">
              <div className="flex items-center gap-2">
                <AgentAvatar agent={agent} size="sm" />
                <div className="min-w-0">
                  <p className="text-sm font-medium">{agent.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{agent.role}</p>
                </div>
              </div>
              <ModelPicker
                label={`Model for ${agent.name}`}
                models={models}
                value={settings.agent_models[agent.id] ?? ''}
                disabled={saving || (loading && models.length === 0)}
                onChange={(model) => setAgentModel(agent.id, model)}
                emptyLabel="Use the default model"
              />
            </li>
          ))}
        </ul>
      </div>
    </SettingsSection>
  )
}
