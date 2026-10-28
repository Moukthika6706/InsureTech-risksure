import { useEffect, useState } from 'react'
import { api } from '../api'
import { navigate } from '../router'
import { Card, ErrorBox, Spinner } from '../components/ui'

// Icons are looked up by product code; unknown (new) products get a generic one,
// so adding a product YAML needs no frontend change.
const ICONS = {
  auto: 'M5 17h14M6 17l1.5-5h9L18 17M7 17v2m10-2v2M8.5 12l1-3h5l1 3',
  home: 'M4 11l8-7 8 7v8a1 1 0 01-1 1h-4v-6H9v6H5a1 1 0 01-1-1z',
  business: 'M4 20V8l8-4 8 4v12M9 20v-5h6v5M8 10h.01M12 10h.01M16 10h.01',
}
const GENERIC = 'M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z'

export default function ProductPicker() {
  const [products, setProducts] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setError(null)
    api.products().then(setProducts).catch(setError)
  }
  useEffect(load, [])

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Get a quote</h1>
      <p className="mt-1 text-slate-600">
        Choose a product. We price it, score the risk and decide in seconds, and show you exactly how.
      </p>
      <div className="mt-6">
        {error ? <ErrorBox error={error} onRetry={load} />
          : !products ? <Spinner label="Loading products…" />
          : (
            <div className="grid gap-4 sm:grid-cols-3">
              {products.map((p) => (
                <button key={p.code} onClick={() => navigate(`/quote/${p.code}`)} className="text-left">
                  <Card className="h-full p-5 transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md">
                    <svg viewBox="0 0 24 24" className="h-9 w-9 text-indigo-600" fill="none" stroke="currentColor"
                      strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d={ICONS[p.code] || GENERIC} />
                    </svg>
                    <h2 className="mt-3 text-lg font-semibold">{p.name}</h2>
                    <p className="mt-1 text-sm text-slate-600">{p.description}</p>
                    <p className="mt-4 text-xs text-slate-400">
                      Risk scored by {p.risk_method === 'ml_model' ? 'a machine-learning model' : 'a points scorecard'}
                    </p>
                  </Card>
                </button>
              ))}
            </div>
          )}
      </div>
    </div>
  )
}
