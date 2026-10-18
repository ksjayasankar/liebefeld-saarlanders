import { api, apiUrl } from './api.js'
import { ACTIONS, STAGES } from './labels.js'
import { Ext, Quote } from './parts.jsx'

const EMAIL = /^[^\s@<>"]+@[^\s@<>"]+\.[a-z]{2,}$/i
const PHONE = /^\+?[\d ()./-]{6,20}$/
const KINDS = { project: 'Project', facility: 'Infrastructure or service' }

function Person({ p }) {
  return (
    <li className="rounded-xl border border-line/10 bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-medium">{[p.titles, p.name].filter(Boolean).join(' ')}</p>
        {p.contact && <span className="tag">Contact person</span>}
      </div>
      {p.function && <p className="text-sm">{p.function}</p>}
      <p className="text-sm text-ink/70">{p.affiliation}</p>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {p.email && <li className="break-all">{EMAIL.test(p.email) ? <a className="link" href={`mailto:${p.email}`}>{p.email}</a> : p.email}</li>}
        {p.phone && <li>{PHONE.test(p.phone) ? <a className="link" href={`tel:${p.phone.replace(/[^\d+]/g, '')}`}>{p.phone}</a> : p.phone}</li>}
        {p.profile_url && <li><Ext href={p.profile_url}>Profile</Ext></li>}
        <li><Ext href={p.source_url}>Source</Ext></li>
      </ul>
      {p.reason && <div className="mt-3"><Quote reason={p.reason} /></div>}
    </li>
  )
}

const Part = ({ title, children }) => <section><h4 className="kicker mb-2">{title}</h4>{children}</section>

function Lead({ lead, needText, onFeedback, busy }) {
  return (
    <article className="card space-y-5" aria-labelledby={`lead-${lead.unit_id}`}>
      <header className="space-y-2">
        <h3 id={`lead-${lead.unit_id}`} className="text-lg font-semibold">{lead.name}</h3>
        <p className="text-sm text-ink/70">
          {lead.parent && <>{lead.parent} · </>}<Ext href={lead.url}>{lead.host}</Ext>
          {lead.page_date && <> · page dated {lead.page_date}</>} · {lead.page_count} pages indexed
        </p>
        <div className="flex flex-wrap gap-1.5">
          {lead.stale && <span className="warn">May be outdated</span>}
          {lead.expertise.map((x) => <span key={x} className="tag">{x}</span>)}
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="min-w-0 space-y-5">
          <Part title="Why it matches">
            {lead.explanation && <p className="mb-3">{lead.explanation}</p>}
            <p className="mb-3 text-sm">Answers: {lead.need_ids.map(needText).join('; ')}</p>
            <ul className="space-y-3">{lead.reasons.map((r, i) => <li key={i}><Quote reason={r} /></li>)}</ul>
          </Part>
          {lead.items.length > 0 && (
            <Part title="Projects, infrastructure and services">
              <ul className="space-y-1.5">
                {lead.items.map((it) => <li key={it.url} className="text-sm"><span className="text-ink/70">{KINDS[it.kind]}:</span> <Ext href={it.url}>{it.name}</Ext></li>)}
              </ul>
            </Part>
          )}
          <Part title="About"><p className="text-sm">{lead.summary}</p></Part>
        </div>
        <Part title="People and contacts">
          {lead.people.length > 0
            ? <ul className="space-y-2">{lead.people.map((p) => <Person key={p.source_url + p.name} p={p} />)}</ul>
            : <p className="hint">No people listed on the indexed pages.</p>}
        </Part>
      </div>

      <div className="flex flex-wrap gap-1.5 border-t border-line/10 pt-4" role="group" aria-label={`Feedback on ${lead.name}`}>
        {Object.entries(ACTIONS).map(([action, text]) => (
          <button key={action} type="button" className="chip" disabled={busy} onClick={() => onFeedback(action)}>{text}</button>
        ))}
      </div>
    </article>
  )
}

export default function Results({ result, setResult, run, busy, onBack }) {
  const id = result.request_id
  const { card } = result
  const needText = (nid) => card.needs.find((n) => n.id === nid).text
  const feedback = (lead, action) => run(async () =>
    setResult(await api(`/api/requests/${id}/feedback`, { unit_id: lead.unit_id, need_id: lead.need_ids[0], action })))

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap justify-between gap-2">
        <button type="button" className="btn-ghost" onClick={onBack}>New search</button>
        <a className="btn" href={apiUrl(`/api/requests/${id}/report.pdf`)}>Download report (PDF)</a>
      </div>

      <section className="card space-y-2" aria-labelledby="request-title">
        <h2 id="request-title" className="kicker">Search for</h2>
        {(card.sector || card.product || card.stage) && (
          <p className="font-medium">{[card.sector, card.product, card.stage && STAGES[card.stage]].filter(Boolean).join(' · ')}</p>
        )}
        <p className="rounded-xl bg-brand-50 px-3 py-2 text-sm font-medium text-brand-900 dark:bg-brand-500/15 dark:text-brand-100">{result.coverage_line}</p>
        {result.message && <p role="status" className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-400/10 dark:text-amber-100">{result.message}</p>}
      </section>

      {result.groups.map((g) => (
        <section key={g.category} className="space-y-4" aria-labelledby={`group-${g.category}`}>
          <h2 id={`group-${g.category}`} className="text-lg font-semibold">{g.label} <span className="text-ink/60">({g.leads.length})</span></h2>
          {g.leads.map((l) => <Lead key={l.unit_id} lead={l} needText={needText} busy={busy} onFeedback={(a) => feedback(l, a)} />)}
        </section>
      ))}
    </div>
  )
}
