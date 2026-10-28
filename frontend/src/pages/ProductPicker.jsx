import { useEffect, useState } from 'react'
import { api } from '../api'
import { navigate } from '../router'
import Icon from '../components/icons'
import { Button, Card, ErrorBox, Spinner } from '../components/ui'
import { DECISIONS, inr, inrWords } from '../format'

// Landing page: hero, live portfolio numbers, product picker, how it works, what's inside.
// Product cards come from GET /products, so a new product YAML appears here automatically.
const PRODUCT_ICON = { auto: 'car', home: 'home', business: 'business' }
const TINT = ['bg-indigo-50 text-indigo-600', 'bg-sky-50 text-sky-600', 'bg-violet-50 text-violet-600']

export default function ProductPicker() {
  const [products, setProducts] = useState(null)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setError(null)
    api.products().then(setProducts).catch(setError)
    api.dashboard().then(setStats).catch(() => setStats(null))
  }
  useEffect(load, [])

  const toProducts = () => document.getElementById('products')?.scrollIntoView({ behavior: 'smooth' })

  return (
    <div>
      {/* Hero */}
      <section className="hero-glow border-b border-slate-200/70">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:py-24">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white/70 px-3 py-1 text-xs font-semibold text-indigo-700">
              <Icon name="sparkles" className="h-3.5 w-3.5" /> Property &amp; casualty insurance for India
            </span>
            <h1 className="mt-5 text-4xl font-extrabold leading-[1.08] text-slate-900 sm:text-5xl lg:text-6xl">
              Insurance priced in seconds,{' '}
              <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-sky-500 bg-clip-text text-transparent">explained line by line.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600">
              Get a quote for your car, home or business. See every factor that shaped your price, why you were accepted, and what would change it.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" onClick={toProducts}>Get a quote <Icon name="arrow" className="h-5 w-5" strokeWidth={2} /></Button>
              <Button size="lg" variant="secondary" onClick={() => navigate('/dashboard')}>Underwriter workspace</Button>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
              {['Instant decision', 'Every rupee explained', 'Buy in one click'].map((t) => (
                <li key={t} className="flex items-center gap-1.5"><Icon name="check" className="h-4 w-4 text-emerald-600" strokeWidth={2.2} />{t}</li>
              ))}
            </ul>
          </div>
          <HeroPreview />
        </div>
      </section>

      {/* Live numbers from the demo book */}
      {stats?.quotes > 0 && (
        <section className="border-b border-slate-200/70 bg-white">
          <dl className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-8 sm:px-6 md:grid-cols-4">
            {[
              [stats.quotes.toLocaleString('en-IN'), 'quotes priced'],
              [`${Math.round((stats.straight_through_rate || 0) * 100)}%`, 'decided with no human'],
              [stats.policies.toLocaleString('en-IN'), 'policies issued'],
              [inrWords(stats.written_premium), 'premium written'],
            ].map(([v, l]) => (
              <div key={l}>
                <dt className="sr-only">{l}</dt>
                <dd className="font-display text-3xl font-bold tracking-tight text-slate-900">{v}</dd>
                <dd className="mt-1 text-sm text-slate-500">{l}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* Products */}
      <section id="products" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16 sm:px-6">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-indigo-600">Choose your cover</p>
          <h2 className="mt-1 text-3xl font-bold text-slate-900">What would you like to insure?</h2>
        </div>
        <div className="mt-8">
          {error ? <ErrorBox error={error} onRetry={load} />
            : !products ? <Spinner label="Loading products…" />
            : (
              <div className="grid gap-5 md:grid-cols-3">
                {products.map((p, i) => (
                  <Card key={p.code} className="group flex flex-col p-6 transition hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-500/10">
                    <span className={`grid h-12 w-12 place-items-center rounded-2xl ${TINT[i % TINT.length]}`}>
                      <Icon name={PRODUCT_ICON[p.code] || 'shield'} className="h-6 w-6" />
                    </span>
                    <h3 className="mt-5 text-xl font-bold text-slate-900">{p.name}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{p.description}</p>
                    <ul className="mt-5 space-y-2 text-sm text-slate-700">
                      {p.coverages.slice(0, 4).map((c) => (
                        <li key={c.code} className="flex items-start gap-2">
                          <Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" strokeWidth={2.2} />
                          <span>{c.name}{c.mandatory && <span className="text-slate-400"> · included</span>}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="mt-auto pt-6">
                      <div className="flex items-baseline justify-between border-t border-slate-100 pt-4">
                        <span className="text-sm text-slate-500">From <b className="font-display text-lg text-slate-900">{inr(p.min_premium)}</b>/year</span>
                        <span className="text-xs text-slate-400">{p.questions} questions</span>
                      </div>
                      <Button className="mt-4 w-full" onClick={() => navigate(`/quote/${p.code}`)}>
                        Get a {p.name.toLowerCase()} quote <Icon name="arrow" className="h-4 w-4" strokeWidth={2} />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
        </div>
      </section>

      {/* How it works */}
      <section className="border-y border-slate-200/70 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-3xl font-bold text-slate-900">How it works</h2>
          <ol className="mt-8 grid gap-8 md:grid-cols-3">
            {[
              ['Tell us about the risk', 'A short form built from each product’s configuration: driver and vehicle, property and location, or business and premises.'],
              ['Get a price you can read', 'Every step of the premium is shown, along with your risk score, the factors behind it, and any underwriting rule that applied.'],
              ['Buy, or ask a human', 'Most quotes are decided instantly. Unusual risks go to an underwriter, who can approve, adjust the price or decline.'],
            ].map(([t, d], i) => (
              <li key={t} className="flex gap-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-900 font-display text-sm font-bold text-white">{i + 1}</span>
                <div>
                  <h3 className="font-semibold text-slate-900">{t}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-slate-600">{d}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Under the hood */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-indigo-600">Under the hood</p>
          <h2 className="mt-1 text-3xl font-bold text-slate-900">Built like a real policy system</h2>
          <p className="mt-2 text-slate-600">Pricing and decisions are plain, tested code driven by configuration. The AI only helps underwriters write rules.</p>
        </div>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['doc', 'Config-driven products', 'Coverages, rates, rating tables and form fields live in YAML. A new product is a new file, with no engine changes.'],
            ['chart', 'Explainable premium', 'The rating engine returns every step, drawn as a waterfall from base cover to final price.'],
            ['brain', 'ML and scorecards', 'Gradient boosting with SHAP explanations for auto; transparent points scorecards for home and business.'],
            ['scale', 'Rules engine', 'Decline, refer or load rules, with an impact preview on 9,000 sample applicants before anything goes live.'],
            ['sparkles', 'Plain-English rules', 'Claude drafts rules from an underwriter’s words. The engine validates them and a person approves.'],
            ['clock', 'Full audit trail', 'Quote, refer, approve, bind, issue: every change records who, when and why.'],
          ].map(([icon, t, d]) => (
            <Card key={t} className="p-6">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-slate-900 text-white"><Icon name={icon} className="h-5 w-5" /></span>
              <h3 className="mt-4 font-semibold text-slate-900">{t}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{d}</p>
            </Card>
          ))}
        </div>
      </section>
    </div>
  )
}

// A real quote for a fixed sample driver, priced live by the API (nothing is saved).
const SAMPLE_DRIVER = {
  driver_age: 24, years_licensed: 5, prior_claims_3y: 0, no_claim_bonus_pct: 35, city_tier: 1,
  vehicle_type: 'hatchback', vehicle_age_years: 3, insured_declared_value_inr: 650000,
  annual_km: 12000, parking: 'garage', anti_theft_device: true,
}
const KIND_COLOR = { level: '#eda100', up: '#e34948', down: '#2a78d6' }

function HeroPreview() {
  const [q, setQ] = useState(null)
  useEffect(() => {
    api.rate('auto', SAMPLE_DRIVER).then(setQ).catch(() => setQ(null))
  }, [])
  const rows = (q?.steps || []).filter((s) => s.amount_change !== 0)
    .sort((a, b) => (a.kind === 'coverage') === (b.kind === 'coverage') ? Math.abs(b.amount_change) - Math.abs(a.amount_change) : a.kind === 'coverage' ? -1 : 1)
    .slice(0, 5)
  const max = Math.max(1, ...rows.map((s) => Math.abs(s.amount_change)))
  const approved = q && ['auto_approve', 'approve_adjusted'].includes(q.decision)
  return (
    <div className="relative" aria-hidden="true">
      <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-indigo-500/15 to-sky-400/10 blur-2xl" />
      <Card className="relative p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Live example · 24-year-old, hatchback, Mumbai</p>
            <p className="mt-1 font-display text-3xl font-bold text-slate-900">
              {q ? inr(q.premium) : '₹ ……'}<span className="text-base font-medium text-slate-400"> /year</span>
            </p>
          </div>
          {q && (
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${approved ? 'bg-emerald-50 text-emerald-700 ring-emerald-600/20' : 'bg-sky-50 text-sky-700 ring-sky-600/20'}`}>
              <span className="h-1.5 w-1.5 rounded-full bg-current" /> {DECISIONS[q.decision]?.label}
            </span>
          )}
        </div>
        <ul className="mt-6 space-y-3">
          {(q ? rows : Array.from({ length: 5 }, (_, i) => ({ step: i }))).map((s) => {
            const kind = s.kind === 'coverage' ? 'level' : s.amount_change > 0 ? 'up' : 'down'
            return (
              <li key={s.step}>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-700">{s.label || <span className="inline-block h-3 w-32 rounded bg-slate-100" />}
                    {s.multiplier != null && <span className="text-slate-400"> · ×{s.multiplier}</span>}</span>
                  {s.label && <span className={`shrink-0 whitespace-nowrap pl-3 tabular-nums font-medium ${kind === 'down' ? 'text-blue-700' : 'text-slate-900'}`}>{s.amount_change > 0 ? '+' : '−'}{inr(Math.abs(s.amount_change))}</span>}
                </div>
                <div className="mt-1.5 h-1.5 rounded-full bg-slate-100">
                  {s.label && <div className="h-1.5 rounded-full" style={{ width: `${(Math.abs(s.amount_change) / max) * 100}%`, background: KIND_COLOR[kind] }} />}
                </div>
              </li>
            )
          })}
        </ul>
        <p className="mt-5 border-t border-slate-100 pt-4 text-xs text-slate-500">Priced just now by the same engine as every quote. Yours shows every step, your risk score and the reasons behind it.</p>
      </Card>
    </div>
  )
}
