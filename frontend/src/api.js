// Base URL of the backend, injected at build time by Vite.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function getHealth() {
  const res = await fetch(`${API_URL}/health`)
  if (!res.ok) throw new Error(`API returned ${res.status}`)
  return res.json()
}
