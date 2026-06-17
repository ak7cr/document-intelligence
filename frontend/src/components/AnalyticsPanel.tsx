import { useQuery } from '@tanstack/react-query'
import { fetchAnalytics } from '../api/documents'
import type { AnalyticsResult } from '../types'

interface Props {
  sessionId: string
}

const ENTITY_COLOR: Record<string, string> = {
  party:     'bg-violet-400',
  amount:    'bg-emerald-400',
  reference: 'bg-gray-400',
  date:      'bg-blue-400',
  deadline:  'bg-red-400',
  doc_type:  'bg-amber-400',
}

const ENTITY_LABEL: Record<string, string> = {
  party:     'Parties',
  amount:    'Amounts',
  reference: 'References',
  date:      'Dates',
  deadline:  'Deadlines',
  doc_type:  'Doc Types',
}

const FILETYPE_COLOR: Record<string, string> = {
  pdf:  'bg-red-400',
  docx: 'bg-blue-400',
  doc:  'bg-blue-400',
  xlsx: 'bg-emerald-400',
  xls:  'bg-emerald-400',
  csv:  'bg-violet-400',
  pptx: 'bg-orange-400',
  png:  'bg-gray-400',
  jpg:  'bg-gray-400',
}

export default function AnalyticsPanel({ sessionId }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics', sessionId],
    queryFn: () => fetchAnalytics(sessionId),
    staleTime: 60_000,
  })

  if (isLoading) return <LoadingSkeleton />
  if (isError || !data) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-gray-400">
        Failed to load analytics.
      </div>
    )
  }

  return <Dashboard data={data} />
}

function Dashboard({ data }: { data: AnalyticsResult }) {
  const { totals, doc_types, entity_types, top_entities, timeline } = data

  const docTypeEntries = Object.entries(doc_types).sort((a, b) => b[1] - a[1])
  const entityTypeEntries = Object.entries(entity_types)
    .filter(([k]) => k !== 'doc_type')
    .sort((a, b) => b[1] - a[1])

  const maxDocType = Math.max(...docTypeEntries.map(([, v]) => v), 1)
  const maxEntityType = Math.max(...entityTypeEntries.map(([, v]) => v), 1)
  const maxTimeline = Math.max(...timeline.map((t) => t.count), 1)

  return (
    <div className="px-8 py-6 space-y-6 max-w-5xl">

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Documents" value={totals.documents} sub={totals.ready + ' ready'} color="text-blue-600" />
        <StatCard label="Total Pages" value={totals.pages} sub="across all docs" color="text-violet-600" />
        <StatCard label="Total Words" value={totals.words.toLocaleString()} sub={totals.chunks + ' chunks'} color="text-emerald-600" />
        <StatCard label="Entities" value={totals.entities} sub="extracted" color="text-amber-600" />
      </div>

      {/* Status breakdown */}
      {(totals.processing > 0 || totals.failed > 0) && (
        <div className="bg-white border border-gray-100 rounded-xl p-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Document Status</h3>
          <div className="flex gap-4 text-xs">
            <StatusPill label="Ready" count={totals.ready} color="bg-emerald-100 text-emerald-700" />
            <StatusPill label="Processing" count={totals.processing} color="bg-yellow-100 text-yellow-700" />
            <StatusPill label="Failed" count={totals.failed} color="bg-red-100 text-red-600" />
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {/* Document types bar chart */}
        <div className="bg-white border border-gray-100 rounded-xl p-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Document Types</h3>
          <div className="space-y-2.5">
            {docTypeEntries.map(([type, count]) => (
              <BarRow
                key={type}
                label={type.toUpperCase()}
                count={count}
                max={maxDocType}
                color={FILETYPE_COLOR[type] ?? 'bg-gray-400'}
              />
            ))}
          </div>
        </div>

        {/* Entity type distribution */}
        <div className="bg-white border border-gray-100 rounded-xl p-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Entity Types</h3>
          <div className="space-y-2.5">
            {entityTypeEntries.map(([type, count]) => (
              <BarRow
                key={type}
                label={ENTITY_LABEL[type] ?? type}
                count={count}
                max={maxEntityType}
                color={ENTITY_COLOR[type] ?? 'bg-gray-400'}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Upload timeline */}
      {timeline.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-xl p-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Upload Timeline</h3>
          <div className="flex items-end gap-2 h-20">
            {timeline.map((t) => {
              const pct = Math.round((t.count / maxTimeline) * 100)
              return (
                <div key={t.date} className="flex flex-col items-center gap-1 flex-1">
                  <span className="text-[10px] text-gray-500">{t.count}</span>
                  <div
                    className="w-full bg-blue-400 rounded-t-sm"
                    style={{ height: Math.max(pct, 8) + '%' }}
                    title={t.date + ': ' + t.count + ' doc' + (t.count !== 1 ? 's' : '')}
                  />
                  <span className="text-[9px] text-gray-400 truncate w-full text-center">
                    {t.date.slice(5)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Top entities tables */}
      {Object.keys(top_entities).length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {(['party', 'amount', 'deadline', 'reference', 'date'] as const)
            .filter((k) => top_entities[k]?.length)
            .map((etype) => (
              <TopEntityTable
                key={etype}
                label={ENTITY_LABEL[etype] ?? etype}
                color={ENTITY_COLOR[etype] ?? 'bg-gray-400'}
                rows={top_entities[etype]}
              />
            ))}
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, sub, color }: {
  label: string; value: string | number; sub: string; color: string
}) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-5">
      <p className="text-[11px] font-medium text-gray-400 mb-1">{label}</p>
      <p className={'text-2xl font-bold ' + color}>{value}</p>
      <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>
    </div>
  )
}

function StatusPill({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span className={'px-3 py-1 rounded-full text-xs font-medium ' + color}>
      {count} {label}
    </span>
  )
}

function BarRow({ label, count, max, color }: {
  label: string; count: number; max: number; color: string
}) {
  const pct = Math.round((count / max) * 100)
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-gray-500 w-20 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div
          className={'h-2 rounded-full ' + color}
          style={{ width: Math.max(pct, 4) + '%' }}
        />
      </div>
      <span className="text-[11px] text-gray-400 w-4 text-right shrink-0">{count}</span>
    </div>
  )
}

function TopEntityTable({ label, color, rows }: {
  label: string
  color: string
  rows: { value: string; count: number }[]
}) {
  const max = rows[0]?.count ?? 1
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className={'w-2.5 h-2.5 rounded-full shrink-0 ' + color} />
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Top {label}</h3>
      </div>
      <div className="space-y-2">
        {rows.map((row, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="text-[11px] text-gray-700 flex-1 truncate" title={row.value}>{row.value}</span>
            <div className="w-20 bg-gray-100 rounded-full h-1.5 shrink-0">
              <div
                className={'h-1.5 rounded-full ' + color}
                style={{ width: Math.round((row.count / max) * 100) + '%' }}
              />
            </div>
            <span className="text-[10px] text-gray-400 w-4 text-right shrink-0">{row.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="px-8 py-6 space-y-6 max-w-5xl animate-pulse">
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 bg-white border border-gray-100 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="h-48 bg-white border border-gray-100 rounded-xl" />
        <div className="h-48 bg-white border border-gray-100 rounded-xl" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="h-36 bg-white border border-gray-100 rounded-xl" />
        <div className="h-36 bg-white border border-gray-100 rounded-xl" />
      </div>
    </div>
  )
}
