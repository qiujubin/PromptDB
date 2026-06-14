import client from './client'

export interface GenerateRequest {
  system_prompt: string
  user_input: string
}

export interface GenerateResponse {
  text: string
}

export function generatePrompt(req: GenerateRequest) {
  return client.post<GenerateResponse>('/generate', req).then((r) => r.data)
}