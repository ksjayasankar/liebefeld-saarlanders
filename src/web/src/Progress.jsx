import { useEffect, useState } from 'react'
import { apiUrl } from './api.js'
import { AGENTS, AgentBadge, From, Icon } from './agents.jsx'
import { ALERT, TICK } from './parts.jsx'

// Cowork's progress panel. Every state is read from the API calls themselves: running while the call runs, done with counts from its answer.
const STATE = {
  wait: { label: 'Waiting', mark: <span className="size-3.5 rounded-full border-2 border-line/25" /> },
  run: { label: 'Working', mark: <span className="size-3.5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" /> },
  done: { label: 'Done', mark: <Icon className="size-4 text-emerald-600 dark:text-emerald-400"><circle cx="12" cy="12" r="9" /><path d="m8.5 12 2.5 2.5 4.5-5" /></Icon> },
}

function Row({ id, state, note, children }) {
  return (
    <li className="flex gap-3">
      <AgentBadge id={id} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="flex-1 truncate text-sm font-semibold">{AGENTS[id].name}</p>
          <span className="grid size-4 place-items-center">{STATE[state].mark}</span><span className="sr-only">{STATE[state].label}</span>
        </div>
        {note && <p className="text-xs text-ink/65">{note}</p>}
        {children}
      </div>
    </li>
  )
}

export default function Progress({ keyword, draft, card, feed, result, task }) {
  const searching = task === 'search' || task === 'rerank'
  const finished = result && !searching
  const leads = finished ? result.groups.flatMap((g) => g.leads) : []
  const needs = (finished ? result.card : card)?.needs ?? []
  const hosts = [...new Set(leads.map((l) => l.host))]
  const quotes = leads.flatMap((l) => l.reasons).filter((r) => r.live)
  const pages = feed.filter((e) => e.step === 'verify').length
  const step = searching ? 'run' : finished ? 'done' : 'wait'
  return (
    <div className="space-y-5 rounded-2xl border border-line/10 bg-card p-4 shadow-soft" role="status" aria-live="polite">
      <section>
        <h2 className="kicker mb-3">Progress</h2>
        <ol className="space-y-4">
          {!keyword && (
            <Row id="analyst" state={task === 'draft' ? 'run' : draft ? 'done' : 'wait'}
              note={draft ? `${draft.card.needs.length} needs${draft.ignored.length ? `, ${draft.ignored.length} sentences left out` : ''}` : 'Reading the business model'} />
          )}
          <Row id="scout" state={step} note={step === 'wait' && card ? 'Waiting for you to confirm the needs' : null}>
            <ul className="mt-2 space-y-1.5 border-l border-line/15 pl-3">
              {needs.map((n, i) => {
                const found = leads.filter((l) => l.need_ids.includes(n.id)).length
                return (
                  <li key={n.id} className="flex items-baseline gap-2 text-xs">
                    <span className="font-medium tabular-nums text-ink/50">{i + 1}</span>
                    <span className="min-w-0 flex-1 truncate" title={n.text}>{n.text}</span>
                    <span className="shrink-0 text-ink/65 tabular-nums">{finished ? (result.uncovered.includes(n.id) ? 'no lead' : `${found} leads`) : searching ? (feed.some((e) => e.step === 'rerank' && e.need === n.id) ? 'searched' : '…') : ''}</span>
                  </li>
                )
              })}
            </ul>
          </Row>
          <Row id="checker" state={step}
            note={finished ? `${leads.filter((l) => l.explanation).length} of ${leads.length} explanations confirmed${quotes.length ? `, ${quotes.filter((r) => r.live === 'found').length} of ${quotes.length} quotes found live` : ''}`
              : task === 'search' && feed.some((e) => e.step === 'select') ? `${feed.filter((e) => e.step === 'explain').length} checked${pages ? `, ${pages} pages fetched live` : ''}` : null} />
          <Row id="writer" state={finished ? 'done' : 'wait'}>
            {finished && <a className="link mt-1 inline-block text-xs" href={apiUrl(`/api/requests/${result.request_id}/report.pdf`)}>Download report (PDF)</a>}
          </Row>
        </ol>
      </section>
      {hosts.length > 0 && (
        <section className="border-t border-line/10 pt-4">
          <h2 className="kicker mb-2.5">Sources</h2>
          <ul className="flex flex-wrap gap-1.5">{hosts.map((h) => <li key={h} className="tag">{h.replace(/^www\./, '')}</li>)}</ul>
        </section>
      )}
    </div>
  )
}

const clock = (ms) => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`

// The first few of a list as chips, the rest as a count: the Scouts use all of them.
function Chips({ items, shown, className = 'tag' }) {
  return (
    <ul className="flex flex-wrap items-center gap-1.5">
      {items.slice(0, shown).map((t, j) => <li key={t + j} className={`${className} animate-pop`} style={{ animationDelay: `${j * 50}ms` }}>{t}</li>)}
      {items.length > shown && <li className="px-1 text-xs text-ink/65">+{items.length - shown} more</li>}
    </ul>
  )
}

function Step({ state, children }) {
  return (
    <li className="flex gap-2.5">
      <span className="mt-0.5 grid size-4 shrink-0 place-items-center">{STATE[state].mark}</span>
      <div className="min-w-0 flex-1 space-y-2">{children}</div>
    </li>
  )
}

// What runs after the last step the stream sent, shimmering; the stream itself says nothing until a step is done.
function next(feed, needs) {
  const last = feed.at(-1)
  const at = last?.need ? needs.findIndex((n) => n.id === last.need) : -1
  if (!last) return `Turning need 1 into search terms`
  if (last.step === 'expand') return `Searching every indexed page for need ${at + 1}`
  if (last.step === 'retrieve') return `Reranking the closest passages for need ${at + 1}`
  if (last.step === 'rerank') return at + 1 < needs.length ? `Turning need ${at + 2} into search terms` : 'Choosing leads that cover every need'
  return 'Checking each explanation against its source and fetching the quoted pages live'
}

// One line per quoted page fetched again (D-32): a tick when every quote is still there, a warning when one changed or the page is gone.
function Page({ e }) {
  const url = new URL(e.url)
  const bad = e.status.includes('changed') || e.status.includes('gone')
  const note = e.status.includes('gone') ? 'page gone' : e.status.includes('changed') ? `${e.found} of ${e.quotes} quotes still there`
    : e.status.includes('unreachable') ? 'did not answer' : e.status.includes('not_checked') ? 'not checked, read with a browser' : null
  return (
    <li className="flex items-center gap-2 text-ink/80">
      {bad || e.found === e.quotes ? <Icon className={`size-3.5 ${bad ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>{bad ? ALERT : TICK}</Icon>
        : <span className="grid size-3.5 place-items-center text-ink/45" aria-hidden="true">–</span>}
      <span className="min-w-0 truncate" title={e.url}>{url.host.replace(/^www\./, '')}{url.pathname.replace(/\/$/, '')}</span>
      {note ? <span className="shrink-0 text-xs text-ink/65">{note}</span> : <span className="sr-only">quote found</span>}
    </li>
  )
}

// ChatGPT's "searching the web" card, driven by the search stream (D-30): per need the terms, the sites read and the closest units,
// then the shortlist and one tick or cross per explanation check. Once done it folds into one line that opens again.
export function Activity({ needs, feed, task, started }) {
  const searching = task === 'search'
  const [now, setNow] = useState(started)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!searching) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [searching])
  const of = (step, need) => feed.find((e) => e.step === step && e.need === need)
  const leads = feed.find((e) => e.step === 'select')?.leads ?? []
  const checks = feed.filter((e) => e.step === 'explain')
  const verified = feed.filter((e) => e.step === 'verify')
  const quotes = verified.reduce((n, e) => n + e.quotes, 0)
  const terms = feed.filter((e) => e.step === 'expand').flatMap((e) => e.terms)
  const sites = new Set(feed.filter((e) => e.step === 'retrieve').flatMap((e) => e.sites))
  const elapsed = clock(Math.max(0, now - started))
  return (
    <section className="animate-fade-up" aria-label="Search activity">
      <From ids={['scout', 'checker']}><span className="ml-auto text-xs text-ink/65 tabular-nums">{searching ? elapsed : `Done in ${elapsed}`}</span></From>
      <div className="card p-4 sm:p-5">
        {!searching && (
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-2 text-left text-sm font-medium">
            <span className="flex-1">{feed.at(-1)?.step === 'done'
              ? `Searched ${terms.length} terms on ${sites.size} sites · ${checks.filter((c) => c.supported).length} of ${leads.length} explanations confirmed`
                + (quotes ? ` · ${verified.reduce((n, e) => n + e.found, 0)} of ${quotes} quotes found live` : '')
              : `Stopped with an error after ${feed.length} steps`}</span>
            <Icon className={`size-4 text-ink/65 transition-transform ${open ? 'rotate-180' : ''}`}><path d="m6 9 6 6 6-6" /></Icon>
          </button>
        )}
        {(searching || open) && (
          <ol className={`space-y-5 text-sm ${searching ? '' : 'mt-4 border-t border-line/10 pt-4'}`}>
            {needs.filter((n) => of('expand', n.id)).map((n) => {
              const [expand, retrieve, rerank] = ['expand', 'retrieve', 'rerank'].map((s) => of(s, n.id))
              return (
                <li key={n.id} className="space-y-3">
                  <p className="truncate font-medium" title={n.text}>{n.text}</p>
                  <ol className="space-y-3 border-l border-line/15 pl-3">
                    <Step state="done"><p>Searching for {expand.terms.length} terms</p><Chips items={expand.terms} shown={8} /></Step>
                    {retrieve && <Step state="done"><p>Read {retrieve.passages.toLocaleString('en-GB')} passages on {retrieve.sites.length} sites</p><Chips items={retrieve.sites} shown={6} className="source" /></Step>}
                    {rerank && <Step state="done"><p>Closest of {rerank.passages} reranked passages</p><Chips items={rerank.closest} shown={5} /></Step>}
                  </ol>
                </li>
              )
            })}
            {leads.length > 0 && (
              <li>
                <Step state={checks.length < leads.length ? 'run' : 'done'}>
                  <p>Checked {checks.length} of {leads.length} explanations against their sources</p>
                  <ul className="space-y-1">
                    {leads.map((name) => {
                      const c = checks.find((e) => e.lead === name)
                      return (
                        <li key={name} className="flex items-center gap-2 text-ink/80">
                          {c ? <Icon className={`size-3.5 ${c.supported ? 'text-emerald-600 dark:text-emerald-400' : 'text-ink/45'}`}>{c.supported ? <path d="m5 12 4.5 4.5L19 7" /> : <path d="M6 6l12 12M18 6 6 18" />}</Icon>
                            : <span className="size-3.5" />}
                          <span className="truncate">{name}</span>
                          {c && <span className="sr-only">{c.supported ? 'confirmed' : 'not confirmed, no explanation shown'}</span>}
                        </li>
                      )
                    })}
                  </ul>
                </Step>
              </li>
            )}
            {verified.length > 0 && (
              <li>
                <Step state={searching ? 'run' : 'done'}>
                  <p>Fetched {verified.length} quoted {verified.length === 1 ? 'page' : 'pages'} again to check the quotes are still there</p>
                  <ul className="space-y-1">{verified.map((e) => <Page key={e.url} e={e} />)}</ul>
                </Step>
              </li>
            )}
            {searching && <li><Step state="run"><p className="shimmer">{next(feed, needs)}…</p></Step></li>}
          </ol>
        )}
      </div>
    </section>
  )
}
