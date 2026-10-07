import { toast } from 'sonner'

import { SettingsSection } from '@/components/settings/settings-section'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useWorkspace } from '@/hooks/use-workspace'
import { errorMessage, patchJson } from '@/lib/api'
import type { WorkspaceSettings } from '@/types/api'

export function ResearchSection() {
  const { settings, setSettings } = useWorkspace()
  if (!settings) return null

  const save = async (changes: Partial<Pick<WorkspaceSettings, 'research_region' | 'currency'>>) => {
    try {
      setSettings(await patchJson<WorkspaceSettings>('/api/settings', changes, 'Could not save the preference'))
      toast.success('Preference saved')
    } catch (err) {
      toast.error(errorMessage(err, 'Could not save the preference'))
    }
  }

  return (
    <SettingsSection
      title="Region and currency"
      description="Tells the agents where you shop. South Africa enables the Checkers, Pick n Pay, Woolworths and Takealot search tools; other regions use web search only."
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="research-region">Research region</Label>
          <Select value={settings.research_region} onValueChange={(value) => void save({ research_region: value })}>
            <SelectTrigger id="research-region" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {settings.options.regions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">Sets the web search region and which retailer tools are offered.</p>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="preferred-currency">Preferred currency</Label>
          <Select value={settings.currency} onValueChange={(value) => void save({ currency: value })}>
            <SelectTrigger id="preferred-currency" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {settings.options.currencies.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.value} · {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Agents prefer listings in this currency and the cart shows its subtotal first. Prices are never converted.
          </p>
        </div>
      </div>
    </SettingsSection>
  )
}
