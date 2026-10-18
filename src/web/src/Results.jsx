import { api, apiUrl } from './api.js'
import { ACTIONS, STAGES } from './labels.js'
import { Ext, Quote, Source } from './parts.jsx'

const EMAIL = /^[^\s@<>"]+@[^\s@<>"]+\.[a-z]{2,}$/i
const PHONE = /^\+?[\d ()./-]{6,20}$/
const KINDS = { project: 'Project', facility: 'Infrastructure or service' }
const day = (d) => new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

function Person({ p }) {
  return (
    <li className="rounded-xl border border-line/10 bg-card p-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-semibold">{[p.titles, p.name].filter(Boolean).join(' ')}</p>
        {p.contact && <span className="tag-brand">Contact person</span>}
      </div>
      {p.function && <p className="text-sm">{p.function}</p>}
      <p className="text-sm text-ink/65">{p.affiliation}</p>
      <ul className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm">
        {p.email && <li className="break-all">{EMAIL.test(p.email) ? <a className="link" href={`mailto:${p.email}`}>{p.email}</a> : p.email}</li>}
        {p.phone && <li className="tabular-nums">{PHONE.test(p.phone) ? <a className="link" href={`tel:${p.phone.replace(/[^\d+]/g, '')}`}>{p.phone}</a> : p.phone}</li>}
        {p.profile_url && <li><Ext href={p.profile_url}>Profile</Ext></li>}
        <li><Source href={p.source_url} /></li>
      </ul>
      {p.reason && <div className="mt-3 text-sm"><Quote reason={p.reason} /></div>}
    </li>
  )
}

const Part = ({ title, children }) => <section><h4 className="kicker mb-2.5">{title}</h4>{children}</section>

function Lead({ lead, needText, onFeedback, busy, delay }) {
  return (
    <article className="card animate-fade-up space-y-6" style={{ animationDelay: `${delay}ms` }} aria-labelledby={`lead-${lead.unit_id}`}>
      <header className="space-y-2.5">
        <div>
          <h3 id={`lead-${lead.unit_id}`} className="text-lg font-semibold tracking-tight">{lead.name}</h3>
          {lead.parent && <p className="text-sm text-ink/65">{lead.parent}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-ink/65 tabular-nums">
          <Source href={lead.url} />
          {lead.page_date && <span>Page dated {day(lead.page_date)}</span>}
          <span>{lead.page_count} pages indexed</span>
          {lead.stale && <span className="warn">May be outdated</span>}
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="min-w-0 space-y-6">
          <Part title="Why it matches">
            {lead.explanation && <p className="mb-3 text-base">{lead.explanation}</p>}
            <p className="mb-3 text-sm text-ink/65">Answers: {lead.need_ids.map(needText).join('; ')}</p>
            <ul className="space-y-4">{lead.reasons.map((r, i) => <li key={i}><Quote reason={r} delay={delay + i * 80} /></li>)}</ul>
          </Part>
          {lead.expertise.length > 0 && (
            <Part title="Fields of expertise">
              <ul className="flex flex-wrap gap-1.5">{lead.expertise.map((x) => <li key={x} className="tag">{x}</li>)}</ul>
            </Part>
          )}
          {lead.items.length > 0 && (
            <Part title="Projects, infrastructure and services">
              <ul className="space-y-1.5">
                {lead.items.map((it) => <li key={it.url} className="flex flex-wrap items-baseline gap-2 text-sm"><span className="tag">{KINDS[it.kind]}</span><Ext href={it.url}>{it.name}</Ext></li>)}
              </ul>
            </Part>
          )}
          <Part title="About"><p className="text-sm text-ink/80">{lead.summary}</p></Part>
        </div>
        <div className="min-w-0 self-start rounded-2xl bg-surface p-3 sm:p-4">
          <Part title="People and contacts">
            {lead.people.length > 0
              ? <ul className="space-y-2">{lead.people.map((p) => <Person key={p.source_url + p.name} p={p} />)}</ul>
              : <p className="hint">No people listed on the indexed pages.</p>}
          </Part>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 border-t border-line/10 pt-4" role="group" aria-label={`Feedback on ${lead.name}`}>
        <span className="kicker mr-1">Feedback</span>
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
  const feedback = (lead, action) => run('Re-ranking the leads with your feedback…', async () =>
    setResult(await api(`/api/requests/${id}/feedback`, { unit_id: lead.unit_id, need_id: lead.need_ids[0], action })))

  return (
    <div className="space-y-8">
      <section className="animate-fade-up space-y-4" aria-labelledby="request-title">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <button type="button" className="btn-ghost" onClick={onBack}><span aria-hidden="true">←&nbsp;</span>New search</button>
          <a className="btn" href={apiUrl(`/api/requests/${id}/report.pdf`)}>Download report (PDF)</a>
        </div>
        <div className="card space-y-3">
          <h2 id="request-title" className="kicker">Results for</h2>
          {(card.sector || card.product || card.stage) && (
            <p className="text-lg font-semibold tracking-tight">{[card.sector, card.product, card.stage && STAGES[card.stage]].filter(Boolean).join(' · ')}</p>
          )}
          <p className="rounded-xl bg-surface px-3.5 py-2.5 text-sm">{result.coverage_line}</p>
          {result.message && <p role="status" className="rounded-xl bg-brand-50 px-3.5 py-2.5 text-sm text-brand-800 dark:bg-brand-500/15 dark:text-brand-100">{result.message}</p>}
        </div>
      </section>

      {result.groups.map((g, gi) => (
        <section key={g.category} className="space-y-4" aria-labelledby={`group-${g.category}`}>
          <h2 id={`group-${g.category}`} className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            {g.label}<span className="rounded-full bg-surface px-2 text-sm font-medium text-ink/65 tabular-nums ring-1 ring-line/10">{g.leads.length}</span>
          </h2>
          {g.leads.map((l, i) => <Lead key={l.unit_id} lead={l} needText={needText} busy={busy} delay={(gi + i) * 80} onFeedback={(a) => feedback(l, a)} />)}
        </section>
      ))}
    </div>
  )
}
