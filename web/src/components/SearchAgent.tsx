import { useState, type FormEvent } from 'react'

type SearchResult = {
  title: string
  url: string
  snippet: string
}

type SearchAgentResponse = {
  answer: string
  sources: SearchResult[]
  queries: string[]
}

const EXAMPLE_QUERIES = [
  'What are the latest trends in renewable energy?',
  'Compare React and Vue for new projects',
  'Summarize recent AI agent developments',
]

function getHostname(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function SearchAgent() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SearchAgentResponse | null>(null)

  async function runSearch(searchQuery: string) {
    const trimmed = searchQuery.trim()
    if (!trimmed || loading) return

    setQuery(trimmed)
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch('/api/agent/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed }),
      })

      const data = (await response.json()) as SearchAgentResponse | { detail?: string }

      if (!response.ok) {
        throw new Error(
          typeof data === 'object' && data && 'detail' in data && data.detail
            ? String(data.detail)
            : 'Search failed',
        )
      }

      setResult(data as SearchAgentResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void runSearch(query)
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-badge">Web search agent</div>
        <h1>MarketMesh</h1>
        <p className="hero-subtitle">
          Ask anything. The agent searches the web and synthesizes an answer with sources.
        </p>
      </header>

      <section className="search-panel">
        <form onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="search-query">
            Search query
          </label>
          <div className={`input-wrap${loading ? ' loading' : ''}`}>
            <textarea
              id="search-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="What would you like to know?"
              rows={3}
              disabled={loading}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                  event.preventDefault()
                  void runSearch(query)
                }
              }}
            />
            <button type="submit" disabled={loading || !query.trim()} aria-label="Search">
              {loading ? (
                <span className="spinner" aria-hidden="true" />
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M21 21l-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              )}
            </button>
          </div>
          <p className="hint">Press Ctrl+Enter to search</p>
        </form>

        {!result && !loading && !error && (
          <div className="examples">
            <span className="examples-label">Try asking</span>
            <div className="example-chips">
              {EXAMPLE_QUERIES.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="chip"
                  onClick={() => void runSearch(example)}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {error && (
        <div className="alert alert-error" role="alert">
          <strong>Search failed</strong>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <section className="loading-panel" aria-live="polite" aria-busy="true">
          <div className="loading-header">
            <span className="pulse-dot" />
            Searching the web…
          </div>
          <div className="skeleton-lines">
            <div className="skeleton" />
            <div className="skeleton short" />
            <div className="skeleton medium" />
          </div>
        </section>
      )}

      {result && !loading && (
        <section className="results">
          <article className="result-card answer-card">
            <div className="card-label">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6L12 2Z"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinejoin="round"
                />
              </svg>
              Answer
            </div>
            <p className="answer-text">{result.answer}</p>
          </article>

          {result.queries.length > 0 && (
            <article className="result-card">
              <div className="card-label">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M21 21l-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
                Searches performed
              </div>
              <div className="query-chips">
                {result.queries.map((searchQuery) => (
                  <span key={searchQuery} className="query-chip">
                    {searchQuery}
                  </span>
                ))}
              </div>
            </article>
          )}

          {result.sources.length > 0 && (
            <article className="result-card">
              <div className="card-label">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                  <path
                    d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
                {result.sources.length} source{result.sources.length === 1 ? '' : 's'}
              </div>
              <ul className="sources">
                {result.sources.map((source) => (
                  <li key={source.url} className="source-item">
                    <a href={source.url} target="_blank" rel="noreferrer" className="source-link">
                      <span className="source-domain">{getHostname(source.url)}</span>
                      <span className="source-title">{source.title || source.url}</span>
                    </a>
                    {source.snippet && <p className="source-snippet">{source.snippet}</p>}
                  </li>
                ))}
              </ul>
            </article>
          )}
        </section>
      )}
    </div>
  )
}
