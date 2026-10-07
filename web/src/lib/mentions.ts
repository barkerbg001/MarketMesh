import type { Agent } from '@/types/api'

const MENTION = /(?<![\w@])@([A-Za-z]+)\b/g

/** Agents mentioned in a message, in order, matched by handle or alias (mirrors the API's routing). */
export function findMentions(text: string, agents: Agent[]): Agent[] {
  const found: Agent[] = []
  for (const match of text.matchAll(MENTION)) {
    const handle = match[1].toLowerCase()
    const agent = agents.find((entry) => entry.handle === handle || entry.aliases.includes(handle))
    if (agent && !found.includes(agent)) found.push(agent)
  }
  return found
}

/** Who will answer: one specialist mention goes direct, anything else goes to the orchestrator. */
export function predictResponder(text: string, agents: Agent[], orchestratorId = 'orchestrator') {
  const mentioned = findMentions(text, agents)
  const specialists = mentioned.filter((agent) => agent.id !== orchestratorId)
  const orchestratorMentioned = mentioned.some((agent) => agent.id === orchestratorId)
  if (specialists.length === 1 && !orchestratorMentioned) return specialists[0]
  return agents.find((agent) => agent.id === orchestratorId) ?? null
}

/** The partial @handle being typed at the caret, if any, for autocomplete. */
export function mentionQueryAt(text: string, caret: number): { query: string; start: number } | null {
  const before = text.slice(0, caret)
  const match = /(^|[^\w@])@([A-Za-z]*)$/.exec(before)
  if (!match) return null
  return { query: match[2].toLowerCase(), start: caret - match[2].length - 1 }
}

export function insertMention(text: string, start: number, caret: number, handle: string) {
  const next = `${text.slice(0, start)}@${handle} ${text.slice(caret)}`
  return { text: next, caret: start + handle.length + 2 }
}
