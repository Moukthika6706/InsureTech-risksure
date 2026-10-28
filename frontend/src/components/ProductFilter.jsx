// One row of product filter chips ("All" + every configured product).
import { useEffect, useState } from 'react'
import { api } from '../api'

export default function ProductFilter({ value, onChange }) {
  const [products, setProducts] = useState([])
  useEffect(() => {
    api.products().then(setProducts).catch(() => setProducts([]))
  }, [])
  const options = [{ code: '', name: 'All products' }, ...products]
  return (
    <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Product">
      {options.map((p) => (
        <button key={p.code} role="radio" aria-checked={value === p.code} onClick={() => onChange(p.code)}
          className={`rounded-full px-3 py-1 text-sm ${value === p.code ? 'bg-indigo-600 font-medium text-white' : 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50'}`}>
          {p.name}
        </button>
      ))}
    </div>
  )
}
