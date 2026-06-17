import { apiClient } from './client'

async function _download(url: string, filename: string) {
  const res = await apiClient.get(url, { responseType: 'blob' })
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  URL.revokeObjectURL(href)
}

export function exportJson(sessionId: string, sessionName: string) {
  return _download(
    `/sessions/${sessionId}/export/json`,
    sessionName.replace(/\s+/g, '_') + '_export.json',
  )
}

export function exportCsv(sessionId: string, sessionName: string, sheet: 'entities' | 'summaries' | 'documents') {
  return _download(
    `/sessions/${sessionId}/export/csv?sheet=${sheet}`,
    sessionName.replace(/\s+/g, '_') + '_' + sheet + '.csv',
  )
}

export function exportXlsx(sessionId: string, sessionName: string) {
  return _download(
    `/sessions/${sessionId}/export/xlsx`,
    sessionName.replace(/\s+/g, '_') + '_report.xlsx',
  )
}
