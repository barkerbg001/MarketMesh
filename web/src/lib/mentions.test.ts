import { describe, expect, it } from 'vitest'

import { findMentions, insertMention, mentionQueryAt, predictResponder } from '@/lib/mentions'
import type { Agent } from '@/types/api'

const agent = (id: string, handle: string, aliases: string[] = []): Agent => ({
  id,
  name: handle[0].toUpperCase() + handle.slice(1),
  handle,
  role: '',
  quirk: '',
  intro: '',
  avatar_seed: handle,
  avatar_background: 'ffffff',
  avatar_style: 'notionists',
  aliases,
  capabilities: [],
})

const AGENTS = [
  agent('orchestrator', 'mesh', ['lead']),
  agent('researcher', 'scout', ['researcher']),
  agent('comparer', 'tally'),
  agent('analyst', 'atlas'),
]

describe('findMentions', () => {
  it('matches handles and aliases case-insensitively, once each, in order', () => {
    const found = findMentions('@Tally and @researcher, then @tally again', AGENTS)
    expect(found.map((entry) => entry.id)).toEqual(['comparer', 'researcher'])
  })

  it('ignores email addresses and unknown handles', () => {
    expect(findMentions('mail me at bob@scout.com or ask @nobody', AGENTS)).toEqual([])
  })
})

describe('predictResponder', () => {
  it('routes a single specialist mention directly', () => {
    expect(predictResponder('@scout find kettles', AGENTS)?.id).toBe('researcher')
  })

  it('falls back to the orchestrator for no mention, several mentions, or a lead mention', () => {
    expect(predictResponder('find kettles', AGENTS)?.id).toBe('orchestrator')
    expect(predictResponder('@scout and @tally help', AGENTS)?.id).toBe('orchestrator')
    expect(predictResponder('@mesh ask @scout', AGENTS)?.id).toBe('orchestrator')
  })
})

describe('mention autocomplete', () => {
  it('finds the partial handle at the caret', () => {
    expect(mentionQueryAt('hello @sc', 9)).toEqual({ query: 'sc', start: 6 })
    expect(mentionQueryAt('@', 1)).toEqual({ query: '', start: 0 })
    expect(mentionQueryAt('a@b', 3)).toBeNull()
    expect(mentionQueryAt('hello @scout done', 17)).toBeNull()
  })

  it('inserts the handle and places the caret after it', () => {
    expect(insertMention('ask @sc please', 4, 7, 'scout')).toEqual({ text: 'ask @scout  please', caret: 11 })
  })
})
