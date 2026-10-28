// Top risk drivers as diverging bars from a centre line: right = raises risk,
// left = lowers it. Direction is also written in words, never colour alone.
import { readable } from '../format'

const UP = '#e34948'
const DOWN = '#2a78d6'

export default function RiskFactors({ factors, unit }) {
  if (!factors?.length) return null
  const max = Math.max(...factors.map((f) => Math.abs(f.impact)))
  return (
    <div>
      <ul className="space-y-2.5">
        {factors.map((f) => {
          const width = `${(Math.abs(f.impact) / max) * 50}%`
          const up = f.impact > 0
          return (
            <li key={f.field} className="text-sm">
              <div className="flex justify-between gap-3">
                <span className="text-steel-800">{f.label} <span className="text-steel-500">· {readable(f.field, f.value)}</span></span>
                <span className="shrink-0 text-xs text-steel-600">{up ? '▲ raises' : '▼ lowers'}</span>
              </div>
              <div className="relative mt-1 h-2 rounded-full bg-steel-100" aria-hidden="true">
                <span className="absolute inset-y-[-2px] left-1/2 w-px bg-steel-400" />
                <span className="absolute inset-y-0 rounded-full"
                  style={{ background: up ? UP : DOWN, width, [up ? 'left' : 'right']: '50%' }} />
              </div>
            </li>
          )
        })}
      </ul>
      <p className="mt-3 text-xs text-steel-500">
        {unit === 'points'
          ? 'Bar length = scorecard points added or removed.'
          : 'Bar length = SHAP contribution: how much each answer moved the predicted claim chance for this applicant.'}
      </p>
    </div>
  )
}
