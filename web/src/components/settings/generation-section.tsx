import { useState } from 'react'
import { Loader2Icon } from 'lucide-react'
import { toast } from 'sonner'

import { SettingsSection } from '@/components/settings/settings-section'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useWorkspace } from '@/hooks/use-workspace'
import { errorMessage, patchJson } from '@/lib/api'
import type { GenerationSettings, WorkspaceSettings } from '@/types/api'

const FIELDS: { name: keyof GenerationSettings; label: string; help: string; step: number; unit?: string }[] = [
  { name: 'temperature', label: 'Temperature', help: 'Lower is more focused and repeatable; higher is more varied.', step: 0.1 },
  { name: 'max_tokens', label: 'Max tokens per reply', help: 'Upper bound on the length of each agent reply.', step: 100 },
  {
    name: 'max_tool_rounds',
    label: 'Tool rounds per agent',
    help: 'How many search or page-reading rounds one agent may take in a turn.',
    step: 1,
  },
  {
    name: 'max_delegations',
    label: 'Delegations per turn',
    help: 'How many specialist tasks Mesh may hand out in one turn.',
    step: 1,
  },
  { name: 'request_timeout', label: 'Model timeout', help: 'Give up on a model call after this long.', step: 5, unit: 'seconds' },
]

const toDraft = (generation: GenerationSettings) =>
  Object.fromEntries(FIELDS.map(({ name }) => [name, String(generation[name])]))

export function GenerationSection() {
  const { settings } = useWorkspace()
  if (!settings) return null
  // Re-key so the form resets to the saved values whenever they change on the server.
  return <GenerationForm key={JSON.stringify(settings.generation)} settings={settings} />
}

function GenerationForm({ settings }: { settings: WorkspaceSettings }) {
  const { setSettings } = useWorkspace()
  const [draft, setDraft] = useState<Record<string, string>>(() => toDraft(settings.generation))
  const [saving, setSaving] = useState(false)

  const problems = FIELDS.flatMap(({ name, label }) => {
    const { min, max } = settings.limits[name]
    const value = Number(draft[name])
    if (draft[name] === '' || !Number.isFinite(value)) return [`${label} must be a number.`]
    if (value < min || value > max) return [`${label} must be between ${min} and ${max}.`]
    if (name !== 'temperature' && !Number.isInteger(value)) return [`${label} must be a whole number.`]
    return []
  })
  const dirty = FIELDS.some(({ name }) => Number(draft[name]) !== settings.generation[name])

  const save = async () => {
    if (problems.length) return
    setSaving(true)
    try {
      const changes = Object.fromEntries(FIELDS.map(({ name }) => [name, Number(draft[name])]))
      setSettings(await patchJson<WorkspaceSettings>('/api/settings', changes, 'Could not save generation settings'))
      toast.success('Generation settings saved')
    } catch (err) {
      toast.error(errorMessage(err, 'Could not save generation settings'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <SettingsSection title="Generation" description="Advanced limits that apply to every agent call.">
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {FIELDS.map(({ name, label, help, step, unit }) => {
            const { min, max } = settings.limits[name]
            const id = `generation-${name}`
            return (
              <div key={name} className="flex flex-col gap-1.5">
                <Label htmlFor={id}>{label}</Label>
                <Input
                  id={id}
                  type="number"
                  inputMode="decimal"
                  min={min}
                  max={max}
                  step={step}
                  value={draft[name] ?? ''}
                  aria-describedby={`${id}-help`}
                  onChange={(event) => setDraft((current) => ({ ...current, [name]: event.target.value }))}
                />
                <p id={`${id}-help`} className="text-xs text-muted-foreground">
                  {help} Range {min}–{max}
                  {unit ? ` ${unit}` : ''}.
                </p>
              </div>
            )
          })}
        </div>
        {problems.length > 0 && (
          <ul className="text-sm text-destructive" role="alert">
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <Button type="submit" disabled={saving || !dirty || problems.length > 0}>
            {saving && <Loader2Icon data-icon="inline-start" className="animate-spin" aria-hidden="true" />}
            Save
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={!dirty}
            onClick={() => setDraft(toDraft(settings.generation))}
          >
            Reset
          </Button>
        </div>
      </form>
    </SettingsSection>
  )
}
