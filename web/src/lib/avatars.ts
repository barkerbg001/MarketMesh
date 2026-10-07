import { createAvatar } from '@dicebear/core'
import * as notionists from '@dicebear/notionists'

const cache = new Map<string, string>()

/**
 * DiceBear "Notionists" avatar (artwork CC0 1.0, by Zoish), generated locally.
 * Seeds are fixed per agent, so nothing user-specific is ever encoded or requested.
 */
export function agentAvatarUri(seed: string, background: string) {
  const key = `${seed}|${background}`
  let uri = cache.get(key)
  if (!uri) {
    uri = createAvatar(notionists, {
      seed,
      backgroundColor: [background.replace(/^#/, '')],
      radius: 50,
    }).toDataUri()
    cache.set(key, uri)
  }
  return uri
}
