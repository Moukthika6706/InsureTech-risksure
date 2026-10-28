// Shared UI pieces: the design system every page uses (Tailwind).
// Editorial style: quiet surfaces, large radii, pill buttons, light display type.
const TONES = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  amber: 'bg-amber-50 text-amber-800 ring-amber-600/25',
  blue: 'bg-sky-50 text-sky-700 ring-sky-600/20',
  red: 'bg-rose-50 text-rose-700 ring-rose-600/20',
  indigo: 'bg-brand-50 text-brand-700 ring-brand-600/20',
  slate: 'bg-steel-100 text-steel-700 ring-steel-500/20',
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
    <div className={`rounded-[1.5rem] border border-steel-200/70 bg-white shadow-[0_1px_2px_rgb(17_23_29/0.04)] ${className}`} {...props}>
      {children}
    </div>
  )
}

// Card with a titled header row (title, optional description and right-side actions).
export function Panel({ title, description, actions, className = '', children }) {
  return (
    <Card className={className}>
      <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-6 sm:px-7">
        <div>
          <h2 className="text-lg font-medium text-steel-950">{title}</h2>
          {description && <p className="mt-0.5 text-sm text-steel-500">{description}</p>}
        </div>
        {actions}
      </div>
      <div className="px-5 pt-5 pb-7 sm:px-7">{children}</div>
    </Card>
  )
}

export function Button({ variant = 'primary', size = 'md', className = '', ...props }) {
  const styles = {
    primary: 'bg-brand-600 text-white hover:bg-brand-500 disabled:bg-brand-300',
    dark: 'bg-steel-950 text-white hover:bg-steel-800 disabled:bg-steel-400',
    secondary: 'bg-white text-steel-900 ring-1 ring-inset ring-steel-300 hover:bg-steel-50 disabled:text-steel-400',
    ghost: 'text-steel-600 hover:bg-steel-100',
  }
  const sizes = { sm: 'h-8 px-3.5 text-sm', md: 'h-10 px-5 text-sm', lg: 'h-12 px-7 text-[15px]' }
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors disabled:cursor-not-allowed ${sizes[size]} ${styles[variant]} ${className}`}
      {...props}
    />
  )
}

// Small spaced-out label used above titles.
export function Eyebrow({ children, className = '' }) {
  return <p className={`text-xs font-medium uppercase tracking-[0.18em] text-steel-500 ${className}`}>{children}</p>
}

// Top of every page: eyebrow, large light title, description, optional actions.
export function PageHeader({ eyebrow, title, description, actions, back }) {
  return (
    <div className="mb-10">
      {back}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
          <h1 className="mt-2 text-4xl font-light text-steel-950 sm:text-5xl">{title}</h1>
          {description && <p className="mt-3 text-base leading-relaxed text-steel-600">{description}</p>}
        </div>
        {actions}
      </div>
    </div>
  )
}

export function Stat({ label, value, sub, icon, href }) {
  const body = (
    <div className="flex h-full flex-col rounded-[1.5rem] border border-steel-200/70 bg-white p-5 transition hover:border-steel-300">
      <dt className="flex items-center gap-2 text-sm text-steel-500">{icon}{label}</dt>
      <dd className="mt-3 font-display text-3xl font-light tabular-nums tracking-tight text-steel-950">{value}</dd>
      {sub && <dd className="mt-1 text-xs text-steel-500">{sub}</dd>}
    </div>
  )
  return href ? <a href={href} className="block">{body}</a> : body
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center gap-3 py-10 text-steel-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-steel-200 border-t-brand-600" />
      {label}
    </div>
  )
}

export function EmptyState({ title, children }) {
  return (
    <Card className="px-6 py-14 text-center">
      <p className="font-display text-2xl font-light text-steel-950">{title}</p>
      <div className="mt-2 text-sm text-steel-600">{children}</div>
    </Card>
  )
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
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
    <a href={href} className="mb-6 inline-flex items-center gap-1.5 text-sm text-steel-500 hover:text-steel-950">
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
      {children}
    </a>
  )
}
