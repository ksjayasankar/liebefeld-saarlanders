import { useEffect, useState } from 'react'

// Light / Dark / System, as in the AI-template. index.html applies the stored choice before the first paint.
const KEY = 'navigator-theme'
const DARK = matchMedia('(prefers-color-scheme: dark)')
const ICONS = {
  light: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  dark: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />,
  system: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></>,
}

function stored() {
  try { return localStorage.getItem(KEY) ?? 'system' } catch { return 'system' }
}

export default function Theme() {
  const [theme, setTheme] = useState(stored)
  useEffect(() => {
    const apply = () => document.documentElement.classList.toggle('dark', theme === 'dark' || (theme === 'system' && DARK.matches))
    apply()
    try { if (theme === 'system') localStorage.removeItem(KEY); else localStorage.setItem(KEY, theme) } catch { /* storage blocked: the choice lasts for this visit */ }
    DARK.addEventListener('change', apply)
    return () => DARK.removeEventListener('change', apply)
  }, [theme])

  return (
    <div role="group" aria-label="Colour theme" className="flex shrink-0 rounded-full border border-line/15 bg-card p-0.5">
      {Object.entries(ICONS).map(([t, icon]) => (
        <button key={t} type="button" aria-pressed={theme === t} aria-label={`${t[0].toUpperCase()}${t.slice(1)} theme`} onClick={() => setTheme(t)}
          className="grid size-8 place-items-center rounded-full text-ink/60 transition-colors duration-150 hover:text-ink aria-pressed:bg-surface aria-pressed:text-ink aria-pressed:ring-1 aria-pressed:ring-line/10 aria-pressed:ring-inset">
          <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4 fill-none stroke-current stroke-[1.8] [stroke-linecap:round] [stroke-linejoin:round]">{icon}</svg>
        </button>
      ))}
    </div>
  )
}
