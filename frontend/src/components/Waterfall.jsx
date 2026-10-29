// Premium waterfall: how the price is built step by step.
// Each bar floats from the running total before a step to the total after it
// (an invisible "base" bar underneath does the floating), ending in the premium.
import { useEffect, useState } from 'react'
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { inr } from '../format'

// Validated with the dataviz palette checker (adjacent + all pairs, light surface):
// levels and increases/decreases stay distinguishable with colour-vision deficiency.
const COLORS = { level: '#eda100', up: '#e34948', down: '#2a78d6' }
const KIND_TEXT = { coverage: 'Cover', factor: 'Rating factor', modifier: 'Discount / surcharge',
  underwriting: 'Underwriting', minimum: 'Minimum premium' }

const compact = (n) => (n >= 1e5 ? `₹${+(n / 1e5).toFixed(1)}L` : n >= 1e3 ? `₹${Math.round(n / 1e3)}k` : `₹${n}`)

function toBars(steps, premium) {
  const rows = steps.filter((s) => s.amount_change !== 0).map((s) => {
    const end = s.running_total
    const start = end - s.amount_change
    return {
      key: `${s.step}-${s.code}`, label: s.label, detail: s.detail, kind: s.kind, multiplier: s.multiplier,
      change: s.amount_change, total: end, base: Math.min(start, end), size: Math.abs(s.amount_change),
      color: s.kind === 'coverage' ? COLORS.level : s.amount_change > 0 ? COLORS.up : COLORS.down,
    }
  })
  rows.push({ key: 'total', label: 'Premium', kind: 'total', change: premium, total: premium,
    base: 0, size: premium, color: COLORS.level, isTotal: true })
  return rows
}

// True on phone-width screens, where the label column must shrink.
function useNarrow() {
  const query = '(max-width: 639px)'
  const [narrow, setNarrow] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const m = window.matchMedia(query)
    const on = () => setNarrow(m.matches)
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [])
  return narrow
}

export default function Waterfall({ steps, premium, highlight }) {
  const [view, setView] = useState('chart')
  const narrow = useNarrow()
  // Respect the OS 'reduce motion' setting: draw bars without the grow-in animation.
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const rows = toBars(steps, premium)
  const neutral = steps.filter((s) => s.amount_change === 0).length

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Legend />
        <div className="inline-flex rounded-lg bg-steel-100 p-0.5 text-xs" role="tablist" aria-label="Breakdown view">
          {['chart', 'table'].map((v) => (
            <button key={v} role="tab" aria-selected={view === v} onClick={() => setView(v)}
              className={`rounded-md px-2.5 py-1 font-medium capitalize ${view === v ? 'bg-white shadow-sm text-steel-900' : 'text-steel-500'}`}>
              {v}
            </button>
          ))}
        </div>
      </div>

      {view === 'chart' ? (
        <div className={`mt-3 rounded-lg p-2 ${highlight ? 'ring-2 ring-brand-200' : ''}`}>
          <ResponsiveContainer width="100%" height={rows.length * 30 + 36}>
            <BarChart data={rows} layout="vertical" margin={{ top: 4, right: narrow ? 48 : 64, bottom: 4, left: 0 }} barCategoryGap={2}>
              <XAxis type="number" tickFormatter={compact} tick={{ fontSize: 11, fill: '#64748b' }}
                axisLine={false} tickLine={false} domain={[0, 'auto']} tickCount={5} />
              <YAxis type="category" dataKey="label" width={narrow ? 88 : 150} interval={0}
                tick={{ fontSize: narrow ? 11 : 12, fill: '#334155' }} axisLine={false} tickLine={false} />
              <Tooltip content={<StepTooltip />} cursor={{ fill: '#f1f5f9' }} isAnimationActive={false} />
              <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
              <Bar dataKey="size" stackId="w" radius={4} animationDuration={300} isAnimationActive={!reduceMotion}>
                {rows.map((r) => <Cell key={r.key} fill={r.color} />)}
                <LabelList dataKey="total" content={<TotalLabel rows={rows} />} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {neutral > 0 && (
            <p className="mt-1 text-xs text-steel-500">{neutral} step{neutral > 1 ? 's' : ''} at ×1 (no effect) not drawn; see the table.</p>
          )}
        </div>
      ) : (
        <BreakdownTable steps={steps} premium={premium} />
      )}
    </div>
  )
}

function Legend() {
  const items = [['level', 'Cover & premium'], ['up', 'Raises price'], ['down', 'Lowers price']]
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-steel-600">
      {items.map(([k, label]) => (
        <li key={k} className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: COLORS[k] }} aria-hidden="true" />
          {label}
        </li>
      ))}
    </ul>
  )
}

// Direct label on the final premium bar only (selective labelling).
function TotalLabel({ rows, x, y, width, height, index }) {
  if (!rows[index]?.isTotal) return null
  return (
    <text x={x + width + 6} y={y + height / 2} dominantBaseline="middle" fontSize={12} fontWeight={600} fill="#0f172a">
      {inr(rows[index].total)}
    </text>
  )
}

function StepTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  return (
    <div className="max-w-64 rounded-lg border border-steel-200 bg-white p-3 text-xs shadow-lg">
      <p className="font-semibold text-steel-900">{r.label}</p>
      {r.detail && <p className="mt-0.5 text-steel-500">{r.detail}</p>}
      {!r.isTotal && (
        <p className="mt-2 text-steel-700">
          {KIND_TEXT[r.kind]}{r.multiplier != null && <> · ×{r.multiplier}</>} ·{' '}
          <b>{r.change > 0 ? '+' : '−'}{inr(Math.abs(r.change))}</b>
        </p>
      )}
      <p className="mt-1 text-steel-700">{r.isTotal ? 'Annual premium' : 'Running total'}: <b>{inr(r.total)}</b></p>
    </div>
  )
}

export function BreakdownTable({ steps, premium }) {
  return (
    <table className="mt-3 w-full text-sm">
      <caption className="sr-only">Premium breakdown, step by step</caption>
      <tbody>
        {steps.map((s) => (
          <tr key={`${s.step}-${s.code}`} className="border-b border-steel-100 align-top">
            <td className="py-2 pr-2">
              <span className="font-medium">{s.label}</span>
              <span className="block text-xs text-steel-500">{s.detail}</span>
            </td>
            <td className="py-2 text-right text-steel-500">{s.multiplier != null ? `×${s.multiplier}` : ''}</td>
            <td className={`py-2 pl-3 text-right tabular-nums ${s.amount_change < 0 ? 'text-blue-700' : ''}`}>
              {s.amount_change === 0 ? '—' : `${s.amount_change > 0 ? '+' : '−'}${inr(Math.abs(s.amount_change))}`}
            </td>
          </tr>
        ))}
        <tr>
          <td className="pt-3 font-semibold">Premium</td>
          <td />
          <td className="pt-3 text-right font-semibold tabular-nums">{inr(premium)}</td>
        </tr>
      </tbody>
    </table>
  )
}
