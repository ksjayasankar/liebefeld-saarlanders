import Theme from './Theme.jsx'

// The template's navbar: the XpertVS logo (light and dark versions, a pulsing dot while an agent works), then whatever the screen adds, then the theme menu.
export default function TopBar({ busy, onHome, children }) {
  return (
    <header className="sticky top-0 z-10 border-b border-line/10 bg-page/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
        <button type="button" onClick={onHome} className="flex shrink-0 items-center gap-2.5 rounded-lg" aria-label="XpertVS, new enquiry">
          <img src="/logo.png" alt="" width="361" height="96" className="h-7 w-auto dark:hidden" />
          <img src="/logo-dark.png" alt="" width="361" height="96" className="hidden h-7 w-auto dark:block" />
          {busy && (
            <span aria-hidden="true" className="relative size-2.5">
              <span className="absolute inset-0 animate-ring rounded-full bg-brand-500" />
              <span className="absolute inset-0 rounded-full bg-brand-600" />
            </span>
          )}
        </button>
        <div className="flex min-w-0 flex-1 items-center gap-3">{children}</div>
        <Theme />
      </div>
    </header>
  )
}
