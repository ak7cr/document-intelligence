import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchOcrReview } from '../api/sessions'

interface Props {
  sessionId: string
}

export default function OcrReviewBanner({ sessionId }: Props) {
  const [expanded, setExpanded] = useState(false)

  const { data } = useQuery({
    queryKey: ['ocr-review', sessionId],
    queryFn: () => fetchOcrReview(sessionId),
    staleTime: 2 * 60 * 1000,
  })

  const items = data?.items ?? []
  if (items.length === 0) return null

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-amber-100 transition"
      >
        <span className="text-amber-500 text-base shrink-0">&#9888;</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-amber-800">
            {items.length} document{items.length !== 1 ? 's' : ''} with low OCR confidence
          </p>
          <p className="text-[11px] text-amber-600 mt-0.5">
            These may contain extraction errors. Consider re-uploading a cleaner scan.
          </p>
        </div>
        <span className="text-amber-400 text-xs shrink-0">
          {expanded ? '&#9650;' : '&#9660;'}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-amber-200 divide-y divide-amber-100">
          {items.map((item) => {
            const pct = item.ocr_confidence != null ? Math.round(item.ocr_confidence * 100) : null
            const color = pct == null
              ? 'text-gray-500'
              : pct < 50
              ? 'text-red-600'
              : 'text-amber-700'

            return (
              <div key={item.document_id} className="flex items-center gap-3 px-4 py-2.5">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">{item.filename}</p>
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    {item.page_count != null ? item.page_count + 'p' : ''}
                    {item.word_count != null ? ' · ' + item.word_count.toLocaleString() + ' words' : ''}
                  </p>
                </div>
                <div className={'text-xs font-semibold shrink-0 ' + color}>
                  {pct != null ? pct + '% confidence' : 'No score'}
                </div>
                <div className="w-16 shrink-0">
                  <div className="w-full bg-white rounded-full h-1.5 border border-amber-100">
                    <div
                      className={'h-1.5 rounded-full ' + (pct == null ? 'bg-gray-200' : pct < 50 ? 'bg-red-400' : 'bg-amber-400')}
                      style={{ width: (pct ?? 0) + '%' }}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
