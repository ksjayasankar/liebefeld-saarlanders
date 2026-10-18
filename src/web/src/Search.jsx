import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { CATEGORIES, STAGES } from './labels.js'

const IDS = ['n1', 'n2', 'n3', 'n4', 'n5']

export default function Search({ domain, run, busy, onResult }) {
  const [query, setQuery] = useState('')
  const [description, setDescription] = useState('')
  const [draft, setDraft] = useState(null)
  const [card, setCard] = useState(null)
  const cardRef = useRef(null)
  useEffect(() => { if (draft) cardRef.current.scrollIntoView({ behavior: 'smooth' }) }, [draft])

  const search = (c) => run(async () => onResult(await api(`/api/${domain}/search`, { card: c })))
  const draftCard = () => run(async () => {
    const d = await api(`/api/${domain}/need-card/draft`, { description })
    setDraft(d)
    setCard(d.card)
  })
  const set = (field, value) => setCard({ ...card, [field]: value })
  const setNeed = (id, field, value) => set('needs', card.needs.map((n) => (n.id === id ? { ...n, [field]: value } : n)))
  const addNeed = () => set('needs', [...card.needs, { id: IDS.find((id) => !card.needs.some((n) => n.id === id)), text: '', category: null }])
  const submit = (fn) => (e) => { e.preventDefault(); fn() }

  return (
    <div className="space-y-6">
      <section className="card" aria-labelledby="model-title">
        <h2 id="model-title" className="text-xl font-semibold sm:text-2xl">Find collaborators in Bern for a company</h2>
        <p className="hint mt-1">Paste the business model the company sent. Apertus drafts a need card from it; you check and edit the card before anything is searched.</p>
        <form className="mt-4" onSubmit={submit(draftCard)}>
          <label htmlFor="model" className="label">Company business model (plain text)</label>
          <div className="rounded-2xl border border-line/15 bg-field p-2 focus-within:ring-2 focus-within:ring-brand-500">
            <textarea id="model" rows={8} className="block w-full resize-y bg-transparent px-2 py-1 outline-none placeholder:text-ink/45"
              value={description} onChange={(e) => setDescription(e.target.value)} required minLength={20} maxLength={5000}
              placeholder="e.g. We build a wearable optical glucose sensor and need clinical validation and an optics research partner…" />
            <div className="flex items-center justify-between gap-3 px-2 pt-1">
              <span className="text-xs text-ink/60">{description.length} / 5000</span>
              <button className="btn" disabled={busy}>Draft need card</button>
            </div>
          </div>
        </form>
      </section>

      <section className="card" aria-labelledby="quick-title">
        <h2 id="quick-title" className="font-semibold">Quick keyword search</h2>
        <form className="mt-3 flex flex-wrap gap-2" onSubmit={submit(() => search({ needs: [{ id: 'n1', text: query }] }))}>
          <label className="min-w-0 flex-[1_1_16rem]">
            <span className="sr-only">Keywords</span>
            <input className="field" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. clinical validation of a glucose sensor" required minLength={3} maxLength={300} />
          </label>
          <button className="btn" disabled={busy}>Search</button>
        </form>
      </section>

      {card && (
        <form ref={cardRef} className="card animate-fade-up scroll-mt-20 space-y-5" onSubmit={submit(() => search(card))} aria-labelledby="card-title">
          <div>
            <h2 id="card-title" className="text-xl font-semibold">Need card</h2>
            <p className="hint mt-1">Check and edit the draft. Only the card you confirm is searched.</p>
          </div>
          {draft.ignored.length > 0 && (
            <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-400/10 dark:text-amber-100">
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
                    <span aria-hidden="true" className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-600 text-sm font-semibold text-white">{i + 1}</span>
                    <label className="min-w-0 flex-[1_1_14rem]"><span className="sr-only">Need {i + 1}</span>
                      <input className="field bg-card" value={n.text} onChange={(e) => setNeed(n.id, 'text', e.target.value)} required minLength={3} maxLength={300} />
                    </label>
                    <label className="min-w-0 flex-[1_1_12rem] sm:flex-none"><span className="sr-only">Category for need {i + 1}</span>
                      <select className="field bg-card" value={n.category ?? ''} onChange={(e) => setNeed(n.id, 'category', e.target.value || null)}>
                        <option value="">Any category</option>
                        {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </label>
                    <button type="button" className="btn-ghost px-3 py-1.5 text-sm" onClick={() => set('needs', card.needs.filter((m) => m.id !== n.id))}
                      disabled={card.needs.length === 1} aria-label={`Remove need ${i + 1}`}>Remove</button>
                  </div>
                  {draft.sources[n.id] && (
                    <ul className="mt-2 space-y-1 border-l-2 border-brand-400 pl-3 text-sm text-ink/70" aria-label={`Cited from the business model for need ${i + 1}`}>
                      {draft.sources[n.id].map((s) => <li key={s}>“{draft.sentences[s - 1]}”</li>)}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          </fieldset>
          <div className="flex flex-wrap justify-between gap-2">
            <button type="button" className="btn-ghost" onClick={addNeed} disabled={card.needs.length === IDS.length}>Add need</button>
            <button className="btn" disabled={busy}>Confirm and search</button>
          </div>
        </form>
      )}
    </div>
  )
}
