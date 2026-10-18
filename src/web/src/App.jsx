import { useEffect, useState } from 'react'
import { api } from './api.js'
import Search from './Search.jsx'
import Results from './Results.jsx'

export default function App() {
  const [health, setHealth] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  // Runs one API call at a time; any error is shown as-is.
  const run = async (fn) => {
    setBusy(true)
    setError(null)
    try { await fn() } catch (e) { setError(e) } finally { setBusy(false) }
  }
  useEffect(() => { api('/api/health').then(setHealth, setError) }, [])
  const show = (r) => { setResult(r); window.scrollTo(0, 0) }

  const domain = health && Object.keys(health.domains)[0]
  return (
    <>
      <header className="sticky top-0 z-10 border-b border-line/10 bg-page/85 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <span aria-hidden="true" className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-600 text-lg font-semibold text-white shadow-pill">N</span>
          <div className="min-w-0">
            <p className="kicker">Bern Economic Development Agency</p>
            <h1 className="truncate font-semibold">Research &amp; Expertise Navigator</h1>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-6 sm:py-10" aria-busy={busy}>
        {domain && <div hidden={result !== null}><Search domain={domain} run={run} busy={busy} onResult={show} /></div>}
        {result && <Results result={result} setResult={setResult} run={run} busy={busy} onBack={() => setResult(null)} />}
      </main>

      <footer className="mx-auto max-w-5xl px-4 pb-24 text-xs text-ink/60">
        {domain && <>Domain {domain} · index build <code>{health.domains[domain].build_id}</code></>}
      </footer>

      <div className="fixed inset-x-4 bottom-4 z-20 mx-auto max-w-2xl space-y-2">
        {busy && (
          <p role="status" className="mx-auto flex w-fit items-center gap-3 rounded-full bg-card px-4 py-2 text-sm shadow-soft">
            <span aria-hidden="true" className="relative size-2.5">
              <span className="absolute inset-0 rounded-full bg-brand-500 motion-safe:animate-ring" />
              <span className="absolute inset-0 rounded-full bg-brand-600" />
            </span>
            Working… Apertus answers can take up to a minute.
          </p>
        )}
        {error && (
          <div role="alert" className="max-h-[50vh] overflow-auto rounded-2xl border-2 border-red-600 bg-card p-4 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <strong className="text-red-700 dark:text-red-300">The request failed.</strong>
              <button type="button" className="btn-ghost px-3 py-1 text-sm" onClick={() => setError(null)}>Dismiss</button>
            </div>
            <pre className="mt-2 text-sm break-words whitespace-pre-wrap">{error.message}</pre>
            {error.requestId && <p className="mt-2 text-sm">Request id: <code>{error.requestId}</code></p>}
          </div>
        )}
      </div>
    </>
  )
}
