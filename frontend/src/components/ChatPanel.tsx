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
        { role: 'assistant', content: res.answer, sources: res.sources, confidence: res.confidence },
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
            <div className="text-4xl mb-3">&#128172;</div>
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
            <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-xs shrink-0 mt-0.5 text-blue-700 font-bold">
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
  const [showSources, setShowSources] = useState(true)

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
        <div className="w-7 h-7 rounded-full bg-red-100 flex items-center justify-center text-xs shrink-0 mt-0.5 text-red-500 font-bold">
          !
        </div>
        <div className="bg-red-50 border border-red-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-red-600 max-w-[80%]">
          {message.content}
        </div>
      </div>
    )
  }

  const hasSources = message.sources && message.sources.length > 0
  const conf = message.confidence
  const confStyle = conf === 'high'
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : conf === 'medium'
    ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
    : conf === 'low'
    ? 'bg-red-50 text-red-600 border-red-200'
    : null

  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-xs shrink-0 mt-0.5 text-blue-700 font-bold">
        AI
      </div>
      <div className="max-w-[80%] space-y-2">
        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 leading-relaxed">
          {message.content}
        </div>
        {confStyle && (
          <div className="flex items-center gap-1.5 px-1">
            <span className={'text-[10px] font-semibold uppercase tracking-wider border rounded-full px-2 py-0.5 ' + confStyle}>
              {conf} confidence
            </span>
          </div>
        )}

        {hasSources && (
          <div>
            <button
              onClick={() => setShowSources((v) => !v)}
              className="flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-gray-600 transition px-1 mb-1.5"
            >
              <span className="text-[10px]">{showSources ? '&#9660;' : '&#9654;'}</span>
              <span>
                {message.sources!.length} source{message.sources!.length !== 1 ? 's' : ''}
                {showSources ? '' : ' (click to expand)'}
              </span>
            </button>
            {showSources && (
              <div className="space-y-1.5">
                {message.sources!.map((s, i) => (
                  <SourceCard key={i} source={s} index={i + 1} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function SourceCard({ source, index }: { source: ChatSource; index: number }) {
  const pct = Math.round(source.score * 100)
  const location = source.page_number != null
    ? 'p. ' + source.page_number
    : 'chunk ' + source.chunk_index

  return (
    <div className="bg-gray-50 border border-gray-100 rounded-xl px-3 py-2.5">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] font-bold text-blue-600 bg-blue-50 rounded px-1.5 py-0.5 shrink-0">
            [{index}]
          </span>
          <p className="text-[11px] font-semibold text-gray-700 truncate">{source.filename}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[10px] text-gray-400 bg-gray-100 rounded px-1.5 py-0.5">{location}</span>
          <span className="text-[10px] text-emerald-600 bg-emerald-50 rounded px-1.5 py-0.5">{pct}%</span>
        </div>
      </div>
      <p className="text-[11px] text-gray-500 leading-relaxed line-clamp-3">{source.text}</p>
    </div>
  )
}
