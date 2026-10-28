import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { navigate } from '../router'
import Field from '../components/Field'
import { displayValue, toApiValue, validateField } from '../fields'
import { Badge, Button, Card, ErrorBox, Spinner } from '../components/ui'

const COVER_STEP = 'Coverages'
const REVIEW_STEP = 'Review'

// Quote wizard built entirely from GET /products/{code}:
// one page per field `group`, then coverages, then review & submit.
export default function QuoteWizard({ productCode }) {
  const [product, setProduct] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [values, setValues] = useState({})
  const [selected, setSelected] = useState(new Set())
  const [step, setStep] = useState(0)
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api.product(productCode).then((p) => {
      setProduct(p)
      setValues(Object.fromEntries(p.fields.map((f) => [f.name, f.default ?? (f.type === 'bool' ? false : '')])))
      setSelected(new Set(p.coverages.filter((c) => c.mandatory || c.default).map((c) => c.code)))
    }).catch(setLoadError)
  }, [productCode])

  // Pages, in the order groups first appear in the config.
  const groups = useMemo(() => {
    if (!product) return []
    const order = []
    for (const f of product.fields) {
      const g = f.group || 'Details'
      if (!order.includes(g)) order.push(g)
    }
    return order
  }, [product])
  const steps = [...groups, COVER_STEP, REVIEW_STEP]
  const fieldsOf = (group) => product.fields.filter((f) => (f.group || 'Details') === group)

  if (loadError) return <ErrorBox error={loadError} />
  if (!product) return <Spinner label="Loading product…" />

  const current = steps[step]

  const checkStep = (group) => {
    const found = {}
    for (const f of fieldsOf(group)) {
      const msg = validateField(f, values[f.name])
      if (msg) found[f.name] = msg
    }
    setErrors(found)
    return Object.keys(found).length === 0
  }

  const next = () => {
    if (groups.includes(current) && !checkStep(current)) return
    setStep(step + 1)
  }

  const submit = async () => {
    setSubmitting(true)
    setSubmitError(null)
    const applicant = Object.fromEntries(product.fields.map((f) => [f.name, toApiValue(f, values[f.name])]))
    try {
      const quote = await api.createQuote(product.code, applicant, [...selected])
      navigate(`/quotes/${quote.id}`)
    } catch (e) {
      // Server-side field errors look like "driver_age: must be at least 18".
      const byField = {}
      for (const msg of e.errors || []) {
        const [name, ...rest] = msg.split(': ')
        byField[name] = rest.join(': ')
      }
      setErrors(byField)
      const firstBad = groups.findIndex((g) => fieldsOf(g).some((f) => byField[f.name]))
      if (firstBad >= 0) setStep(firstBad)
      setSubmitError(e)
      setSubmitting(false)
    }
  }

  return (
    <div>
      <button onClick={() => navigate('/')} className="text-sm text-slate-500 hover:text-indigo-600">← All products</button>
      <h1 className="mt-2 text-2xl font-bold tracking-tight">{product.name} quote</h1>

      <ol className="mt-5 flex flex-wrap gap-2" aria-label="Steps">
        {steps.map((s, i) => (
          <li key={s}>
            <button type="button" disabled={i > step} onClick={() => setStep(i)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                i === step ? 'bg-indigo-600 text-white' : i < step ? 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200' : 'bg-slate-200 text-slate-500'}`}>
              {i + 1}. {s}
            </button>
          </li>
        ))}
      </ol>

      <Card className="mt-5 p-6">
        {groups.includes(current) && (
          <div className="grid gap-5 sm:grid-cols-2">
            {fieldsOf(current).map((f) => (
              <Field key={f.name} field={f} value={values[f.name]} error={errors[f.name]}
                onChange={(v) => {
                  setValues({ ...values, [f.name]: v })
                  setErrors({ ...errors, [f.name]: undefined })
                }} />
            ))}
          </div>
        )}

        {current === COVER_STEP && (
          <div>
            <p className="text-sm text-slate-600">Choose what the policy covers. Required covers are always included.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {product.coverages.map((c) => {
                const on = selected.has(c.code)
                return (
                  <label key={c.code} className={`flex cursor-pointer gap-3 rounded-lg border p-4 ${on ? 'border-indigo-300 bg-indigo-50/50' : 'border-slate-200'} ${c.mandatory ? 'cursor-default' : ''}`}>
                    <input type="checkbox" className="mt-1 h-4 w-4 accent-indigo-600" checked={on} disabled={c.mandatory}
                      onChange={() => {
                        const s = new Set(selected)
                        s.has(c.code) ? s.delete(c.code) : s.add(c.code)
                        setSelected(s)
                      }} />
                    <span>
                      <span className="flex items-center gap-2 font-medium">{c.name}{c.mandatory && <Badge>Required</Badge>}</span>
                      <span className="mt-0.5 block text-sm text-slate-600">{c.description}</span>
                    </span>
                  </label>
                )
              })}
            </div>
          </div>
        )}

        {current === REVIEW_STEP && (
          <div className="space-y-5">
            {groups.map((g, i) => (
              <section key={g}>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{g}</h2>
                  <button className="text-xs text-indigo-600 hover:underline" onClick={() => setStep(i)}>Edit</button>
                </div>
                <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                  {fieldsOf(g).map((f) => (
                    <div key={f.name} className="flex justify-between gap-4 border-b border-slate-100 py-1">
                      <dt className="text-slate-600">{f.label}</dt>
                      <dd className="text-right font-medium">{displayValue(f, values[f.name])}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            ))}
            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Coverages</h2>
              <p className="mt-2 text-sm">
                {product.coverages.filter((c) => selected.has(c.code)).map((c) => c.name).join(' · ')}
              </p>
            </section>
            <ErrorBox error={submitError} />
          </div>
        )}

        <div className="mt-8 flex justify-between border-t border-slate-100 pt-5">
          <Button variant="secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</Button>
          {current === REVIEW_STEP
            ? <Button onClick={submit} disabled={submitting}>{submitting ? 'Pricing…' : 'Get my quote'}</Button>
            : <Button onClick={next}>Next</Button>}
        </div>
      </Card>
    </div>
  )
}
