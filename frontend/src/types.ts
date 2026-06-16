export interface Session {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface Document {
  id: string
  session_id: string
  filename: string
  filetype: string
  bucket: string | null
  object_key: string | null
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  uploaded_at: string
  word_count: number | null
  page_count: number | null
  chunk_count: number
}

export interface DocumentChunk {
  id: string
  document_id: string
  chunk_index: number
  text: string
  token_count: number
}

export interface SearchResult {
  score: number
  document_id: string
  chunk_id: string
  chunk_index: number
  filename: string
  text: string
}
