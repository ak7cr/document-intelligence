import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchDocuments, deleteDocument, getDocumentUrl,
  fetchDocumentEntities, reextractEntities,
  fetchDocumentSummary, resummarizeDocument,
} from '../api/documents'
import type { Document, DocumentEntity, DocumentSummary } from '../types'

const TYPE_STYLE: Record<string, { bg: string; label: string }> = {
  pdf:  { bg: 'bg-red-100 text-red-700',      label: 'PDF' },
  docx: { bg: 'bg-blue-100 text-blue-700',     label: 'DOC' },
  doc:  { bg: 'bg-blue-100 text-blue-700',     label: 'DOC' },
  pptx: { bg: 'bg-orange-100 text-orange-700', label: 'PPT' },
  ppt:  { bg: 'bg-orange-100 text-orange-700', label: 'PPT' },
  xlsx: { bg: 'bg-green-100 text-green-700',   label: 'XLS' },
  xls:  { bg: 'bg-green-100 text-green-700',   label: 'XLS' },
  csv:  { bg: 'bg-violet-100 text-violet-700', label: 'CSV' },
  png:  { bg: 'bg-gray-100 text-gray-500',     label: 'IMG' },
  jpg:  { bg: 'bg-gray-100 text-gray-500',     label: 'IMG' },
  jpeg: { bg: 'bg-gray-100 text-gray-500',     label: 'IMG' },
  tiff: { bg: 'bg-gray-100 text-gray-500',     label: 'IMG' },
  tif:  { bg: 'bg-gray-100 text-gray-500',     label: 'IMG' },
}

const STATUS_STYLE: Record<string, string> = {
  uploaded:   'bg-gray-100 text-gray-500',
  processing: 'bg-yellow-100 text-yellow-700',
  ready:      'bg-emerald-100 text-emerald-700',
  failed:     'bg-red-100 text-red-600',
}

const ENTITY_STYLE: Record<string, string> = {
  doc_type:  'bg-amber-50 text-amber-700 border-amber-200',
  date:      'bg-blue-50 text-blue-700 border-blue-200',
  deadline:  'bg-red-50 text-red-700 border-red-200',
  party:     'bg-violet-50 text-violet-700 border-violet-200',
  amount:    'bg-emerald-50 text-emerald-700 border-emerald-200',
  reference: 'bg-gray-50 text-gray-600 border-gray-200',
}

const IN_PROGRESS = new Set(['uploaded', 'processing'])

type InsightsTab = 'summary' | 'entities'

interface Props {
  sessionId: string
}

export default function DocumentList({ sessionId }: Props) {
  const qc = useQueryClient()

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents', sessionId],
    queryFn: () => fetchDocuments(sessionId),
    refetchInterval: (query) => {
      const list = query.state.data ?? []
      return list.some((d) => IN_PROGRESS.has(d.status)) ? 2000 : false
    },
  })

  const deleteMut = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents', sessionId] }),
  })

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <div key={i} className="h-16 bg-white border border-gray-100 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (docs.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <div className="text-5xl mb-3">&#128194;</div>
        <p className="text-sm">No documents yet -- upload one above.</p>
      </div>
    )
  }

  return (
    <div>
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest mb-2">
        {'Documents · ' + docs.length}
      </p>
      <div className="space-y-1.5">
        {docs.map((doc) => (
          <DocRow key={doc.id} doc={doc} onDelete={() => deleteMut.mutate(doc.id)} />
        ))}
      </div>
    </div>
  )
}

function DocRow({ doc, onDelete }: { doc: Document; onDelete: () => void }) {
  const [downloading, setDownloading] = useState(false)
  const [showInsights, setShowInsights] = useState(false)
  const [insightsTab, setInsightsTab] = useState<InsightsTab>('summary')
  const qc = useQueryClient()

  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useQuery({
    queryKey: ['summary', doc.id],
    queryFn: () => fetchDocumentSummary(doc.id),
    enabled: showInsights && insightsTab === 'summary' && doc.status === 'ready',
    staleTime: 10 * 60 * 1000,
    retry: false,
  })

  const { data: entities = [], isLoading: entitiesLoading } = useQuery({
    queryKey: ['entities', doc.id],
    queryFn: () => fetchDocumentEntities(doc.id),
    enabled: showInsights && insightsTab === 'entities' && doc.status === 'ready',
    staleTime: 5 * 60 * 1000,
  })

  const resummarizeMut = useMutation({
    mutationFn: () => resummarizeDocument(doc.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['summary', doc.id] }),
  })

  const reextractMut = useMutation({
    mutationFn: () => reextractEntities(doc.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['entities', doc.id] }),
  })

  const typeStyle = TYPE_STYLE[doc.filetype] ?? {
    bg: 'bg-gray-100 text-gray-500',
    label: doc.filetype.slice(0, 3).toUpperCase(),
  }
  const statusStyle = STATUS_STYLE[doc.status] ?? STATUS_STYLE.uploaded
  const isProcessing = IN_PROGRESS.has(doc.status)

  async function handleDownload() {
    setDownloading(true)
    try {
      const url = await getDocumentUrl(doc.id)
      window.open(url, '_blank')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="bg-white border border-gray-100 rounded-lg hover:border-gray-200 hover:shadow-sm transition">
      {/* Main row */}
      <div className="group flex items-center gap-3 px-4 py-3">
        <div className={'shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-[11px] font-bold ' + typeStyle.bg}>
          {typeStyle.label}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate" title={doc.filename}>
            {doc.filename}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-xs text-gray-400">
              {new Date(doc.uploaded_at).toLocaleDateString('en-IN', {
                day: 'numeric', month: 'short', year: 'numeric',
              })}
            </p>
            {doc.word_count != null && (
              <span className="text-xs text-gray-400">
                {'· ' + doc.word_count.toLocaleString() + ' words'}
                {doc.page_count != null ? ' · ' + doc.page_count + 'p' : ''}
                {doc.chunk_count > 0 ? ' · ' + doc.chunk_count + ' chunks' : ''}
              </span>
            )}
          </div>
        </div>

        <span className={'flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-medium shrink-0 ' + statusStyle}>
          {isProcessing && <span className="w-2 h-2 rounded-full bg-current animate-pulse inline-block" />}
          {doc.status}
        </span>

        {doc.status === 'ready' && (
          <button
            onClick={() => setShowInsights((v) => !v)}
            className={'text-[11px] px-2 py-0.5 rounded-full border font-medium shrink-0 transition ' +
              (showInsights
                ? 'bg-blue-50 text-blue-600 border-blue-200'
                : 'bg-gray-50 text-gray-400 border-gray-200 hover:text-blue-600 hover:border-blue-200')}
          >
            Insights
          </button>
        )}

        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition shrink-0">
          <button
            onClick={handleDownload}
            disabled={downloading}
            title="Download"
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition disabled:opacity-40 text-sm"
          >
            {downloading ? '...' : '⬇'}
          </button>
          <button
            onClick={onDelete}
            title="Delete"
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition text-xs"
          >
            x
          </button>
        </div>
      </div>

      {/* Insights panel */}
      {showInsights && (
        <div className="border-t border-gray-100">
          {/* Tab bar */}
          <div className="flex gap-0 border-b border-gray-100 px-4">
            {(['summary', 'entities'] as InsightsTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setInsightsTab(tab)}
                className={'px-3 py-2 text-[11px] font-medium border-b-2 -mb-px transition capitalize ' +
                  (insightsTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-400 hover:text-gray-600')}
              >
                {tab === 'summary' ? 'Summary' : 'Entities'}
              </button>
            ))}
          </div>

          <div className="px-4 py-3">
            {insightsTab === 'summary' ? (
              <SummaryPane
                summary={summary ?? null}
                loading={summaryLoading}
                missing={summaryError}
                onGenerate={() => resummarizeMut.mutate()}
                generating={resummarizeMut.isPending}
                generateError={resummarizeMut.isError}
              />
            ) : (
              <EntitiesPane
                entities={entities}
                loading={entitiesLoading}
                onExtract={() => reextractMut.mutate()}
                extracting={reextractMut.isPending}
                extractError={reextractMut.isError}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryPane({
  summary, loading, missing, onGenerate, generating, generateError,
}: {
  summary: DocumentSummary | null
  loading: boolean
  missing: boolean
  onGenerate: () => void
  generating: boolean
  generateError: boolean
}) {
  if (loading) {
    return (
      <div className="space-y-2 animate-pulse">
        <div className="h-4 bg-gray-100 rounded w-3/4" />
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-5/6" />
      </div>
    )
  }

  if (missing || !summary || (!summary.headline && !summary.summary_text)) {
    return (
      <div className="flex items-center gap-3">
        <p className="text-[11px] text-gray-400">No summary generated yet.</p>
        <button
          onClick={onGenerate}
          disabled={generating}
          className="text-[11px] px-2.5 py-1 bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 transition disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate summary'}
        </button>
        {generateError && <span className="text-[11px] text-red-500">Failed -- check server logs</span>}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {summary.headline && (
        <p className="text-sm font-semibold text-gray-800 leading-snug">{summary.headline}</p>
      )}
      {summary.summary_text && (
        <p className="text-xs text-gray-600 leading-relaxed">{summary.summary_text}</p>
      )}
      {summary.key_points.length > 0 && (
        <ul className="space-y-1">
          {summary.key_points.map((pt, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
              <span className="text-blue-400 shrink-0 mt-0.5">&#8226;</span>
              <span>{pt}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="flex justify-end">
        <button
          onClick={onGenerate}
          disabled={generating}
          className="text-[10px] text-gray-300 hover:text-gray-500 transition disabled:opacity-50"
        >
          {generating ? 'Regenerating...' : 'Regenerate'}
        </button>
      </div>
    </div>
  )
}

function EntitiesPane({
  entities, loading, onExtract, extracting, extractError,
}: {
  entities: DocumentEntity[]
  loading: boolean
  onExtract: () => void
  extracting: boolean
  extractError: boolean
}) {
  if (loading) {
    return (
      <div className="flex gap-2 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 w-24 bg-gray-100 rounded-full" />
        ))}
      </div>
    )
  }

  if (entities.length === 0) {
    return (
      <div className="flex items-center gap-3">
        <p className="text-[11px] text-gray-400">No entities extracted yet.</p>
        <button
          onClick={onExtract}
          disabled={extracting}
          className="text-[11px] px-2.5 py-1 bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 transition disabled:opacity-50"
        >
          {extracting ? 'Extracting...' : 'Run extraction'}
        </button>
        {extractError && <span className="text-[11px] text-red-500">Failed -- check server logs</span>}
      </div>
    )
  }

  const grouped: Record<string, DocumentEntity[]> = {}
  for (const e of entities) {
    if (!grouped[e.entity_type]) grouped[e.entity_type] = []
    grouped[e.entity_type].push(e)
  }
  const ORDER = ['doc_type', 'reference', 'deadline', 'date', 'amount', 'party']
  const types = [...new Set([...ORDER, ...Object.keys(grouped)])].filter((t) => grouped[t])

  return (
    <div className="space-y-2">
      {types.map((type) => (
        <div key={type} className="flex flex-wrap gap-1.5 items-start">
          <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider w-16 shrink-0 pt-0.5">
            {type === 'doc_type' ? 'Type' : type}
          </span>
          <div className="flex flex-wrap gap-1.5 flex-1">
            {grouped[type].map((e) => {
              const style = ENTITY_STYLE[e.entity_type] ?? 'bg-gray-50 text-gray-600 border-gray-200'
              return (
                <span
                  key={e.id}
                  title={e.label}
                  className={'inline-flex flex-col border rounded-lg px-2 py-1 text-[11px] ' + style}
                >
                  <span className="font-medium leading-tight">{e.value}</span>
                  <span className="text-[9px] opacity-60 leading-tight">{e.label}</span>
                </span>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
