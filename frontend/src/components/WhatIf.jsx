// What-if simulator: change any answer and re-price live through POST /rate
// (which saves nothing). The parent shows the result in the waterfall.
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import Field from './Field'
import { Badge, Button } from './ui'
import { DECISIONS, inr, inrWords, isMoneyField } from '../format'

const DEBOUNCE_MS = 300

// A "nice" slider step: 1, 2 or 5 times a power of ten.
function niceStep(raw) {
  const p = 10 ** Math.floor(Math.log10(raw))
  return [1, 2, 5, 10].map((m) => m * p).find((s) => s >= raw)
}

// Slider range: the config's min/max, narrowed around the current value for
// money fields so the slider stays useful (a ₹30 lakh car doesn't need ₹1 crore).
function sliderRange(field, start) {
  let lo = field.min ?? 0
  let hi = field.max ?? Math.max(10, start * 4)
  if (isMoneyField(field) && start > 0) {
    lo = Math.max(lo, start / 4)
    hi = Math.min(hi, start * 4)
  }
  const step = field.type === 'int' && hi - lo <= 200 ? 1 : niceStep((hi - lo) / 100)
  return { lo: Math.floor(lo / step) * step, hi: Math.ceil(hi / step) * step, step }
}

function Slider({ field, start, value, onChange }) {
  const { lo, hi, step } = sliderRange(field, start)
  const id = `w-${field.name}`
  const changed = Number(value) !== Number(start)
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium text-steel-800">{field.label}</label>
        <span className={`text-sm tabular-nums ${changed ? 'font-semibold text-brand-700' : 'text-steel-600'}`}>
          {isMoneyField(field) ? inrWords(value) : Number(value).toLocaleString('en-IN')}
        </span>
      </div>
      <input id={id} type="range" min={lo} max={hi} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))} className="mt-1 w-full accent-brand-600" />
    </div>
  )
}

export default function WhatIf({ product, applicant, coverages, basePremium, onResult }) {
  const [values, setValues] = useState(applicant)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const latest = useRef(0)
  const changed = product.fields.filter((f) => String(values[f.name]) !== String(applicant[f.name]))

  useEffect(() => {
    if (changed.length === 0) {
      setResult(null)
      onResult(null)
      return
    }
    const id = ++latest.current
    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const r = await api.rate(product.code, values, coverages)
        if (id !== latest.current) return          // a newer request is on its way
        setResult(r)
        setError(null)
        onResult(r)
      } catch (e) {
        if (id === latest.current) setError(e)
      }
      if (id === latest.current) setLoading(false)
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-run only when the answers change
  }, [values])

  const groups = [...new Set(product.fields.map((f) => f.group || 'Details'))]
  const diff = result ? result.premium - basePremium : 0
  const d = result && DECISIONS[result.decision]

  return (
    <div>
      {/* Summary of the simulated quote */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-steel-50 p-4">
        {result ? (
          <div>
            <p className="text-sm text-steel-600">What-if premium {loading && <span className="text-steel-400">(updating…)</span>}</p>
            <p className="font-display text-3xl font-light tabular-nums">
              {inr(result.premium)}{' '}
              <span className={`text-base font-semibold ${diff > 0 ? 'text-rose-700' : diff < 0 ? 'text-blue-700' : 'text-steel-500'}`}>
                {diff > 0 ? '▲' : diff < 0 ? '▼' : ''} {diff === 0 ? 'no change' : `${inr(Math.abs(diff))} (${diff > 0 ? '+' : '−'}${Math.abs((diff / basePremium) * 100).toFixed(1)}%)`}
              </span>
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
              <Badge tone={d.tone}>{d.label}</Badge>
              <span className="text-steel-600">
                Risk {result.risk.method === 'ml_model' ? `${(result.risk.risk_score * 100).toFixed(1)}%` : `${result.risk.risk_score} pts`} ({result.risk.risk_band.replace('_', ' ')})
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-steel-600">
            {loading ? 'Re-pricing…' : 'Move a slider or change an answer to see how the price and decision would change. Nothing is saved.'}
          </p>
        )}
        {changed.length > 0 && (
          <Button variant="secondary" onClick={() => setValues(applicant)}>Reset ({changed.length} changed)</Button>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-rose-700">{error.message}{error.errors?.length ? `: ${error.errors.join('; ')}` : ''}</p>}

      {/* Controls, grouped like the wizard */}
      <div className="mt-5 space-y-6">
        {groups.map((g) => (
          <section key={g}>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-steel-500">{g}</h3>
            <div className="mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2">
              {product.fields.filter((f) => (f.group || 'Details') === g).map((f) =>
                f.type === 'int' || f.type === 'float'
                  ? <Slider key={f.name} field={f} start={applicant[f.name]} value={values[f.name]}
                      onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))} />
                  : <Field key={f.name} field={f} value={values[f.name]}
                      onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))} />,
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
