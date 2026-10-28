import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { navigate, useRoute } from './router'
import Dashboard from './pages/Dashboard'
import ProductPicker from './pages/ProductPicker'
import QuoteResult from './pages/QuoteResult'
import QuoteWizard from './pages/QuoteWizard'
import RulesPage from './pages/RulesPage'
import UnderwritingQueue from './pages/UnderwritingQueue'

// App shell: header + hash routes.
//   #/                 product picker          #/underwriting   underwriter queue
//   #/quote/<product>  quote wizard            #/rules          rules + assistant
//   #/quotes/<id>      quote result            #/dashboard      portfolio dashboard
export default function App() {
  const [page, param] = useRoute()
  const [queueCount, setQueueCount] = useState(null)
  const refreshQueue = useCallback(() => {
    api.queue().then((q) => setQueueCount(q.length)).catch(() => setQueueCount(null))
  }, [])
  useEffect(refreshQueue, [page, param, refreshQueue])

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header page={page} queueCount={queueCount} />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {page === 'quote' && param ? <QuoteWizard key={param} productCode={param} />
          : page === 'quotes' && param ? <QuoteResult key={param} quoteId={param} />
          : page === 'underwriting' ? <UnderwritingQueue onChange={refreshQueue} />
          : page === 'rules' ? <RulesPage />
          : page === 'dashboard' ? <Dashboard />
          : <ProductPicker />}
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-8 text-xs text-slate-400 sm:px-6">
        Portfolio demo. All data, rates and models are synthetic and illustrative, not real actuarial pricing.
      </footer>
    </div>
  )
}

const NAV = [
  ['', 'New quote', ['', 'quote', 'quotes']],
  ['underwriting', 'Underwriting', ['underwriting']],
  ['rules', 'Rules', ['rules']],
  ['dashboard', 'Dashboard', ['dashboard']],
]

function Header({ page = '', queueCount }) {
  const [apiUp, setApiUp] = useState(null)
  useEffect(() => {
    api.health().then(() => setApiUp(true)).catch(() => setApiUp(false))
  }, [])
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-left">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-sm font-bold text-white">R</span>
          <span>
            <span className="block text-base font-bold leading-tight">RiskSure</span>
            <span className="block text-xs text-slate-500">P&amp;C quoting &amp; underwriting</span>
          </span>
        </button>
        <nav className="flex flex-wrap items-center gap-1 text-sm" aria-label="Main">
          {NAV.map(([path, label, pages]) => {
            const active = pages.includes(page)
            return (
              <a key={label} href={`#/${path}`} aria-current={active ? 'page' : undefined}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium ${active ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`}>
                {label}
                {path === 'underwriting' && queueCount > 0 && (
                  <span className="rounded-full bg-sky-600 px-1.5 text-xs font-semibold text-white" aria-label={`${queueCount} waiting`}>{queueCount}</span>
                )}
              </a>
            )
          })}
          <span className="ml-2 flex items-center gap-1.5 text-xs text-slate-500" title="Backend API status">
            <span className={`h-2 w-2 rounded-full ${apiUp ? 'bg-emerald-500' : apiUp === false ? 'bg-rose-500' : 'bg-slate-300'}`} />
            {apiUp ? 'API online' : apiUp === false ? 'API offline' : 'Checking…'}
          </span>
        </nav>
      </div>
    </header>
  )
}
