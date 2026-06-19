import client from './client'
import type { LibraryItem } from './prompts'

export interface RecordImageOut {
  id: number
  file_path: string
  position: number
  url: string | null
  created_at: string
}

export interface RecordOut {
  id: number
  name: string | null
  text_zh: string | null
  text_en: string | null
  rating: number
  comment: string | null
  is_favorite: boolean
  created_at: string
  updated_at: string
  images: RecordImageOut[]
  prompts: LibraryItem[]
}

export interface RecordListResponse {
  items: RecordOut[]
  total: number
  page: number
  page_size: number
}

export interface RecordUpdate {
  name?: string | null
  text_zh?: string | null
  text_en?: string | null
  rating?: number
  comment?: string | null
  is_favorite?: boolean
}

export interface RecordListParams {
  page?: number
  page_size?: number
  search?: string
  min_rating?: number
  favorites_only?: boolean
  tag_id?: number
  sort?: 'favorites_first' | 'created_desc'
}

export function fetchRecords(params: RecordListParams = {}) {
  return client.get<RecordListResponse>('/records', { params }).then((r) => r.data)
}

export function fetchRecord(id: number) {
  return client.get<RecordOut>(`/records/${id}`).then((r) => r.data)
}

export function updateRecord(id: number, payload: RecordUpdate) {
  return client.patch<RecordOut>(`/records/${id}`, payload).then((r) => r.data)
}

export function deleteRecord(id: number) {
  return client.delete(`/records/${id}`).then((r) => r.status)
}

export function uploadRecordImages(id: number, files: File[]) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  return client
    .post<RecordOut>(`/records/${id}/images`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export function deleteRecordImage(id: number, imageId: number) {
  return client.delete(`/records/${id}/images/${imageId}`).then((r) => r.status)
}

export function reorderRecordImages(id: number, imageIds: number[]) {
  return client
    .patch<RecordOut>(`/records/${id}/images/order`, { image_ids: imageIds })
    .then((r) => r.data)
}
