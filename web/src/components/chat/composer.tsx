import { useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { ArrowUpIcon, SquareIcon } from 'lucide-react'

import { AgentAvatar } from '@/components/agents/agent-avatar'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { insertMention, mentionQueryAt, predictResponder } from '@/lib/mentions'
import { cn } from '@/lib/utils'
import type { Agent } from '@/types/api'

const MAX_LENGTH = 4000

type ComposerProps = {
  agents: Agent[]
  running: boolean
  disabled: boolean
  disabledReason?: string
  onSend: (text: string) => Promise<boolean> | boolean
  onStop: () => void
  value: string
  onChange: (value: string) => void
}

export function Composer({ agents, running, disabled, disabledReason, onSend, onStop, value, onChange }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const listId = useId()
  const hintId = useId()
  const [caret, setCaret] = useState(0)
  const [highlight, setHighlight] = useState(0)
  const [dismissedAt, setDismissedAt] = useState<number | null>(null)

  const mention = mentionQueryAt(value, caret)
  const suggestions = useMemo(() => {
    if (!mention) return []
    return agents.filter((agent) => agent.handle.startsWith(mention.query) || agent.name.toLowerCase().startsWith(mention.query))
  }, [agents, mention])
  const showSuggestions = suggestions.length > 0 && dismissedAt !== caret
  const responder = value.trim() ? predictResponder(value, agents) : null

  function choose(agent: Agent) {
    if (!mention) return
    const next = insertMention(value, mention.start, caret, agent.handle)
    onChange(next.text)
    setCaret(next.caret)
    requestAnimationFrame(() => {
      textareaRef.current?.focus()
      textareaRef.current?.setSelectionRange(next.caret, next.caret)
    })
  }

  async function submit() {
    const text = value.trim()
    if (!text || disabled || running) return
    onChange('')
    const sent = await onSend(text)
    if (!sent) onChange(text)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (showSuggestions) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        const step = event.key === 'ArrowDown' ? 1 : -1
        setHighlight((current) => (current + step + suggestions.length) % suggestions.length)
        return
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        event.preventDefault()
        choose(suggestions[Math.min(highlight, suggestions.length - 1)])
        return
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        setDismissedAt(caret)
        return
      }
    }
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      void submit()
    }
  }

  return (
    <form
      className="relative flex flex-col gap-1.5"
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
    >
      {showSuggestions && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Mention an agent"
          className="absolute bottom-full left-0 z-20 mb-2 w-72 overflow-hidden rounded-lg border bg-popover p-1 shadow-md"
        >
          {suggestions.map((agent, index) => (
            <li
              key={agent.id}
              role="option"
              aria-selected={index === highlight}
              className={cn(
                'flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm',
                index === highlight && 'bg-accent text-accent-foreground',
              )}
              onMouseDown={(event) => {
                event.preventDefault()
                choose(agent)
              }}
              onMouseEnter={() => setHighlight(index)}
            >
              <AgentAvatar agent={agent} size="sm" />
              <span className="font-medium">@{agent.handle}</span>
              <span className="truncate text-xs text-muted-foreground">{agent.role}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-end gap-2 rounded-xl border bg-background p-2 shadow-xs focus-within:ring-3 focus-within:ring-ring/50">
        <Textarea
          ref={textareaRef}
          value={value}
          maxLength={MAX_LENGTH}
          rows={1}
          disabled={disabled}
          placeholder={disabledReason ?? 'Ask about a product or a market… Type @ to address an agent.'}
          aria-label="Message the research team"
          aria-describedby={hintId}
          aria-controls={showSuggestions ? listId : undefined}
          aria-expanded={showSuggestions}
          aria-autocomplete="list"
          role="combobox"
          className="max-h-48 min-h-10 flex-1 resize-none border-0 bg-transparent px-2 py-2 shadow-none focus-visible:ring-0 dark:bg-transparent"
          onChange={(event) => {
            onChange(event.target.value)
            setCaret(event.target.selectionStart)
            setHighlight(0)
          }}
          onSelect={(event) => setCaret(event.currentTarget.selectionStart)}
          onKeyDown={handleKeyDown}
        />
        {running ? (
          <Button type="button" variant="outline" size="icon" onClick={onStop} aria-label="Stop the agents">
            <SquareIcon className="fill-current" aria-hidden="true" />
          </Button>
        ) : (
          <Button type="submit" size="icon" disabled={disabled || !value.trim()} aria-label="Send message">
            <ArrowUpIcon aria-hidden="true" />
          </Button>
        )}
      </div>
      <p id={hintId} className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs text-muted-foreground">
        <span>
          {responder ? (
            <>
              <span className="font-medium text-foreground">{responder.name}</span> will answer
              {responder.id === 'orchestrator' ? ' and bring in specialists if needed' : ' directly'}.
            </>
          ) : (
            'Enter to send, Shift+Enter for a new line.'
          )}
        </span>
        <span className="tabular-nums">{value.length > MAX_LENGTH - 500 ? `${value.length}/${MAX_LENGTH}` : ''}</span>
      </p>
    </form>
  )
}
