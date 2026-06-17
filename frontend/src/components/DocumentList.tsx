import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDocuments, deleteDocument, getDocumentUrl, fetchDocumentEntities, reextractEntities } from '../api/documents'
import type { Document, DocumentEntity } from '../types'

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
          <DocRow
            key={doc.id}
            doc={doc}
            onDelete={() => deleteMut.mutate(doc.id)}
          />
        ))}
      </div>
    </div>
  )
}

function DocRow({ doc, onDelete }: { doc: Document; onDelete: () => void }) {
  const [downloading, setDownloading] = useState(false)
  const [showEntities, setShowEntities] = useState(false)

  const qc = useQueryClient()

  const { data: entities = [], isLoading: entitiesLoading } = useQuery({
    queryKey: ['entities', doc.id],
    queryFn: () => fetchDocumentEntities(doc.id),
    enabled: showEntities && doc.status === 'ready',
    staleTime: 5 * 60 * 1000,
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
        {/* Type badge */}
        <div
          className={'shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-[11px] font-bold ' + typeStyle.bg}
        >
          {typeStyle.label}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate" title={doc.filename}>
            {doc.filename}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-xs text-gray-400">
              {new Date(doc.uploaded_at).toLocaleDateString('en-IN', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
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

        {/* Status */}
        <span
          className={'flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-medium shrink-0 ' + statusStyle}
        >
          {isProcessing && (
            <span className="w-2 h-2 rounded-full bg-current animate-pulse inline-block" />
          )}
          {doc.status}
        </span>

        {/* Insights toggle — only for ready docs */}
        {doc.status === 'ready' && (
          <button
            onClick={() => setShowEntities((v) => !v)}
            title="Show extracted entities"
            className={'text-[11px] px-2 py-0.5 rounded-full border font-medium shrink-0 transition ' +
              (showEntities
                ? 'bg-blue-50 text-blue-600 border-blue-200'
                : 'bg-gray-50 text-gray-400 border-gray-200 hover:text-blue-600 hover:border-blue-200')}
          >
            Insights
          </button>
        )}

        {/* Actions — visible on hover */}
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

      {/* Entity panel */}
      {showEntities && (
        <div className="border-t border-gray-100 px-4 py-3">
          {entitiesLoading ? (
            <div className="flex gap-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-6 w-24 bg-gray-100 rounded-full animate-pulse" />
              ))}
            </div>
          ) : entities.length === 0 ? (
            <div className="flex items-center gap-3">
              <p className="text-[11px] text-gray-400">No entities extracted yet.</p>
              <button
                onClick={() => reextractMut.mutate()}
                disabled={reextractMut.isPending}
                className="text-[11px] px-2.5 py-1 bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 transition disabled:opacity-50"
              >
                {reextractMut.isPending ? 'Extracting...' : 'Run extraction'}
              </button>
              {reextractMut.isError && (
                <span className="text-[11px] text-red-500">Failed — check server logs</span>
              )}
            </div>
          ) : (
            <EntityPanel entities={entities} />
          )}
        </div>
      )}
    </div>
  )
}

function EntityPanel({ entities }: { entities: DocumentEntity[] }) {
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
            {grouped[type].map((e) => (
              <EntityChip key={e.id} entity={e} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function EntityChip({ entity }: { entity: DocumentEntity }) {
  const style = ENTITY_STYLE[entity.entity_type] ?? 'bg-gray-50 text-gray-600 border-gray-200'
  return (
    <span
      className={'inline-flex flex-col border rounded-lg px-2 py-1 text-[11px] ' + style}
      title={entity.label}
    >
      <span className="font-medium leading-tight">{entity.value}</span>
      <span className="text-[9px] opacity-60 leading-tight">{entity.label}</span>
    </span>
  )
}
