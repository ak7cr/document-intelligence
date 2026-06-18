import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchEntityGraph, runSessionAnalysis } from '../api/sessions'
import type { EntityCluster } from '../types'

interface Props {
  sessionId: string
}

const ENTITY_COLORS: Record<string, { chip: string; dot: string }> = {
  date:          { chip: 'bg-blue-50 text-blue-700 border-blue-200',    dot: 'bg-blue-400' },
  deadline:      { chip: 'bg-red-50 text-red-700 border-red-200',       dot: 'bg-red-400' },
  party:         { chip: 'bg-violet-50 text-violet-700 border-violet-200', dot: 'bg-violet-400' },
  amount:        { chip: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-400' },
  reference:     { chip: 'bg-gray-50 text-gray-600 border-gray-200',    dot: 'bg-gray-300' },
  certification: { chip: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-400' },
}
const DEFAULT_COLORS = { chip: 'bg-gray-50 text-gray-600 border-gray-200', dot: 'bg-gray-300' }

const ENTITY_ORDER = ['party', 'deadline', 'date', 'amount', 'certification', 'reference']

export default function EntityGraphPanel({ sessionId }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['entity-graph', sessionId],
    queryFn: () => fetchEntityGraph(sessionId),
    staleTime: 2 * 60 * 1000,
  })

  const runMut = useMutation({
    mutationFn: () => runSessionAnalysis(sessionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entity-graph', sessionId] })
      qc.invalidateQueries({ queryKey: ['checklist'] })
      qc.invalidateQueries({ queryKey: ['eligibility'] })
    },
  })

  const clusters = data?.clusters ?? []

  // Group clusters by entity type in preferred order
  const byType: Record<string, EntityCluster[]> = {}
  for (const c of clusters) {
    ;(byType[c.entity_type] ??= []).push(c)
  }
  const orderedTypes = [
    ...ENTITY_ORDER.filter((t) => byType[t]?.length),
    ...Object.keys(byType).filter((t) => !ENTITY_ORDER.includes(t)),
  ]

  if (isLoading) {
    return (
      <div className="px-8 py-6 space-y-3 animate-pulse">
        {[1, 2, 3].map((k) => (
          <div key={k} className="h-20 bg-white border border-gray-100 rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="px-8 py-6 max-w-4xl space-y-6">
      {/* Header + Run All */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">Cross-Document Entity Graph</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Entities that appear in multiple documents within this session
            {data ? ' · ' + data.total_shared + ' shared' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {runMut.isSuccess && (
            <span className="text-xs text-emerald-600">
              +{runMut.data?.checklist_run ?? 0} checklists, +{runMut.data?.eligibility_run ?? 0} checks
            </span>
          )}
          <button
            onClick={() => runMut.mutate()}
            disabled={runMut.isPending}
            className="text-xs px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 font-medium"
          >
            {runMut.isPending ? 'Running...' : 'Run All Analysis'}
          </button>
        </div>
      </div>

      {clusters.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center select-none">
          <div className="text-4xl mb-3">&#128257;</div>
          <p className="text-sm font-medium text-gray-600 mb-1">No shared entities found yet</p>
          <p className="text-xs text-gray-400 max-w-xs">
            Upload multiple documents. When the same entity (party, date, amount) appears across 2 or more documents, it will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {orderedTypes.map((etype) => {
            const color = ENTITY_COLORS[etype] ?? DEFAULT_COLORS
            return (
              <div key={etype}>
                <div className="flex items-center gap-2 mb-3">
                  <div className={'w-2 h-2 rounded-full shrink-0 ' + color.dot} />
                  <h3 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    {etype} &nbsp;&middot;&nbsp; {byType[etype].length} shared
                  </h3>
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {byType[etype].map((cluster, i) => (
                    <ClusterCard key={i} cluster={cluster} color={color} />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ClusterCard({ cluster, color }: { cluster: EntityCluster; color: { chip: string; dot: string } }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <p className={'inline-flex text-xs font-semibold border rounded-lg px-2 py-0.5 mb-2 ' + color.chip}>
            {cluster.value}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {cluster.documents.map((doc) => (
              <div key={doc.id} className="flex items-center gap-1 bg-gray-50 border border-gray-100 rounded-lg px-2 py-1">
                <span className="text-[10px] text-gray-400 font-medium">{doc.label}:</span>
                <span className="text-[11px] text-gray-700 font-medium truncate max-w-[180px]">{doc.filename}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="shrink-0 text-center pt-0.5">
          <span className="text-xl font-bold text-gray-200">{cluster.doc_count}</span>
          <p className="text-[9px] text-gray-300 font-medium uppercase tracking-wider -mt-0.5">docs</p>
        </div>
      </div>
    </div>
  )
}
