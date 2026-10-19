import { useState } from 'react'
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
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

// One person, laid out the same in the card's contact slot and in the details. Affiliation and source are shown only
// when they differ from what the card already says (the unit's name, the page all its people are listed on).
function Person({ p, unit, source, quote, checkedAt }) {
  return (
    <div className="min-w-0 space-y-1">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <p className="font-semibold">{[p.titles, p.name].filter(Boolean).join(' ')}</p>
        {p.contact && <span className="tag-brand">Contact person</span>}
      </div>
      {p.function && <p className="text-sm">{p.function}</p>}
      {p.affiliation && p.affiliation !== unit && <p className="text-sm text-ink/65">{p.affiliation}</p>}
      <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-1 text-sm">
        {p.email && <li className="break-all">{EMAIL.test(p.email) ? <a className="link" href={`mailto:${p.email}`}>{p.email}</a> : p.email}</li>}
        {p.phone && <li className="tabular-nums">{PHONE.test(p.phone) ? <a className="link" href={`tel:${p.phone.replace(/[^\d+]/g, '')}`}>{p.phone}</a> : p.phone}</li>}
        {p.profile_url && <li><Ext href={p.profile_url}>Profile</Ext></li>}
        {p.source_url !== source && <li><Source href={p.source_url} /></li>}
        {!p.email && !p.phone && !p.profile_url && <li className="text-ink/65">No email or phone on the page</li>}
      </ul>
      {quote && <div className="pt-2 text-sm"><Quote reason={p.reason} checkedAt={checkedAt} /></div>}
    </div>
  )
}

const Part = ({ title, children }) => <section><h4 className="kicker mb-3">{title}</h4>{children}</section>

function Lead({ lead, needs, onFeedback, busy, delay }) {
  const [open, setOpen] = useState(false)
  const [first, ...others] = lead.people
  // When every person comes from one page, that page is cited once instead of on each person.
  const source = lead.people.length > 0 && lead.people.every((p) => p.source_url === first.source_url) ? first.source_url : null
  // A sentence quoted for several people (a shared team page) is shown once, under the first of them.
  const seen = new Set()
  const quoted = (p) => p.reason && !seen.has(p.reason.sentence) && seen.add(p.reason.sentence)
  // Without an explanation the first quote stands in for it on the card, so the details list the rest.
  const evidence = lead.explanation ? lead.reasons : lead.reasons.slice(1)
  const details = `lead-details-${lead.unit_id}`

  return (
    <article className="card animate-fade-up space-y-4" style={{ animationDelay: `${delay}ms` }} aria-labelledby={`lead-${lead.unit_id}`}>
      <header className="space-y-2">
        <div>
          <h3 id={`lead-${lead.unit_id}`} className="text-lg font-semibold tracking-tight">{lead.name}</h3>
          {lead.parent && <p className="mt-0.5 text-sm text-ink/65">{lead.parent}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-ink/65 tabular-nums">
          <Source href={lead.url} />
          <span>Answers {lead.need_ids.length} of {plural(needs.length, 'need')}</span>
          {lead.page_date && <span>Page dated {day(lead.page_date)}</span>}
          {lead.stale && <span className="warn">May be outdated</span>}
        </div>
      </header>

      {lead.explanation ? <p className="text-base">{lead.explanation}</p> : <Quote reason={lead.reasons[0]} checkedAt={lead.checked_at} />}

      <section className="rounded-xl bg-surface p-4" aria-label={`Contact for ${lead.name}`}>
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h4 className="kicker">Contact</h4>
          {source && <span className="flex items-center gap-1.5 text-xs text-ink/65">Listed on <Source href={source} /></span>}
        </div>
        {first
          ? <Person p={first} unit={lead.name} source={source} quote={open && quoted(first)} checkedAt={lead.checked_at} />
          : <p className="text-sm text-ink/65">No people listed on the indexed pages. <Ext href={lead.url}>Open the unit's page</Ext></p>}
      </section>

      {open && (
        <div id={details} className="animate-fade-up space-y-6 border-t border-line/10 pt-5">
          {evidence.length > 0 && (
            <Part title={lead.explanation ? "Evidence from the unit's pages" : "More evidence from the unit's pages"}>
              <ul className="space-y-4">{evidence.map((r, i) => <li key={i}><Quote reason={r} checkedAt={lead.checked_at} /></li>)}</ul>
            </Part>
          )}
          {others.length > 0 && (
            <Part title={`More people (${others.length})`}>
              <ul className="grid gap-2 sm:grid-cols-2">
                {others.map((p) => (
                  <li key={p.source_url + p.name} className="rounded-xl border border-line/10 p-4">
                    <Person p={p} unit={lead.name} source={source} quote={quoted(p)} checkedAt={lead.checked_at} />
                  </li>
                ))}
              </ul>
            </Part>
          )}
          {lead.items.length > 0 && (
            <Part title="Projects, infrastructure and services">
              <ul className="space-y-2">
                {lead.items.map((it) => <li key={it.url} className="flex flex-wrap items-baseline gap-2 text-sm"><span className="tag">{KINDS[it.kind]}</span><Ext href={it.url}>{it.name}</Ext></li>)}
              </ul>
            </Part>
          )}
          {lead.expertise.length > 0 && (
            <Part title="Fields of expertise">
              <ul className="flex flex-wrap gap-1.5">{lead.expertise.map((x) => <li key={x} className="tag">{x}</li>)}</ul>
            </Part>
          )}
          <Part title="About">
            <p className="text-sm text-ink/80">{lead.summary}</p>
            <p className="mt-2 text-xs text-ink/65 tabular-nums">{plural(lead.page_count, 'page')} indexed</p>
          </Part>
        </div>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line/10 pt-4">
        <button type="button" className="btn-ghost" aria-expanded={open} aria-controls={details} onClick={() => setOpen(!open)}>
          {open ? 'Hide details' : others.length > 0 ? `Show details and ${plural(others.length, 'more person', 'more people')}` : 'Show details'}
          <Icon className={`size-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}><path d="m6 9 6 6 6-6" /></Icon>
        </button>
        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label={`Feedback on ${lead.name}`}>
          {QUICK.map(([action, icon]) => (
            <button key={action} type="button" className="grid size-9 place-items-center rounded-full text-ink/65 transition-colors duration-150 hover:bg-surface hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
              disabled={busy} onClick={() => onFeedback(action)} aria-label={ACTIONS[action]} title={ACTIONS[action]}><Icon>{icon}</Icon></button>
          ))}
          <label className="ml-1"><span className="sr-only">Other feedback on {lead.name}</span>
            <select className="h-9 rounded-full border border-line/15 bg-card px-3 text-sm text-ink/75 transition-colors duration-150 hover:border-line/25 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50" value="" disabled={busy} onChange={(e) => onFeedback(e.target.value)}>
              <option value="" disabled>Other feedback…</option>
              {Object.entries(ACTIONS).filter(([a]) => !QUICK.some(([q]) => q === a)).map(([a, text]) => <option key={a} value={a}>{text}</option>)}
            </select>
          </label>
        </div>
      </footer>
    </article>
  )
}

export default function Results({ result, setResult, run, busy }) {
  const feedback = (lead, action) => run('rerank', async () =>
    setResult(await api(`/api/requests/${result.request_id}/feedback`, { unit_id: lead.unit_id, need_id: lead.need_ids[0], action })))
  const total = result.groups.reduce((n, g) => n + g.leads.length, 0)
  const needs = result.card.needs

  return (
    <section id="leads" className="animate-fade-up scroll-mt-20" aria-label="Leads">
      <div className="space-y-6">
        <div className="space-y-2">
          <p className="text-sm text-ink/65 tabular-nums">{plural(total, 'lead')} · {result.covered.length} of {plural(needs.length, 'need')} covered</p>
          {result.message && <p role="status" className="rounded-xl border border-line/10 border-l-2 border-l-ink/40 bg-card px-4 py-3 text-sm shadow-soft">{result.message}</p>}
        </div>
        {result.groups.length > 1 && (
          <nav aria-label="Result groups" className="sticky top-14 z-[5] -mx-4 border-b border-line/10 bg-page/85 px-4 py-2.5 backdrop-blur-md lg:mx-0 lg:px-0">
            <ul className="flex gap-1.5 overflow-x-auto">
              {result.groups.map((g) => (
                <li key={g.category} className="shrink-0">
                  <a className="chip inline-flex items-center gap-1.5" href={`#group-${g.category}`}>{g.label}<span className="text-ink/60 tabular-nums">{g.leads.length}</span></a>
                </li>
              ))}
            </ul>
          </nav>
        )}
        {result.groups.map((g, gi) => (
          <section key={g.category} id={`group-${g.category}`} className="scroll-mt-32 space-y-3" aria-labelledby={`group-title-${g.category}`}>
            <h2 id={`group-title-${g.category}`} className="flex items-center gap-2 pt-2 text-lg font-semibold tracking-tight">
              {g.label}<span className="tag tabular-nums">{g.leads.length}</span>
            </h2>
            {g.leads.map((l, i) => <Lead key={l.unit_id} lead={l} needs={needs} busy={busy} delay={(gi + i) * 80} onFeedback={(a) => feedback(l, a)} />)}
          </section>
        ))}
      </div>
    </section>
  )
}
