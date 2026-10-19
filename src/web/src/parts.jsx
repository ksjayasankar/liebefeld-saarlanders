import { Icon } from './agents.jsx'

// Every link to a source page goes through Ext: http(s) only, new tab, no opener.
export function Ext({ href, children, className = 'link', ...rest }) {
  if (!/^https?:\/\//i.test(href)) throw new Error(`not an http(s) link: ${href}`)
  return (
    <a className={className} href={href} target="_blank" rel="noopener noreferrer" {...rest}>
      {children}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span>
    </a>
  )
}

// The template's source chip: host and last page folder the claim was read from; the full address shows on hover.
export function Source({ href, delay = 0 }) {
  const url = new URL(href)
  const page = url.pathname.split('/').filter((s) => s && !s.startsWith('index')).pop()
  return (
    <Ext href={href} className="source animate-pop" title={href} style={{ animationDelay: `${delay}ms` }}>
      <span className="sr-only">Source: </span><span className="truncate">{url.host.replace(/^www\./, '')}{page && ` › ${page}`}</span>
    </Ext>
  )
}

// The live check of a quote (D-32): a tick when the page still has it, a warning when it changed or is gone, neutral otherwise.
export const TICK = <path d="m5 12 4.5 4.5L19 7" />
export const ALERT = <><path d="M12 4 3 20h18z" /><path d="M12 10v4M12 17v.01" /></>
const LIVE = {
  found: { label: 'Checked live', className: 'tag text-emerald-700 dark:text-emerald-300', icon: TICK },
  changed: { label: 'Quote no longer on the page', className: 'warn', icon: ALERT },
  gone: { label: 'Page gone', className: 'warn', icon: ALERT },
  unreachable: { label: 'Page did not answer', className: 'tag' },
  not_checked: { label: 'Not checked live', className: 'tag', title: 'This site is read with a browser, so it is not fetched again at search time.' },
}
const time = (d) => new Date(d).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

export function Live({ status, at }) {
  const s = LIVE[status]
  if (!s) return null
  return (
    <span className={`${s.className} gap-1 tabular-nums`} title={s.title ?? (at ? `Page fetched again ${new Date(at).toLocaleString('en-GB')}` : undefined)}>
      {s.icon && <Icon className="size-3.5">{s.icon}</Icon>}{s.label}{at && status !== 'not_checked' && ` ${time(at)}`}
    </span>
  )
}

export function Quote({ reason, checkedAt, delay = 0 }) {
  return (
    <figure className="animate-fade-up" style={{ animationDelay: `${delay}ms` }}>
      <blockquote className="border-l-2 border-brand-500/60 pl-3 leading-relaxed">“{reason.sentence}”</blockquote>
      <figcaption className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 pl-3.5 text-xs text-ink/65">
        <span>For: {reason.need_text}</span>
        <Source href={reason.url} delay={delay + 150} />
        <Live status={reason.live} at={checkedAt} />
      </figcaption>
    </figure>
  )
}
