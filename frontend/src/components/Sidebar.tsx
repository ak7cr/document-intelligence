import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchSessions, createSession, deleteSession } from '../api/sessions'
import type { Session } from '../types'

interface Props {
  activeSessionId: string | null
  onSessionSelect: (id: string | null) => void
}

export default function Sidebar({ activeSessionId, onSessionSelect }: Props) {
  const qc = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')

  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions'],
    queryFn: fetchSessions,
  })

  const createMut = useMutation({
    mutationFn: (n: string) => createSession(n),
    onSuccess: (session) => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      onSessionSelect(session.id)
      setName('')
      setCreating(false)
    },
  })

  const deleteMut = useMutation({
    mutationFn: deleteSession,
    onSuccess: (_, deletedId) => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      if (deletedId === activeSessionId) onSessionSelect(null)
    },
  })

  function submit() {
    if (name.trim()) createMut.mutate(name.trim())
  }

  return (
    <aside className="w-60 h-screen bg-gray-950 flex flex-col shrink-0 border-r border-gray-800">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-blue-600 rounded-md flex items-center justify-center shrink-0">
            <span className="text-white text-[10px] font-bold tracking-tight">TI</span>
          </div>
          <span className="text-white text-sm font-semibold tracking-tight">
            Tender Intelligence
          </span>
        </div>
      </div>

      {/* New session */}
      <div className="px-3 py-2.5 border-b border-gray-800">
        {creating ? (
          <div className="flex gap-1">
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') submit()
                if (e.key === 'Escape') {
                  setCreating(false)
                  setName('')
                }
              }}
              placeholder="Session name…"
              className="flex-1 min-w-0 text-xs bg-gray-800 text-gray-100 placeholder-gray-500 border border-gray-700 focus:border-blue-500 rounded px-2 py-1.5 outline-none"
            />
            <button
              onClick={submit}
              disabled={createMut.isPending}
              className="px-2 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 transition"
            >
              ✓
            </button>
          </div>
        ) : (
          <button
            onClick={() => setCreating(true)}
            className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-gray-500 hover:text-gray-200 hover:bg-gray-800 rounded transition"
          >
            <span className="text-base leading-none">+</span>
            New session
          </button>
        )}
      </div>

      {/* Session list */}
      <nav className="flex-1 overflow-y-auto py-2 px-2">
        <p className="text-[10px] text-gray-600 uppercase tracking-widest px-2 mb-1.5">
          Sessions ({sessions.length})
        </p>
        {sessions.length === 0 ? (
          <p className="text-xs text-gray-700 px-2 py-2">No sessions yet</p>
        ) : (
          sessions.map((session) => (
            <SessionRow
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onSelect={() => onSessionSelect(session.id)}
              onDelete={() => deleteMut.mutate(session.id)}
            />
          ))
        )}
      </nav>
    </aside>
  )
}

function SessionRow({
  session,
  isActive,
  onSelect,
  onDelete,
}: {
  session: Session
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <div
      onClick={onSelect}
      className={`group flex items-center justify-between px-2 py-1.5 rounded cursor-pointer mb-0.5 transition ${
        isActive
          ? 'bg-blue-600 text-white'
          : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
      }`}
    >
      <span className="text-xs truncate flex-1">{session.name}</span>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        className={`shrink-0 ml-1 opacity-0 group-hover:opacity-100 text-xs w-4 h-4 flex items-center justify-center rounded transition ${
          isActive ? 'hover:text-red-200' : 'hover:text-red-400'
        }`}
      >
        ✕
      </button>
    </div>
  )
}
