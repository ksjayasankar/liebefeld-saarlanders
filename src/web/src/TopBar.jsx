import Theme from './Theme.jsx'

// The template's navbar: logo mark (pulsing while an agent works), product name, then whatever the screen adds, then the theme menu.
export default function TopBar({ busy, onHome, children }) {
  return (
    <header className="sticky top-0 z-10 border-b border-line/10 bg-page/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
        <button type="button" onClick={onHome} className="flex shrink-0 items-center gap-2.5 rounded-xl" aria-label="Navigator, new enquiry">
          <span aria-hidden="true" className="relative grid size-8 place-items-center">
            {busy && <span className="absolute inset-0 animate-ring rounded-lg bg-brand-500" />}
            <span className={`relative grid size-8 place-items-center rounded-lg bg-brand-600 text-white shadow-pill ${busy ? 'animate-breathe' : ''}`}>
              <svg viewBox="0 0 24 24" className="size-[1.1rem] fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="8.5" /><path d="m15.5 8.5-2.2 4.8-4.8 2.2 2.2-4.8z" className="fill-current" /></svg>
            </span>
          </span>
          <span className="font-semibold tracking-tight">Navigator</span>
        </button>
        {children}
        <Theme />
      </div>
    </header>
  )
}
