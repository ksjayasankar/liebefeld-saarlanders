import { ACTIONS, CATEGORIES, STAGES } from './labels.js'
import { Ext, Reasons } from './parts.jsx'

export default function Introduction({ intro }) {
  const { card } = intro
  return (
    <section className="panel intro" aria-labelledby="intro-title">
      <h2 id="intro-title">Introduction request sent</h2>
      <p className="hint">This is exactly what the agency receives.</p>
      <dl>
        <dt>Reference</dt><dd><code>{intro.id}</code></dd>
        <dt>Status</dt><dd>{intro.status}</dd>
        <dt>Created</dt><dd>{new Date(intro.created_at).toLocaleString()}</dd>
        <dt>Your message</dt><dd className="pre">{intro.message}</dd>
        <dt>Company</dt><dd>{[card.sector, card.product, card.stage && STAGES[card.stage]].filter(Boolean).join(' · ')}</dd>
      </dl>
      <h3>Needs</h3>
      <ul>{card.needs.map((n) => <li key={n.id}>{n.text}{n.category && <> ({CATEGORIES[n.category]})</>}</li>)}</ul>
      <h3>Chosen leads</h3>
      {intro.leads.map((l) => (
        <div key={l.unit_id} className="lead">
          <h4><Ext href={l.url}>{l.name}</Ext></h4>
          {l.parent && <p className="meta">{l.parent}</p>}
          <Reasons reasons={l.reasons} />
        </div>
      ))}
      <h3>Your feedback</h3>
      <ul>{intro.feedback.map((f, i) => <li key={i}>{ACTIONS[f.action]} on <code>{f.unit_id}</code> for need {f.need_id}</li>)}</ul>
      <details>
        <summary>Raw record</summary>
        <pre>{JSON.stringify(intro, null, 2)}</pre>
      </details>
    </section>
  )
}
