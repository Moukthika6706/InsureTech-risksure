import { useEffect, useState } from 'react'
import { api } from '../api'
import ProductFilter from '../components/ProductFilter'
import UnderwriteForm from '../components/UnderwriteForm'
import { Badge, Card, ErrorBox, Spinner } from '../components/ui'
import { inr, sentenceCase, titleCase, when } from '../format'

const BAND_TONE = { low: 'green', medium: 'amber', high: 'red', very_high: 'red' }

// Referred quotes waiting for a human decision, oldest first.
export default function UnderwritingQueue({ onChange }) {
  const [product, setProduct] = useState('')
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [open, setOpen] = useState(null)
  const [done, setDone] = useState([])

  useEffect(() => {
    setItems(null)
    api.queue(product).then(setItems).catch(setError)
  }, [product])

  const decided = (q) => {
    setItems((list) => list.filter((x) => x.id !== q.id))
    setDone((d) => [q, ...d].slice(0, 5))
    setOpen(null)
    onChange?.()
  }

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Underwriting queue</h1>
      <p className="mt-1 text-slate-600">
        Quotes the rules referred for a human decision. Approve (optionally at a different premium) or decline, with a reason for the audit trail.
      </p>
      <div className="mt-5"><ProductFilter value={product} onChange={setProduct} /></div>

      {done.length > 0 && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">
          {done.map((q) => (
            <p key={q.id}>
              <a href={`#/quotes/${q.id}`} className="font-medium underline">{q.quote_number}</a>{' '}
              {q.status === 'quoted' ? `approved at ${inr(q.final_premium)}` : 'declined'}.
            </p>
          ))}
        </div>
      )}

      <div className="mt-5 space-y-3">
        {error ? <ErrorBox error={error} />
          : !items ? <Spinner label="Loading queue…" />
          : items.length === 0 ? (
            <Card className="p-8 text-center text-slate-600">Nothing waiting. Every quote has been decided.</Card>
          ) : items.map((q) => (
            <Card key={q.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <a href={`#/quotes/${q.id}`} className="font-semibold text-indigo-700 hover:underline">{q.quote_number}</a>
                    <span className="text-sm text-slate-500">{titleCase(q.product)} · referred {when(q.updated_at)}</span>
                  </div>
                  <ul className="mt-2 space-y-1 text-sm text-slate-700">
                    {q.rule_hits.filter((h) => h.action !== 'load').map((h) => <li key={h.id}>• {h.reason}</li>)}
                  </ul>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold tabular-nums">{inr(q.premium)}</p>
                  <Badge tone={BAND_TONE[q.risk_band]}>{sentenceCase(q.risk_band)} risk</Badge>
                </div>
              </div>
              <div className="mt-4 border-t border-slate-100 pt-4">
                {open === q.id
                  ? <UnderwriteForm quote={q} onDone={decided} />
                  : <button className="text-sm font-semibold text-indigo-600 hover:underline" onClick={() => setOpen(q.id)}>Review and decide →</button>}
              </div>
            </Card>
          ))}
      </div>
    </div>
  )
}
