import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { CATEGORIES, STAGES } from './labels.js'

const IDS = ['n1', 'n2', 'n3', 'n4', 'n5']
const SEARCHING = 'Searching research units in Bern and checking each explanation against its sources…'

export default function Search({ domain, run, busy, onResult }) {
  const [query, setQuery] = useState('')
  const [description, setDescription] = useState('')
  const [draft, setDraft] = useState(null)
  const [card, setCard] = useState(null)
  const cardRef = useRef(null)
  useEffect(() => { if (draft) cardRef.current.scrollIntoView() }, [draft])

  const search = (c) => run(SEARCHING, async () => onResult(await api(`/api/${domain}/search`, { card: c })))
  const draftCard = () => run('Apertus is drafting the need card from the business model…', async () => {
    const d = await api(`/api/${domain}/need-card/draft`, { description })
    setDraft(d)
    setCard(d.card)
  })
  const set = (field, value) => setCard({ ...card, [field]: value })
  const setNeed = (id, field, value) => set('needs', card.needs.map((n) => (n.id === id ? { ...n, [field]: value } : n)))
  const addNeed = () => set('needs', [...card.needs, { id: IDS.find((id) => !card.needs.some((n) => n.id === id)), text: '', category: null }])
  const submit = (fn) => (e) => { e.preventDefault(); fn() }

  return (
    <div className="space-y-8">
      <section className="animate-fade-up space-y-5" aria-labelledby="model-title">
        <div className="max-w-2xl">
          <p className="kicker">New enquiry</p>
          <h2 id="model-title" className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Find collaborators in Bern for a company</h2>
          <p className="hint mt-2 text-[15px]">Paste the business model the company sent. Apertus drafts a need card from it; you check and edit the card before anything is searched.</p>
        </div>
        <form onSubmit={submit(draftCard)}>
          <label htmlFor="model" className="sr-only">Company business model (plain text)</label>
          <div className="rounded-3xl border border-line/10 bg-card p-2 shadow-panel transition-shadow focus-within:ring-2 focus-within:ring-brand-500/60">
            <textarea id="model" rows={7} className="block w-full resize-y bg-transparent px-3 py-2 leading-relaxed outline-none placeholder:text-ink/45"
              value={description} onChange={(e) => setDescription(e.target.value)} required minLength={20} maxLength={5000}
              placeholder="Paste the company's business model here (plain text)…" />
            <div className="flex items-center justify-between gap-3 border-t border-line/10 px-3 pt-2">
              <span className="text-xs text-ink/55 tabular-nums">{description.length} / 5000</span>
              <button className="btn" disabled={busy}>Draft need card</button>
            </div>
          </div>
        </form>
        <form onSubmit={submit(() => search({ needs: [{ id: 'n1', text: query }] }))}>
          <label htmlFor="quick" className="label text-ink/70">Or a quick keyword search</label>
          <div className="flex items-center gap-2 rounded-full border border-line/10 bg-card p-1.5 pl-4 shadow-soft focus-within:ring-2 focus-within:ring-brand-500/60">
            <input id="quick" className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-ink/45" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. clinical validation of a glucose sensor" required minLength={3} maxLength={300} />
            <button className="btn" disabled={busy}>Search</button>
          </div>
        </form>
      </section>

      {card && (
        <form ref={cardRef} className="card animate-fade-up scroll-mt-20 space-y-6" onSubmit={submit(() => search(card))} aria-labelledby="card-title">
          <div>
            <p className="kicker">Drafted by Apertus</p>
            <h2 id="card-title" className="mt-1 text-xl font-semibold tracking-tight">Check the need card</h2>
            <p className="hint mt-1">Edit the draft where needed. Only the card you confirm is searched.</p>
          </div>
          {draft.ignored.length > 0 && (
            <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-600/20 ring-inset dark:bg-amber-400/10 dark:text-amber-100">
              <p className="font-medium">Left out because they address an AI system rather than describe the company:</p>
              <ul className="mt-1 list-disc pl-5">{draft.ignored.map((s) => <li key={s}>“{s}”</li>)}</ul>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-3">
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
            <ol className="space-y-3">
              {card.needs.map((n, i) => (
                <li key={n.id} className="rounded-xl border border-line/10 bg-surface p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span aria-hidden="true" className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-50 text-sm font-semibold text-brand-700 tabular-nums dark:bg-brand-500/15 dark:text-brand-200">{i + 1}</span>
                    <label className="min-w-0 flex-[1_1_14rem]"><span className="sr-only">Need {i + 1}</span>
                      <input className="field bg-card" value={n.text} onChange={(e) => setNeed(n.id, 'text', e.target.value)} required minLength={3} maxLength={300} />
                    </label>
                    <label className="min-w-0 flex-[1_1_12rem] sm:flex-none"><span className="sr-only">Category for need {i + 1}</span>
                      <select className="field bg-card" value={n.category ?? ''} onChange={(e) => setNeed(n.id, 'category', e.target.value || null)}>
                        <option value="">Any category</option>
                        {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </label>
                    <button type="button" className="btn-ghost px-3 py-1.5" onClick={() => set('needs', card.needs.filter((m) => m.id !== n.id))}
                      disabled={card.needs.length === 1} aria-label={`Remove need ${i + 1}`}>Remove</button>
                  </div>
                  {draft.sources[n.id] && (
                    <ul className="mt-2.5 space-y-1 border-l-2 border-brand-400 pl-3 text-sm text-ink/70" aria-label={`Cited from the business model for need ${i + 1}`}>
                      {draft.sources[n.id].map((s) => <li key={s}>“{draft.sentences[s - 1]}”</li>)}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          </fieldset>
          <div className="flex flex-wrap justify-between gap-2 border-t border-line/10 pt-5">
            <button type="button" className="btn-ghost" onClick={addNeed} disabled={card.needs.length === IDS.length}>Add need</button>
            <button className="btn" disabled={busy}>Confirm and search</button>
          </div>
        </form>
      )}
    </div>
  )
}
