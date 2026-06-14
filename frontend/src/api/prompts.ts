import client from './client'
import type { TagOut } from './tags'

export interface LibraryItem {
  id: number
  text_en: string
  text_zh: string | null
  usage_count: number
  source: string | null
  created_at: string
  updated_at: string
  last_used_at: string | null
  tags: TagOut[]
}

export interface SaveRequest {
  raw_text: string
  source?: string
}

export interface SaveResponse {
  saved: number
  incremented: number
  failed_translations: number
  tag_failures: number
  items: LibraryItem[]
}

export function savePrompts(req: SaveRequest) {
  return client.post<SaveResponse>('/prompts/save', req).then((r) => r.data)
}