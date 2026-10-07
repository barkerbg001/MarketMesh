import type { ModelInfo } from '@/types/api'

/** OpenRouter prices are USD per token; show them per million tokens. */
export function formatModelPrice(model: ModelInfo) {
  if (model.is_free) return 'Free'
  const perMillion = (value: string | null) => {
    const amount = value === null ? Number.NaN : Number(value)
    return Number.isFinite(amount) ? `$${(amount * 1_000_000).toFixed(2)}` : '?'
  }
  return `${perMillion(model.prompt_price)} in / ${perMillion(model.completion_price)} out per 1M tokens`
}
