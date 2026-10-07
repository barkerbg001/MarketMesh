import { useState } from 'react'
import { CheckCircle2Icon, CircleAlertIcon, KeyRoundIcon, Loader2Icon, PlugZapIcon, Trash2Icon } from 'lucide-react'
import { toast } from 'sonner'

import { SettingsSection } from '@/components/settings/settings-section'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useWorkspace } from '@/hooks/use-workspace'
import { deleteJson, errorMessage, postJson, putJson } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { ConnectionTest, WorkspaceSettings } from '@/types/api'

function TestResult({ result }: { result: ConnectionTest }) {
  if (!result.ok) {
    return (
      <Alert variant="destructive">
        <CircleAlertIcon aria-hidden="true" />
        <AlertTitle>Connection failed</AlertTitle>
        <AlertDescription>{result.error.message}</AlertDescription>
      </Alert>
    )
  }
  const { details } = result
  const usd = (value: number) => `$${value.toFixed(value < 1 ? 4 : 2)}`
  const parts = [
    details.is_free_tier ? 'Free tier account' : 'Account with purchased credits',
    details.limit_remaining != null ? `${usd(details.limit_remaining)} left on this key's limit` : 'No spending limit on this key',
    details.usage != null ? `${usd(details.usage)} used so far` : null,
  ].filter(Boolean)
  return (
    <Alert>
      <CheckCircle2Icon className="text-success" aria-hidden="true" />
      <AlertTitle>Connected to OpenRouter</AlertTitle>
      <AlertDescription>{parts.join(' · ')}</AlertDescription>
    </Alert>
  )
}

export function OpenRouterSection() {
  const { settings, setSettings } = useWorkspace()
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<ConnectionTest | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  if (!settings) return null
  const status = settings.openrouter

  const save = async () => {
    const key = draft.trim()
    if (!key) return
    setSaving(true)
    setFieldError(null)
    setResult(null)
    try {
      setSettings(await putJson<WorkspaceSettings>('/api/settings/openrouter-key', { api_key: key }, 'Could not save the key'))
      setDraft('')
      toast.success('API key saved and encrypted')
      setTesting(true)
      setResult(await postJson<ConnectionTest>('/api/settings/openrouter/test', {}, 'Could not test the key'))
    } catch (err) {
      setFieldError(errorMessage(err, 'Could not save the key'))
    } finally {
      setSaving(false)
      setTesting(false)
    }
  }

  const test = async () => {
    setTesting(true)
    setResult(null)
    try {
      const body = draft.trim() ? { api_key: draft.trim() } : {}
      setResult(await postJson<ConnectionTest>('/api/settings/openrouter/test', body, 'Could not test the key'))
    } catch (err) {
      setResult({ ok: false, error: { code: 'request_failed', message: errorMessage(err, 'Could not test the key') } })
    } finally {
      setTesting(false)
    }
  }

  const remove = async () => {
    try {
      setSettings(await deleteJson<WorkspaceSettings>('/api/settings/openrouter-key', 'Could not remove the key'))
      setResult(null)
      toast.success('API key removed')
    } catch (err) {
      toast.error(errorMessage(err, 'Could not remove the key'))
    }
  }

  return (
    <SettingsSection
      title="OpenRouter connection"
      description={
        <>
          MarketMesh talks to models through{' '}
          <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
            OpenRouter
          </a>
          . Your key is encrypted on the API server with a secret kept outside the database. It is never sent back to
          the browser.
        </>
      }
    >
      <div className="flex flex-wrap items-center gap-2 text-sm" role="status">
        <KeyRoundIcon className="size-4 text-muted-foreground" aria-hidden="true" />
        {status.source === 'settings' && (
          <>
            <Badge variant="secondary">Key saved</Badge>
            {status.hint && (
              <span className="text-muted-foreground">
                ending <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{status.hint}</code>
              </span>
            )}
            {status.updated_at && <span className="text-muted-foreground">updated {formatDateTime(status.updated_at)}</span>}
          </>
        )}
        {status.source === 'environment' && (
          <>
            <Badge variant="secondary">Using OPEN_ROUTER_API_KEY</Badge>
            <span className="text-muted-foreground">from the API server environment. Save a key here to override it.</span>
          </>
        )}
        {status.source === 'none' && <Badge variant="outline">No key</Badge>}
      </div>

      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <Label htmlFor="openrouter-key">{status.source === 'settings' ? 'Replace API key' : 'API key'}</Label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            id="openrouter-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            placeholder="sk-or-v1-…"
            value={draft}
            aria-invalid={fieldError ? true : undefined}
            aria-describedby={fieldError ? 'openrouter-key-error' : undefined}
            onChange={(event) => {
              setDraft(event.target.value)
              setFieldError(null)
            }}
          />
          <Button type="submit" disabled={saving || !draft.trim()}>
            {saving && <Loader2Icon data-icon="inline-start" className="animate-spin" aria-hidden="true" />}
            Save key
          </Button>
        </div>
        {fieldError && (
          <p id="openrouter-key-error" className="text-sm text-destructive">
            {fieldError}
          </p>
        )}
      </form>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => void test()} disabled={testing || (!status.configured && !draft.trim())}>
          {testing ? (
            <Loader2Icon data-icon="inline-start" className="animate-spin" aria-hidden="true" />
          ) : (
            <PlugZapIcon data-icon="inline-start" aria-hidden="true" />
          )}
          {draft.trim() ? 'Test this key' : 'Test connection'}
        </Button>
        {status.source === 'settings' && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" className="text-destructive">
                <Trash2Icon data-icon="inline-start" aria-hidden="true" />
                Remove key
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Remove the saved API key?</AlertDialogTitle>
                <AlertDialogDescription>
                  {status.environment_fallback
                    ? 'The agents will fall back to the key in the API server environment.'
                    : 'The agents will stop working until you add a key again.'}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={() => void remove()}>
                  Remove key
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>

      {result && <TestResult result={result} />}
    </SettingsSection>
  )
}
