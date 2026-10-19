// The four agents the staff see. Each one is a real step of the pipeline with its own model call.
export const AGENTS = {
  analyst: { name: 'Need Analyst', model: 'Apertus 8B', line: 'Turns the business model into up to five needs you can edit.',
    icon: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h4" /></> },
  scout: { name: 'Scouts', model: 'BGE-M3 · reranker', line: 'One per need, searching every indexed page in Bern.',
    icon: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></> },
  checker: { name: 'Fact Checker', model: 'Apertus 70B', line: 'Keeps an explanation only when its quoted source backs it.',
    icon: <><path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" /><path d="m9 12 2 2 4-4" /></> },
  writer: { name: 'Report Writer', model: 'PDF', line: 'Writes an internal review and the report for the company.',
    icon: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M12 11v6M9.5 14.5 12 17l2.5-2.5" /></> },
}

export function Icon({ children, className = 'size-4' }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className={`${className} shrink-0 fill-none stroke-current stroke-[1.8] [stroke-linecap:round] [stroke-linejoin:round]`}>{children}</svg>
}

export function AgentBadge({ id, className = 'size-8' }) {
  return <span className={`${className} grid shrink-0 place-items-center rounded-lg border border-line/10 bg-surface text-ink/75`}><Icon>{AGENTS[id].icon}</Icon></span>
}

// Header of a block in the workspace thread: which agent produced it.
export function From({ ids, children }) {
  return (
    <div className="mb-3 flex items-center gap-2.5">
      <span className="flex -space-x-1.5">{ids.map((id) => <AgentBadge key={id} id={id} className="size-7 ring-2 ring-page" />)}</span>
      <p className="text-sm font-semibold tracking-tight">{ids.map((id) => AGENTS[id].name).join(' · ')}</p>
      {children}
    </div>
  )
}
