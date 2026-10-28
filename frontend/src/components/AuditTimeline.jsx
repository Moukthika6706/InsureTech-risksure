// Audit trail of one quote: every status change, who made it, when and why.
import { Badge } from './ui'
import { DECISIONS, STATUS_TONE, inr, when } from '../format'

const ACTIONS = {
  create: 'Quote started', rate: 'Priced and decided', approve: 'Approved by underwriter',
  decline: 'Declined by underwriter', bind: 'Bound (customer accepted)', issue: 'Policy issued',
}

// The interesting parts of an event's detail, as short phrases.
function facts(e) {
  const d = e.detail || {}
  const out = []
  if (d.decision) out.push(DECISIONS[d.decision]?.label || d.decision)
  if (d.premium != null && e.action !== 'issue') out.push(inr(d.premium))
  if (d.risk_band) out.push(`${d.risk_band.replace('_', ' ')} risk`)
  if (d.rule_hits?.length) out.push(`rules: ${d.rule_hits.join(', ')}`)
  if (d.override_premium != null) out.push(`premium ${inr(d.system_premium)} → ${inr(d.override_premium)}`)
  if (d.policy_number) out.push(`${d.policy_number}, ${d.start_date} to ${d.end_date}`)
  return out
}

export default function AuditTimeline({ events }) {
  return (
    <ol className="relative space-y-5 border-l border-steel-200 pl-5">
      {events.map((e) => (
        <li key={e.id} className="relative">
          <span className="absolute -left-[26.5px] top-1 h-3 w-3 rounded-full border-2 border-white bg-brand-600 ring-1 ring-brand-200" />
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">{ACTIONS[e.action] || e.action}</span>
            <Badge tone={STATUS_TONE[e.to_status]}>{e.from_status ? `${e.from_status} → ` : ''}{e.to_status}</Badge>
          </div>
          <p className="mt-0.5 text-xs text-steel-500">{when(e.created_at)} · by {e.actor}</p>
          {facts(e).length > 0 && <p className="mt-1 text-sm text-steel-700">{facts(e).join(' · ')}</p>}
          {e.detail?.note && <p className="mt-1 text-sm italic text-steel-600">“{e.detail.note}”</p>}
        </li>
      ))}
    </ol>
  )
}
