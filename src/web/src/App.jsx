import { useEffect, useState } from 'react'
import { api } from './api.js'
import Search from './Search.jsx'
import Results from './Results.jsx'
import Theme from './Theme.jsx'

export default function App() {
  const [health, setHealth] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [task, setTask] = useState(null)   // what the running API call does, shown while it runs

  // Runs one API call at a time; any error is shown as-is.
  const run = async (label, fn) => {
    setTask(label)
    setError(null)
    try { await fn() } catch (e) { setError(e) } finally { setTask(null) }
  }
  useEffect(() => { api('/api/health').then(setHealth, setError) }, [])
  const show = (r) => { setResult(r); window.scrollTo(0, 0) }

  const busy = task !== null
  const domain = health && Object.keys(health.domains)[0]
  return (
    <>
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[28rem] w-[56rem] -translate-x-1/2 animate-drift rounded-full bg-brand-200/30 blur-3xl dark:bg-brand-600/15" />
      </div>

      <header className="sticky top-0 z-10 border-b border-line/10 bg-page/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <span aria-hidden="true" className="relative grid size-9 shrink-0 place-items-center">
            {busy && <span className="absolute inset-0 animate-ring rounded-xl bg-brand-500" />}
            <span className={`relative grid size-9 place-items-center rounded-xl bg-brand-600 text-white shadow-pill ${busy ? 'animate-breathe' : ''}`}>
              <svg viewBox="0 0 24 24" className="size-5 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="8.5" /><path d="m15.5 8.5-2.2 4.8-4.8 2.2 2.2-4.8z" className="fill-current" /></svg>
            </span>
          </span>
          <div className="min-w-0">
            <p className="kicker hidden sm:block">Bern Economic Development Agency</p>
            <h1 className="leading-tight font-semibold tracking-tight">Research &amp; Expertise Navigator</h1>
          </div>
          <Theme />
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:py-12" aria-busy={busy}>
        {domain && <div hidden={result !== null}><Search domain={domain} run={run} busy={busy} onResult={show} /></div>}
        {result && <Results result={result} setResult={setResult} run={run} busy={busy} onBack={() => setResult(null)} />}
      </main>

      <footer className="mx-auto max-w-5xl px-4 pb-24 text-xs text-ink/55">
        {domain && <>Domain {domain} · index build <code className="tabular-nums">{health.domains[domain].build_id}</code></>}
      </footer>

      <div className="fixed inset-x-4 bottom-4 z-20 mx-auto max-w-2xl space-y-2">
        {busy && (
          <p role="status" className="mx-auto flex w-fit animate-fade-up items-center gap-3 rounded-full border border-line/10 bg-card px-4 py-2 text-sm shadow-panel">
            <span aria-hidden="true" className="relative size-2.5 shrink-0">
              <span className="absolute inset-0 animate-ring rounded-full bg-brand-500" />
              <span className="absolute inset-0 rounded-full bg-brand-600" />
            </span>
            {task}
          </p>
        )}
        {error && (
          <div role="alert" className="max-h-[50vh] animate-fade-up overflow-auto rounded-2xl border border-red-600/40 bg-card p-4 shadow-panel">
            <div className="flex items-start justify-between gap-3">
              <p className="font-semibold text-red-700 dark:text-red-300">The request failed.</p>
              <button type="button" className="btn-ghost px-3 py-1" onClick={() => setError(null)}>Dismiss</button>
            </div>
            <pre className="mt-2 text-sm break-words whitespace-pre-wrap">{error.message}</pre>
            {error.requestId && <p className="mt-2 text-sm">Request id: <code>{error.requestId}</code></p>}
          </div>
        )}
      </div>
    </>
  )
}
