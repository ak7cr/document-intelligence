import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import Sidebar from './components/Sidebar'
import UploadZone from './components/UploadZone'
import DocumentList from './components/DocumentList'
import SearchPanel from './components/SearchPanel'
import ChatPanel from './components/ChatPanel'
import ComparePanel from './components/ComparePanel'
import { fetchSessions } from './api/sessions'

type Tab = 'documents' | 'chat' | 'compare'

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('documents')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions'],
    queryFn: fetchSessions,
  })

  useEffect(() => {
    if (sessions.length > 0 && activeSessionId === null) {
      setActiveSessionId(sessions[0].id)
    }
  }, [sessions, activeSessionId])

  // Reset UI state on session switch
  useEffect(() => {
    setTab('documents')
    setSearchQuery('')
    setDebouncedQuery('')
  }, [activeSessionId])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(searchQuery), 300)
    return () => clearTimeout(t)
  }, [searchQuery])

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? null
  const isSearching = tab === 'documents' && debouncedQuery.trim().length > 2

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
              <div className="flex items-start justify-between gap-6">
                {/* Title + tabs */}
                <div className="min-w-0">
                  <h1 className="text-lg font-semibold text-gray-900 leading-tight truncate">
                    {activeSession.name}
                  </h1>
                  {activeSession.description && (
                    <p className="text-sm text-gray-500 mt-0.5 truncate">
                      {activeSession.description}
                    </p>
                  )}
                  {/* Tab bar */}
                  <div className="flex gap-1 mt-3">
                    <TabButton label="Documents" active={tab === 'documents'} onClick={() => setTab('documents')} />
                    <TabButton label="Chat" active={tab === 'chat'} onClick={() => setTab('chat')} />
                    <TabButton label="Compare" active={tab === 'compare'} onClick={() => setTab('compare')} />
                  </div>
                </div>

                {/* Search bar — only visible in Documents tab */}
                {tab === 'documents' && (
                  <div className="relative w-64 shrink-0 mt-1">
                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none">
                      🔍
                    </span>
                    <input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search documents..."
                      className="w-full text-sm bg-gray-50 border border-gray-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 rounded-lg pl-9 pr-8 py-2 outline-none transition"
                    />
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery('')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs transition"
                      >
                        x
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Content */}
            {tab === 'chat' ? (
              <div className="flex-1 overflow-hidden">
                <ChatPanel sessionId={activeSession.id} />
              </div>
            ) : tab === 'compare' ? (
              <div className="flex-1 overflow-hidden">
                <ComparePanel sessionId={activeSession.id} />
              </div>
            ) : (
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
            )}
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

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={
        'px-3 py-1 text-xs font-medium rounded-md transition ' +
        (active
          ? 'bg-blue-50 text-blue-700'
          : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100')
      }
    >
      {label}
    </button>
  )
}
