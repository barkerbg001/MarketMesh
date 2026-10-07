import { useId, useMemo, useState } from 'react'
import { CheckIcon, ChevronsUpDownIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatModelPrice } from '@/lib/models'
import { cn } from '@/lib/utils'
import type { ModelInfo } from '@/types/api'

const MAX_RESULTS = 60

type ModelPickerProps = {
  label: string
  models: ModelInfo[]
  value: string
  onChange: (value: string) => void
  /** Label for the empty value, e.g. "Use the default model". Omit to require a model. */
  emptyLabel?: string
  disabled?: boolean
}

export function ModelPicker({ label, models, value, onChange, emptyLabel, disabled }: ModelPickerProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [freeOnly, setFreeOnly] = useState(false)
  const searchId = useId()
  const freeId = useId()

  const selected = models.find((model) => model.id === value)
  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return models
      .filter((model) => !freeOnly || model.is_free)
      .filter((model) => !needle || model.id.toLowerCase().includes(needle) || model.name.toLowerCase().includes(needle))
  }, [models, query, freeOnly])

  const choose = (next: string) => {
    onChange(next)
    setOpen(false)
    setQuery('')
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        className="h-auto w-full justify-between py-2 text-left"
        disabled={disabled}
        onClick={() => setOpen(true)}
        aria-label={`${label}: ${selected?.name ?? (value || emptyLabel || 'none selected')}`}
      >
        <span className="flex min-w-0 flex-col">
          <span className="truncate font-medium">{selected?.name ?? (value || emptyLabel || 'Choose a model')}</span>
          {value && (
            <span className="truncate text-xs font-normal text-muted-foreground">
              {value}
              {selected ? ` · ${formatModelPrice(selected)}` : models.length > 0 ? ' · not in the current tool-capable list' : ''}
            </span>
          )}
        </span>
        <ChevronsUpDownIcon className="shrink-0 opacity-60" aria-hidden="true" />
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="flex max-h-[85dvh] flex-col sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{label}</DialogTitle>
            <DialogDescription>
              Only models that support tool calling are listed, because the agents need tools to research.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor={searchId} className="sr-only">
              Search models
            </Label>
            <Input
              id={searchId}
              autoFocus
              placeholder="Search by name or ID, e.g. llama or google/"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="flex items-center gap-2">
              <Checkbox id={freeId} checked={freeOnly} onCheckedChange={(checked) => setFreeOnly(checked === true)} />
              <Label htmlFor={freeId} className="font-normal">
                Free models only
              </Label>
              <span className="ml-auto text-xs text-muted-foreground">
                {matches.length} of {models.length}
              </span>
            </div>
          </div>
          <ul role="listbox" aria-label={label} className="-mx-2 min-h-0 flex-1 overflow-y-auto">
            {emptyLabel && (
              <li>
                <button
                  type="button"
                  role="option"
                  aria-selected={value === ''}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent"
                  onClick={() => choose('')}
                >
                  <CheckIcon className={cn('size-4', value !== '' && 'invisible')} aria-hidden="true" />
                  {emptyLabel}
                </button>
              </li>
            )}
            {matches.slice(0, MAX_RESULTS).map((model) => (
              <li key={model.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={model.id === value}
                  className="flex w-full items-start gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent"
                  onClick={() => choose(model.id)}
                >
                  <CheckIcon className={cn('mt-0.5 size-4 shrink-0', model.id !== value && 'invisible')} aria-hidden="true" />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="flex items-center gap-2">
                      <span className="truncate font-medium">{model.name}</span>
                      {model.is_free && <Badge variant="secondary">Free</Badge>}
                    </span>
                    <span className="truncate text-xs text-muted-foreground">
                      {model.id}
                      {model.context_length ? ` · ${Math.round(model.context_length / 1000)}k context` : ''}
                      {model.is_free ? '' : ` · ${formatModelPrice(model)}`}
                    </span>
                  </span>
                </button>
              </li>
            ))}
            {matches.length > MAX_RESULTS && (
              <li className="px-2 py-2 text-xs text-muted-foreground">
                Showing the first {MAX_RESULTS}. Refine your search to see more.
              </li>
            )}
            {matches.length === 0 && <li className="px-2 py-4 text-sm text-muted-foreground">No models match.</li>}
          </ul>
        </DialogContent>
      </Dialog>
    </>
  )
}
