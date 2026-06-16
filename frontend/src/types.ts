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
}
