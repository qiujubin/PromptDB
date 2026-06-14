import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

client.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const detail = err?.response?.data?.detail || err.message || 'Request failed'
    return Promise.reject(new Error(detail))
  },
)

export default client