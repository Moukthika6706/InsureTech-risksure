// Display helpers. Amounts use Indian digit grouping: 1234567 -> ₹12,34,567.
const inrFormat = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

export const inr = (n) => (n == null || Number.isNaN(Number(n)) ? '—' : `₹${inrFormat.format(Math.round(n))}`)

// "₹12.5 lakh" / "₹1.2 crore" — how Indian customers read large sums.
export function inrWords(n) {
  if (n == null || n === '') return ''
  const v = Number(n)
  if (v >= 1e7) return `₹${+(v / 1e7).toFixed(2)} crore`
  if (v >= 1e5) return `₹${+(v / 1e5).toFixed(2)} lakh`
  return inr(v)
}

// Fields whose name ends in _inr hold rupee amounts (a naming convention in the configs).
export const isMoneyField = (field) => field.name.endsWith('_inr')

export const titleCase = (s) => s.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())

// "very_high" -> "Very high"
export const sentenceCase = (s) => {
  const t = (s || '').replaceAll('_', ' ')
  return t.charAt(0).toUpperCase() + t.slice(1)
}

// A raw value from the API, shown the way a person reads it (₹30 lakh, Yes/No).
export function readable(name, value) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (name.endsWith('_inr')) return inrWords(value)
  return typeof value === 'number' ? value.toLocaleString('en-IN') : String(value).replaceAll('_', ' ')
}

// How each underwriting decision is shown.
export const DECISIONS = {
  auto_approve: { label: 'Approved', tone: 'green', text: 'Your quote is ready to buy.' },
  approve_adjusted: { label: 'Approved with loading', tone: 'amber', text: 'Approved, with an extra charge for higher risk.' },
  refer: { label: 'Referred to underwriter', tone: 'blue', text: 'An underwriter will review this quote before it can be bought.' },
  decline: { label: 'Declined', tone: 'red', text: 'This risk is outside what we can insure.' },
}

export const STATUS_TONE = {
  draft: 'slate', quoted: 'green', referred: 'blue', declined: 'red', bound: 'indigo', issued: 'indigo',
}
