import { useEffect, useState } from 'react'
import { api } from '../api'
import Icon from '../components/icons'
import RulePreview from '../components/RulePreview'
import { Badge, Button, Card, ErrorBox, PageHeader, Spinner } from '../components/ui'
import { titleCase, when } from '../format'
import { ruleSentence } from '../rules'

const ACTION_TONE = { decline: 'red', refer: 'blue', load: 'amber' }

// Rules screen: plain-English assistant (draft -> preview -> approve -> publish)
// and the list of active rules. The AI only drafts; publishing is the underwriter's call.
export default function RulesPage() {
  const [products, setProducts] = useState([])
  const [examples, setExamples] = useState([])
  const [rules, setRules] = useState(null)
  const [text, setText] = useState('')
  const [product, setProduct] = useState('')
  const [draft, setDraft] = useState(null)          // POST /rules/draft response
  const [ruleJson, setRuleJson] = useState('')      // editable rule
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [name, setName] = useState('')
  const [conflict, setConflict] = useState(false)
  const [published, setPublished] = useState(null)

  const loadRules = () => api.rules().then(setRules).catch(setError)
  useEffect(() => {
    api.products().then(setProducts).catch(() => {})
    api.ruleExamples().then(setExamples).catch(() => {})
    loadRules()
  }, [])

  const showRule = (rule, prev) => {
    setRuleJson(rule ? JSON.stringify(rule, null, 2) : '')
    setPreview(prev || null)
    setReviewed(false)
    setConflict(false)
  }

  const run = async (label, fn) => {
    setBusy(label)
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e)
    }
    setBusy('')
  }

  const onDraft = (e) => {
    e.preventDefault()
    setPublished(null)
    run('draft', async () => {
      const d = await api.draftRule(text, product)
      setDraft(d)
      showRule(d.rule, d.preview)
    })
  }

  const parsed = () => {
    try {
      return JSON.parse(ruleJson)
    } catch {
      throw new Error('The rule is not valid JSON. Check brackets and quotes.')
    }
  }

  const onPreview = () => run('preview', async () => {
    setReviewed(false)
    setPreview(await api.previewRule(parsed()))
  })

  const onPublish = (replace = false) => run('publish', async () => {
    try {
      const r = await api.publishRule({ rule: parsed(), approved: reviewed, published_by: name, source_text: text || null, replace })
      setPublished(r.published)
      setDraft(null)
      showRule(null)
      setText('')
      loadRules()
    } catch (e) {
      if (e.status === 409) setConflict(true)
      throw e
    }
  })

  const onDisable = (id) => run('disable', async () => {
    await api.disableRule(id)
    loadRules()
  })

  let currentRule = null
  try {
    currentRule = ruleJson ? JSON.parse(ruleJson) : null
  } catch { /* shown as an error when previewing */ }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Underwriter workspace" title="Underwriting rules"
        description="Describe a rule in plain English. The assistant drafts it in RiskSure's rule format, the engine validates it, and you see its impact on the sample book before you publish." />

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 font-semibold"><Icon name="sparkles" className="h-5 w-5 text-indigo-600" />Rule assistant</h2>
          <ol className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500" aria-label="How publishing works">
            {['Describe in English', 'Engine validates + previews', 'You approve and publish'].map((s, i) => (
              <li key={s} className="flex items-center gap-2">
                <span className="grid h-5 w-5 place-items-center rounded-full bg-slate-900 text-[11px] font-bold text-white">{i + 1}</span>{s}
                {i < 2 && <span className="text-slate-300">→</span>}
              </li>
            ))}
          </ol>
        </div>
        <form onSubmit={onDraft} className="mt-3 space-y-3">
          <label htmlFor="rule-text" className="sr-only">Rule in plain English</label>
          <textarea id="rule-text" rows={2} value={text} onChange={(e) => setText(e.target.value)} required minLength={5} maxLength={500}
            placeholder="e.g. Refer anyone under 21 who drives a sports car"
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-[15px] shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-100" />
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="rule-product" className="text-sm text-slate-600">Product</label>
            <select id="rule-product" value={product} onChange={(e) => setProduct(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="">Let the assistant decide</option>
              {products.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
            </select>
            <Button type="submit" disabled={busy !== '' || text.trim().length < 5}>{busy === 'draft' ? 'Drafting…' : 'Draft rule'}</Button>
          </div>
        </form>
        {examples.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="text-slate-500">Try:</span>
            {examples.slice(0, 4).map((ex) => (
              <button key={ex.text} onClick={() => setText(ex.text)} className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-700 hover:bg-slate-200">{ex.text}</button>
            ))}
          </div>
        )}
      </Card>

      {published && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800" role="status">
          Published <b>{published.id}</b>. New quotes use it from now on.
        </div>
      )}
      <ErrorBox error={error} />

      {draft && (
        <Card className="p-6">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-semibold">Draft</h2>
            {draft.source === 'ai'
              ? <Badge tone="indigo">Drafted by AI ({draft.model})</Badge>
              : <Badge tone="amber">AI unavailable: pre-written example</Badge>}
            {draft.attempts > 1 && <Badge>repaired after validation</Badge>}
          </div>
          {draft.notes && <p className="mt-2 text-sm text-slate-600">{draft.notes}</p>}
          {!draft.feasible && (
            <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm">The assistant could not express this with RiskSure's data, so no rule was drafted.</p>
          )}
          {draft.source === 'fallback' && draft.examples.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="text-slate-500">Other examples:</span>
              {draft.examples.map((ex) => (
                <button key={ex.rule.id} onClick={() => run('preview', async () => { showRule(ex.rule, await api.previewRule(ex.rule)) })}
                  className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-700 hover:bg-slate-200">{ex.text}</button>
              ))}
            </div>
          )}

          {ruleJson && (
            <div className="mt-4 grid gap-5 lg:grid-cols-2">
              <div>
                {currentRule && <p className="rounded-lg bg-indigo-50 p-3 text-sm font-medium text-indigo-900">{ruleSentence(currentRule)}</p>}
                {draft.errors?.length > 0 && <ErrorBox error={{ message: 'This draft did not pass validation. Edit it below.', errors: draft.errors }} />}
                <label htmlFor="rule-json" className="mt-3 block text-sm font-medium">Rule (you can edit it)</label>
                <textarea id="rule-json" rows={16} spellCheck={false} value={ruleJson}
                  onChange={(e) => { setRuleJson(e.target.value); setPreview(null); setReviewed(false) }}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-xs" />
                <Button variant="secondary" className="mt-2" onClick={onPreview} disabled={busy !== ''}>
                  {busy === 'preview' ? 'Checking…' : 'Validate and preview impact'}
                </Button>
              </div>
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Impact on the sample book</h3>
                <div className="mt-3">
                  {busy === 'preview' ? <Spinner label="Running the rule on the sample book…" />
                    : preview ? <RulePreview preview={preview} />
                    : <p className="text-sm text-slate-600">Run the preview to see the impact before publishing.</p>}
                </div>
              </div>
            </div>
          )}

          {preview && (
            <div className="mt-6 space-y-3 border-t border-slate-100 pt-5">
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" className="mt-0.5 h-4 w-4 accent-indigo-600" checked={reviewed} onChange={(e) => setReviewed(e.target.checked)} />
                I have reviewed this rule and its impact preview, and approve publishing it.
              </label>
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label htmlFor="publisher" className="block text-sm font-medium">Your name</label>
                  <input id="publisher" value={name} onChange={(e) => setName(e.target.value)} className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                </div>
                <Button onClick={() => onPublish(false)} disabled={!reviewed || name.trim().length < 2 || busy !== ''}>
                  {busy === 'publish' ? 'Publishing…' : 'Publish rule'}
                </Button>
                {conflict && <Button variant="secondary" onClick={() => onPublish(true)} disabled={!reviewed || busy !== ''}>Replace the existing rule</Button>}
              </div>
            </div>
          )}
        </Card>
      )}

      <Card className="p-6">
        <h2 className="font-semibold">Active rules</h2>
        <p className="mt-1 text-sm text-slate-600">From config/rules.yaml, plus rules published here (stored in the database).</p>
        {!rules ? <Spinner label="Loading rules…" /> : (
          <ul className="mt-4 divide-y divide-slate-100">
            {rules.map((r) => (
              <li key={r.id} className={`py-3 ${r.enabled === false ? 'opacity-50' : ''}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={ACTION_TONE[r.action]}>{r.action === 'load' ? `${r.load_pct > 0 ? '+' : ''}${r.load_pct}%` : r.action}</Badge>
                  <span className="font-medium">{r.description}</span>
                  <span className="text-xs text-slate-500">{r.product === '*' ? 'All products' : titleCase(r.product)}</span>
                  {r.source === 'published'
                    ? <Badge tone="indigo">Published by {r.published_by}, {when(r.published_at)}</Badge>
                    : <Badge>rules.yaml</Badge>}
                  {r.enabled === false && <Badge>Disabled</Badge>}
                </div>
                <p className="mt-1 text-sm text-slate-600">{ruleSentence(r)}</p>
                {r.source === 'published' && r.enabled !== false && (
                  <button onClick={() => onDisable(r.id)} className="mt-1 text-xs text-rose-700 hover:underline">Disable</button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
