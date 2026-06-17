import { apiClient } from './client'
import type { ChatResponse } from '../types'

export async function chatSession(sessionId: string, question: string): Promise<ChatResponse> {
  const res = await apiClient.post<ChatResponse>(`/sessions/${sessionId}/chat`, { question })
  return res.data
}
