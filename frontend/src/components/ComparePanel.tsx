import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { fetchDocuments, compareDocuments } from '../api/documents'
import type { ComparisonDoc, ComparisonResult, Document, DocumentEntity } from '../types'

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

export default function ComparePanel({ sessionId }: Props) {
  const [docIdA, setDocIdA] = useState('')
  const [docIdB, setDocIdB] = useState('')

  const { data: docs = [] } = useQuery({
    queryKey: ['documents', sessionId],
    queryFn: () => fetchDocuments(sessionId),
  })

  const readyDocs = docs.filter((d) => d.status === 'ready')

  const compareMut = useMutation({
    mutationFn: () => compareDocuments(sessionId, docIdA, docIdB),
  })

  const canCompare = docIdA && docIdB && docIdA !== docIdB

  function handleCompare() {
    if (canCompare) compareMut.mutate()
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Selector bar */}
      <div className="bg-white border-b border-gray-100 px-8 py-4 shrink-0">
        <div className="flex items-center gap-3 flex-wrap">
          <DocSelector
            label="Document A"
            docs={readyDocs}
            value={docIdA}
            exclude={docIdB}
            onChange={setDocIdA}
          />
          <span className="text-gray-300 font-light text-xl select-none">vs</span>
          <DocSelector
            label="Document B"
            docs={readyDocs}
            value={docIdB}
            exclude={docIdA}
            onChange={setDocIdB}
          />
          <button
            onClick={handleCompare}
            disabled={!canCompare || compareMut.isPending}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-40 transition font-medium shrink-0"
          >
            {compareMut.isPending ? 'Comparing...' : 'Compare'}
          </button>
          {compareMut.isError && (
            <span className="text-xs text-red-500">Failed -- check server logs</span>
          )}
        </div>
        {readyDocs.length < 2 && (
          <p className="text-xs text-gray-400 mt-2">
            Upload and process at least 2 documents to compare them.
          </p>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 px-8 py-6">
        {!compareMut.data && !compareMut.isPending && (
          <EmptyState hasEnoughDocs={readyDocs.length >= 2} />
        )}

        {compareMut.isPending && (
          <div className="space-y-4 animate-pulse">
            <div className="grid grid-cols-2 gap-4">
              <div className="h-40 bg-white border border-gray-100 rounded-xl" />
              <div className="h-40 bg-white border border-gray-100 rounded-xl" />
            </div>
            <div className="h-32 bg-white border border-gray-100 rounded-xl" />
            <div className="h-48 bg-white border border-gray-100 rounded-xl" />
          </div>
        )}

        {compareMut.data && !compareMut.isPending && (
          <ComparisonView result={compareMut.data} />
        )}
      </div>
    </div>
  )
}

function DocSelector({
  label, docs, value, exclude, onChange,
}: {
  label: string
  docs: Document[]
  value: string
  exclude: string
  onChange: (id: string) => void
}) {
  return (
    <div className="flex flex-col gap-1 min-w-48">
      <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-sm bg-gray-50 border border-gray-200 focus:border-blue-400 rounded-lg px-3 py-2 outline-none transition text-gray-700"
      >
        <option value="">Select document...</option>
        {docs
          .filter((d) => d.id !== exclude)
          .map((d) => (
            <option key={d.id} value={d.id}>{d.filename}</option>
          ))}
      </select>
    </div>
  )
}

function EmptyState({ hasEnoughDocs }: { hasEnoughDocs: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center select-none">
      <div className="text-5xl mb-4">&#9878;</div>
      <p className="text-sm font-medium text-gray-500 mb-1">Compare two documents side by side</p>
      <p className="text-xs text-gray-400 max-w-xs leading-relaxed">
        {hasEnoughDocs
          ? 'Select two documents above and click Compare to see differences, similarities, and an AI recommendation.'
          : 'Upload and process at least 2 documents in this session first.'}
      </p>
    </div>
  )
}

function ComparisonView({ result }: { result: ComparisonResult }) {
  const { doc_a, doc_b, analysis } = result

  return (
    <div className="space-y-6">
      {/* Side-by-side doc cards */}
      <div className="grid grid-cols-2 gap-4">
        <DocCard doc={doc_a} label="A" />
        <DocCard doc={doc_b} label="B" />
      </div>

      {/* Differences table */}
      {analysis.differences.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
            <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Key Differences</h3>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-5 py-2.5 text-gray-400 font-medium w-1/4">Aspect</th>
                <th className="text-left px-5 py-2.5 text-gray-700 font-semibold w-[37.5%]">
                  {doc_a.filename.length > 30 ? doc_a.filename.slice(0, 28) + '...' : doc_a.filename}
                </th>
                <th className="text-left px-5 py-2.5 text-gray-700 font-semibold w-[37.5%]">
                  {doc_b.filename.length > 30 ? doc_b.filename.slice(0, 28) + '...' : doc_b.filename}
                </th>
              </tr>
            </thead>
            <tbody>
              {analysis.differences.map((diff, i) => (
                <tr key={i} className={'border-b border-gray-50 ' + (i % 2 === 0 ? '' : 'bg-gray-50/50')}>
                  <td className="px-5 py-2.5 text-gray-500 font-medium">{diff.aspect}</td>
                  <td className="px-5 py-2.5 text-gray-700">{diff.doc_a || '--'}</td>
                  <td className="px-5 py-2.5 text-gray-700">{diff.doc_b || '--'}</td>
                </tr>
              ))}
            </tbody>
          </table>
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

function DocCard({ doc, label }: { doc: ComparisonDoc; label: string }) {
  const grouped: Record<string, DocumentEntity[]> = {}
  for (const e of doc.entities) {
    if (!grouped[e.entity_type]) grouped[e.entity_type] = []
    grouped[e.entity_type].push(e)
  }
  const ORDER = ['doc_type', 'reference', 'deadline', 'date', 'amount', 'party']
  const types = [...new Set([...ORDER, ...Object.keys(grouped)])].filter((t) => grouped[t])

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      <div className={'px-4 py-2.5 flex items-center gap-2 border-b border-gray-100 ' +
        (label === 'A' ? 'bg-blue-50' : 'bg-violet-50')}>
        <span className={'text-[11px] font-bold px-1.5 py-0.5 rounded ' +
          (label === 'A' ? 'bg-blue-100 text-blue-700' : 'bg-violet-100 text-violet-700')}>
          {label}
        </span>
        <p className="text-xs font-semibold text-gray-700 truncate">{doc.filename}</p>
        {doc.page_count != null && (
          <span className="text-[10px] text-gray-400 shrink-0">{doc.page_count}p</span>
        )}
      </div>

      <div className="p-4 space-y-3">
        {doc.headline && (
          <p className="text-xs font-medium text-gray-700 leading-snug">{doc.headline}</p>
        )}
        {doc.key_points.length > 0 && (
          <ul className="space-y-1">
            {doc.key_points.slice(0, 4).map((pt, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[11px] text-gray-500">
                <span className="shrink-0 mt-0.5 text-gray-300">&#8226;</span>
                <span>{pt}</span>
              </li>
            ))}
          </ul>
        )}
        {types.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {types.flatMap((type) =>
              grouped[type].slice(0, 2).map((e) => {
                const style = ENTITY_STYLE[e.entity_type] ?? 'bg-gray-50 text-gray-600 border-gray-200'
                return (
                  <span
                    key={e.id}
                    title={e.label + ': ' + e.value}
                    className={'inline-flex border rounded-md px-1.5 py-0.5 text-[10px] font-medium ' + style}
                  >
                    {e.value.length > 22 ? e.value.slice(0, 20) + '...' : e.value}
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
