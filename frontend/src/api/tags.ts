import client from './client'

export interface TagOut {
  id: number
  name: string
  parent_id: number | null
}

export interface TagTreeNode extends TagOut {
  usage_count: number
  children: TagTreeNode[]
}

export interface TagTreeResponse {
  categories: TagTreeNode[]
}

export interface TagCreate {
  name: string
  parent_id?: number | null
}

export interface TagUpdate {
  name?: string
  parent_id?: number | null
}

export interface BulkAutoTagResponse {
  scanned: number
  tagged: number
  failed: number
}

export function fetchTags() {
  return client.get<TagTreeResponse>('/tags').then((r) => r.data)
}

export function createTag(req: TagCreate) {
  return client.post<TagOut>('/tags', req).then((r) => r.data)
}

export function updateTag(id: number, req: TagUpdate) {
  return client.patch<TagOut>(`/tags/${id}`, req).then((r) => r.data)
}

export function deleteTag(id: number) {
  return client.delete(`/tags/${id}`).then((r) => r.status)
}

export function setPromptTags(promptId: number, tagIds: number[]) {
  return client
    .post<TagOut[]>(`/prompts/${promptId}/tags`, { tag_ids: tagIds })
    .then((r) => r.data)
}

export function bulkAutoTag() {
  return client
    .post<BulkAutoTagResponse>('/prompts/bulk-auto-tag')
    .then((r) => r.data)
}