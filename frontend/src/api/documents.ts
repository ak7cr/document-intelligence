import { apiClient } from './client'
import type { AnalyticsResult, ComparisonResult, Document, DocumentChecklist, DocumentEntity, DocumentPrediction, DocumentSummary, EligibilityCheck } from '../types'

export async function fetchDocuments(sessionId: string): Promise<Document[]> {
  const res = await apiClient.get<Document[]>(`/documents/${sessionId}`)
  return res.data
}

export async function uploadDocument(sessionId: string, file: File): Promise<Document> {
  const form = new FormData()
  form.append('file', file)
  form.append('session_id', sessionId)
  const res = await apiClient.post<Document>('/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/documents/${id}`)
}

export async function getDocumentUrl(id: string): Promise<string> {
  const res = await apiClient.get<{ url: string }>(`/documents/${id}/url`)
  return res.data.url
}

export async function fetchDocumentEntities(id: string): Promise<DocumentEntity[]> {
  const res = await apiClient.get<{ document_id: string; entities: DocumentEntity[] }>(
    `/documents/${id}/entities`
  )
  return res.data.entities
}

export async function reextractEntities(id: string): Promise<DocumentEntity[]> {
  const res = await apiClient.post<{ document_id: string; entities: DocumentEntity[] }>(
    `/documents/${id}/extract`
  )
  return res.data.entities
}

export async function fetchDocumentSummary(id: string): Promise<DocumentSummary> {
  const res = await apiClient.get<DocumentSummary>(`/documents/${id}/summary`)
  return res.data
}

export async function resummarizeDocument(id: string): Promise<DocumentSummary> {
  const res = await apiClient.post<DocumentSummary>(`/documents/${id}/summarize`)
  return res.data
}

export async function fetchPrediction(docId: string): Promise<DocumentPrediction> {
  const res = await apiClient.get<DocumentPrediction>(`/documents/${docId}/prediction`)
  return res.data
}

export async function runPrediction(docId: string): Promise<DocumentPrediction> {
  const res = await apiClient.post<DocumentPrediction>(`/documents/${docId}/predict`)
  return res.data
}

export async function fetchAnalytics(sessionId: string): Promise<AnalyticsResult> {
  const res = await apiClient.get<AnalyticsResult>(`/sessions/${sessionId}/analytics`)
  return res.data
}

export async function compareDocuments(sessionId: string, docIds: string[]): Promise<ComparisonResult> {
  const res = await apiClient.post<ComparisonResult>(`/sessions/${sessionId}/compare`, {
    doc_ids: docIds,
  })
  return res.data
}

export async function fetchEligibility(docId: string): Promise<EligibilityCheck> {
  const res = await apiClient.get<EligibilityCheck>(`/documents/${docId}/eligibility`)
  return res.data
}

export async function runEligibility(docId: string): Promise<EligibilityCheck> {
  const res = await apiClient.post<EligibilityCheck>(`/documents/${docId}/eligibility`)
  return res.data
}

export async function fetchChecklist(docId: string): Promise<DocumentChecklist> {
  const res = await apiClient.get<DocumentChecklist>(`/documents/${docId}/checklist`)
  return res.data
}

export async function runChecklist(docId: string): Promise<DocumentChecklist> {
  const res = await apiClient.post<DocumentChecklist>(`/documents/${docId}/checklist`)
  return res.data
}
