// Thin wrapper around the RiskSure REST API.
// Base URL of the backend, injected at build time by Vite.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Error with the API's details: status, message and (for 422) a list of field errors.
export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail ? String(body.detail) : `API returned ${status}`)
    this.status = status
    this.errors = body?.errors || []
  }
}

async function request(method, path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

export const api = {
  health: () => request('GET', '/health'),
  products: () => request('GET', '/products'),
  product: (code) => request('GET', `/products/${code}`),
  createQuote: (product, applicant, coverages) =>
    request('POST', '/quotes', { product, applicant, coverages }),
  quote: (id) => request('GET', `/quotes/${id}`),
  rate: (product, applicant, coverages) => request('POST', '/rate', { product, applicant, coverages }),
  bind: (id) => request('POST', `/quotes/${id}/bind`, { actor: 'customer' }),
  issue: (id) => request('POST', `/quotes/${id}/issue`, { actor: 'customer' }),
  quotes: (params = {}) => request('GET', `/quotes?${query(params)}`),

  // Underwriting
  queue: (product) => request('GET', `/underwriting/queue?${query({ product })}`),
  underwrite: (id, body) => request('POST', `/quotes/${id}/underwrite`, body),

  // Audit and portfolio
  activity: (params = {}) => request('GET', `/audit?${query(params)}`),
  dashboard: (product) => request('GET', `/dashboard/summary?${query({ product })}`),

  // Rules and the plain-English assistant
  rules: () => request('GET', '/rules'),
  ruleExamples: () => request('GET', '/rules/examples'),
  draftRule: (text, product) => request('POST', '/rules/draft', { text, product: product || null }),
  previewRule: (rule) => request('POST', '/rules/preview', { rule }),
  publishRule: (body) => request('POST', '/rules/publish', body),
  disableRule: (id) => request('POST', `/rules/${id}/disable`),
}

// Query string from an object, skipping empty values.
function query(params) {
  return new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')).toString()
}
