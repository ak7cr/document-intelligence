import { apiClient } from './client'

export type OcrEngine = 'gemini' | 'easyocr' | 'tesseract'

export async function fetchOcrEngine(): Promise<OcrEngine> {
  const res = await apiClient.get<{ ocr_engine: OcrEngine }>('/config/ocr-engine')
  return res.data.ocr_engine
}

export async function setOcrEngine(engine: OcrEngine): Promise<void> {
  await apiClient.post('/config/ocr-engine', { ocr_engine: engine })
}
