export type Product = {
  key: string
  title: string
  url: string
  seller: string | null
  source: string
  source_type: 'retailer' | 'web' | 'cart'
  image_url: string | null
  price: string | null
  price_amount: string | null
  currency: string | null
  specs: Record<string, string>
  retrieved_at: string | null
  retailer?: string
  rating?: string | null
  in_stock?: boolean | null
}

export type Source = {
  url: string
  title: string
  snippet?: string
  retrieved_at: string | null
  via?: 'web_search' | 'fetch_page'
}

export type Activity = {
  tool: string
  label: string
  ok: boolean
  summary: string | null
}

export type ComparisonRow = {
  name: string
  values: Record<string, string>
  verdict: string | null
  derived: boolean
}

export type Comparison = {
  title: string
  product_keys: string[]
  rows: ComparisonRow[]
  best_pick_key: string | null
  summary: string
  created_at: string
  products: Product[]
}

export type ProviderError = {
  code: string
  message: string
  retry_after?: number
}

export type CartAction = { action: 'added' | 'already_in_cart' | 'removed'; key: string; title: string }

export type MessagePayload = {
  task?: string
  delegated_by?: string
  requested?: string[]
  product_keys?: string[]
  products?: Product[]
  sources?: Source[]
  activity?: Activity[]
  comparison?: Comparison
  cart_actions?: CartAction[]
  cart_item_ids?: number[]
  error?: ProviderError
}

export type MessageStatus = 'complete' | 'streaming' | 'cancelled' | 'error'

export type ChatMessage = {
  id: number
  conversation_id: string
  role: 'user' | 'assistant'
  agent: string | null
  content: string
  status: MessageStatus
  payload: MessagePayload
  created_at: string
}

export type ConversationSummary = {
  id: string
  title: string
  created_at: string
  updated_at: string
  running: boolean
}

export type Conversation = ConversationSummary & {
  messages: ChatMessage[]
  product_count: number
  source_count: number
}

export type Agent = {
  id: string
  name: string
  handle: string
  role: string
  quirk: string
  intro: string
  avatar_seed: string
  avatar_background: string
  avatar_style: string
  aliases: string[]
  capabilities: string[]
}

export type CartItem = {
  id: number
  product_key: string
  title: string
  url: string
  seller: string
  source: string
  image_url: string | null
  price: string | null
  price_amount: string | null
  currency: string | null
  line_total: string | null
  specs: Record<string, string>
  notes: string
  quantity: number
  retrieved_at: string | null
  conversation_id: string | null
  added_at: string
}

export type Subtotal = { currency: string; amount: string; item_count: number }

export type CartState = {
  items: CartItem[]
  subtotals: Subtotal[]
  unknown_price_count: number
  item_count: number
}

export type KeyStatus = {
  configured: boolean
  source: 'settings' | 'environment' | 'none'
  hint: string | null
  updated_at: string | null
  environment_fallback: boolean
}

export type GenerationSettings = {
  temperature: number
  max_tokens: number
  max_tool_rounds: number
  max_delegations: number
  request_timeout: number
}

export type Option = { value: string; label: string }

export type WorkspaceSettings = {
  openrouter: KeyStatus
  default_model: string
  agent_models: Record<string, string>
  generation: GenerationSettings
  limits: Record<keyof GenerationSettings, { min: number; max: number }>
  research_region: string
  currency: string
  options: { regions: Option[]; currencies: Option[] }
}

export type ModelInfo = {
  id: string
  name: string
  context_length: number | null
  prompt_price: string | null
  completion_price: string | null
  is_free: boolean
}

export type ConnectionTest =
  | { ok: true; details: { is_free_tier?: boolean; limit?: number | null; limit_remaining?: number | null; usage?: number } }
  | { ok: false; error: ProviderError }

export type StreamEvent =
  | { type: 'run'; run_id: string; conversation: ConversationSummary; user_message: ChatMessage }
  | { type: 'agent_start'; message: ChatMessage }
  | { type: 'token'; message_id: number; text: string }
  | { type: 'tool_start'; message_id: number; tool: string; label: string }
  | ({ type: 'tool_end'; message_id: number } & Activity)
  | { type: 'message'; message: ChatMessage }
  | { type: 'message_removed'; message_id: number }
  | { type: 'cart_changed' }
  | { type: 'error'; error: ProviderError }
  | { type: 'ping' }
  | { type: 'done'; status: 'complete' | 'cancelled' | 'error' }
