import { useState, useEffect } from 'react';
import { apiClient } from './api/client';

interface Session {
  id: string;
  name: string;
}

interface Document {
  id: string;
  filename: string;
  filetype: string;
  status: string;
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [newSessionName, setNewSessionName] = useState('');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (activeSession) fetchDocuments(activeSession);
    else setDocuments([]);
  }, [activeSession]);

  const fetchSessions = async () => {
    try {
      const response = await apiClient.get('/sessions');
      setSessions(response.data);
      if (response.data.length > 0 && !activeSession) {
        setActiveSession(response.data[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch sessions', error);
    }
  };

  const fetchDocuments = async (sessionId: string) => {
    try {
      const response = await apiClient.get(`/documents/${sessionId}`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to fetch documents', error);
    }
  };

  const createSession = async () => {
    if (!newSessionName.trim()) return;
    try {
      const response = await apiClient.post('/sessions', { name: newSessionName });
      setNewSessionName('');
      await fetchSessions();
      setActiveSession(response.data.id);
    } catch (error) {
      console.error('Failed to create session', error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeSession) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', activeSession);

    setUploading(true);
    try {
      await apiClient.post('/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      await fetchDocuments(activeSession);
    } catch (error) {
      console.error('Failed to upload document', error);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">

      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-gray-100">
          <h1 className="text-lg font-bold text-gray-800">Tender Analysis</h1>
        </div>

        <div className="p-4 border-b border-gray-200">
          <input
            type="text"
            placeholder="New Session Name..."
            className="w-full text-sm border border-gray-300 rounded px-2 py-1 mb-2"
            value={newSessionName}
            onChange={(e) => setNewSessionName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && createSession()}
          />
          <button
            onClick={createSession}
            className="w-full bg-blue-600 text-white rounded text-sm py-1.5 hover:bg-blue-700 transition"
          >
            + Create Session
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setActiveSession(session.id)}
              className={`w-full text-left px-3 py-2 rounded mb-1 text-sm ${
                activeSession === session.id
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {session.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {activeSession ? (
          <div className="p-8 flex flex-col gap-6 h-full overflow-y-auto">
            <h2 className="text-2xl font-semibold">
              {sessions.find((s) => s.id === activeSession)?.name}
            </h2>

            <div className="border-2 border-dashed border-gray-300 rounded-lg p-10 text-center bg-white">
              <p className="text-gray-500 mb-4">
                {uploading
                  ? 'Uploading...'
                  : 'Drag and drop tender documents here (PDF, Excel, CSV)'}
              </p>
              <input
                type="file"
                className="hidden"
                id="file-upload"
                accept=".pdf,.xlsx,.xls,.csv"
                onChange={handleFileUpload}
                disabled={uploading}
              />
              <label
                htmlFor="file-upload"
                className={`cursor-pointer bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 transition ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                Browse Files
              </label>
            </div>

            {documents.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 text-sm font-medium text-gray-700">
                  Uploaded Documents ({documents.length})
                </div>
                <ul>
                  {documents.map((doc) => (
                    <li
                      key={doc.id}
                      className="flex items-center justify-between px-4 py-3 border-b border-gray-100 last:border-0 text-sm"
                    >
                      <span className="text-gray-800">{doc.filename}</span>
                      <span className="text-xs text-gray-400 uppercase">{doc.filetype}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            Create or select a session to begin.
          </div>
        )}
      </div>
    </div>
  );
}
