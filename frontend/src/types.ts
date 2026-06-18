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

export interface DocumentSummary {
  document_id: string
  headline: string
  summary_text: string
  key_points: string[]
}

export interface DocumentEntity {
  id: string
  document_id: string
  entity_type: string
  label: string
  value: string
}

export interface DocumentPrediction {
  document_id: string
  risk_level: 'low' | 'medium' | 'high' | 'unknown'
  confidence: number
  timeline_urgency: string
  risk_factors: string[]
  opportunities: string[]
  recommended_actions: string[]
  created_at: string
}

export interface AnalyticsTotals {
  documents: number
  ready: number
  processing: number
  failed: number
  pages: number
  words: number
  chunks: number
  entities: number
}

export interface AnalyticsResult {
  session_id: string
  session_name: string
  totals: AnalyticsTotals
  doc_types: Record<string, number>
  entity_types: Record<string, number>
  top_entities: Record<string, { value: string; count: number }[]>
  timeline: { date: string; count: number }[]
}

export interface ComparisonDifference {
  aspect: string
  values: string[]  // one entry per selected document, in order
}

export interface ComparisonAnalysis {
  similarities: string[]
  differences: ComparisonDifference[]
  recommendation: string
}

export interface ComparisonDoc {
  id: string
  filename: string
  page_count: number | null
  word_count: number | null
  headline: string
  summary_text: string
  key_points: string[]
  entities: DocumentEntity[]
}

export interface ComparisonResult {
  docs: ComparisonDoc[]   // N documents in the order they were submitted
  analysis: ComparisonAnalysis
}

export interface CompanyProfile {
  id: string
  session_id: string
  company_name: string
  annual_turnover: string
  years_in_business: number | null
  certifications: string[]
  similar_projects: number | null
  employee_count: string
  extra_details: string
  created_at: string
  updated_at: string
}

export interface EligibilityDocRequired {
  name: string
  status: 'available' | 'required'
}

export interface EligibilityCheck {
  id: string
  document_id: string
  profile_id: string
  score: number
  met: string[]
  missing: string[]
  documents_required: EligibilityDocRequired[]
  recommendation: string
  created_at: string
}

export interface ChatSource {
  document_id: string
  filename: string
  chunk_index: number
  page_number: number | null
  text: string
  score: number
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  content: string
  sources?: ChatSource[]
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
}
