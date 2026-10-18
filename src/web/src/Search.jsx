import { useState } from 'react'
import { api } from './api.js'
import { CATEGORIES, STAGES } from './labels.js'

const IDS = ['n1', 'n2', 'n3', 'n4', 'n5']

export default function Search({ domain, run, busy, onResult }) {
  const [query, setQuery] = useState('')
  const [description, setDescription] = useState('')
  const [draft, setDraft] = useState(null)
  const [card, setCard] = useState(null)

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
    <>
      <section className="panel">
        <h2>Quick search</h2>
        <form className="row" onSubmit={submit(() => search({ needs: [{ id: 'n1', text: query }] }))}>
          <label className="grow">
            <span className="sr-only">What are you looking for?</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. clinical validation of a glucose sensor" required minLength={3} maxLength={300} />
          </label>
          <button disabled={busy}>Search</button>
        </form>
      </section>

      <section className="panel">
        <h2>Or start from your company description</h2>
        <form onSubmit={submit(draftCard)}>
          <label>
            Paste your company's public description
            <textarea rows={6} value={description} onChange={(e) => setDescription(e.target.value)} required minLength={20} maxLength={5000} />
          </label>
          <button disabled={busy}>Draft from description</button>
        </form>
      </section>

      {card && (
        <form className="panel" onSubmit={submit(() => search(card))}>
          <h2>Your need card</h2>
          <p className="hint">Check and edit the draft. Only the card you confirm is searched.</p>
          <div className="grid">
            <label>Sector<input value={card.sector ?? ''} onChange={(e) => set('sector', e.target.value || null)} maxLength={100} /></label>
            <label>Product<input value={card.product ?? ''} onChange={(e) => set('product', e.target.value || null)} maxLength={200} /></label>
            <label>Stage
              <select value={card.stage ?? ''} onChange={(e) => set('stage', e.target.value || null)}>
                <option value="">Not set</option>
                {Object.entries(STAGES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
          </div>
          <h3>Needs</h3>
          <ol className="needs">
            {card.needs.map((n) => (
              <li key={n.id}>
                <div className="row">
                  <label className="grow"><span className="sr-only">Need {n.id}</span>
                    <input value={n.text} onChange={(e) => setNeed(n.id, 'text', e.target.value)} required minLength={3} maxLength={300} />
                  </label>
                  <label><span className="sr-only">Category for need {n.id}</span>
                    <select value={n.category ?? ''} onChange={(e) => setNeed(n.id, 'category', e.target.value || null)}>
                      <option value="">Any category</option>
                      {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </label>
                  <button type="button" className="ghost" onClick={() => set('needs', card.needs.filter((m) => m.id !== n.id))} disabled={card.needs.length === 1}>Remove</button>
                </div>
                {draft.sources[n.id] && (
                  <ul className="cites" aria-label="From your description">
                    {draft.sources[n.id].map((i) => <li key={i}><q>{draft.sentences[i - 1]}</q></li>)}
                  </ul>
                )}
              </li>
            ))}
          </ol>
          <div className="row">
            <button type="button" className="ghost" onClick={addNeed} disabled={card.needs.length === IDS.length}>Add need</button>
            <button disabled={busy}>Confirm and search</button>
          </div>
        </form>
      )}
    </>
  )
}
