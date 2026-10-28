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
        ? <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6">{content}</main>
        : <main className="flex-1"><ProductPicker /></main>}
      <Footer />
    </div>
  )
}

const NAV = [
  ['', 'Quote', ['', 'quote', 'quotes']],
  ['underwriting', 'Underwriting', ['underwriting']],
  ['rules', 'Rules', ['rules']],
  ['dashboard', 'Portfolio', ['dashboard']],
]

export function Logo({ light = false }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className={`grid h-9 w-9 place-items-center rounded-xl ${light ? 'bg-white text-steel-950' : 'bg-steel-950 text-white'}`}>
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 3l7.5 3v5.6c0 4.9-3.2 8.6-7.5 9.9-4.3-1.3-7.5-5-7.5-9.9V6z" />
          <circle cx="12" cy="11.5" r="2.2" fill="#3a6bff" stroke="none" />
        </svg>
      </span>
      <span className={`font-display text-lg font-medium tracking-tight ${light ? 'text-white' : 'text-steel-950'}`}>RiskSure</span>
    </span>
  )
}

function Header({ page, queueCount }) {
  const [apiUp, setApiUp] = useState(null)
  useEffect(() => {
    api.health().then(() => setApiUp(true)).catch(() => setApiUp(false))
  }, [])
  return (
    <header className="sticky top-0 z-30 border-b border-steel-200/60 bg-steel-50/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3.5 sm:flex-nowrap sm:px-6">
        <button onClick={() => navigate('/')} aria-label="RiskSure home" className="mr-auto sm:mr-0"><Logo /></button>
        {/* Phones: nav on its own full-width row; larger screens: inline. */}
        <nav className="no-scrollbar order-last flex w-full items-center justify-between gap-1 overflow-x-auto text-sm sm:order-none sm:w-auto sm:flex-1 sm:justify-center sm:gap-7" aria-label="Main">
          {NAV.map(([path, label, pages]) => {
            const active = pages.includes(page)
            return (
              <a key={label} href={`#/${path}`} aria-current={active ? 'page' : undefined}
                className={`flex shrink-0 items-center gap-1.5 px-1 py-1 transition-colors ${active ? 'text-steel-950' : 'text-steel-500 hover:text-steel-950'}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-brand-600' : 'bg-transparent'}`} aria-hidden="true" />
                {label}
                {path === 'underwriting' && queueCount > 0 && (
                  <span className="rounded-full bg-steel-950 px-1.5 text-[11px] font-medium text-white" aria-label={`${queueCount} waiting`}>{queueCount}</span>
                )}
              </a>
            )
          })}
        </nav>
        <span className="hidden items-center gap-1.5 text-xs text-steel-500 md:flex" title="Backend API status">
          <span className={`h-1.5 w-1.5 rounded-full ${apiUp ? 'bg-emerald-500' : apiUp === false ? 'bg-rose-500' : 'bg-steel-400'}`} />
          {apiUp ? 'Live' : apiUp === false ? 'Offline' : 'Connecting'}
        </span>
        <a href="#/" className="hidden h-9 items-center gap-1.5 rounded-full bg-steel-950 px-4 text-sm font-medium text-white hover:bg-steel-800 sm:inline-flex">
          Get a quote <Icon name="arrow" className="h-4 w-4" strokeWidth={1.8} />
        </a>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-16 bg-steel-950 text-steel-300">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
          <div>
            <Logo light />
            <p className="mt-6 max-w-lg font-display text-3xl font-light leading-tight text-white">
              Intelligence behind every <span className="text-steel-400">insured decision.</span>
            </p>
          </div>
          <p className="max-w-sm text-xs leading-relaxed text-steel-400">
            A portfolio project. All applicants, rates and models are synthetic and illustrative. This is not real actuarial pricing and not an insurance offer.
          </p>
        </div>
        <div className="mt-10 border-t border-white/10 pt-6 text-xs text-steel-500">
          <span>Config-driven P&amp;C quoting, rating and underwriting</span>
        </div>
      </div>
    </footer>
  )
}
