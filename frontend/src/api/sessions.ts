import { apiClient } from './client'
import type { CompanyProfile, SearchResult, Session, TimelineItem } from '../types'

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

export async function fetchProfile(sessionId: string): Promise<CompanyProfile> {
  const res = await apiClient.get<CompanyProfile>(`/sessions/${sessionId}/profile`)
  return res.data
}

export async function upsertProfile(sessionId: string, data: Partial<CompanyProfile>): Promise<CompanyProfile> {
  const res = await apiClient.post<CompanyProfile>(`/sessions/${sessionId}/profile`, data)
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
