import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import Sidebar from './components/Sidebar'
import UploadZone from './components/UploadZone'
import DocumentList from './components/DocumentList'
import SearchPanel from './components/SearchPanel'
import ChatPanel from './components/ChatPanel'
import ComparePanel from './components/ComparePanel'
import AnalyticsPanel from './components/AnalyticsPanel'
import PredictionsPanel from './components/PredictionsPanel'
import EligibilityPanel from './components/EligibilityPanel'
import { fetchSessions } from './api/sessions'
import { exportJson, exportCsv, exportXlsx } from './api/export'

type Tab = 'documents' | 'chat' | 'compare' | 'analytics' | 'predictions' | 'eligibility'

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
      <Sidebar activeSessionId={activeSessionId} onSessionSelect={setActiveSessionId} />

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
                  <div className="flex gap-1 mt-3">
                    <TabButton label="Documents" active={tab === 'documents'} onClick={() => setTab('documents')} />
                    <TabButton label="Chat" active={tab === 'chat'} onClick={() => setTab('chat')} />
                    <TabButton label="Compare" active={tab === 'compare'} onClick={() => setTab('compare')} />
                    <TabButton label="Analytics" active={tab === 'analytics'} onClick={() => setTab('analytics')} />
                    <TabButton label="Predictions" active={tab === 'predictions'} onClick={() => setTab('predictions')} />
                    <TabButton label="Eligibility" active={tab === 'eligibility'} onClick={() => setTab('eligibility')} />
                  </div>
                </div>

                {/* Right side: search (Documents tab) + Export button */}
                <div className="flex items-start gap-3 mt-1 shrink-0">
                  {tab === 'documents' && (
                    <div className="relative w-56">
                      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none">
                        &#128269;
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
                  <ExportMenu sessionId={activeSession.id} sessionName={activeSession.name} />
                </div>
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
            ) : tab === 'analytics' ? (
              <div className="flex-1 overflow-y-auto">
                <AnalyticsPanel sessionId={activeSession.id} />
              </div>
            ) : tab === 'predictions' ? (
              <div className="flex-1 overflow-y-auto">
                <PredictionsPanel sessionId={activeSession.id} />
              </div>
            ) : tab === 'eligibility' ? (
              <div className="flex-1 overflow-y-auto">
                <EligibilityPanel sessionId={activeSession.id} />
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto p-8 space-y-6">
                {isSearching ? (
                  <SearchPanel sessionId={activeSession.id} query={debouncedQuery.trim()} />
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
              &#128196;
            </div>
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Document Intelligence</h2>
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
        (active ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100')
      }
    >
      {label}
    </button>
  )
}

function ExportMenu({ sessionId, sessionName }: { sessionId: string; sessionName: string }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  async function run(fn: () => Promise<void>) {
    setOpen(false)
    setBusy(true)
    try { await fn() } finally { setBusy(false) }
  }

  const items: { label: string; desc: string; fn: () => Promise<void> }[] = [
    {
      label: 'Excel report (.xlsx)',
      desc: 'Documents, summaries & entities',
      fn: () => exportXlsx(sessionId, sessionName),
    },
    {
      label: 'Entities CSV',
      desc: 'All extracted entities as spreadsheet',
      fn: () => exportCsv(sessionId, sessionName, 'entities'),
    },
    {
      label: 'Summaries CSV',
      desc: 'Headlines and key points',
      fn: () => exportCsv(sessionId, sessionName, 'summaries'),
    },
    {
      label: 'Full JSON',
      desc: 'Complete structured data dump',
      fn: () => exportJson(sessionId, sessionName),
    },
  ]

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={busy}
        className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:border-gray-300 hover:bg-gray-50 transition disabled:opacity-50"
      >
        <span>&#8659;</span>
        {busy ? 'Downloading...' : 'Export'}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-56 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider px-3 py-2 border-b border-gray-100">
            Download session data
          </p>
          {items.map((item) => (
            <button
              key={item.label}
              onClick={() => run(item.fn)}
              className="w-full text-left px-3 py-2.5 hover:bg-gray-50 transition border-b border-gray-50 last:border-0"
            >
              <p className="text-xs font-medium text-gray-700">{item.label}</p>
              <p className="text-[10px] text-gray-400 mt-0.5">{item.desc}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
