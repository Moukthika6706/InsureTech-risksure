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
  bind: (id) => request('POST', `/quotes/${id}/bind`, { actor: 'customer' }),
  issue: (id) => request('POST', `/quotes/${id}/issue`, { actor: 'customer' }),
}
