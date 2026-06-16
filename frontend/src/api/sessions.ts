import { apiClient } from './client'
import type { Session } from '../types'

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
