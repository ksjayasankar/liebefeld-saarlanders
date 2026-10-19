import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { From } from './agents.jsx'
import Landing from './Landing.jsx'
import NeedCard from './NeedCard.jsx'
import Progress from './Progress.jsx'
import Results from './Results.jsx'
import TopBar from './TopBar.jsx'

// The enquiry the staff typed, shown as their message at the top of the thread.
function Enquiry({ text }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="ml-auto max-w-2xl animate-fade-up rounded-3xl rounded-br-md bg-surface px-4 py-3">
      <p className={`whitespace-pre-wrap ${open ? '' : 'line-clamp-4'}`}>{text}</p>
      {text.length > 300 && <button type="button" className="link mt-1 text-sm" onClick={() => setOpen(!open)}>{open ? 'Show less' : 'Show all'}</button>}
    </div>
  )
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [enquiry, setEnquiry] = useState(null)   // { text, keyword }
  const [draft, setDraft] = useState(null)
  const [card, setCard] = useState(null)
  const [result, setResult] = useState(null)
  const [task, setTask] = useState(null)         // 'draft' | 'search' | 'rerank' while a call runs
  const [error, setError] = useState(null)
  const end = useRef(null)
  useEffect(() => { api('/api/health').then(setHealth, setError) }, [])
  useEffect(() => { if (task) end.current?.scrollIntoView({ block: 'end' }) }, [task])
  useEffect(() => { if (result && !result.message) document.getElementById('leads').scrollIntoView() }, [result])   // a new search, not a re-rank

  // Runs one API call at a time; any error is shown as-is.
  const run = async (name, fn) => {
    setTask(name)
    setError(null)
    try { await fn() } catch (e) { setError(e) } finally { setTask(null) }
  }
  const domain = health && Object.keys(health.domains)[0]
  const search = (c) => run('search', async () => setResult(await api(`/api/${domain}/search`, { card: c })))
  const start = (text, keyword) => {
    setEnquiry({ text, keyword })
    setDraft(null)
    setResult(null)
    window.scrollTo(0, 0)
    if (keyword) {
      const c = { needs: [{ id: 'n1', text }] }
      setCard(c)
      search(c)
    } else {
      setCard(null)
      run('draft', async () => {
        const d = await api(`/api/${domain}/need-card/draft`, { description: text })
        setDraft(d)
        setCard(d.card)
      })
    }
  }
  const reset = () => { setEnquiry(null); setDraft(null); setCard(null); setResult(null); setError(null) }

  const busy = task !== null
  const title = card?.product ?? card?.needs[0].text
  return (
    <>
      {!enquiry
        ? <Landing health={health} onStart={start} />
        : <>
            <TopBar busy={busy} onHome={reset}>
              <p className="hidden min-w-0 flex-1 truncate border-l border-line/15 pl-3 text-sm text-ink/70 sm:block">{title}</p>
              <button type="button" className="btn-ghost ml-auto px-3.5 py-1.5 sm:ml-0" onClick={reset} disabled={busy}>New enquiry</button>
            </TopBar>
            <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[minmax(0,1fr)_19rem] lg:py-8" aria-busy={busy}>
              <aside className="lg:sticky lg:top-20 lg:order-2 lg:self-start" aria-label="Agents">
                <Progress keyword={enquiry.keyword} draft={draft} card={card} result={result} task={task} />
              </aside>
              <main className="min-w-0 space-y-8">
                <Enquiry text={enquiry.text} />
                {draft && <NeedCard draft={draft} card={card} setCard={setCard} onSearch={search} busy={busy} searched={result !== null} />}
                {result && <Results result={result} setResult={setResult} run={run} busy={busy} />}
                {busy && (
                  <From ids={task === 'draft' ? ['analyst'] : ['scout', 'checker']}>
                    <span className="text-sm text-ink/60">{task === 'draft' ? 'is reading the business model…' : 'are searching and checking sources…'}</span>
                  </From>
                )}
                <div ref={end} />
              </main>
            </div>
          </>}

      {error && (
        <div role="alert" className="fixed inset-x-4 bottom-4 z-20 mx-auto max-h-[50vh] max-w-2xl animate-fade-up overflow-auto rounded-2xl border border-red-600/40 bg-card p-4 shadow-panel">
          <div className="flex items-start justify-between gap-3">
            <p className="font-semibold text-red-700 dark:text-red-300">The request failed.</p>
            <button type="button" className="btn-ghost px-3 py-1" onClick={() => setError(null)}>Dismiss</button>
          </div>
          <pre className="mt-2 text-sm break-words whitespace-pre-wrap">{error.message}</pre>
          {error.requestId && <p className="mt-2 text-sm">Request id: <code>{error.requestId}</code></p>}
        </div>
      )}
    </>
  )
}
