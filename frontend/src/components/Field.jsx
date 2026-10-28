// One form input, rendered from a product-config field:
//   { name, label, type: int|float|select|bool, options, min, max, help }
// The same component serves every product, so a new product YAML needs no UI code.
import { inrWords, isMoneyField } from '../format'

const inputClass = (error) =>
  `mt-1.5 block h-11 w-full rounded-xl border bg-white px-3.5 text-[15px] text-steel-900 shadow-sm transition focus:outline-none focus:ring-4 ${
    error ? 'border-rose-400 focus:ring-rose-100' : 'border-steel-300 hover:border-steel-400 focus:border-brand-500 focus:ring-brand-100'
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
        className={`mt-2 relative inline-flex h-7 w-12 items-center rounded-full transition-colors ${value ? 'bg-brand-600' : 'bg-steel-300'}`}>
        <span className={`inline-block h-6 w-6 transform rounded-full bg-white shadow transition ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
      </button>
    )
  } else if (field.type === 'select' && field.options.length <= 3) {
    // Few options: show them all as buttons (one click instead of opening a list).
    input = (
      <div className="mt-1.5 flex flex-wrap gap-2" role="radiogroup" id={id}>
        {field.options.map((o) => {
          const on = String(o.value) === String(value)
          return (
            <button type="button" key={String(o.value)} role="radio" aria-checked={on} onClick={() => onChange(o.value)}
              className={`min-h-11 rounded-xl border px-4 py-2 text-sm transition ${on ? 'border-brand-600 bg-brand-50 font-semibold text-brand-700 ring-1 ring-brand-600' : 'border-steel-300 bg-white text-steel-700 hover:border-steel-400'}`}>
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
      <label htmlFor={id} className="block text-sm font-semibold text-steel-800">{field.label}</label>
      {input}
      {error ? <p className="mt-1.5 text-xs font-medium text-rose-600">{error}</p>
        : hint.length > 0 && <p className="mt-1.5 text-xs leading-relaxed text-steel-500">{hint.join(' ')}</p>}
    </div>
  )
}
