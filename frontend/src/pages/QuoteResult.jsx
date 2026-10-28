import { useEffect, useState } from 'react'
import { api } from '../api'
import Icon from '../components/icons'
import { BackLink, Badge, Button, Card, ErrorBox, Panel, Spinner } from '../components/ui'
import AuditTimeline from '../components/AuditTimeline'
import RiskFactors from '../components/RiskFactors'
import UnderwriteForm from '../components/UnderwriteForm'
import Waterfall from '../components/Waterfall'
import WhatIf from '../components/WhatIf'
import { DECISIONS, inr, sentenceCase, titleCase } from '../format'

const PRODUCT_ICON = { auto: 'car', home: 'home', business: 'business' }
const BAND = { green: 'from-emerald-500 to-teal-400', amber: 'from-amber-400 to-orange-400', blue: 'from-sky-500 to-brand-500', red: 'from-rose-500 to-red-400' }
const RISK_TONE = { low: 'green', medium: 'amber', high: 'red', very_high: 'red' }

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

  // Headline: the system's decision, unless an underwriter has since decided a referral.
  const d = quote.decision === 'refer' && quote.status === 'quoted'
    ? { label: 'Approved by underwriter', tone: 'green', text: 'An underwriter reviewed and approved this quote. It is ready to buy.' }
    : quote.decision === 'refer' && quote.status === 'declined'
      ? { label: 'Declined by underwriter', tone: 'red', text: 'An underwriter reviewed this quote and declined it.' }
      : DECISIONS[quote.decision] || DECISIONS.auto_approve
  const message = quote.status === 'issued' ? 'Your policy is issued and active.'
    : quote.status === 'bound' ? 'Bound. Issue the policy to create your policy number.'
    : d.text
  // What the panels below show: the saved quote, or the what-if simulation.
  const view = whatIf
    ? { steps: whatIf.steps, premium: whatIf.premium, risk: whatIf.risk, hits: whatIf.rule_hits }
    : { steps: quote.breakdown, premium: quote.premium, risk: quote.risk || {}, hits: quote.rule_hits }
  const risk = view.risk
  const titled = (text) => <span className="flex items-center gap-2">{text}{whatIf && <Badge tone="indigo">What-if</Badge>}</span>

  return (
    <div className="space-y-6">
      <BackLink>New quote</BackLink>

      {/* Headline: decision + price + lifecycle */}
      <Card className="overflow-hidden">
        <div className={`h-1.5 bg-gradient-to-r ${BAND[d.tone]}`} />
        <div className="p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div className="flex gap-4">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-600">
                <Icon name={PRODUCT_ICON[quote.product] || 'shield'} className="h-6 w-6" />
              </span>
              <div>
                <p className="text-sm text-steel-500">{titleCase(quote.product)} · <span className="font-mono text-steel-600">{quote.quote_number}</span></p>
                <h1 className="mt-1 text-3xl font-light text-steel-950 sm:text-4xl">{d.label}</h1>
                <p className="mt-1.5 max-w-lg text-steel-600">{message}</p>
              </div>
            </div>
            <div className="sm:text-right">
              <p className="text-sm font-medium text-steel-500">Annual premium</p>
              <p className="font-display text-5xl font-light tracking-tight text-steel-900 sm:text-6xl">{inr(quote.final_premium)}</p>
              {quote.override_premium != null && (
                <p className="mt-1 text-xs text-steel-500">Set by underwriter · system price {inr(quote.premium)}</p>
              )}
              {quote.total_load_pct !== 0 && quote.override_premium == null && (
                <p className="mt-1 text-xs font-medium text-amber-700">Includes {quote.total_load_pct > 0 ? '+' : ''}{quote.total_load_pct}% underwriting loading</p>
              )}
            </div>
          </div>
          <Lifecycle quote={quote} busy={busy} onBind={() => act(api.bind)} onIssue={() => act(api.issue)} />
          <div className="mt-3"><ErrorBox error={quote && error} /></div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel className="lg:col-span-3" title={titled('How your premium is calculated')}
          description="From base cover, through each rating factor and discount, to the final price.">
          <Waterfall steps={view.steps} premium={view.premium} highlight={!!whatIf} />
        </Panel>

        <div className="space-y-6 lg:col-span-2">
          <Panel title={titled('Risk assessment')}>
            <div className="flex items-end justify-between gap-3">
              <div>
                <p className="font-display text-4xl font-light text-steel-900">
                  {risk.method === 'ml_model' ? `${(risk.risk_score * 100).toFixed(1)}%` : risk.risk_score}
                  <span className="ml-1 text-sm font-medium text-steel-400">{risk.method === 'ml_model' ? 'claim chance' : '/ 100 points'}</span>
                </p>
                <p className="mt-0.5 text-xs text-steel-500">
                  {risk.method === 'ml_model' ? `Average driver ${(risk.baseline * 100).toFixed(1)}% · ML model with SHAP` : 'Transparent points scorecard'}
                </p>
              </div>
              <Badge dot tone={RISK_TONE[risk.risk_band]}>{sentenceCase(risk.risk_band)} risk</Badge>
            </div>
            <div className="mt-5"><RiskFactors factors={risk.factors} unit={risk.unit} /></div>
          </Panel>

          <Panel title={titled('Underwriting rules')}>
            {view.hits.length === 0
              ? (
                <p className="flex items-center gap-2 text-sm text-steel-600">
                  <Icon name="check" className="h-4 w-4 text-emerald-600" strokeWidth={2.2} />No rules applied. Decided automatically.
                </p>
              ) : (
                <ul className="space-y-3 text-sm">
                  {view.hits.map((h) => (
                    <li key={h.id} className="rounded-xl bg-steel-50 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={{ decline: 'red', refer: 'blue', load: 'amber' }[h.action]}>
                          {h.action === 'load' ? `${h.load_pct > 0 ? '+' : ''}${h.load_pct}%` : h.action}
                        </Badge>
                        <span className="font-medium text-steel-900">{h.description}</span>
                      </div>
                      <p className="mt-1 text-steel-600">{h.reason}</p>
                    </li>
                  ))}
                </ul>
              )}
          </Panel>
        </div>
      </div>

      {quote.status === 'referred' && (
        <Panel className="ring-1 ring-sky-200" title="Underwriter decision"
          description="This quote was referred. Review the rules and risk above, then decide.">
          <UnderwriteForm quote={quote} onDone={setQuote} />
        </Panel>
      )}

      {product && (
        <Panel title={<span className="flex items-center gap-2"><Icon name="sparkles" className="h-5 w-5 text-brand-600" />What-if simulator</span>}
          description="Change any answer to see how the price, risk score and decision would change. Nothing is saved.">
          <WhatIf product={product} applicant={quote.applicant} coverages={quote.coverages.map((c) => c.code)}
            basePremium={quote.premium} onResult={setWhatIf} />
        </Panel>
      )}

      <Panel title="Audit trail" description="Every change to this quote: who made it, when and why. Entries are never edited.">
        <AuditTimeline events={quote.events} />
      </Panel>
    </div>
  )
}

function Lifecycle({ quote, busy, onBind, onIssue }) {
  const steps = ['Quoted', 'Bound', 'Issued']
  const reached = ['quoted', 'bound', 'issued'].indexOf(quote.status)
  return (
    <div className="mt-8 flex flex-wrap items-center justify-between gap-5 border-t border-steel-100 pt-6">
      <ol className="flex items-center" aria-label="Policy progress">
        {steps.map((label, i) => (
          <li key={label} className="flex items-center">
            <span className="flex items-center gap-2">
              <span className={`grid h-7 w-7 place-items-center rounded-full text-xs font-bold ${i <= reached ? 'bg-brand-600 text-white' : 'border-2 border-steel-200 bg-white text-steel-400'}`}>
                {i < reached ? '✓' : i + 1}
              </span>
              <span className={`text-sm font-medium ${i <= reached ? 'text-steel-900' : 'text-steel-400'}`}>{label}</span>
            </span>
            {i < steps.length - 1 && <span className={`mx-2 h-0.5 w-5 rounded sm:mx-3 sm:w-14 ${i < reached ? 'bg-brand-600' : 'bg-steel-200'}`} />}
          </li>
        ))}
      </ol>
      <div className="flex items-center gap-3">
        {quote.status === 'quoted' && <Button size="lg" onClick={onBind} disabled={busy}>Buy this policy</Button>}
        {quote.status === 'bound' && <Button size="lg" onClick={onIssue} disabled={busy}>Issue policy</Button>}
        {quote.status === 'issued' && quote.policy && (
          <div className="rounded-xl bg-emerald-50 px-4 py-2 text-sm text-emerald-800 ring-1 ring-inset ring-emerald-600/20">
            Policy <b className="font-mono">{quote.policy.policy_number}</b> · {quote.policy.start_date} to {quote.policy.end_date}
          </div>
        )}
        {quote.status === 'referred' && (
          <p className="flex items-center gap-2 text-sm font-medium text-sky-700"><Icon name="clock" className="h-4 w-4" />Waiting for an underwriter</p>
        )}
        {quote.status === 'declined' && <p className="text-sm font-medium text-rose-700">This quote can’t be bought.</p>}
      </div>
    </div>
  )
}
