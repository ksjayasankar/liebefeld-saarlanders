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

  const domain = health && Object.keys(health.domains)[0]
  return (
    <>
      <header className="top">
        <div className="wrap">
          <p className="org">Bern economic development agency</p>
          <h1>Research &amp; Expertise Navigator</h1>
          <p>Find research groups, labs and support in Bern that match what your company needs.</p>
        </div>
      </header>
      <main className="wrap" aria-busy={busy}>
        {error && (
          <div className="error" role="alert">
            <strong>The request failed.</strong>
            <pre>{error.message}</pre>
            {error.requestId && <p>Request id: <code>{error.requestId}</code></p>}
          </div>
        )}
        {busy && <p className="status" role="status">Working…</p>}
        {domain && <div hidden={result !== null}><Search domain={domain} run={run} busy={busy} onResult={setResult} /></div>}
        {result && <Results result={result} setResult={setResult} run={run} busy={busy} onBack={() => setResult(null)} />}
      </main>
      <footer className="wrap foot">
        {domain && <>Domain {domain} · index build <code>{health.domains[domain].build_id}</code></>}
      </footer>
    </>
  )
}
