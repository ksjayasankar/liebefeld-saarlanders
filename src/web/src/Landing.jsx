import { useState } from 'react'
import { api } from './api.js'
import { AGENTS, AgentBadge, Icon } from './agents.jsx'
import TopBar from './TopBar.jsx'

// Made-up business models, one click away, so a first visit can see a run without pasting anything.
const EXAMPLES = {
  'Wearable glucose sensor': 'We are a Zurich startup developing a non-invasive wearable glucose sensor for people with type 2 diabetes. The prototype works in the lab. We now need a clinical partner for a validation study and expertise in biomedical signal processing.',
  'Spine surgery robot': 'Our company builds a robotic arm for minimally invasive spine surgery. We are looking for surgeons who can test it, a research group in image-guided navigation, and support with medical device certification in Switzerland.',
  'CT scan AI': 'We develop software that detects early signs of lung disease on CT scans. We need annotated imaging data, a hospital radiology department for a pilot, and researchers in medical image analysis.',
}
const LIMITS = { model: [20, 20000], keyword: [3, 300] }   // DraftRequest.description, Need.text

function PromptBox({ onStart, ready, run, domain }) {
  const [mode, setMode] = useState('model')
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)   // { name, pages } of the PDF the text was read from; no pages while it is read
  const [drag, setDrag] = useState(false)
  const [min, max] = LIMITS[mode]
  const reading = file !== null && file.pages === undefined
  const over = text.length > max
  const submit = (e) => { e.preventDefault(); onStart(text.trim(), mode === 'keyword') }
  const keyDown = (e) => {
    if (e.key === 'Enter' && (mode === 'keyword' ? !e.shiftKey : e.metaKey || e.ctrlKey)) e.currentTarget.form.requestSubmit()
  }
  const readPdf = (f) => run('pdf', async () => {
    setFile({ name: f.name })
    try {
      const d = await api(`/api/${domain}/need-card/pdf`, f)
      setText(d.text)
      setFile({ name: f.name, pages: d.pages })
    } catch (e) { setFile(null); throw e }
  })
  const attachable = ready && !reading
  const drop = {   // always handled, so a PDF dropped on the box never replaces the page
    onDragOver: (e) => { e.preventDefault(); setDrag(attachable) },
    onDragLeave: (e) => { if (!e.currentTarget.contains(e.relatedTarget)) setDrag(false) },
    onDrop: (e) => { e.preventDefault(); setDrag(false); if (attachable) { setMode('model'); readPdf(e.dataTransfer.files[0]) } },
  }
  return (
    <form onSubmit={submit} className="w-full">
      <label htmlFor="prompt" className="sr-only">{mode === 'model' ? 'Company business model' : 'Keyword search'}</label>
      <div {...drop} className={`rounded-3xl border border-line/10 bg-card p-2 text-left shadow-panel transition-shadow focus-within:ring-2 focus-within:ring-brand-500/60 ${drag ? 'ring-2 ring-brand-500/60' : ''}`}>
        {mode === 'model' && file && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 pt-1">
            <p role="status" className="flex min-w-0 items-center gap-2 rounded-full bg-surface py-0.5 pr-1 pl-3 text-sm">
              <Icon className="size-4 text-brand-600 dark:text-brand-300"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /></Icon>
              <span className="truncate font-medium">{file.name}</span>
              {reading
                ? <><span className="size-3.5 shrink-0 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" /><span className="pr-3 text-ink/60">Reading…</span></>
                : <><span className="shrink-0 text-ink/60 tabular-nums">{file.pages} {file.pages === 1 ? 'page' : 'pages'}</span>
                    <button type="button" className="grid size-10 shrink-0 place-items-center rounded-full -my-2 text-ink/60 hover:bg-card hover:text-ink" onClick={() => setFile(null)} aria-label={`Remove note about ${file.name}`}>
                      <Icon><path d="M18 6 6 18M6 6l12 12" /></Icon>
                    </button></>}
            </p>
            {!reading && <p className="hint text-xs">Check and edit the text: everything in this box, including text hidden in the PDF, is what Apertus reads.</p>}
          </div>
        )}
        <textarea id="prompt" rows={mode === 'model' ? 5 : 2} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={keyDown}
          required minLength={min} className="block w-full resize-none bg-transparent px-3 py-2 leading-relaxed outline-none placeholder:text-ink/45"
          placeholder={mode === 'model' ? "Paste the company's business model, or drop a PDF…" : 'e.g. clinical validation of a glucose sensor'} />
        <div className="flex items-center gap-2 px-1 pt-1">
          {mode === 'model' && (
            <label title="Upload PDF" className="grid size-10 shrink-0 cursor-pointer place-items-center rounded-full text-ink/60 transition-colors hover:bg-surface hover:text-ink has-disabled:pointer-events-none has-disabled:opacity-40 has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-brand-500">
              <span className="sr-only">Upload PDF</span>
              <input type="file" accept="application/pdf,.pdf" className="sr-only" disabled={!attachable}
                onChange={(e) => { const f = e.target.files[0]; e.target.value = ''; readPdf(f) }} />
              <Icon className="size-5"><path d="m21 11.5-8.6 8.6a5.5 5.5 0 0 1-7.8-7.8l8.6-8.6a3.7 3.7 0 0 1 5.2 5.2l-8.6 8.6a1.8 1.8 0 0 1-2.6-2.6l7.9-7.9" /></Icon>
            </label>
          )}
          <div role="radiogroup" aria-label="Input type" className="flex rounded-full bg-surface p-0.5 text-sm">
            {[['model', 'Business model'], ['keyword', 'Keyword']].map(([m, label]) => (
              <button key={m} type="button" role="radio" aria-checked={mode === m} onClick={() => setMode(m)}
                className="rounded-full px-3 py-1 font-medium text-ink/60 transition-colors hover:text-ink aria-checked:bg-card aria-checked:text-ink aria-checked:shadow-soft">{label}</button>
            ))}
          </div>
          <span className={`text-xs tabular-nums sm:ml-auto ${over ? 'font-medium text-red-600 dark:text-red-400' : 'hidden text-ink/50 sm:block'}`}>{text.length} / {max}</span>
          <button className="ml-auto grid size-9 place-items-center rounded-full bg-brand-600 text-white shadow-pill transition hover:bg-brand-700 active:scale-95 disabled:bg-ink/15 disabled:text-ink/50 disabled:shadow-none sm:ml-0"
            disabled={!ready || reading || over || text.trim().length < min} aria-label={mode === 'model' ? 'Draft needs' : 'Search'}>
            <Icon><path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" /></Icon>
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {Object.entries(EXAMPLES).map(([label, model]) => (
          <button key={label} type="button" className="chip" disabled={reading} onClick={() => { setMode('model'); setText(model); setFile(null) }}>{label}</button>
        ))}
      </div>
    </form>
  )
}

// The template's chat preview card, redrawn as a finished run: the enquiry, the agents' progress and one lead.
function Preview() {
  return (
    <div aria-hidden="true" className="mx-auto mt-16 grid max-w-4xl gap-4 rounded-3xl border border-line/10 bg-card p-4 text-left text-sm shadow-panel sm:mt-20 sm:grid-cols-[1fr_15rem] sm:p-6">
      <div className="space-y-4">
        <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md border border-line/10 bg-surface px-4 py-3 text-ink/80">Wearable glucose sensor, needs a clinical validation partner and signal-processing expertise…</p>
        {[0, 1].map((i) => (   // lead cards drawn as placeholder lines: no invented unit or source
          <div key={i} className="space-y-2 rounded-xl border border-line/10 bg-card p-4">
            <div className="h-3 w-1/2 rounded-full bg-ink/15" />
            <div className="h-2 w-1/3 rounded-full bg-ink/10" />
            <div className="space-y-1.5 border-l-2 border-brand-500/60 py-0.5 pl-3"><div className="h-2 rounded-full bg-ink/10" /><div className="h-2 w-4/5 rounded-full bg-ink/10" /></div>
            <div className="h-4 w-24 rounded-full border border-line/15" />
          </div>
        ))}
      </div>
      <ul className="space-y-3 self-start rounded-xl bg-surface p-4">
        {Object.keys(AGENTS).map((id) => (
          <li key={id} className="flex items-center gap-2.5">
            <AgentBadge id={id} className="size-7" />
            <span className="min-w-0 flex-1 truncate font-medium text-ink/85">{AGENTS[id].name}</span>
            <Icon className="size-4 text-emerald-600 dark:text-emerald-400"><circle cx="12" cy="12" r="9" /><path d="m8.5 12 2.5 2.5 4.5-5" /></Icon>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Landing({ health, onStart, run }) {
  const counts = health && Object.values(health.domains)[0].counts
  return (
    <>
      <TopBar onHome={() => window.scrollTo(0, 0)}>
        <a href="#agents" className="ml-auto hidden rounded-full px-3 py-1.5 text-sm font-medium text-ink/70 transition-colors duration-150 hover:bg-surface hover:text-ink sm:block">How it works</a>
      </TopBar>

      <main className="mx-auto max-w-5xl px-4">
        <section className="animate-fade-up pt-16 text-center sm:pt-24">
          <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
            Find the right partners in Bern, <span className="text-brand-600 dark:text-brand-400">with sources</span>.
          </h1>
          {counts && (
            <p className="mt-6 text-ink/70 tabular-nums">{counts.units.toLocaleString('en-GB')} research units · {counts.people.toLocaleString('en-GB')} people · every claim linked to its page</p>
          )}
          <div className="mx-auto mt-10 max-w-2xl"><PromptBox onStart={onStart} ready={health !== null} run={run} domain={health && Object.keys(health.domains)[0]} /></div>
          <Preview />
        </section>

        <section id="agents" className="scroll-mt-20 py-20 sm:py-24" aria-labelledby="agents-title">
          <h2 id="agents-title" className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">Four agents, one enquiry</h2>
          <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(AGENTS).map(([id, a], i) => (
              <li key={id} className="card flex animate-fade-up flex-col" style={{ animationDelay: `${i * 60}ms` }}>
                <div className="flex items-center justify-between"><AgentBadge id={id} className="size-10" /><span className="tag">{a.model}</span></div>
                <h3 className="mt-5 font-semibold tracking-tight">{a.name}</h3>
                <p className="hint mt-1">{a.line}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="border-t border-line/10 bg-card/50">
        <p className="mx-auto max-w-5xl px-4 py-6 text-xs text-ink/65">Bern Economic Development Agency{health && <> · index build <code className="tabular-nums">{Object.values(health.domains)[0].build_id}</code></>}</p>
      </footer>
    </>
  )
}
