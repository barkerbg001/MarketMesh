export const APPEARANCE_STORAGE_KEY = 'marketmesh-appearance'

export const ACCENTS = [
  { id: 'indigo', label: 'Indigo', swatch: 'oklch(0.511 0.262 276.966)' },
  { id: 'blue', label: 'Blue', swatch: 'oklch(0.488 0.217 264)' },
  { id: 'teal', label: 'Teal', swatch: 'oklch(0.511 0.096 186.4)' },
  { id: 'green', label: 'Green', swatch: 'oklch(0.527 0.154 150.069)' },
  { id: 'amber', label: 'Amber', swatch: 'oklch(0.555 0.163 48.998)' },
  { id: 'rose', label: 'Rose', swatch: 'oklch(0.514 0.222 16.9)' },
] as const

export const TEXT_SIZES = [
  { id: 'sm', label: 'Small' },
  { id: 'md', label: 'Default' },
  { id: 'lg', label: 'Large' },
] as const

export const DENSITIES = [
  { id: 'comfortable', label: 'Comfortable' },
  { id: 'compact', label: 'Compact' },
] as const

export type Accent = (typeof ACCENTS)[number]['id']
export type TextSize = (typeof TEXT_SIZES)[number]['id']
export type Density = (typeof DENSITIES)[number]['id']

export type Appearance = { accent: Accent; textSize: TextSize; density: Density }

export const DEFAULT_APPEARANCE: Appearance = { accent: 'indigo', textSize: 'md', density: 'comfortable' }

function pick<T extends string>(value: unknown, allowed: readonly { id: T }[], fallback: T): T {
  return allowed.some((option) => option.id === value) ? (value as T) : fallback
}

export function parseAppearance(raw: string | null): Appearance {
  let data: Record<string, unknown> = {}
  try {
    const parsed: unknown = raw ? JSON.parse(raw) : {}
    if (parsed && typeof parsed === 'object') data = parsed as Record<string, unknown>
  } catch {
    // Corrupt preferences fall back to defaults.
  }
  return {
    accent: pick(data.accent, ACCENTS, DEFAULT_APPEARANCE.accent),
    textSize: pick(data.textSize, TEXT_SIZES, DEFAULT_APPEARANCE.textSize),
    density: pick(data.density, DENSITIES, DEFAULT_APPEARANCE.density),
  }
}

export function loadAppearance(): Appearance {
  try {
    return parseAppearance(localStorage.getItem(APPEARANCE_STORAGE_KEY))
  } catch {
    return DEFAULT_APPEARANCE
  }
}

/** Mirrors the pre-render script in index.html so the first paint already has these attributes. */
export function applyAppearance(appearance: Appearance, root: HTMLElement = document.documentElement) {
  root.dataset.accent = appearance.accent
  root.dataset.textSize = appearance.textSize
  root.dataset.density = appearance.density
}

export function saveAppearance(appearance: Appearance) {
  try {
    localStorage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify(appearance))
  } catch {
    // Storage can be unavailable (private mode); the choice still applies for this session.
  }
  applyAppearance(appearance)
}
