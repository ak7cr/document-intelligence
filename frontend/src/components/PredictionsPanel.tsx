import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDocuments, fetchPrediction, runPrediction } from '../api/documents'
import type { DocumentPrediction as Prediction } from '../types'

interface Props {
  sessionId: string
}

const RISK_STYLE: Record<string, { badge: string; bar: string; border: string; bg: string }> = {
  low:     { badge: 'bg-emerald-100 text-emerald-700', bar: 'bg-emerald-400', border: 'border-emerald-200', bg: 'bg-emerald-50' },
  medium:  { badge: 'bg-yellow-100 text-yellow-700',   bar: 'bg-yellow-400',  border: 'border-yellow-200',  bg: 'bg-yellow-50'  },
  high:    { badge: 'bg-red-100 text-red-700',          bar: 'bg-red-400',     border: 'border-red-200',     bg: 'bg-red-50'     },
  unknown: { badge: 'bg-gray-100 text-gray-500',        bar: 'bg-gray-300',    border: 'border-gray-200',    bg: 'bg-gray-50'    },
}

export default function PredictionsPanel({ sessionId }: Props) {
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents', sessionId],
    queryFn: () => fetchDocuments(sessionId),
  })

  const readyDocs = docs.filter((d) => d.status === 'ready')

  if (isLoading) {
    return (
      <div className="px-8 py-6 space-y-3 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-white border border-gray-100 rounded-xl" />
        ))}
      </div>
    )
  }

  if (readyDocs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center select-none px-8">
        <div className="text-5xl mb-4">&#9881;</div>
        <p className="text-sm font-medium text-gray-500 mb-1">No ready documents</p>
        <p className="text-xs text-gray-400 max-w-xs leading-relaxed">
          Upload and process documents to generate AI risk predictions.
        </p>
      </div>
    )
  }

  return (
    <div className="px-8 py-6 space-y-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-700">Risk Predictions</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            AI-generated risk assessment for each document in this session
          </p>
        </div>
      </div>

      {readyDocs.map((doc) => (
        <PredictionCard key={doc.id} docId={doc.id} filename={doc.filename} />
      ))}
    </div>
  )
}

function PredictionCard({ docId, filename }: { docId: string; filename: string }) {
  const [expanded, setExpanded] = useState(false)
  const qc = useQueryClient()

  const { data: prediction, isLoading, isError } = useQuery<Prediction>({
    queryKey: ['prediction', docId],
    queryFn: () => fetchPrediction(docId),
    retry: false,
    staleTime: 10 * 60 * 1000,
  })

  const predictMut = useMutation({
    mutationFn: () => runPrediction(docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prediction', docId] }),
  })

  const risk: string = prediction?.risk_level ?? 'unknown'
  const style = RISK_STYLE[risk] ?? RISK_STYLE.unknown
  const confidencePct = prediction ? Math.round(prediction.confidence * 100) : 0
  const hasPrediction = !!prediction && risk !== 'unknown'

  return (
    <div className={'bg-white border rounded-xl overflow-hidden transition ' + (hasPrediction ? style.border : 'border-gray-100')}>
      {/* Header row */}
      <div className="flex items-center gap-3 px-5 py-3.5">
        {/* Risk badge */}
        <span className={'text-[11px] font-bold px-2 py-1 rounded-lg uppercase tracking-wide shrink-0 ' + style.badge}>
          {isLoading ? '...' : risk}
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{filename}</p>
          {hasPrediction && prediction.timeline_urgency && (
            <p className="text-[11px] text-gray-400 mt-0.5 truncate">{prediction.timeline_urgency}</p>
          )}
        </div>

        {hasPrediction && (
          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1.5">
              <div className="w-16 bg-gray-100 rounded-full h-1.5">
                <div className={'h-1.5 rounded-full ' + style.bar} style={{ width: confidencePct + '%' }} />
              </div>
              <span className="text-[10px] text-gray-400">{confidencePct}% confidence</span>
            </div>
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-[11px] text-gray-400 hover:text-gray-600 transition px-2 py-1 rounded hover:bg-gray-50"
            >
              {expanded ? 'Collapse' : 'Details'}
            </button>
          </div>
        )}

        {!isLoading && (isError || !prediction) && (
          <button
            onClick={() => predictMut.mutate()}
            disabled={predictMut.isPending}
            className="text-[11px] px-3 py-1.5 bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 transition disabled:opacity-50 shrink-0"
          >
            {predictMut.isPending ? 'Analysing...' : 'Run prediction'}
          </button>
        )}

        {hasPrediction && !expanded && (
          <button
            onClick={() => predictMut.mutate()}
            disabled={predictMut.isPending}
            title="Re-run prediction"
            className="text-[10px] text-gray-300 hover:text-gray-500 transition shrink-0 px-1"
          >
            {predictMut.isPending ? '...' : 'Refresh'}
          </button>
        )}

        {predictMut.isError && (
          <span className="text-[11px] text-red-500 shrink-0">Failed</span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && hasPrediction && (
        <div className={'border-t px-5 py-4 grid grid-cols-3 gap-4 ' + style.bg + ' ' + style.border}>
          <Section
            title="Risk Factors"
            items={prediction.risk_factors}
            color="text-red-600"
            bullet="&#9679;"
            empty="No risk factors identified."
          />
          <Section
            title="Opportunities"
            items={prediction.opportunities}
            color="text-emerald-600"
            bullet="&#9679;"
            empty="No opportunities identified."
          />
          <Section
            title="Recommended Actions"
            items={prediction.recommended_actions}
            color="text-blue-600"
            numbered
            empty="No actions recommended."
          />
        </div>
      )}
    </div>
  )
}

function Section({ title, items, color, bullet, numbered, empty }: {
  title: string
  items: string[]
  color: string
  bullet?: string
  numbered?: boolean
  empty: string
}) {
  return (
    <div>
      <h4 className={'text-[10px] font-semibold uppercase tracking-wider mb-2 ' + color}>{title}</h4>
      {items.length === 0 ? (
        <p className="text-[11px] text-gray-400">{empty}</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-1.5 text-[11px] text-gray-700">
              <span className={'shrink-0 mt-0.5 ' + color}>
                {numbered ? (i + 1) + '.' : bullet}
              </span>
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
