import { useEffect, useState } from 'react'
import { api } from './api'
import { navigate, useRoute } from './router'
import ProductPicker from './pages/ProductPicker'
import QuoteWizard from './pages/QuoteWizard'
import QuoteResult from './pages/QuoteResult'

// App shell: header + hash routes.
//   #/                 product picker
//   #/quote/<product>  quote wizard (form built from the product config)
//   #/quotes/<id>      quote result
export default function App() {
  const [page, param] = useRoute()
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {page === 'quote' && param ? <QuoteWizard key={param} productCode={param} />
          : page === 'quotes' && param ? <QuoteResult key={param} quoteId={param} />
          : <ProductPicker />}
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-8 text-xs text-slate-400 sm:px-6">
        Portfolio demo. All data, rates and models are synthetic and illustrative, not real actuarial pricing.
      </footer>
    </div>
  )
}

function Header() {
  const [apiUp, setApiUp] = useState(null)
  useEffect(() => {
    api.health().then(() => setApiUp(true)).catch(() => setApiUp(false))
  }, [])
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-left">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-sm font-bold text-white">R</span>
          <span>
            <span className="block text-base font-bold leading-tight">RiskSure</span>
            <span className="block text-xs text-slate-500">P&amp;C quoting &amp; underwriting</span>
          </span>
        </button>
        <nav className="flex items-center gap-4 text-sm">
          <a href="#/" className="font-medium text-slate-700 hover:text-indigo-600">New quote</a>
          <span className="flex items-center gap-1.5 text-xs text-slate-500" title="Backend API status">
            <span className={`h-2 w-2 rounded-full ${apiUp ? 'bg-emerald-500' : apiUp === false ? 'bg-rose-500' : 'bg-slate-300'}`} />
            {apiUp ? 'API online' : apiUp === false ? 'API offline' : 'Checking…'}
          </span>
        </nav>
      </div>
    </header>
  )
}
