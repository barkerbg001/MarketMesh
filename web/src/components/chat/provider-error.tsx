import { CircleAlertIcon, XIcon } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import type { ProviderError } from '@/types/api'

const SETTINGS_CODES = new Set(['missing_key', 'invalid_key', 'missing_model', 'model_unavailable', 'forbidden',
  'encryption_unavailable'])

const TITLES: Record<string, string> = {
  missing_key: 'OpenRouter is not set up',
  invalid_key: 'OpenRouter rejected the API key',
  missing_model: 'No model selected',
  model_unavailable: 'Model unavailable',
  insufficient_credits: 'Out of OpenRouter credits',
  rate_limited: 'Rate limited',
  timeout: 'The model took too long',
  network_error: 'Could not reach OpenRouter',
  provider_error: 'The model provider failed',
  interrupted: 'Response interrupted',
  encryption_unavailable: 'Saved key cannot be read',
}

function hint(error: ProviderError) {
  switch (error.code) {
    case 'rate_limited':
      return error.retry_after ? `Try again in about ${error.retry_after} seconds.` : 'Wait a moment and try again.'
    case 'insufficient_credits':
      return 'Add credits on openrouter.ai, or pick a free model in Settings.'
    case 'timeout':
    case 'network_error':
    case 'provider_error':
      return 'Try again, or choose a different model in Settings.'
    default:
      return null
  }
}

export function ProviderErrorAlert({ error, onDismiss }: { error: ProviderError; onDismiss?: () => void }) {
  const extra = hint(error)
  return (
    <Alert variant="destructive" className="relative">
      <CircleAlertIcon aria-hidden="true" />
      <AlertTitle>{TITLES[error.code] ?? 'Something went wrong'}</AlertTitle>
      <AlertDescription>
        <p>
          {error.message}
          {extra ? ` ${extra}` : ''}
        </p>
        {SETTINGS_CODES.has(error.code) && (
          <a href="#/settings/openrouter" className="font-medium underline underline-offset-2">
            Open OpenRouter settings
          </a>
        )}
      </AlertDescription>
      {onDismiss && (
        <Button variant="ghost" size="icon-sm" className="absolute top-2 right-2" onClick={onDismiss} aria-label="Dismiss">
          <XIcon aria-hidden="true" />
        </Button>
      )}
    </Alert>
  )
}
