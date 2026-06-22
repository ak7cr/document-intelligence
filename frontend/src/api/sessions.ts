import { apiClient } from './client'
import type { EntityGraph, OcrReviewItem, SearchResult, Session, TimelineItem } from '../types'

export async function fetchSessions(): Promise<Session[]> {
  const res = await apiClient.get<Session[]>('/sessions')
  return res.data
}

export async function createSession(name: string, description?: string): Promise<Session> {
  const res = await apiClient.post<Session>('/sessions', { name, description })
  return res.data
}

export async function deleteSession(id: string): Promise<void> {
  await apiClient.delete(`/sessions/${id}`)
}

export async function fetchOcrReview(sessionId: string): Promise<{ session_id: string; items: OcrReviewItem[]; threshold: number }> {
  const res = await apiClient.get(`/sessions/${sessionId}/ocr-review`)
  return res.data
}

export async function fetchEntityGraph(sessionId: string): Promise<EntityGraph> {
  const res = await apiClient.get<EntityGraph>(`/sessions/${sessionId}/entity-graph`)
  return res.data
}

export async function fetchTimeline(sessionId: string): Promise<{ session_id: string; items: TimelineItem[] }> {
  const res = await apiClient.get(`/sessions/${sessionId}/timeline`)
  return res.data
}

export async function searchSession(
  sessionId: string,
  query: string,
  limit = 5,
): Promise<{ query: string; results: SearchResult[] }> {
  const res = await apiClient.get(`/sessions/${sessionId}/search`, {
    params: { q: query, limit },
  })
  return res.data
}
