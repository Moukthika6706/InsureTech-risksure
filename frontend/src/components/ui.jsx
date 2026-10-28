// Shared UI pieces: the design system every page uses (Tailwind).
const TONES = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  amber: 'bg-amber-50 text-amber-800 ring-amber-600/25',
  blue: 'bg-sky-50 text-sky-700 ring-sky-600/20',
  red: 'bg-rose-50 text-rose-700 ring-rose-600/20',
  indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20',
  slate: 'bg-slate-100 text-slate-700 ring-slate-500/20',
}

export function Badge({ tone = 'slate', dot = false, children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  )
}

export function Card({ className = '', children, ...props }) {
  return (
    <div className={`rounded-2xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgb(15_23_42/0.04),0_4px_16px_-8px_rgb(15_23_42/0.08)] ${className}`} {...props}>
      {children}
    </div>
  )
}

// Card with a titled header row (title, optional description and right-side actions).
export function Panel({ title, description, actions, className = '', children }) {
  return (
    <Card className={className}>
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 pt-5 sm:px-6">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
        </div>
        {actions}
      </div>
      <div className="px-4 pt-4 pb-6 sm:px-6">{children}</div>
    </Card>
  )
}

export function Button({ variant = 'primary', size = 'md', className = '', ...props }) {
  const styles = {
    primary: 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20 hover:bg-indigo-500 disabled:bg-indigo-300 disabled:shadow-none',
    dark: 'bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-400',
    secondary: 'bg-white text-slate-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:text-slate-400',
    ghost: 'text-slate-600 hover:bg-slate-100',
  }
  const sizes = { sm: 'h-8 px-3 text-sm', md: 'h-10 px-4 text-sm', lg: 'h-12 px-6 text-base' }
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors disabled:cursor-not-allowed ${sizes[size]} ${styles[variant]} ${className}`}
      {...props}
    />
  )
}

// Top of every page: small eyebrow, title, description, optional actions.
export function PageHeader({ eyebrow, title, description, actions, back }) {
  return (
    <div className="mb-8">
      {back}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          {eyebrow && <p className="text-sm font-semibold text-indigo-600">{eyebrow}</p>}
          <h1 className="mt-1 text-3xl font-bold text-slate-900 sm:text-[2rem]">{title}</h1>
          {description && <p className="mt-2 text-base text-slate-600">{description}</p>}
        </div>
        {actions}
      </div>
    </div>
  )
}

export function Stat({ label, value, sub, icon, href }) {
  const body = (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgb(15_23_42/0.04)] transition hover:border-slate-300">
      <dt className="flex items-center gap-2 text-sm text-slate-500">{icon}{label}</dt>
      <dd className="mt-2 font-display text-2xl font-bold tabular-nums tracking-tight text-slate-900">{value}</dd>
      {sub && <dd className="mt-0.5 text-xs text-slate-500">{sub}</dd>}
    </div>
  )
  return href ? <a href={href} className="block">{body}</a> : body
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center gap-3 py-10 text-slate-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
      {label}
    </div>
  )
}

export function EmptyState({ title, children }) {
  return (
    <Card className="px-6 py-12 text-center">
      <p className="font-display text-lg font-semibold text-slate-900">{title}</p>
      <div className="mt-1 text-sm text-slate-600">{children}</div>
    </Card>
  )
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
      <p className="font-medium">{error.message || String(error)}</p>
      {error.errors?.length > 0 && (
        <ul className="mt-2 list-disc pl-5">
          {error.errors.map((e) => <li key={e}>{e}</li>)}
        </ul>
      )}
      {onRetry && <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>Try again</Button>}
    </div>
  )
}

export function BackLink({ href = '#/', children }) {
  return (
    <a href={href} className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-indigo-600">
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
      {children}
    </a>
  )
}
