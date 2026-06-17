import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import Sidebar from './components/Sidebar'
import UploadZone from './components/UploadZone'
import DocumentList from './components/DocumentList'
import SearchPanel from './components/SearchPanel'
import { fetchSessions } from './api/sessions'

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions'],
    queryFn: fetchSessions,
  })

  // Auto-select the first session on initial load
  useEffect(() => {
    if (sessions.length > 0 && activeSessionId === null) {
      setActiveSessionId(sessions[0].id)
    }
  }, [sessions, activeSessionId])

  // Clear search when switching sessions
  useEffect(() => {
    setSearchQuery('')
    setDebouncedQuery('')
  }, [activeSessionId])

  // Debounce search input by 300 ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(searchQuery), 300)
    return () => clearTimeout(t)
  }, [searchQuery])

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? null
  const isSearching = debouncedQuery.trim().length > 2

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar
        activeSessionId={activeSessionId}
        onSessionSelect={setActiveSessionId}
      />

      <main className="flex-1 flex flex-col min-w-0">
        {activeSession ? (
          <>
            {/* Session header */}
            <div className="bg-white border-b border-gray-200 px-8 py-4 shrink-0">
              <div className="flex items-center justify-between gap-6">
                <div className="min-w-0">
                  <h1 className="text-lg font-semibold text-gray-900 leading-tight truncate">
                    {activeSession.name}
                  </h1>
                  {activeSession.description && (
                    <p className="text-sm text-gray-500 mt-0.5 truncate">
                      {activeSession.description}
                    </p>
                  )}
                </div>

                {/* Search bar */}
                <div className="relative w-72 shrink-0">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none">
                    🔍
                  </span>
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search documents…"
                    className="w-full text-sm bg-gray-50 border border-gray-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 rounded-lg pl-9 pr-8 py-2 outline-none transition"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs transition"
                      aria-label="Clear search"
                    >
                      x
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              {isSearching ? (
                <SearchPanel
                  sessionId={activeSession.id}
                  query={debouncedQuery.trim()}
                />
              ) : (
                <>
                  <UploadZone sessionId={activeSession.id} />
                  <DocumentList sessionId={activeSession.id} />
                </>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8 select-none">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center text-3xl mb-5">
              📄
            </div>
            <h2 className="text-xl font-semibold text-gray-700 mb-2">
              Tender Intelligence
            </h2>
            <p className="text-sm text-gray-400 max-w-xs leading-relaxed">
              Create a session from the sidebar, then upload tender documents to begin analysis.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
