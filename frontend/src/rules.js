// Turn a rule into one readable sentence, e.g.
// "If driver age < 21 and vehicle type = sports → refer".
const OPS = { eq: '=', ne: '≠', lt: '<', lte: '≤', gt: '>', gte: '≥', in: 'is one of', not_in: 'is not one of' }

const val = (v) => (Array.isArray(v) ? v.join(', ') : typeof v === 'boolean' ? (v ? 'yes' : 'no') : String(v))

function group(g) {
  const kind = g.all ? 'all' : 'any'
  const parts = g[kind].map((c) =>
    c.field ? `${c.field.replaceAll('_', ' ')} ${OPS[c.op] || c.op} ${val(c.value)}` : `(${group(c)})`)
  return parts.join(kind === 'all' ? ' and ' : ' or ')
}

export function ruleSentence(rule) {
  if (!rule?.when) return ''
  const then = rule.action === 'load'
    ? `${rule.load_pct > 0 ? 'add' : 'discount'} ${Math.abs(rule.load_pct)}% to the premium`
    : rule.action
  return `If ${group(rule.when)} → ${then}`
}
