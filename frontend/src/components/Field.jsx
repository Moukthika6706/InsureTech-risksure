// One form input, rendered from a product-config field:
//   { name, label, type: int|float|select|bool, options, min, max, help }
// The same component serves every product, so a new product YAML needs no UI code.
import { inrWords, isMoneyField } from '../format'

const inputClass = (error) =>
  `mt-1 block w-full rounded-lg border bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 ${
    error ? 'border-rose-400 focus:ring-rose-200' : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-100'
  }`

export default function Field({ field, value, onChange, error }) {
  const id = `f-${field.name}`
  const hint = [
    field.help,
    isMoneyField(field) && value !== '' && !Number.isNaN(Number(value)) ? `= ${inrWords(value)}` : null,
  ].filter(Boolean)

  let input
  if (field.type === 'bool') {
    input = (
      <button type="button" role="switch" aria-checked={!!value} id={id} onClick={() => onChange(!value)}
        className={`mt-1 relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-indigo-600' : 'bg-slate-300'}`}>
        <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
      </button>
    )
  } else if (field.type === 'select' && field.options.length <= 3) {
    // Few options: show them all as buttons (one click instead of opening a list).
    input = (
      <div className="mt-1 flex flex-wrap gap-2" role="radiogroup" id={id}>
        {field.options.map((o) => {
          const on = String(o.value) === String(value)
          return (
            <button type="button" key={String(o.value)} role="radio" aria-checked={on} onClick={() => onChange(o.value)}
              className={`rounded-lg border px-3 py-1.5 text-sm ${on ? 'border-indigo-600 bg-indigo-50 font-medium text-indigo-700' : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'}`}>
              {o.label}
            </button>
          )
        })}
      </div>
    )
  } else if (field.type === 'select') {
    input = (
      <select id={id} className={inputClass(error)} value={String(value)}
        onChange={(e) => onChange(field.options.find((o) => String(o.value) === e.target.value)?.value)}>
        {field.options.map((o) => <option key={String(o.value)} value={String(o.value)}>{o.label}</option>)}
      </select>
    )
  } else {
    input = (
      <input id={id} type="number" inputMode={field.type === 'int' ? 'numeric' : 'decimal'}
        step={field.type === 'int' ? 1 : 'any'} min={field.min ?? undefined} max={field.max ?? undefined}
        className={inputClass(error)} value={value} onChange={(e) => onChange(e.target.value)} />
    )
  }

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-800">{field.label}</label>
      {input}
      {error ? <p className="mt-1 text-xs text-rose-600">{error}</p>
        : hint.length > 0 && <p className="mt-1 text-xs text-slate-500">{hint.join(' ')}</p>}
    </div>
  )
}
