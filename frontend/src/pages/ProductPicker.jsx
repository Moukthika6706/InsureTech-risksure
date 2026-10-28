import { useEffect, useState } from 'react'
import { api } from '../api'
import { navigate } from '../router'
import Icon from '../components/icons'
import { Button, Card, ErrorBox, Eyebrow, Spinner } from '../components/ui'
import { DECISIONS, inr, inrWords } from '../format'

// Landing page in an editorial style: split hero (tagline + "route of a quote"
// map), live portfolio numbers, products, the route in five steps, what's inside.
// Product cards come from GET /products, so a new product YAML appears here automatically.
const PRODUCT_ICON = { auto: 'car', home: 'home', business: 'business' }

const ROUTE = [
  { key: 'applicant', label: 'Applicant', text: 'A short form generated from the product’s YAML config.', x: 14, y: 55, side: 'right' },
  { key: 'rating', label: 'Rating', text: 'Base cover × rating factors × discounts, every step recorded.', x: 34, y: 41, side: 'right' },
  { key: 'risk', label: 'Risk score', text: 'ML claim probability with SHAP, or a transparent scorecard.', x: 66, y: 36, side: 'right' },
  { key: 'rules', label: 'Rules', text: 'Approve, load, refer to an underwriter, or decline, with reasons.', x: 54, y: 22, side: 'left' },
  { key: 'policy', label: 'Policy', text: 'Bind and issue, with every change in the audit trail.', x: 74, y: 13, side: 'left' },
]

const toProducts = () => document.getElementById('products')?.scrollIntoView({ behavior: 'smooth' })

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

  return (
    <div>
      {/* Hero: two rounded panels */}
      <section className="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
        <div className="grid gap-4 lg:grid-cols-12">
          <HeroPanel />
          <RoutePanel />
        </div>
      </section>

      {/* Live numbers */}
      {stats?.quotes > 0 && (
        <section className="mx-auto max-w-7xl px-4 pt-16 sm:px-6">
          <dl className="grid grid-cols-2 gap-y-10 border-y border-steel-200 py-10 md:grid-cols-4 md:divide-x md:divide-steel-200">
            {[
              [stats.quotes.toLocaleString('en-IN'), 'quotes priced by the engine'],
              [`${Math.round((stats.straight_through_rate || 0) * 100)}%`, 'decided with no human'],
              [stats.policies.toLocaleString('en-IN'), 'policies issued'],
              [inrWords(stats.written_premium), 'premium written'],
            ].map(([v, l]) => (
              <div key={l} className="md:px-8 md:first:pl-0">
                <dt className="sr-only">{l}</dt>
                <dd className="font-display text-4xl font-light tracking-tight text-steel-950 sm:text-5xl">{v}</dd>
                <dd className="mt-2 text-sm text-steel-500">{l}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* Products */}
      <section id="products" className="mx-auto max-w-7xl scroll-mt-24 px-4 pt-20 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <Eyebrow>Products</Eyebrow>
            <h2 className="mt-3 max-w-xl text-4xl font-light leading-tight text-steel-950 sm:text-5xl">
              Cover for what matters, <span className="text-steel-400">priced in seconds.</span>
            </h2>
          </div>
          <p className="max-w-sm text-sm leading-relaxed text-steel-600">
            Three India-based products, each defined entirely in configuration: questions, covers, rates and rules.
          </p>
        </div>
        <div className="mt-10">
          {error ? <ErrorBox error={error} onRetry={load} />
            : !products ? <Spinner label="Loading products…" />
            : (
              <div className="grid gap-4 md:grid-cols-3">
                {products.map((p, i) => (
                  <Card key={p.code} className="group flex flex-col p-7 transition hover:border-steel-300 hover:shadow-[0_20px_40px_-24px_rgb(17_23_29/0.25)]">
                    <div className="flex items-start justify-between">
                      <span className="grid h-12 w-12 place-items-center rounded-full bg-steel-100 text-steel-800">
                        <Icon name={PRODUCT_ICON[p.code] || 'shield'} className="h-6 w-6" strokeWidth={1.5} />
                      </span>
                      <span className="font-display text-sm text-steel-400">0{i + 1}</span>
                    </div>
                    <h3 className="mt-8 text-2xl font-normal text-steel-950">{p.name}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-steel-600">{p.description}</p>
                    <ul className="mt-6 space-y-2.5 border-t border-steel-100 pt-5 text-sm text-steel-700">
                      {p.coverages.slice(0, 4).map((c) => (
                        <li key={c.code} className="flex items-start justify-between gap-3">
                          <span>{c.name}</span>
                          {c.mandatory && <span className="shrink-0 text-xs text-steel-400">included</span>}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-auto flex items-end justify-between gap-4 pt-8">
                      <div>
                        <p className="text-xs text-steel-500">From</p>
                        <p className="font-display text-2xl font-light text-steel-950">{inr(p.min_premium)}<span className="text-sm text-steel-400"> /year</span></p>
                      </div>
                      <button onClick={() => navigate(`/quote/${p.code}`)} aria-label={`Get a ${p.name} quote`}
                        className="grid h-12 w-12 place-items-center rounded-full bg-steel-950 text-white transition group-hover:bg-brand-600">
                        <Icon name="arrow" className="h-5 w-5" strokeWidth={1.8} />
                      </button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
        </div>
      </section>

      {/* The route of a quote */}
      <section className="mx-auto max-w-7xl px-4 pt-24 sm:px-6">
        <Eyebrow>How it works</Eyebrow>
        <h2 className="mt-3 max-w-2xl text-4xl font-light leading-tight text-steel-950 sm:text-5xl">
          The route of a quote, <span className="text-steel-400">from question to policy.</span>
        </h2>
        <ol className="mt-12 grid gap-px overflow-hidden rounded-[1.5rem] border border-steel-200 bg-steel-200 sm:grid-cols-2 lg:grid-cols-5">
          {ROUTE.map((s, i) => (
            <li key={s.key} className="bg-white p-6">
              <span className="font-display text-sm text-brand-600">0{i + 1}</span>
              <h3 className="mt-6 text-xl font-normal text-steel-950">{s.label}</h3>
              <p className="mt-2 text-sm leading-relaxed text-steel-600">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Under the hood */}
      <section className="mx-auto max-w-7xl px-4 pt-24 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <Eyebrow>Under the hood</Eyebrow>
            <h2 className="mt-3 text-4xl font-light leading-tight text-steel-950 sm:text-5xl">
              Plain, tested code <span className="text-steel-400">makes every decision.</span>
            </h2>
            <p className="mt-6 max-w-md leading-relaxed text-steel-600">
              Pricing, scoring and underwriting are deterministic and driven by configuration. The AI helps underwriters write rules, and a person approves every one.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button variant="dark" size="lg" onClick={() => navigate('/dashboard')}>Open the portfolio</Button>
              <Button variant="secondary" size="lg" onClick={() => navigate('/rules')}>Try the rule assistant</Button>
            </div>
          </div>
          <ul className="divide-y divide-steel-200 border-y border-steel-200 lg:col-span-7">
            {[
              ['Config-driven products', 'Coverages, rates, rating tables and form fields live in YAML. A new product is a new file, with no engine changes.'],
              ['Explainable premium', 'The rating engine returns every step, drawn as a waterfall from base cover to the final price.'],
              ['Machine learning and scorecards', 'Gradient boosting with SHAP explanations for auto; transparent points scorecards for home and business.'],
              ['Rules with an impact preview', 'Every proposed rule is run over 9,000 sample applicants before it goes live.'],
              ['Plain-English rule assistant', 'Claude drafts rules from an underwriter’s words. The engine validates them; a person publishes.'],
              ['Full audit trail', 'Quote, refer, approve, bind, issue: every change records who, when and why.'],
            ].map(([t, d], i) => (
              <li key={t} className="grid gap-2 py-5 sm:grid-cols-[3rem_1fr_1.4fr] sm:gap-6">
                <span className="font-display text-sm text-steel-400">0{i + 1}</span>
                <h3 className="text-lg font-normal text-steel-950">{t}</h3>
                <p className="text-sm leading-relaxed text-steel-600">{d}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  )
}

// Left hero panel: tagline over a dark steel field with a floating glass shield.
function HeroPanel() {
  return (
    <div className="panel-steel relative flex min-h-[520px] flex-col justify-between overflow-hidden rounded-[2rem] p-7 text-white sm:min-h-[600px] sm:p-10 lg:col-span-7">
      <div className="relative z-10 flex items-start justify-between gap-6">
        <p className="max-w-[11.5rem] text-sm leading-relaxed text-white/80 sm:max-w-[15rem]">
          <span className="mb-2 block text-[11px] uppercase tracking-[0.18em] text-white/55">P&amp;C insurance · India</span>
          Quote, rate and underwrite in seconds. Every price explained.
        </p>
      </div>

      <GlassShield />

      <div className="relative z-10">
        <h1 className="font-display text-[clamp(2.6rem,4.7vw,4.6rem)] font-light leading-[0.98]">
          Intelligence Behind<br />
          <span className="text-muted-outline">Every Insured</span><br />
          Decision.
        </h1>
        <div className="mt-8 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              {['car', 'home', 'business'].map((n) => (
                <span key={n} className="grid h-10 w-10 place-items-center rounded-full border-2 border-steel-700 bg-white text-steel-900">
                  <Icon name={n} className="h-5 w-5" strokeWidth={1.6} />
                </span>
              ))}
            </div>
            <span className="hidden text-sm text-white/75 sm:inline">Auto · Home · Business</span>
          </div>
          <button onClick={toProducts} aria-label="Choose a product"
            className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-steel-950 text-white ring-1 ring-white/15 transition hover:bg-brand-600">
            <Icon name="arrow" className="h-5 w-5 rotate-90" strokeWidth={1.8} />
          </button>
        </div>
      </div>
    </div>
  )
}

// A floating "glass" shield drawn in SVG (stands in for the 3D object of editorial heroes).
function GlassShield() {
  return (
    <svg viewBox="0 0 320 320" aria-hidden="true"
      className="animate-float pointer-events-none absolute right-[-5.5rem] top-16 h-[15rem] w-[15rem] opacity-90 sm:right-[-1rem] sm:top-2 sm:h-[21rem] sm:w-[21rem] sm:opacity-95">
      <defs>
        <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.85" />
          <stop offset="0.55" stopColor="#fff" stopOpacity="0.28" />
          <stop offset="1" stopColor="#fff" stopOpacity="0.08" />
        </linearGradient>
        <linearGradient id="edge" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.95" />
          <stop offset="1" stopColor="#fff" stopOpacity="0.2" />
        </linearGradient>
        <radialGradient id="core" cx="0.5" cy="0.45" r="0.5">
          <stop offset="0" stopColor="#5f8bff" />
          <stop offset="1" stopColor="#2453f0" />
        </radialGradient>
        <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14" /></filter>
      </defs>
      <ellipse cx="165" cy="292" rx="88" ry="12" fill="#0b1015" opacity="0.35" filter="url(#soft)" />
      <rect x="44" y="96" width="170" height="108" rx="18" transform="rotate(-14 129 150)" fill="#fff" fillOpacity="0.1" stroke="#fff" strokeOpacity="0.35" />
      <rect x="112" y="70" width="160" height="100" rx="18" transform="rotate(10 192 120)" fill="#fff" fillOpacity="0.08" stroke="#fff" strokeOpacity="0.3" />
      <path d="M160 40l84 32v62c0 54-36 96-84 110-48-14-84-56-84-110V72z" fill="url(#glass)" stroke="url(#edge)" strokeWidth="2" />
      <path d="M160 58l66 25v51c0 43-28 77-66 89-38-12-66-46-66-89V83z" fill="#fff" fillOpacity="0.12" />
      <circle cx="160" cy="138" r="30" fill="url(#core)" />
      <path d="M146 138l10 10 19-20" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      <ellipse cx="160" cy="150" rx="128" ry="42" fill="none" stroke="#fff" strokeOpacity="0.3" strokeDasharray="2 7" transform="rotate(-12 160 150)" />
      <circle cx="44" cy="176" r="4" fill="#fff" fillOpacity="0.8" />
      <circle cx="282" cy="118" r="3" fill="#fff" fillOpacity="0.7" />
    </svg>
  )
}

// Right hero panel: the route of a quote drawn like a navigation map, with a live quote on top.
const SAMPLE_DRIVER = {
  driver_age: 24, years_licensed: 5, prior_claims_3y: 0, no_claim_bonus_pct: 35, city_tier: 1,
  vehicle_type: 'hatchback', vehicle_age_years: 3, insured_declared_value_inr: 650000,
  annual_km: 12000, parking: 'garage', anti_theft_device: true,
}

function RoutePanel() {
  const [q, setQ] = useState(null)
  useEffect(() => {
    api.rate('auto', SAMPLE_DRIVER).then(setQ).catch(() => setQ(null))
  }, [])
  const pts = ROUTE.map((p) => `${p.x},${p.y}`)
  const top = (q?.steps || []).filter((s) => s.kind !== 'coverage' && s.amount_change !== 0)
    .sort((a, b) => Math.abs(b.amount_change) - Math.abs(a.amount_change)).slice(0, 3)

  return (
    <div className="panel-map relative min-h-[520px] overflow-hidden rounded-[2rem] sm:min-h-[600px] lg:col-span-5">
      {/* Route line (drawn in a 100×100 box that stretches with the panel) */}
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden="true">
        <polyline points={pts.slice(0, 4).join(' ')} fill="none" stroke="#fff" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <polyline points={pts.slice(0, 4).join(' ')} fill="none" stroke="#11171d" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <polyline points={pts.slice(3).join(' ')} fill="none" stroke="#2453f0" strokeWidth="3" strokeDasharray="2 8" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      </svg>

      {/* Pins */}
      {ROUTE.map((p) => (
        <div key={p.key} className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${p.x}%`, top: `${p.y}%` }}>
          <span className="relative grid h-5 w-5 place-items-center">
            {p.key === 'risk' && <span className="absolute inset-0 animate-ping rounded-full bg-brand-500/40" />}
            <span className={`h-5 w-5 rounded-full border-[3px] ${p.key === 'risk' ? 'border-white bg-brand-600' : 'border-steel-950 bg-white'}`} />
          </span>
          <span className={`absolute top-1/2 -translate-y-1/2 whitespace-nowrap rounded-full bg-white px-2.5 py-1 text-xs font-medium text-steel-900 shadow-sm ${p.side === 'left' ? 'right-7' : 'left-7'}`}>
            {p.label}
          </span>
        </div>
      ))}

      <button onClick={toProducts} className="absolute right-5 top-5 rounded-full bg-brand-600 px-4 py-2 text-xs font-medium text-white shadow-sm hover:bg-brand-500">
        Get a quote
      </button>

      {/* Live quote card */}
      <div className="absolute inset-x-4 bottom-4 sm:inset-x-6 sm:bottom-6" aria-live="polite">
        <div className="rounded-[1.25rem] bg-white/95 p-5 shadow-[0_20px_40px_-20px_rgb(17_23_29/0.35)] backdrop-blur">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] uppercase tracking-[0.14em] text-steel-500">Live quote · 24, hatchback, Mumbai</p>
              <p className="mt-1 font-display text-3xl font-light text-steel-950">
                {q ? inr(q.premium) : '₹ …'}<span className="text-sm text-steel-400"> /year</span>
              </p>
            </div>
            {q && (
              <span className="shrink-0 rounded-full bg-steel-950 px-2.5 py-1 text-[11px] font-medium text-white">
                {DECISIONS[q.decision]?.label}
              </span>
            )}
          </div>
          <ul className="mt-3 space-y-1.5 border-t border-steel-100 pt-3 text-sm">
            {(q ? top : [1, 2, 3].map((k) => ({ step: k }))).map((s) => (
              <li key={s.step} className="flex justify-between gap-3">
                <span className="truncate text-steel-600">{s.label || <span className="inline-block h-3 w-28 rounded bg-steel-100" />}</span>
                {s.label && (
                  <span className={`shrink-0 whitespace-nowrap tabular-nums ${s.amount_change < 0 ? 'text-blue-700' : 'text-steel-950'}`}>
                    {s.amount_change > 0 ? '+' : '−'}{inr(Math.abs(s.amount_change))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
