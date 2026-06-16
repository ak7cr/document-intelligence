import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import Sidebar from './components/Sidebar'
import UploadZone from './components/UploadZone'
import DocumentList from './components/DocumentList'
import { fetchSessions } from './api/sessions'

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

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

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? null

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
              <h1 className="text-lg font-semibold text-gray-900 leading-tight">
                {activeSession.name}
              </h1>
              {activeSession.description && (
                <p className="text-sm text-gray-500 mt-0.5">{activeSession.description}</p>
              )}
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              <UploadZone sessionId={activeSession.id} />
              <DocumentList sessionId={activeSession.id} />
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
