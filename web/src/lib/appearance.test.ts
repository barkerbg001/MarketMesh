import { describe, expect, it } from 'vitest'

import { DEFAULT_APPEARANCE, parseAppearance } from '@/lib/appearance'
import { parseRoute, routeHref } from '@/hooks/use-route'

describe('parseAppearance', () => {
  it('reads valid stored preferences', () => {
    expect(parseAppearance('{"accent":"teal","textSize":"lg","density":"compact"}')).toEqual({
      accent: 'teal',
      textSize: 'lg',
      density: 'compact',
    })
  })

  it('falls back to defaults for missing, unknown, or corrupt values', () => {
    expect(parseAppearance(null)).toEqual(DEFAULT_APPEARANCE)
    expect(parseAppearance('not json')).toEqual(DEFAULT_APPEARANCE)
    expect(parseAppearance('{"accent":"neon","textSize":"lg"}')).toEqual({ ...DEFAULT_APPEARANCE, textSize: 'lg' })
  })
})

describe('parseRoute', () => {
  const id = '3f2b8c1e-9a4d-4e6f-8b7a-1c2d3e4f5a6b'

  it('parses each view', () => {
    expect(parseRoute('')).toEqual({ view: 'chat', conversationId: null })
    expect(parseRoute(`#/chat/${id}`)).toEqual({ view: 'chat', conversationId: id })
    expect(parseRoute('#/search')).toEqual({ view: 'search' })
    expect(parseRoute('#/settings/models')).toEqual({ view: 'settings', section: 'models' })
  })

  it('ignores conversation ids that are not UUIDs', () => {
    expect(parseRoute('#/chat/<script>')).toEqual({ view: 'chat', conversationId: null })
  })

  it('round-trips through routeHref', () => {
    for (const hash of [`#/chat/${id}`, '#/chat', '#/search', '#/settings', '#/settings/data']) {
      expect(routeHref(parseRoute(hash))).toBe(hash)
    }
  })
})
