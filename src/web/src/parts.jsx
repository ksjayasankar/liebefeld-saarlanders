export const Ext = ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>

export function Reasons({ reasons }) {
  return (
    <ul className="reasons">
      {reasons.map((r, i) => (
        <li key={i}>
          <p><span className="k">Your need:</span> {r.need_text}</p>
          <p><span className="k">Their page says:</span> “{r.sentence}” <Ext href={r.url}>Source</Ext></p>
        </li>
      ))}
    </ul>
  )
}
