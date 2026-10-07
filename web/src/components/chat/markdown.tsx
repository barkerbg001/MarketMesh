import { memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/** Agent text as Markdown. Raw HTML is not rendered and unsafe link protocols are dropped. */
export const Markdown = memo(function Markdown({ children }: { children: string }) {
  return (
    <div className="chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children: label }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {label}
            </a>
          ),
          img: ({ alt }) => <span>{alt}</span>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
})
