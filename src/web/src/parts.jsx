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

export function Quote({ reason, delay = 0 }) {
  return (
    <figure className="animate-fade-up" style={{ animationDelay: `${delay}ms` }}>
      <blockquote className="border-l-2 border-brand-500/60 pl-3 leading-relaxed">“{reason.sentence}”</blockquote>
      <figcaption className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 pl-3.5 text-xs text-ink/65">
        <span>For: {reason.need_text}</span>
        <Source href={reason.url} delay={delay + 150} />
      </figcaption>
    </figure>
  )
}
