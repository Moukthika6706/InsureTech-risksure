import { useEffect, useState } from 'react'
import { api } from '../api'
import { navigate } from '../router'
import { Badge, Button, Card, ErrorBox, Spinner } from '../components/ui'
import RiskFactors from '../components/RiskFactors'
import Waterfall from '../components/Waterfall'
import WhatIf from '../components/WhatIf'
import { DECISIONS, STATUS_TONE, inr, sentenceCase, titleCase } from '../format'

// Quote result: decision, premium, how it was built, why, and the next lifecycle step.
export default function QuoteResult({ quoteId }) {
  const [quote, setQuote] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [product, setProduct] = useState(null)     // config, for the what-if controls
  const [whatIf, setWhatIf] = useState(null)       // POST /rate result while simulating

  useEffect(() => {
    api.quote(quoteId).then((q) => {
      setQuote(q)
      return api.product(q.product).then(setProduct)
    }).catch(setError)
  }, [quoteId])

  const act = async (fn) => {
    setBusy(true)
    setError(null)
    try {
      setQuote(await fn(quote.id))
    } catch (e) {
      setError(e)
    }
    setBusy(false)
  }

  if (error && !quote) return <ErrorBox error={error} />
  if (!quote) return <Spinner label="Loading quote…" />

  const d = DECISIONS[quote.decision] || DECISIONS.auto_approve
  // What the panels below show: the saved quote, or the what-if simulation.
  const view = whatIf
    ? { steps: whatIf.steps, premium: whatIf.premium, risk: whatIf.risk, hits: whatIf.rule_hits }
    : { steps: quote.breakdown, premium: quote.premium, risk: quote.risk || {}, hits: quote.rule_hits }
  const risk = view.risk
  const tag = whatIf && <Badge tone="indigo">What-if</Badge>

  return (
    <div className="space-y-5">
      <button onClick={() => navigate('/')} className="text-sm text-slate-500 hover:text-indigo-600">← New quote</button>

      {/* Headline: decision + price */}
      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">{quote.quote_number} · {titleCase(quote.product)}</p>
            <div className="mt-2 flex items-center gap-2">
              <Badge tone={d.tone}>{d.label}</Badge>
              <Badge tone={STATUS_TONE[quote.status]}>Status: {quote.status}</Badge>
            </div>
            <p className="mt-3 text-slate-700">
              {quote.status === 'issued' ? 'Your policy is issued and active.'
                : quote.status === 'bound' ? 'Bound. Issue the policy to create your policy number.'
                : d.text}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-500">Annual premium</p>
            <p className="text-4xl font-bold tracking-tight">{inr(quote.final_premium)}</p>
            {quote.override_premium != null && (
              <p className="text-xs text-slate-500">Set by underwriter (system price {inr(quote.premium)})</p>
            )}
            {quote.total_load_pct !== 0 && quote.override_premium == null && (
              <p className="text-xs text-amber-700">Includes {quote.total_load_pct > 0 ? '+' : ''}{quote.total_load_pct}% underwriting loading</p>
            )}
          </div>
        </div>

        <Lifecycle quote={quote} busy={busy} onBind={() => act(api.bind)} onIssue={() => act(api.issue)} />
        <div className="mt-3"><ErrorBox error={quote && error} /></div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-5">
        {/* How the price was built */}
        <Card className="p-6 lg:col-span-3">
          <h2 className="flex items-center gap-2 font-semibold">How the premium is calculated {tag}</h2>
          <div className="mt-3">
            <Waterfall steps={view.steps} premium={view.premium} highlight={!!whatIf} />
          </div>
        </Card>

        <div className="space-y-5 lg:col-span-2">
          {/* Risk score and its top drivers */}
          <Card className="p-6">
            <h2 className="flex items-center gap-2 font-semibold">Risk assessment {tag}</h2>
            <p className="mt-1 text-sm text-slate-600">
              {risk.method === 'ml_model'
                ? <>Predicted claim chance <b>{(risk.risk_score * 100).toFixed(1)}%</b> (average driver {(risk.baseline * 100).toFixed(1)}%)</>
                : <>Scorecard <b>{risk.risk_score}</b> points out of 100</>}
            </p>
            <div className="mt-2"><Badge tone={{ low: 'green', medium: 'amber', high: 'red', very_high: 'red' }[risk.risk_band]}>{sentenceCase(risk.risk_band)} risk</Badge></div>
            <div className="mt-4"><RiskFactors factors={risk.factors} unit={risk.unit} /></div>
          </Card>

          {/* Underwriting rules that fired */}
          <Card className="p-6">
            <h2 className="flex items-center gap-2 font-semibold">Underwriting rules {tag}</h2>
            {view.hits.length === 0
              ? <p className="mt-2 text-sm text-slate-600">No rules applied. This quote was approved automatically.</p>
              : (
                <ul className="mt-3 space-y-3 text-sm">
                  {view.hits.map((h) => (
                    <li key={h.id}>
                      <div className="flex items-center gap-2">
                        <Badge tone={{ decline: 'red', refer: 'blue', load: 'amber' }[h.action]}>
                          {h.action === 'load' ? `${h.load_pct > 0 ? '+' : ''}${h.load_pct}%` : h.action}
                        </Badge>
                        <span className="font-medium">{h.description}</span>
                      </div>
                      <p className="mt-0.5 text-slate-600">{h.reason}</p>
                    </li>
                  ))}
                </ul>
              )}
          </Card>
        </div>
      </div>

      {product && (
        <Card className="p-6">
          <h2 className="font-semibold">What-if simulator</h2>
          <p className="mt-1 text-sm text-slate-600">See how each answer changes the price, the risk score and the decision.</p>
          <div className="mt-4">
            <WhatIf product={product} applicant={quote.applicant} coverages={quote.coverages.map((c) => c.code)}
              basePremium={quote.premium} onResult={setWhatIf} />
          </div>
        </Card>
      )}
    </div>
  )
}

function Lifecycle({ quote, busy, onBind, onIssue }) {
  const steps = ['quoted', 'bound', 'issued']
  const reached = steps.indexOf(quote.status)
  return (
    <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-5">
      <ol className="flex items-center gap-2 text-xs">
        {['Quoted', 'Bound', 'Issued'].map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span className={`rounded-full px-2.5 py-1 font-medium ${i <= reached ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'}`}>{label}</span>
            {i < 2 && <span className="text-slate-300">→</span>}
          </li>
        ))}
      </ol>
      <div className="flex items-center gap-3">
        {quote.status === 'quoted' && <Button onClick={onBind} disabled={busy}>Buy this policy (bind)</Button>}
        {quote.status === 'bound' && <Button onClick={onIssue} disabled={busy}>Issue policy</Button>}
        {quote.status === 'issued' && quote.policy && (
          <p className="text-sm">
            Policy <b>{quote.policy.policy_number}</b>, {quote.policy.start_date} to {quote.policy.end_date}
          </p>
        )}
        {quote.status === 'referred' && <p className="text-sm text-sky-700">Waiting for an underwriter's decision.</p>}
        {quote.status === 'declined' && <p className="text-sm text-rose-700">This quote can't be bought.</p>}
      </div>
    </div>
  )
}
