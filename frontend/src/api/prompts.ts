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
  text_zh?: string
}

export interface SaveResponse {
  saved: number
  incremented: number
  failed_translations: number
  tag_failures: number
  items: LibraryItem[]
  record_id?: number | null
}

export function savePrompts(req: SaveRequest) {
  return client.post<SaveResponse>('/prompts/save', req).then((r) => r.data)
}

export interface ParseItem {
  text_en: string
  text_zh: string | null
}

export interface ParseRequest {
  raw_text: string
}

export interface ParseResponse {
  items: ParseItem[]
  split_count: number
  translation_failures: number
}

export interface ImportRequest {
  items: ParseItem[]
  source?: string
}

export interface ImportResponse {
  saved: number
  incremented: number
  tag_failures: number
  items: LibraryItem[]
}

export function parsePrompts(req: ParseRequest) {
  return client.post<ParseResponse>('/prompts/parse', req).then((r) => r.data)
}

export function importPrompts(req: ImportRequest) {
  return client.post<ImportResponse>('/prompts/import', req).then((r) => r.data)
}