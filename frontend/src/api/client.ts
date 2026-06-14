import axios from 'axios'

function serializeParams(params: Record<string, unknown>): string {
  const parts: string[] = []
  const append = (key: string, value: unknown) => {
    if (value === undefined || value === null) return
    if (Array.isArray(value)) {
      for (const v of value) append(key, v)
    } else {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    }
  }
  for (const key of Object.keys(params)) append(key, params[key])
  return parts.join('&')
}

const client = axios.create({
  baseURL: '/api',
  timeout: 60000,
  paramsSerializer: serializeParams,
})

client.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const detail = err?.response?.data?.detail || err.message || 'Request failed'
    return Promise.reject(new Error(detail))
  },
)

export default client