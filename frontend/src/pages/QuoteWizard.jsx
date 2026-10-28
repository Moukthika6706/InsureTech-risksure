import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { navigate } from '../router'
import Field from '../components/Field'
import { displayValue, toApiValue, validateField } from '../fields'
import Icon from '../components/icons'
import { BackLink, Badge, Button, Card, ErrorBox, PageHeader, Spinner } from '../components/ui'

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

  const progress = Math.round(((step + 1) / steps.length) * 100)
  const chosen = product.coverages.filter((c) => selected.has(c.code))

  return (
    <div>
      <PageHeader back={<BackLink>All products</BackLink>} eyebrow="New quote" title={`${product.name} quote`}
        description={product.description} />

      {/* Progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-steel-900">Step {step + 1} of {steps.length}: {current}</span>
          <span className="text-steel-500">{progress}%</span>
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-steel-200">
          <div className="h-1.5 rounded-full bg-gradient-to-r from-brand-600 to-brand-500 transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>
        <ol className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm" aria-label="Steps">
          {steps.map((s, i) => (
            <li key={s}>
              <button type="button" disabled={i > step} onClick={() => setStep(i)}
                className={`flex items-center gap-1.5 ${i === step ? 'font-semibold text-brand-700' : i < step ? 'text-steel-700 hover:text-brand-600' : 'text-steel-400'}`}>
                <span className={`grid h-5 w-5 place-items-center rounded-full text-[11px] font-bold ${i < step ? 'bg-emerald-500 text-white' : i === step ? 'bg-brand-600 text-white' : 'bg-steel-200 text-steel-500'}`}>
                  {i < step ? '✓' : i + 1}
                </span>
                {s}
              </button>
            </li>
          ))}
        </ol>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_18rem]">
        <Card className="p-6 sm:p-8">
          {groups.includes(current) && (
            <div className="grid gap-6 sm:grid-cols-2">
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
              <p className="text-sm text-steel-600">Choose what the policy covers. Required covers are always included.</p>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {product.coverages.map((c) => {
                  const on = selected.has(c.code)
                  return (
                    <label key={c.code} className={`flex gap-3 rounded-xl border p-4 transition ${on ? 'border-brand-300 bg-brand-50/60 ring-1 ring-brand-200' : 'border-steel-200 hover:border-steel-300'} ${c.mandatory ? 'cursor-default' : 'cursor-pointer'}`}>
                      <input type="checkbox" className="mt-1 h-4 w-4 accent-brand-600" checked={on} disabled={c.mandatory}
                        onChange={() => {
                          const s = new Set(selected)
                          s.has(c.code) ? s.delete(c.code) : s.add(c.code)
                          setSelected(s)
                        }} />
                      <span>
                        <span className="flex flex-wrap items-center gap-2 font-medium text-steel-900">{c.name}{c.mandatory && <Badge>Required</Badge>}</span>
                        <span className="mt-0.5 block text-sm text-steel-600">{c.description}</span>
                      </span>
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {current === REVIEW_STEP && (
            <div className="space-y-6">
              {groups.map((g, i) => (
                <section key={g}>
                  <div className="flex items-center justify-between">
                    <h2 className="text-xs font-semibold uppercase tracking-wider text-steel-500">{g}</h2>
                    <button className="text-sm font-medium text-brand-600 hover:underline" onClick={() => setStep(i)}>Edit</button>
                  </div>
                  <dl className="mt-2 grid gap-x-8 sm:grid-cols-2">
                    {fieldsOf(g).map((f) => (
                      <div key={f.name} className="flex justify-between gap-4 border-b border-steel-100 py-2 text-sm">
                        <dt className="text-steel-600">{f.label}</dt>
                        <dd className="text-right font-medium text-steel-900">{displayValue(f, values[f.name])}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ))}
              <ErrorBox error={submitError} />
            </div>
          )}

          <div className="mt-8 flex justify-between border-t border-steel-100 pt-6">
            <Button variant="secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</Button>
            {current === REVIEW_STEP
              ? <Button size="lg" onClick={submit} disabled={submitting}>{submitting ? 'Pricing your quote…' : 'Get my quote'}</Button>
              : <Button onClick={next}>Continue</Button>}
          </div>
        </Card>

        {/* Summary */}
        <aside className="lg:sticky lg:top-24">
          <Card className="p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-steel-500">Your quote</p>
            <p className="mt-1 font-display text-xl font-normal text-steel-900">{product.name}</p>
            <p className="mt-3 text-sm text-steel-600">{product.fields.length} questions in {groups.length} steps · common answers pre-filled</p>
            <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-steel-500">Covers</p>
            <ul className="mt-2 space-y-1.5 text-sm text-steel-700">
              {chosen.map((c) => (
                <li key={c.code} className="flex items-start gap-2"><Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" strokeWidth={2.2} />{c.name}</li>
              ))}
            </ul>
            <p className="mt-5 rounded-xl bg-steel-50 p-3 text-xs leading-relaxed text-steel-600">
              Your price is calculated the moment you finish, with every step explained. Nothing is bought until you choose to.
            </p>
          </Card>
        </aside>
      </div>
    </div>
  )
}
