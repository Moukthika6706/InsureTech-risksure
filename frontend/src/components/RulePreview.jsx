// Impact of a proposed rule on the sample book (from POST /rules/preview).
import { inr, titleCase } from '../format'

const DECISION_LABEL = { auto_approve: 'Auto-approve', approve_adjusted: 'Approve + loading', refer: 'Refer', decline: 'Decline' }
const pct = (x) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)

export default function RulePreview({ preview }) {
  return (
    <div className="space-y-5">
      {preview.replaces_existing && (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">This rule has the same id as an existing rule and would replace it.</p>
      )}
      {preview.products.map((p) => (
        <div key={p.product}>
          <h4 className="font-semibold">{titleCase(p.product)}</h4>
          <dl className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Applicants matched" value={`${p.matched.toLocaleString('en-IN')}`} sub={`${p.matched_pct}% of ${p.applicants.toLocaleString('en-IN')}`} />
            <Stat label="Decisions changed" value={p.decisions_changed.toLocaleString('en-IN')} />
            <Stat label="Written premium" value={inr(p.written_premium_after)} sub={`was ${inr(p.written_premium_before)}`} />
            <Stat label="Loss ratio" value={pct(p.loss_ratio_after)} sub={`was ${pct(p.loss_ratio_before)}`} />
          </dl>
          <table className="mt-3 w-full text-sm">
            <caption className="sr-only">Decision mix before and after</caption>
            <thead>
              <tr className="text-left text-xs text-steel-500"><th className="py-1 font-medium">Decision</th><th className="py-1 text-right font-medium">Before</th><th className="py-1 text-right font-medium">After</th></tr>
            </thead>
            <tbody>
              {Object.keys(DECISION_LABEL).map((d) => {
                const before = p.decisions_before[d]
                const after = p.decisions_after[d]
                return (
                  <tr key={d} className="border-t border-steel-100">
                    <td className="py-1">{DECISION_LABEL[d]}</td>
                    <td className="py-1 text-right tabular-nums">{before.toLocaleString('en-IN')}</td>
                    <td className={`py-1 text-right tabular-nums ${after !== before ? 'font-semibold text-brand-700' : ''}`}>{after.toLocaleString('en-IN')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {p.matched > 0 && p.avg_premium_change_pct_matched !== 0 && (
            <p className="mt-2 text-sm text-steel-600">Matched applicants who stay insured pay {p.avg_premium_change_pct_matched > 0 ? '+' : ''}{p.avg_premium_change_pct_matched}% on average.</p>
          )}
          {p.examples.length > 0 && (
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer text-brand-600">Example applicants ({p.examples.length})</summary>
              <ul className="mt-2 space-y-1 text-steel-700">
                {p.examples.map((e) => (
                  <li key={e.applicant_id} className="tabular-nums">
                    {e.applicant_id}: {DECISION_LABEL[e.decision_before]} {inr(e.premium_before)} → {DECISION_LABEL[e.decision_after]} {inr(e.premium_after)}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
      <p className="text-xs text-steel-500">Measured on the synthetic sample book. Referred applicants count as written business.</p>
    </div>
  )
}

function Stat({ label, value, sub }) {
  return (
    <div className="rounded-lg bg-steel-50 p-3">
      <dt className="text-xs text-steel-500">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold tabular-nums">{value}</dd>
      {sub && <dd className="text-xs text-steel-500">{sub}</dd>}
    </div>
  )
}
