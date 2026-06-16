import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDocuments, deleteDocument, getDocumentUrl } from '../api/documents'
import type { Document } from '../types'

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

const IN_PROGRESS = new Set(['uploaded', 'processing'])

interface Props {
  sessionId: string
}

export default function DocumentList({ sessionId }: Props) {
  const qc = useQueryClient()

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents', sessionId],
    queryFn: () => fetchDocuments(sessionId),
    // Poll every 2s while any document is still being processed
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
        <div className="text-5xl mb-3">📂</div>
        <p className="text-sm">No documents yet — upload one above.</p>
      </div>
    )
  }

  return (
    <div>
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest mb-2">
        Documents · {docs.length}
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
    <div className="group flex items-center gap-3 bg-white border border-gray-100 rounded-lg px-4 py-3 hover:border-gray-200 hover:shadow-sm transition">
      {/* Type badge */}
      <div
        className={`shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-[11px] font-bold ${typeStyle.bg}`}
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
              · {doc.word_count.toLocaleString()} words
              {doc.page_count != null ? ` · ${doc.page_count}p` : ''}
              {doc.chunk_count > 0 ? ` · ${doc.chunk_count} chunks` : ''}
            </span>
          )}
        </div>
      </div>

      {/* Status */}
      <span
        className={`flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-medium shrink-0 ${statusStyle}`}
      >
        {isProcessing && (
          <span className="w-2 h-2 rounded-full bg-current animate-pulse inline-block" />
        )}
        {doc.status}
      </span>

      {/* Actions — visible on hover */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition shrink-0">
        <button
          onClick={handleDownload}
          disabled={downloading}
          title="Download"
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition disabled:opacity-40 text-sm"
        >
          {downloading ? '…' : '⬇'}
        </button>
        <button
          onClick={onDelete}
          title="Delete"
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition text-xs"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
