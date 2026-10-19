import { apiUrl } from './api.js'
import { AGENTS, AgentBadge, Icon } from './agents.jsx'

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

export default function Progress({ keyword, draft, card, result, task }) {
  const searching = task === 'search' || task === 'rerank'
  const finished = result && !searching
  const leads = finished ? result.groups.flatMap((g) => g.leads) : []
  const needs = (finished ? result.card : card)?.needs ?? []
  const hosts = [...new Set(leads.map((l) => l.host))]
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
                    <span className="shrink-0 text-ink/65 tabular-nums">{searching ? '…' : finished ? (result.uncovered.includes(n.id) ? 'no lead' : `${found} leads`) : ''}</span>
                  </li>
                )
              })}
            </ul>
          </Row>
          <Row id="checker" state={step}
            note={finished ? `${leads.filter((l) => l.explanation).length} of ${leads.length} explanations confirmed` : null} />
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
