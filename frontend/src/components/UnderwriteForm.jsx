// Underwriter decision on a referred quote: approve (optionally at a different
// premium) or decline. A note is required: it goes into the audit trail.
import { useState } from 'react'
import { api } from '../api'
import { Button, ErrorBox } from './ui'
import { inr } from '../format'

const NAME_KEY = 'risksure.underwriter'

function savedName() {
  try {
    return localStorage.getItem(NAME_KEY) || ''
  } catch {
    return ''
  }
}

export default function UnderwriteForm({ quote, onDone }) {
  const [action, setAction] = useState('approve')
  const [override, setOverride] = useState('')
  const [note, setNote] = useState('')
  const [name, setName] = useState(savedName)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      localStorage.setItem(NAME_KEY, name)
    } catch { /* private mode: name just isn't remembered */ }
    try {
      const updated = await api.underwrite(quote.id, {
        action, note, actor: name || 'underwriter',
        override_premium: action === 'approve' && override !== '' ? Number(override) : null,
      })
      onDone(updated)
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  const choice = (value, label, tone) => (
    <button type="button" role="radio" aria-checked={action === value} onClick={() => setAction(value)}
      className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${action === value ? tone : 'border-slate-300 bg-white text-slate-700'}`}>
      {label}
    </button>
  )

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="flex gap-2" role="radiogroup" aria-label="Decision">
        {choice('approve', 'Approve', 'border-emerald-600 bg-emerald-50 text-emerald-800')}
        {choice('decline', 'Decline', 'border-rose-600 bg-rose-50 text-rose-800')}
      </div>
      {action === 'approve' && (
        <div>
          <label htmlFor={`ov-${quote.id}`} className="block text-sm font-medium">Premium override (optional)</label>
          <input id={`ov-${quote.id}`} type="number" min="1" step="1" value={override} onChange={(e) => setOverride(e.target.value)}
            placeholder={`System price ${inr(quote.premium)}`}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm sm:w-64" />
        </div>
      )}
      <div>
        <label htmlFor={`note-${quote.id}`} className="block text-sm font-medium">Reason for your decision</label>
        <textarea id={`note-${quote.id}`} rows={2} required minLength={3} value={note} onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Parent is the main driver; accept with a higher premium"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor={`uw-${quote.id}`} className="block text-sm font-medium">Your name</label>
          <input id={`uw-${quote.id}`} value={name} onChange={(e) => setName(e.target.value)} placeholder="underwriter"
            className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <Button type="submit" disabled={busy || note.trim().length < 3}>
          {busy ? 'Saving…' : action === 'approve' ? 'Approve quote' : 'Decline quote'}
        </Button>
      </div>
      <ErrorBox error={error} />
    </form>
  )
}
