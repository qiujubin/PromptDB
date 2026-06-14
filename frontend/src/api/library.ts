import client from './client'
import type { LibraryItem } from './prompts'

export interface LibraryResponse {
  items: LibraryItem[]
  total: number
  page: number
  page_size: number
}

export function fetchLibrary(params: {
  page?: number
  page_size?: number
  search?: string
  tag_id?: number
}) {
  return client.get<LibraryResponse>('/library', { params }).then((r) => r.data)
}

export function deleteLibraryItem(id: number) {
  return client.delete(`/library/${id}`).then((r) => r.status)
}

export function bulkDeleteLibraryItems(ids: number[]) {
  return client
    .post<{ deleted: number }>('/library/bulk-delete', { ids })
    .then((r) => r.data)
}