import { From } from './agents.jsx'
import { CATEGORIES, STAGES } from './labels.js'

const IDS = ['n1', 'n2', 'n3', 'n4', 'n5']

// The Need Analyst's draft, editable; only the card staff confirm is searched.
export default function NeedCard({ draft, card, setCard, onSearch, busy, searched }) {
  const set = (field, value) => setCard({ ...card, [field]: value })
  const setNeed = (id, field, value) => set('needs', card.needs.map((n) => (n.id === id ? { ...n, [field]: value } : n)))
  const addNeed = () => set('needs', [...card.needs, { id: IDS.find((id) => !card.needs.some((n) => n.id === id)), text: '', category: null }])

  return (
    <form className="animate-fade-up" onSubmit={(e) => { e.preventDefault(); onSearch(card) }} aria-label="Need card">
      <From ids={['analyst']} />
      <div className="card space-y-5">
        {draft.ignored.length > 0 && (
          <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-600/20 ring-inset dark:bg-amber-400/10 dark:text-amber-100">
            <p className="font-medium">Left out, addressed to an AI system:</p>
            <ul className="mt-1 list-disc pl-5">{draft.ignored.map((s) => <li key={s}>“{s}”</li>)}</ul>
          </div>
        )}
        <div className="grid gap-3 sm:grid-cols-3">
          <label><span className="label">Sector</span><input className="field" value={card.sector ?? ''} onChange={(e) => set('sector', e.target.value || null)} maxLength={100} /></label>
          <label><span className="label">Product</span><input className="field" value={card.product ?? ''} onChange={(e) => set('product', e.target.value || null)} maxLength={200} /></label>
          <label><span className="label">Stage</span>
            <select className="field" value={card.stage ?? ''} onChange={(e) => set('stage', e.target.value || null)}>
              <option value="">Not set</option>
              {Object.entries(STAGES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
        </div>
        <fieldset>
          <legend className="label">Needs</legend>
          <ol className="space-y-2">
            {card.needs.map((n, i) => (
              <li key={n.id} className="rounded-xl border border-line/10 bg-surface p-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span aria-hidden="true" className="grid size-7 shrink-0 place-items-center rounded-full bg-card text-sm font-semibold text-brand-700 tabular-nums dark:text-brand-200">{i + 1}</span>
                  <label className="min-w-0 flex-[1_1_14rem]"><span className="sr-only">Need {i + 1}</span>
                    <input className="field bg-card" value={n.text} onChange={(e) => setNeed(n.id, 'text', e.target.value)} required minLength={3} maxLength={300} />
                  </label>
                  <label className="min-w-0 flex-[1_1_12rem] sm:flex-none"><span className="sr-only">Category for need {i + 1}</span>
                    <select className="field bg-card" value={n.category ?? ''} onChange={(e) => setNeed(n.id, 'category', e.target.value || null)}>
                      <option value="">Any category</option>
                      {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </label>
                  <button type="button" className="grid size-10 place-items-center rounded-full text-ink/55 transition-colors hover:bg-card hover:text-ink disabled:opacity-30"
                    onClick={() => set('needs', card.needs.filter((m) => m.id !== n.id))} disabled={card.needs.length === 1} aria-label={`Remove need ${i + 1}`}>
                    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4 fill-none stroke-current stroke-[1.8] [stroke-linecap:round]"><path d="M6 6l12 12M18 6 6 18" /></svg>
                  </button>
                </div>
                {draft.sources[n.id] && (
                  <ul className="mt-2 ml-9 space-y-0.5 text-sm text-ink/65" aria-label={`Cited from the business model for need ${i + 1}`}>
                    {draft.sources[n.id].map((s) => <li key={s}>“{draft.sentences[s - 1]}”</li>)}
                  </ul>
                )}
              </li>
            ))}
          </ol>
        </fieldset>
        <div className="flex flex-wrap justify-between gap-2">
          <button type="button" className="btn-ghost" onClick={addNeed} disabled={card.needs.length === IDS.length}>Add need</button>
          <button className="btn" disabled={busy}>{searched ? 'Search again' : 'Confirm and search'}</button>
        </div>
      </div>
    </form>
  )
}
