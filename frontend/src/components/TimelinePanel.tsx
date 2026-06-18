import { useQuery } from '@tanstack/react-query'
import { fetchTimeline } from '../api/sessions'
import type { TimelineItem } from '../types'

interface Props {
  sessionId: string
}

const URGENCY = {
  critical: { dot: 'bg-red-500', badge: 'bg-red-50 text-red-700 border-red-200', line: 'border-red-200', label: 'Urgent' },
  soon: { dot: 'bg-yellow-500', badge: 'bg-yellow-50 text-yellow-700 border-yellow-200', line: 'border-yellow-200', label: 'Soon' },
  future: { dot: 'bg-blue-500', badge: 'bg-blue-50 text-blue-700 border-blue-200', line: 'border-blue-100', label: 'Upcoming' },
  past: { dot: 'bg-gray-300', badge: 'bg-gray-50 text-gray-500 border-gray-200', line: 'border-gray-100', label: 'Past' },
  unknown: { dot: 'bg-gray-300', badge: 'bg-gray-50 text-gray-500 border-gray-200', line: 'border-gray-100', label: '' },
}

function daysLabel(days: number | null): string {
  if (days === null) return ''
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  if (days < 0) return `${Math.abs(days)}d ago`
  return `in ${days}d`
}

export default function TimelinePanel({ sessionId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['timeline', sessionId],
    queryFn: () => fetchTimeline(sessionId),
    staleTime: 60 * 1000,
  })

  const items = data?.items ?? []

  const grouped = {
    critical: items.filter((i) => i.urgency === 'critical'),
    soon: items.filter((i) => i.urgency === 'soon'),
    future: items.filter((i) => i.urgency === 'future'),
    past: items.filter((i) => i.urgency === 'past'),
    unknown: items.filter((i) => i.urgency === 'unknown'),
  }

  if (isLoading) {
    return (
      <div className="px-8 py-6 space-y-3 animate-pulse">
        {[1, 2, 3].map((k) => (
          <div key={k} className="h-16 bg-white border border-gray-100 rounded-xl" />
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center select-none">
        <div className="text-4xl mb-3">&#128197;</div>
        <p className="text-sm font-medium text-gray-600 mb-1">No deadline or date entities found</p>
        <p className="text-xs text-gray-400 max-w-xs">
          Upload and process tender documents. Dates and deadlines extracted by the AI will appear here.
        </p>
      </div>
    )
  }

  const summary = {
    critical: grouped.critical.length,
    soon: grouped.soon.length,
    future: grouped.future.length,
    past: grouped.past.length,
  }

  return (
    <div className="px-8 py-6 max-w-3xl space-y-6">
      {/* Summary strip */}
      <div className="grid grid-cols-4 gap-3">
        {(
          [
            { key: 'critical', label: 'Urgent', color: 'text-red-600', bg: 'bg-red-50 border-red-200' },
            { key: 'soon', label: 'Soon', color: 'text-yellow-700', bg: 'bg-yellow-50 border-yellow-200' },
            { key: 'future', label: 'Upcoming', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-100' },
            { key: 'past', label: 'Past', color: 'text-gray-500', bg: 'bg-gray-50 border-gray-200' },
          ] as const
        ).map(({ key, label, color, bg }) => (
          <div key={key} className={'rounded-xl border px-4 py-3 text-center ' + bg}>
            <p className={'text-2xl font-bold ' + color}>{summary[key]}</p>
            <p className={'text-[11px] font-medium mt-0.5 ' + color}>{label}</p>
          </div>
        ))}
      </div>

      {/* Timeline */}
      <div className="space-y-1">
        {(['critical', 'soon', 'future', 'past', 'unknown'] as const)
          .flatMap((u) => grouped[u])
          .map((item, idx, arr) => (
            <TimelineRow key={item.entity_id} item={item} isLast={idx === arr.length - 1} />
          ))}
      </div>
    </div>
  )
}

function TimelineRow({ item, isLast }: { item: TimelineItem; isLast: boolean }) {
  const u = URGENCY[item.urgency] ?? URGENCY.unknown
  const days = daysLabel(item.days_from_now)

  return (
    <div className="flex gap-4">
      {/* Spine */}
      <div className="flex flex-col items-center shrink-0 w-4">
        <div className={'w-3 h-3 rounded-full mt-1 shrink-0 ' + u.dot} />
        {!isLast && <div className={'flex-1 w-px border-l mt-1 ' + u.line} />}
      </div>

      {/* Card */}
      <div className="pb-4 flex-1 min-w-0">
        <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold text-gray-800 leading-snug">{item.label}</p>
              <p className="text-sm text-gray-600 mt-0.5 leading-snug">{item.value}</p>
              <p className="text-[11px] text-gray-400 mt-1 truncate">{item.filename}</p>
            </div>
            <div className="shrink-0 flex flex-col items-end gap-1.5 mt-0.5">
              {u.label && (
                <span className={'text-[10px] font-semibold uppercase tracking-wider border rounded-full px-2 py-0.5 ' + u.badge}>
                  {u.label}
                </span>
              )}
              {days && (
                <span className="text-[11px] text-gray-500 font-medium">{days}</span>
              )}
              {item.parsed_date && (
                <span className="text-[11px] text-gray-400">{item.parsed_date}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
