import { useState } from 'react'
import { CheckIcon, MonitorIcon, MoonIcon, SunIcon } from 'lucide-react'
import { useTheme } from 'next-themes'

import { SettingsSection } from '@/components/settings/settings-section'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  ACCENTS,
  DENSITIES,
  TEXT_SIZES,
  loadAppearance,
  saveAppearance,
  type Appearance,
} from '@/lib/appearance'
import { cn } from '@/lib/utils'

const THEMES = [
  { id: 'system', label: 'System', icon: MonitorIcon },
  { id: 'light', label: 'Light', icon: SunIcon },
  { id: 'dark', label: 'Dark', icon: MoonIcon },
] as const

function OptionGroup<T extends string>({
  name,
  label,
  value,
  options,
  onChange,
}: {
  name: string
  label: string
  value: T
  options: readonly { id: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-sm font-medium">{label}</legend>
      <RadioGroup value={value} onValueChange={(next) => onChange(next as T)} className="flex flex-wrap gap-4">
        {options.map((option) => (
          <div key={option.id} className="flex items-center gap-2">
            <RadioGroupItem value={option.id} id={`${name}-${option.id}`} />
            <Label htmlFor={`${name}-${option.id}`} className="font-normal">
              {option.label}
            </Label>
          </div>
        ))}
      </RadioGroup>
    </fieldset>
  )
}

export function AppearanceSection() {
  const { theme = 'system', setTheme } = useTheme()
  const [appearance, setAppearance] = useState<Appearance>(loadAppearance)

  const update = (changes: Partial<Appearance>) => {
    const next = { ...appearance, ...changes }
    setAppearance(next)
    saveAppearance(next)
  }

  return (
    <SettingsSection title="Appearance" description="Saved in this browser and applied before the page first paints.">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Theme</legend>
        <RadioGroup value={theme} onValueChange={setTheme} className="grid grid-cols-3 gap-2 sm:max-w-md">
          {THEMES.map(({ id, label, icon: Icon }) => (
            <Label
              key={id}
              htmlFor={`theme-${id}`}
              className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border p-3 font-normal has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5"
            >
              <RadioGroupItem value={id} id={`theme-${id}`} className="sr-only" />
              <Icon className="size-5" aria-hidden="true" />
              {label}
            </Label>
          ))}
        </RadioGroup>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Accent colour</legend>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Accent colour">
          {ACCENTS.map((accent) => {
            const selected = appearance.accent === accent.id
            return (
              <button
                key={accent.id}
                type="button"
                role="radio"
                aria-checked={selected}
                aria-label={accent.label}
                title={accent.label}
                onClick={() => update({ accent: accent.id })}
                className={cn(
                  'flex size-9 items-center justify-center rounded-full ring-offset-2 ring-offset-background transition focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
                  selected && 'ring-2 ring-foreground',
                )}
                style={{ backgroundColor: accent.swatch }}
              >
                {selected && <CheckIcon className="size-4 text-white" aria-hidden="true" />}
              </button>
            )
          })}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <OptionGroup
          name="text-size"
          label="Chat text size"
          value={appearance.textSize}
          options={TEXT_SIZES}
          onChange={(textSize) => update({ textSize })}
        />
        <OptionGroup
          name="density"
          label="Chat density"
          value={appearance.density}
          options={DENSITIES}
          onChange={(density) => update({ density })}
        />
      </div>

      <div className="flex flex-col gap-[var(--chat-gap)] rounded-lg border bg-muted/30 p-4" aria-label="Preview">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Preview</p>
        <div className="self-end rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-[length:var(--chat-text)] text-primary-foreground">
          Which kettle is the best value?
        </div>
        <div className="chat-markdown text-[length:var(--chat-text)]">
          <p>
            Here is what the sources say. <a href="#/settings/appearance">Links</a> use your accent colour.
          </p>
        </div>
      </div>
    </SettingsSection>
  )
}
