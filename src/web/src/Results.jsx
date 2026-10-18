import { useState } from 'react'
import { api, apiUrl } from './api.js'
import { ACTIONS } from './labels.js'
import Introduction from './Introduction.jsx'
import { Ext, Reasons } from './parts.jsx'

function Lead({ lead, label, needText, selected, onSelect, onFeedback, busy }) {
  return (
    <article className="lead">
      <header>
        <h4>{lead.name}</h4>
        <p className="meta">
          {lead.parent && <>{lead.parent} · </>}{label} · <Ext href={lead.url}>{lead.host}</Ext>
          {lead.page_date && <> · page dated {lead.page_date}</>}
          {lead.stale && <span className="badge">may be outdated</span>}
        </p>
      </header>
      <p><span className="k">Answers:</span> {lead.need_ids.map(needText).join('; ')}</p>
      <Reasons reasons={lead.reasons} />
      <p>{lead.summary}</p>
      {lead.items.length > 0 && (
        <ul className="items">
          {lead.items.map((it) => <li key={it.url}>{it.kind === 'project' ? 'Project' : 'Facility'}: <Ext href={it.url}>{it.name}</Ext></li>)}
        </ul>
      )}
      {lead.people.length > 0 && <p><span className="k">People:</span> {lead.people.join(', ')}</p>}
      <div className="chips" role="group" aria-label={`Feedback on ${lead.name}`}>
        {Object.entries(ACTIONS).map(([action, text]) => (
          <button key={action} type="button" className="chip" disabled={busy} onClick={() => onFeedback(action)}>{text}</button>
        ))}
      </div>
      <label className="pick"><input type="checkbox" checked={selected} onChange={onSelect} /> Include in introduction request</label>
    </article>
  )
}

export default function Results({ result, setResult, run, busy, onBack }) {
  const [selected, setSelected] = useState(new Set())
  const [message, setMessage] = useState('')
  const [intro, setIntro] = useState(null)
  const id = result.request_id
  const leads = result.groups.flatMap((g) => g.leads)
  const chosen = leads.filter((l) => selected.has(l.unit_id)).map((l) => l.unit_id)
  const needText = (nid) => result.card.needs.find((n) => n.id === nid).text

  const toggle = (uid) => {
    const next = new Set(selected)
    if (!next.delete(uid)) next.add(uid)
    setSelected(next)
  }
  const feedback = (lead, action) => run(async () =>
    setResult(await api(`/api/requests/${id}/feedback`, { unit_id: lead.unit_id, need_id: lead.need_ids[0], action })))
  const askIntro = (e) => {
    e.preventDefault()
    run(async () => setIntro(await api(`/api/requests/${id}/introduction`, { unit_ids: chosen, message })))
  }

  return (
    <>
      <div className="row between">
        <button type="button" className="ghost" onClick={onBack}>New search</button>
        <a className="button" href={apiUrl(`/api/requests/${id}/report.pdf`)}>Download report (PDF)</a>
      </div>
      <p className="coverage">{result.coverage_line}</p>
      {result.message && <p className="notice" role="status">{result.message}</p>}

      {result.groups.map((g) => (
        <section key={g.category}>
          <h3>{g.label}</h3>
          {g.leads.map((l) => (
            <Lead key={l.unit_id} lead={l} label={g.label} needText={needText} busy={busy}
              selected={selected.has(l.unit_id)} onSelect={() => toggle(l.unit_id)} onFeedback={(a) => feedback(l, a)} />
          ))}
        </section>
      ))}

      {intro ? <Introduction intro={intro} /> : (
        <form className="panel" onSubmit={askIntro}>
          <h2>Ask the agency for an introduction</h2>
          <p className="hint">{chosen.length} of {leads.length} leads selected (up to 10).</p>
          <label>Message to the agency
            <textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)} maxLength={2000} />
          </label>
          <button disabled={busy || chosen.length === 0 || chosen.length > 10}>Ask the agency for an introduction</button>
        </form>
      )}
    </>
  )
}
