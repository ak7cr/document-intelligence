import { useQuery } from '@tanstack/react-query'
import { searchSession } from '../api/sessions'
import type { SearchResult } from '../types'

interface Props {
  sessionId: string
  query: string
}

export default function SearchPanel({ sessionId, query }: Props) {
  const enabled = query.trim().length > 2

  const { data, isFetching, isError } = useQuery({
    queryKey: ['search', sessionId, query],
    queryFn: () => searchSession(sessionId, query, 8),
    enabled,
    staleTime: 60_000,
  })

  if (!enabled) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-sm">Type at least 3 characters to search across documents.</p>
      </div>
    )
  }

  if (isFetching) {
    return (
      <div className="space-y-2.5">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-28 bg-white border border-gray-100 rounded-xl animate-pulse"
          />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-xl bg-red-50 border border-red-100 px-5 py-4 text-sm text-red-600">
        Search failed — make sure Qdrant is running and documents have been processed.
      </div>
    )
  }

  const results = data?.results ?? []

  if (results.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <div className="text-4xl mb-3">🔍</div>
        <p className="text-sm font-medium text-gray-500">No results for "{query}"</p>
        <p className="text-xs mt-1">
          Try different keywords, or upload more documents.
        </p>
      </div>
    )
  }

  return (
    <div>
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest mb-2.5">
        {results.length} result{results.length !== 1 ? 's' : ''} {'·'} "{query}"
      </p>
      <div className="space-y-2">
        {results.map((r) => (
          <ResultCard key={r.chunk_id} result={r} query={query} />
        ))}
      </div>
    </div>
  )
}

// ── Score badge ─────────────────────────────────────────────────────────────

function scoreBadge(score: number) {
  const pct = Math.round(score * 100)
  const cls =
    score >= 0.75
      ? 'bg-emerald-50 text-emerald-700'
      : score >= 0.55
      ? 'bg-blue-50 text-blue-700'
      : 'bg-gray-100 text-gray-500'
  return { pct, cls }
}

// ── Result card ──────────────────────────────────────────────────────────────

function ResultCard({ result, query }: { result: SearchResult; query: string }) {
  const { pct, cls } = scoreBadge(result.score)
  const excerpt = result.text.length > 420 ? result.text.slice(0, 420) + '...' : result.text

  return (
    <div className="bg-white border border-gray-100 rounded-xl px-5 py-4 hover:border-gray-200 hover:shadow-sm transition">
      <div className="flex items-center justify-between gap-3 mb-2">
        <p className="text-sm font-semibold text-gray-900 truncate" title={result.filename}>
          {result.filename}
        </p>
        <span
          className={'shrink-0 text-[11px] font-bold px-2 py-0.5 rounded-full ' + cls}
          title="Similarity score"
        >
          {pct}%
        </span>
      </div>

      <p className="text-xs text-gray-500 leading-relaxed">
        <Highlight text={excerpt} query={query} />
      </p>

      <p className="text-[10px] text-gray-300 mt-2">
        chunk {result.chunk_index}
      </p>
    </div>
  )
}

// ── Keyword highlighter ──────────────────────────────────────────────────────

function Highlight({ text, query }: { text: string; query: string }) {
  const terms = query
    .trim()
    .split(/\s+/)
    .filter((t) => t.length > 1)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))

  if (!terms.length) return <>{text}</>

  const re = new RegExp(`(${terms.join('|')})`, 'gi')
  const parts: { t: string; m: boolean }[] = []
  let last = 0
  let match: RegExpExecArray | null

  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push({ t: text.slice(last, match.index), m: false })
    parts.push({ t: match[0], m: true })
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push({ t: text.slice(last), m: false })

  return (
    <>
      {parts.map((p, i) =>
        p.m ? (
          <mark key={i} className="bg-yellow-100 text-yellow-800 rounded-sm px-0.5 not-italic">
            {p.t}
          </mark>
        ) : (
          p.t
        ),
      )}
    </>
  )
}
