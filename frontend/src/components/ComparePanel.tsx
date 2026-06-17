import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { fetchDocuments, compareDocuments } from '../api/documents'
import type { ComparisonDoc, ComparisonResult, DocumentEntity } from '../types'

interface Props {
  sessionId: string
}

const ENTITY_STYLE: Record<string, string> = {
  doc_type:  'bg-amber-50 text-amber-700 border-amber-200',
  date:      'bg-blue-50 text-blue-700 border-blue-200',
  deadline:  'bg-red-50 text-red-700 border-red-200',
  party:     'bg-violet-50 text-violet-700 border-violet-200',
  amount:    'bg-emerald-50 text-emerald-700 border-emerald-200',
  reference: 'bg-gray-50 text-gray-600 border-gray-200',
}

const DOC_COLORS = [
  'bg-blue-100 text-blue-700 border-blue-200',
  'bg-violet-100 text-violet-700 border-violet-200',
  'bg-emerald-100 text-emerald-700 border-emerald-200',
  'bg-orange-100 text-orange-700 border-orange-200',
  'bg-rose-100 text-rose-700 border-rose-200',
  'bg-cyan-100 text-cyan-700 border-cyan-200',
  'bg-amber-100 text-amber-700 border-amber-200',
  'bg-indigo-100 text-indigo-700 border-indigo-200',
]

export default function ComparePanel({ sessionId }: Props) {
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const { data: docs = [] } = useQuery({
    queryKey: ['documents', sessionId],
    queryFn: () => fetchDocuments(sessionId),
  })

  const readyDocs = docs.filter((d) => d.status === 'ready')

  const compareMut = useMutation({
    mutationFn: () => compareDocuments(sessionId, selectedIds),
  })

  function toggle(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  function selectAll() {
    setSelectedIds(readyDocs.map((d) => d.id))
  }

  function clearAll() {
    setSelectedIds([])
  }

  const canCompare = selectedIds.length >= 2

  return (
    <div className="flex flex-col h-full">
      {/* Selector panel */}
      <div className="bg-white border-b border-gray-100 px-8 py-5 shrink-0">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-sm font-semibold text-gray-700">Select documents to compare</h2>
              <span className="text-[11px] text-gray-400">
                {selectedIds.length} selected
                {selectedIds.length >= 2 ? '' : ' (select at least 2)'}
              </span>
              {readyDocs.length > 0 && (
                <div className="flex gap-2 ml-auto">
                  <button
                    onClick={selectAll}
                    className="text-[11px] text-blue-500 hover:text-blue-700 transition"
                  >
                    Select all
                  </button>
                  {selectedIds.length > 0 && (
                    <button
                      onClick={clearAll}
                      className="text-[11px] text-gray-400 hover:text-gray-600 transition"
                    >
                      Clear
                    </button>
                  )}
                </div>
              )}
            </div>

            {readyDocs.length === 0 ? (
              <p className="text-xs text-gray-400">
                No ready documents in this session. Upload and process documents first.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {readyDocs.map((doc) => {
                  const checked = selectedIds.includes(doc.id)
                  const colorIdx = selectedIds.indexOf(doc.id)
                  const color = colorIdx >= 0 ? DOC_COLORS[colorIdx % DOC_COLORS.length] : ''
                  return (
                    <button
                      key={doc.id}
                      onClick={() => toggle(doc.id)}
                      className={'flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition ' +
                        (checked
                          ? color + ' shadow-sm'
                          : 'bg-gray-50 text-gray-500 border-gray-200 hover:border-gray-300 hover:text-gray-700')}
                    >
                      <span className={'w-4 h-4 rounded border flex items-center justify-center text-[10px] shrink-0 ' +
                        (checked ? 'bg-current border-current text-white' : 'border-gray-300')}>
                        {checked ? String.fromCharCode(10003) : ''}
                      </span>
                      <span className="max-w-45 truncate">{doc.filename}</span>
                      {doc.page_count != null && (
                        <span className="opacity-60 shrink-0">{doc.page_count}p</span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <button
            onClick={() => compareMut.mutate()}
            disabled={!canCompare || compareMut.isPending}
            className="px-5 py-2.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-40 transition font-medium shrink-0 self-end"
          >
            {compareMut.isPending ? 'Comparing...' : 'Compare'}
          </button>
        </div>

        {compareMut.isError && (
          <p className="text-xs text-red-500 mt-2">Comparison failed -- check server logs</p>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {!compareMut.data && !compareMut.isPending && (
          <EmptyState hasEnoughDocs={readyDocs.length >= 2} />
        )}

        {compareMut.isPending && <LoadingSkeleton />}

        {compareMut.data && !compareMut.isPending && (
          <ComparisonView result={compareMut.data} />
        )}
      </div>
    </div>
  )
}

function EmptyState({ hasEnoughDocs }: { hasEnoughDocs: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center select-none">
      <div className="text-5xl mb-4">&#9878;</div>
      <p className="text-sm font-medium text-gray-500 mb-1">Compare multiple documents at once</p>
      <p className="text-xs text-gray-400 max-w-sm leading-relaxed">
        {hasEnoughDocs
          ? 'Select two or more documents above and click Compare. You can compare up to 8 documents simultaneously.'
          : 'Upload and process at least 2 documents in this session first.'}
      </p>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-36 bg-white border border-gray-100 rounded-xl" />
        ))}
      </div>
      <div className="h-48 bg-white border border-gray-100 rounded-xl" />
      <div className="grid grid-cols-2 gap-4">
        <div className="h-28 bg-white border border-gray-100 rounded-xl" />
        <div className="h-28 bg-white border border-gray-100 rounded-xl" />
      </div>
    </div>
  )
}

function ComparisonView({ result }: { result: ComparisonResult }) {
  const { docs, analysis } = result
  const n = docs.length

  // Choose grid cols based on count
  const gridCols = n <= 2 ? 'grid-cols-2' : n === 3 ? 'grid-cols-3' : n === 4 ? 'grid-cols-4' : 'grid-cols-4'

  return (
    <div className="space-y-6">
      {/* Doc cards grid */}
      <div className={'grid gap-3 ' + gridCols}>
        {docs.map((doc, i) => (
          <DocCard key={doc.id} doc={doc} index={i} />
        ))}
      </div>

      {/* N-column differences table */}
      {analysis.differences.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
            <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Key Differences</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-max">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left px-4 py-2.5 text-gray-400 font-medium w-36 shrink-0">Aspect</th>
                  {docs.map((doc, i) => (
                    <th key={doc.id} className="text-left px-4 py-2.5 font-semibold min-w-40">
                      <span className={'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-[11px] ' + DOC_COLORS[i % DOC_COLORS.length]}>
                        <span className="font-bold">{i + 1}</span>
                        <span className="truncate max-w-30">{doc.filename.replace(/\.[^.]+$/, '')}</span>
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {analysis.differences.map((diff, i) => (
                  <tr key={i} className={'border-b border-gray-50 ' + (i % 2 === 0 ? '' : 'bg-gray-50/40')}>
                    <td className="px-4 py-2.5 text-gray-500 font-medium align-top">{diff.aspect}</td>
                    {diff.values.map((val, j) => (
                      <td key={j} className={'px-4 py-2.5 align-top ' + (val === '--' ? 'text-gray-300' : 'text-gray-700')}>
                        {val}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Similarities + Recommendation */}
      <div className="grid grid-cols-2 gap-4">
        {analysis.similarities.length > 0 && (
          <div className="bg-white border border-gray-100 rounded-xl p-5">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Similarities</h3>
            <ul className="space-y-1.5">
              {analysis.similarities.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                  <span className="text-emerald-400 shrink-0 mt-0.5">&#8226;</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {analysis.recommendation && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
            <h3 className="text-xs font-semibold text-blue-600 uppercase tracking-wider mb-3">Recommendation</h3>
            <p className="text-xs text-blue-800 leading-relaxed">{analysis.recommendation}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function DocCard({ doc, index }: { doc: ComparisonDoc; index: number }) {
  const color = DOC_COLORS[index % DOC_COLORS.length]

  const grouped: Record<string, DocumentEntity[]> = {}
  for (const e of doc.entities) {
    if (!grouped[e.entity_type]) grouped[e.entity_type] = []
    grouped[e.entity_type].push(e)
  }
  const ORDER = ['doc_type', 'deadline', 'amount', 'party', 'reference', 'date']
  const types = [...new Set([...ORDER, ...Object.keys(grouped)])].filter((t) => grouped[t])

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      <div className={'px-4 py-2.5 flex items-center gap-2 border-b border-gray-100 ' + color.replace('text-', 'bg-').split(' ')[0].replace('bg-', 'bg-') }>
        <div className={'flex items-center gap-2 ' + color.split(' ').slice(0, 3).join(' ') + ' px-1.5 py-0.5 rounded text-[11px] font-bold'}>
          {index + 1}
        </div>
        <p className="text-xs font-semibold text-gray-700 truncate flex-1">{doc.filename}</p>
        {doc.page_count != null && (
          <span className="text-[10px] text-gray-400 shrink-0">{doc.page_count}p</span>
        )}
      </div>

      <div className="p-3 space-y-2.5">
        {doc.headline && (
          <p className="text-[11px] font-medium text-gray-700 leading-snug">{doc.headline}</p>
        )}
        {doc.key_points.length > 0 && (
          <ul className="space-y-0.5">
            {doc.key_points.slice(0, 3).map((pt, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[10px] text-gray-500">
                <span className="shrink-0 mt-0.5 text-gray-300">&#8226;</span>
                <span className="line-clamp-2">{pt}</span>
              </li>
            ))}
          </ul>
        )}
        {types.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-0.5">
            {types.flatMap((type) =>
              grouped[type].slice(0, 2).map((e) => {
                const style = ENTITY_STYLE[e.entity_type] ?? 'bg-gray-50 text-gray-600 border-gray-200'
                return (
                  <span
                    key={e.id}
                    title={e.label + ': ' + e.value}
                    className={'inline-flex border rounded px-1.5 py-0.5 text-[10px] font-medium ' + style}
                  >
                    {e.value.length > 20 ? e.value.slice(0, 18) + '...' : e.value}
                  </span>
                )
              })
            )}
          </div>
        )}
      </div>
    </div>
  )
}
