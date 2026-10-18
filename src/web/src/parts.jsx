// Every link to a source page goes through Ext: http(s) only, new tab, no opener.
export function Ext({ href, children, className = 'link' }) {
  if (!/^https?:\/\//i.test(href)) throw new Error(`not an http(s) link: ${href}`)
  return (
    <a className={className} href={href} target="_blank" rel="noopener noreferrer">
      {children}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span>
    </a>
  )
}

// The source address itself, so staff see where a claim comes from before clicking.
export const Source = ({ href }) => <Ext href={href} className="link break-all">{href.replace(/^https?:\/\//i, '')}</Ext>

export function Quote({ reason }) {
  return (
    <figure className="border-l-2 border-brand-400 pl-3">
      <blockquote className="text-sm">“{reason.sentence}”</blockquote>
      <figcaption className="mt-1 text-xs text-ink/70">
        Need: {reason.need_text} · <Source href={reason.url} />
      </figcaption>
    </figure>
  )
}
