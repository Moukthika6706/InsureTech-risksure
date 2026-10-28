import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { navigate, useRoute } from './router'
import Icon from './components/icons'
import Dashboard from './pages/Dashboard'
import ProductPicker from './pages/ProductPicker'
import QuoteResult from './pages/QuoteResult'
import QuoteWizard from './pages/QuoteWizard'
import RulesPage from './pages/RulesPage'
import UnderwritingQueue from './pages/UnderwritingQueue'

// App shell: header + hash routes.
//   #/                 landing / product picker   #/underwriting   underwriter queue
//   #/quote/<product>  quote wizard               #/rules          rules + assistant
//   #/quotes/<id>      quote result               #/dashboard      portfolio dashboard
export default function App() {
  const [page = '', param] = useRoute()
  const [queueCount, setQueueCount] = useState(null)
  const refreshQueue = useCallback(() => {
    api.queue().then((q) => setQueueCount(q.length)).catch(() => setQueueCount(null))
  }, [])
  useEffect(refreshQueue, [page, param, refreshQueue])

  const content = page === 'quote' && param ? <QuoteWizard key={param} productCode={param} />
    : page === 'quotes' && param ? <QuoteResult key={param} quoteId={param} />
    : page === 'underwriting' ? <UnderwritingQueue onChange={refreshQueue} />
    : page === 'rules' ? <RulesPage />
    : page === 'dashboard' ? <Dashboard />
    : null

  return (
    <div className="flex min-h-screen flex-col">
      <Header page={page} queueCount={queueCount} />
      {content
        ? <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">{content}</main>
        : <main className="flex-1"><ProductPicker /></main>}
      <Footer />
    </div>
  )
}

const NAV = [
  ['', 'Quote', ['', 'quote', 'quotes']],
  ['underwriting', 'Underwriting', ['underwriting']],
  ['rules', 'Rules', ['rules']],
  ['dashboard', 'Dashboard', ['dashboard']],
]

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-500/30">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 3l7.5 3v5.6c0 4.9-3.2 8.6-7.5 9.9-4.3-1.3-7.5-5-7.5-9.9V6z" /><path d="M8.8 12l2.3 2.3 4.2-4.4" />
        </svg>
      </span>
      <span className="font-display text-lg font-bold tracking-tight text-slate-900">RiskSure</span>
    </span>
  )
}

function Header({ page, queueCount }) {
  const [apiUp, setApiUp] = useState(null)
  useEffect(() => {
    api.health().then(() => setApiUp(true)).catch(() => setApiUp(false))
  }, [])
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:flex-nowrap sm:px-6">
        <button onClick={() => navigate('/')} aria-label="RiskSure home" className="mr-auto sm:mr-0"><Logo /></button>
        {/* Phones: nav takes its own full-width row; larger screens: inline. */}
        <nav className="no-scrollbar order-last flex w-full items-center justify-between gap-0.5 overflow-x-auto text-sm sm:order-none sm:w-auto sm:flex-1 sm:justify-start sm:gap-1" aria-label="Main">
          {NAV.map(([path, label, pages]) => {
            const active = pages.includes(page)
            return (
              <a key={label} href={`#/${path}`} aria-current={active ? 'page' : undefined}
                className={`flex shrink-0 items-center gap-1.5 rounded-lg px-2 py-1.5 font-medium transition-colors sm:px-3 ${active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}>
                {label}
                {path === 'underwriting' && queueCount > 0 && (
                  <span className={`rounded-full px-1.5 text-[11px] font-semibold ${active ? 'bg-white/20 text-white' : 'bg-indigo-600 text-white'}`}
                    aria-label={`${queueCount} waiting`}>{queueCount}</span>
                )}
              </a>
            )
          })}
        </nav>
        <span className="hidden items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 md:flex" title="Backend API status">
          <span className={`h-1.5 w-1.5 rounded-full ${apiUp ? 'bg-emerald-500' : apiUp === false ? 'bg-rose-500' : 'bg-slate-400'}`} />
          {apiUp ? 'API online' : apiUp === false ? 'API offline' : 'Connecting'}
        </span>
        <a href="#/" className="hidden h-9 items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 text-sm font-semibold text-white shadow-sm shadow-indigo-600/20 hover:bg-indigo-500 sm:inline-flex">
          Get a quote <Icon name="arrow" className="h-4 w-4" strokeWidth={2} />
        </a>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <Logo />
          <p className="mt-3 max-w-md text-xs leading-relaxed">
            A portfolio project. All applicants, rates and models are synthetic and illustrative. This is not real actuarial pricing and not an insurance offer.
          </p>
        </div>
        <p className="text-xs">FastAPI · scikit-learn · SHAP · React · Tailwind · Claude</p>
      </div>
    </footer>
  )
}
