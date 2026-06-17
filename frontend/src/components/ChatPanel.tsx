import { useState, useRef, useEffect } from 'react'
import { chatSession } from '../api/chat'
import type { ChatMessage, ChatSource } from '../types'

interface Props {
  sessionId: string
}

export default function ChatPanel({ sessionId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send() {
    const question = input.trim()
    if (!question || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setInput('')
    setLoading(true)

    try {
      const res = await chatSession(sessionId, question)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.answer, sources: res.sources },
      ])
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { error?: string } } }).response?.data?.error
          : undefined
      setMessages((prev) => [
        ...prev,
        { role: 'error', content: msg ?? 'Failed to get a response. Check the server logs.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const empty = messages.length === 0

  return (
    <div className="flex flex-col h-full">
      {/* Message area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {empty && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 select-none pt-16">
            <div className="text-4xl mb-3">💬</div>
            <p className="text-sm font-medium text-gray-500">Ask anything about your documents</p>
            <p className="text-xs mt-1 max-w-xs leading-relaxed">
              The AI will answer using only the content from documents in this session.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-xs shrink-0 mt-0.5">
              AI
            </div>
            <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1 items-center h-5">
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-100 bg-white px-4 py-3">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            disabled={loading}
            placeholder="Ask a question about these documents..."
            className="flex-1 text-sm bg-gray-50 border border-gray-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 rounded-lg px-4 py-2.5 outline-none transition disabled:opacity-50"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-40 transition font-medium shrink-0"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [showSources, setShowSources] = useState(false)

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    )
  }

  if (message.role === 'error') {
    return (
      <div className="flex gap-3">
        <div className="w-7 h-7 rounded-full bg-red-100 flex items-center justify-center text-xs shrink-0 mt-0.5 text-red-500">
          !
        </div>
        <div className="bg-red-50 border border-red-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-red-600 max-w-[80%]">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-xs shrink-0 mt-0.5 text-blue-700 font-bold">
        AI
      </div>
      <div className="max-w-[80%] space-y-2">
        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 leading-relaxed">
          {message.content}
        </div>

        {message.sources && message.sources.length > 0 && (
          <div>
            <button
              onClick={() => setShowSources((v) => !v)}
              className="text-[11px] text-gray-400 hover:text-gray-600 transition px-1"
            >
              {showSources ? 'Hide' : 'Show'} {message.sources.length} source{message.sources.length !== 1 ? 's' : ''}
            </button>
            {showSources && (
              <div className="mt-1.5 space-y-1.5">
                {message.sources.map((s, i) => (
                  <SourceCard key={i} source={s} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function SourceCard({ source }: { source: ChatSource }) {
  const pct = Math.round(source.score * 100)
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-xl px-3 py-2.5">
      <div className="flex items-center justify-between gap-2 mb-1">
        <p className="text-[11px] font-semibold text-gray-700 truncate">{source.filename}</p>
        <span className="text-[10px] text-gray-400 shrink-0">{pct}% match</span>
      </div>
      <p className="text-[11px] text-gray-500 leading-relaxed line-clamp-2">{source.text}</p>
    </div>
  )
}
