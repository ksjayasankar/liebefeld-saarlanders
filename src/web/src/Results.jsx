import { api } from './api.js'
import { Icon } from './agents.jsx'
import { ACTIONS } from './labels.js'
import { Ext, Quote, Source } from './parts.jsx'

const EMAIL = /^[^\s@<>"]+@[^\s@<>"]+\.[a-z]{2,}$/i
const PHONE = /^\+?[\d ()./-]{6,20}$/
// Thumbs up and down, as in the template's answer card; the other reasons sit in one menu.
const QUICK = [
  ['more_like_this', <path key="u" d="M7 11v9H4v-9zM7 11l4-8a2.5 2.5 0 0 1 2.5 2.5V9h5.2a2 2 0 0 1 2 2.3l-1.2 7A2 2 0 0 1 17.5 20H7" />],
  ['not_relevant', <path key="d" d="M17 13V4h3v9zM17 13l-4 8a2.5 2.5 0 0 1-2.5-2.5V15H5.3a2 2 0 0 1-2-2.3l1.2-7A2 2 0 0 1 6.5 4H17" />],
]
const KINDS = { project: 'Project', facility: 'Infrastructure or service' }
const day = (d) => new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

function Person({ p }) {
  return (
    <li className="rounded-xl border border-line/10 bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-semibold">{[p.titles, p.name].filter(Boolean).join(' ')}</p>
        {p.contact && <span className="tag-brand">Contact person</span>}
      </div>
      {p.function && <p className="mt-0.5 text-sm">{p.function}</p>}
      <p className="text-sm text-ink/65">{p.affiliation}</p>
      <ul className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        {p.email && <li className="break-all">{EMAIL.test(p.email) ? <a className="link" href={`mailto:${p.email}`}>{p.email}</a> : p.email}</li>}
        {p.phone && <li className="tabular-nums">{PHONE.test(p.phone) ? <a className="link" href={`tel:${p.phone.replace(/[^\d+]/g, '')}`}>{p.phone}</a> : p.phone}</li>}
        {p.profile_url && <li><Ext href={p.profile_url}>Profile</Ext></li>}
        <li><Source href={p.source_url} /></li>
      </ul>
      {p.reason && <div className="mt-3 text-sm"><Quote reason={p.reason} /></div>}
    </li>
  )
}

const Part = ({ title, children }) => <section><h4 className="kicker mb-3">{title}</h4>{children}</section>

function Lead({ lead, onFeedback, busy, delay }) {
  return (
    <article className="card animate-fade-up space-y-6" style={{ animationDelay: `${delay}ms` }} aria-labelledby={`lead-${lead.unit_id}`}>
      <header className="space-y-3">
        <div>
          <h3 id={`lead-${lead.unit_id}`} className="text-lg font-semibold tracking-tight">{lead.name}</h3>
          {lead.parent && <p className="mt-0.5 text-sm text-ink/65">{lead.parent}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-ink/65 tabular-nums">
          <Source href={lead.url} />
          {lead.page_date && <span>Page dated {day(lead.page_date)}</span>}
          {lead.stale && <span className="warn">May be outdated</span>}
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="min-w-0 space-y-6">
          <Part title="Why it matches">
            {lead.explanation && <p className="mb-3 text-base">{lead.explanation}</p>}
            <ul className="space-y-4">{lead.reasons.map((r, i) => <li key={i}><Quote reason={r} delay={delay + i * 80} /></li>)}</ul>
          </Part>
          {lead.expertise.length > 0 && (
            <Part title="Fields of expertise">
              <ul className="flex flex-wrap gap-1.5">{lead.expertise.map((x) => <li key={x} className="tag">{x}</li>)}</ul>
            </Part>
          )}
          {lead.items.length > 0 && (
            <Part title="Projects, infrastructure and services">
              <ul className="space-y-2">
                {lead.items.map((it) => <li key={it.url} className="flex flex-wrap items-baseline gap-2 text-sm"><span className="tag">{KINDS[it.kind]}</span><Ext href={it.url}>{it.name}</Ext></li>)}
              </ul>
            </Part>
          )}
          <Part title="About"><p className="text-sm text-ink/80">{lead.summary}</p></Part>
        </div>
        <div className="min-w-0 self-start rounded-xl bg-surface p-4">
          <Part title="People and contacts">
            {lead.people.length > 0
              ? <ul className="space-y-2">{lead.people.map((p) => <Person key={p.source_url + p.name} p={p} />)}</ul>
              : <p className="hint">No people listed on the indexed pages.</p>}
          </Part>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 border-t border-line/10 pt-4" role="group" aria-label={`Feedback on ${lead.name}`}>
        {QUICK.map(([action, icon]) => (
          <button key={action} type="button" className="grid size-9 place-items-center rounded-full text-ink/65 transition-colors duration-150 hover:bg-surface hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
            disabled={busy} onClick={() => onFeedback(action)} aria-label={ACTIONS[action]} title={ACTIONS[action]}><Icon>{icon}</Icon></button>
        ))}
        <label className="ml-2"><span className="sr-only">Other feedback on {lead.name}</span>
          <select className="h-9 rounded-full border border-line/15 bg-card px-3 text-sm text-ink/75 transition-colors duration-150 hover:border-line/25 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50" value="" disabled={busy} onChange={(e) => onFeedback(e.target.value)}>
            <option value="" disabled>Other feedback…</option>
            {Object.entries(ACTIONS).filter(([a]) => !QUICK.some(([q]) => q === a)).map(([a, text]) => <option key={a} value={a}>{text}</option>)}
          </select>
        </label>
      </div>
    </article>
  )
}

export default function Results({ result, setResult, run, busy }) {
  const feedback = (lead, action) => run('rerank', async () =>
    setResult(await api(`/api/requests/${result.request_id}/feedback`, { unit_id: lead.unit_id, need_id: lead.need_ids[0], action })))

  return (
    <section id="leads" className="animate-fade-up scroll-mt-20" aria-label="Leads">
      <div className="space-y-8">
        <div className="space-y-2">
          <p className="rounded-xl border border-line/10 bg-surface px-4 py-3 text-sm">{result.coverage_line}</p>
          {result.message && <p role="status" className="rounded-xl border border-line/10 border-l-2 border-l-ink/40 bg-card px-4 py-3 text-sm shadow-soft">{result.message}</p>}
        </div>
        {result.groups.map((g, gi) => (
          <section key={g.category} className="space-y-4" aria-labelledby={`group-${g.category}`}>
            <h2 id={`group-${g.category}`} className="flex items-center gap-2 text-lg font-semibold tracking-tight">
              {g.label}<span className="tag tabular-nums">{g.leads.length}</span>
            </h2>
            {g.leads.map((l, i) => <Lead key={l.unit_id} lead={l} busy={busy} delay={(gi + i) * 80} onFeedback={(a) => feedback(l, a)} />)}
          </section>
        ))}
      </div>
    </section>
  )
}
