import { apiClient } from './client'
import type { ChatMessage, ChatResponse } from '../types'

export async function chatSession(sessionId: string, question: string): Promise<ChatResponse> {
  const res = await apiClient.post<ChatResponse>(`/sessions/${sessionId}/chat`, { question })
  return res.data
}

export async function fetchMessages(sessionId: string): Promise<ChatMessage[]> {
  const res = await apiClient.get<{ id: string; role: string; content: string; sources: ChatMessage['sources']; confidence: ChatMessage['confidence'] }[]>(
    `/sessions/${sessionId}/messages`
  )
  return res.data.map((m) => ({
    role: m.role as ChatMessage['role'],
    content: m.content,
    sources: m.sources ?? undefined,
    confidence: m.confidence ?? undefined,
  }))
}

export async function clearMessages(sessionId: string): Promise<void> {
  await apiClient.delete(`/sessions/${sessionId}/messages`)
}
