import { useEffect, useState } from 'react'
import { api } from '../api'
import ProductFilter from '../components/ProductFilter'
import Icon from '../components/icons'
import { Badge, Card, EmptyState, ErrorBox, PageHeader, Spinner, Stat } from '../components/ui'
import { DECISIONS, STATUS_TONE, inr, inrWords, sentenceCase, titleCase, when } from '../format'

// Decisions are states, so they use the reserved status palette (always with a label).
const DECISION_COLOR = { auto_approve: '#0ca30c', approve_adjusted: '#fab219', refer: '#ec835a', decline: '#d03b3b' }
// Risk bands are ordered, so one hue light -> dark (ordinal blue ramp, steps 250-650).
const BAND_COLOR = { low: '#86b6ef', medium: '#3987e5', high: '#1c5cab', very_high: '#104281' }
const pct = (x) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)

export default function Dashboard() {
  const [product, setProduct] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setData(null)
    setError(null)
    Promise.all([api.dashboard(product), api.quotes({ product, limit: 8 }), api.activity({ product, limit: 10 })])
      .then(([summary, quotes, activity]) => setData({ summary, quotes, activity }))
      .catch(setError)
  }, [product])

  return (
    <div>
      <PageHeader eyebrow="Portfolio" title="Dashboard" description="What has been quoted, sold and referred, across the book." />
      <ProductFilter value={product} onChange={setProduct} />

      <div className="mt-6">
        {error ? <ErrorBox error={error} />
          : !data ? <Spinner label="Loading portfolio…" />
          : data.summary.quotes === 0 ? (
            <EmptyState title="No quotes yet"><a href="#/" className="font-medium text-indigo-600 underline">Create one</a> to see the portfolio fill in.</EmptyState>
          ) : <Body {...data} />}
      </div>
    </div>
  )
}

function Body({ summary: s, quotes, activity }) {
  const decisions = Object.keys(DECISION_COLOR).map((d) => [d, s.by_decision[d] || 0])
  const bands = Object.keys(BAND_COLOR).map((b) => [b, s.by_risk_band[b] || 0])
  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <Stat icon={<Icon name="doc" className="h-4 w-4" />} label="Quotes" value={s.quotes.toLocaleString('en-IN')} />
        <Stat icon={<Icon name="shield" className="h-4 w-4" />} label="Policies issued" value={s.policies.toLocaleString('en-IN')} />
        <Stat icon={<Icon name="chart" className="h-4 w-4" />} label="Written premium" value={inrWords(s.written_premium)} sub="issued policies" />
        <Stat icon={<Icon name="scale" className="h-4 w-4" />} label="Average premium" value={inr(s.average_premium)} />
        <Stat icon={<Icon name="sparkles" className="h-4 w-4" />} label="Straight-through" value={pct(s.straight_through_rate)} sub="decided with no human" />
        <Stat icon={<Icon name="inbox" className="h-4 w-4" />} label="In queue" value={s.in_queue.toLocaleString('en-IN')} sub={`referral rate ${pct(s.referral_rate)}`} href="#/underwriting" />
      </dl>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="font-semibold">Automatic decisions</h2>
          <p className="text-xs text-slate-500">What the rules decided at quote time, before any underwriter review.</p>
          <Bars rows={decisions} total={s.quotes} color={(d) => DECISION_COLOR[d]} label={(d) => DECISIONS[d].label} />
        </Card>
        <Card className="p-6">
          <h2 className="font-semibold">Risk bands</h2>
          <Bars rows={bands} total={s.quotes} color={(b) => BAND_COLOR[b]} label={(b) => `${sentenceCase(b)} risk`} />
        </Card>
      </div>

      {s.by_product.length > 1 && (
        <Card className="p-6">
          <h2 className="font-semibold">By product</h2>
          <table className="mt-3 w-full text-sm">
            <thead><tr className="text-left text-xs text-slate-500"><th className="py-1 font-medium">Product</th><th className="py-1 text-right font-medium">Quotes</th><th className="py-1 text-right font-medium">Policies</th><th className="py-1 text-right font-medium">Written premium</th></tr></thead>
            <tbody>
              {s.by_product.map((p) => (
                <tr key={p.product} className="border-t border-slate-100">
                  <td className="py-1.5">{titleCase(p.product)}</td>
                  <td className="py-1.5 text-right tabular-nums">{p.quotes.toLocaleString('en-IN')}</td>
                  <td className="py-1.5 text-right tabular-nums">{p.policies.toLocaleString('en-IN')}</td>
                  <td className="py-1.5 text-right tabular-nums">{inr(p.written_premium)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="font-semibold">Recent quotes</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {quotes.map((q) => (
              <li key={q.id} className="flex items-center justify-between gap-3 py-2">
                <span>
                  <a href={`#/quotes/${q.id}`} className="font-medium text-indigo-700 hover:underline">{q.quote_number}</a>
                  <span className="ml-2 text-xs text-slate-500">{titleCase(q.product)} · {when(q.created_at)}</span>
                </span>
                <span className="flex items-center gap-2">
                  <span className="tabular-nums">{inr(q.final_premium)}</span>
                  <Badge tone={STATUS_TONE[q.status]}>{q.status}</Badge>
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-6">
          <h2 className="font-semibold">Activity</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {activity.map((e) => (
              <li key={e.id} className="flex flex-wrap items-baseline gap-x-2">
                <a href={`#/quotes/${e.quote_id}`} className="font-medium text-indigo-700 hover:underline">{e.quote_number}</a>
                <span className="text-slate-700">{e.action}{e.from_status ? ` ${e.from_status} → ${e.to_status}` : ''}</span>
                <span className="text-xs text-slate-500">by {e.actor} · {when(e.created_at)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}

// Thin horizontal bars with the label and count always written out.
function Bars({ rows, total, color, label }) {
  const max = Math.max(1, ...rows.map(([, n]) => n))
  return (
    <ul className="mt-4 space-y-3">
      {rows.map(([key, n]) => (
        <li key={key} className="text-sm">
          <div className="flex justify-between">
            <span className="text-slate-700">{label(key)}</span>
            <span className="tabular-nums text-slate-600">{n.toLocaleString('en-IN')} <span className="text-slate-400">({pct(total ? n / total : 0)})</span></span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-100">
            <div className="h-2 rounded-full" style={{ width: `${(n / max) * 100}%`, background: color(key) }} />
          </div>
        </li>
      ))}
    </ul>
  )
}
