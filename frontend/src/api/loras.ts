import client from './client'

export interface LoraMetaOut {
  base_model: string | null
  trigger_words: string | null
  network_module: string | null
  description: string | null
  author: string | null
}

export interface LoraTriggerGroup {
  name: string
  words: string[]
}

export interface LoraItemOut {
  file_path: string
  file_name: string
  file_size: number
  file_mtime: string | null
  meta: LoraMetaOut
  nickname: string | null
  rating: number
  comment: string | null
  lora_type: string | null
  trigger_words_user: string | null
  trigger_groups: LoraTriggerGroup[]
  has_meta: boolean
  updated_at: string | null
}

export interface LoraListResponse {
  folder_path: string | null
  items: LoraItemOut[]
  total: number
}

export interface LoraConfigOut {
  folder_path: string | null
  updated_at: string | null
}

export interface LoraEntryUpdate {
  nickname?: string | null
  rating?: number
  comment?: string | null
  lora_type?: string | null
  trigger_words_user?: string | null
  trigger_groups?: LoraTriggerGroup[] | null
}

export function fetchLoraConfig() {
  return client.get<LoraConfigOut>('/loras/config').then((r) => r.data)
}

export function updateLoraConfig(folderPath: string | null) {
  return client
    .put<LoraConfigOut>('/loras/config', { folder_path: folderPath })
    .then((r) => r.data)
}

export function fetchLoras() {
  return client.get<LoraListResponse>('/loras').then((r) => r.data)
}

export function updateLoraEntry(filePath: string, payload: LoraEntryUpdate) {
  return client
    .patch<LoraItemOut>('/loras/entry', payload, { params: { file_path: filePath } })
    .then((r) => r.data)
}

export function deleteLoraEntry(filePath: string) {
  return client
    .delete('/loras/entry', { params: { file_path: filePath } })
    .then((r) => r.status)
}
