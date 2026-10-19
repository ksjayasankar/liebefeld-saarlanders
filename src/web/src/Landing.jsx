import { useState } from 'react'
import { AGENTS, AgentBadge, Icon } from './agents.jsx'
import TopBar from './TopBar.jsx'

// Made-up business models, one click away, so a first visit can see a run without pasting anything.
const EXAMPLES = {
  'Wearable glucose sensor': 'We are a Zurich startup developing a non-invasive wearable glucose sensor for people with type 2 diabetes. The prototype works in the lab. We now need a clinical partner for a validation study and expertise in biomedical signal processing.',
  'Spine surgery robot': 'Our company builds a robotic arm for minimally invasive spine surgery. We are looking for surgeons who can test it, a research group in image-guided navigation, and support with medical device certification in Switzerland.',
  'CT scan AI': 'We develop software that detects early signs of lung disease on CT scans. We need annotated imaging data, a hospital radiology department for a pilot, and researchers in medical image analysis.',
}
const LIMITS = { model: [20, 5000], keyword: [3, 300] }

function PromptBox({ onStart, ready }) {
  const [mode, setMode] = useState('model')
  const [text, setText] = useState('')
  const [min, max] = LIMITS[mode]
  const submit = (e) => { e.preventDefault(); onStart(text.trim(), mode === 'keyword') }
  const keyDown = (e) => {
    if (e.key === 'Enter' && (mode === 'keyword' ? !e.shiftKey : e.metaKey || e.ctrlKey)) e.currentTarget.form.requestSubmit()
  }
  return (
    <form onSubmit={submit} className="w-full">
      <label htmlFor="prompt" className="sr-only">{mode === 'model' ? 'Company business model' : 'Keyword search'}</label>
      <div className="rounded-3xl border border-line/10 bg-card p-2 text-left shadow-panel transition-shadow focus-within:ring-2 focus-within:ring-brand-500/60">
        <textarea id="prompt" rows={mode === 'model' ? 5 : 2} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={keyDown}
          required minLength={min} maxLength={max} className="block w-full resize-none bg-transparent px-3 py-2 leading-relaxed outline-none placeholder:text-ink/45"
          placeholder={mode === 'model' ? "Paste the company's business model…" : 'e.g. clinical validation of a glucose sensor'} />
        <div className="flex items-center gap-2 px-1 pt-1">
          <div role="radiogroup" aria-label="Input type" className="flex rounded-full bg-surface p-0.5 text-sm">
            {[['model', 'Business model'], ['keyword', 'Keyword']].map(([m, label]) => (
              <button key={m} type="button" role="radio" aria-checked={mode === m} onClick={() => setMode(m)}
                className="rounded-full px-3 py-1 font-medium text-ink/60 transition-colors hover:text-ink aria-checked:bg-card aria-checked:text-ink aria-checked:shadow-soft">{label}</button>
            ))}
          </div>
          <span className="ml-auto hidden text-xs text-ink/50 tabular-nums sm:block">{text.length} / {max}</span>
          <button className="grid size-9 place-items-center rounded-full bg-brand-600 text-white shadow-pill transition hover:bg-brand-700 active:scale-95 disabled:opacity-40 disabled:shadow-none"
            disabled={!ready || text.trim().length < min} aria-label={mode === 'model' ? 'Draft needs' : 'Search'}>
            <Icon><path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" /></Icon>
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {Object.entries(EXAMPLES).map(([label, model]) => (
          <button key={label} type="button" className="chip" onClick={() => { setMode('model'); setText(model) }}>{label}</button>
        ))}
      </div>
    </form>
  )
}

// The template's chat preview card, redrawn as a finished run: the enquiry, the agents' progress and one lead.
function Preview() {
  return (
    <div aria-hidden="true" className="mx-auto mt-16 grid max-w-4xl gap-4 rounded-3xl border border-line/10 bg-card/70 p-4 text-left text-sm shadow-panel backdrop-blur sm:grid-cols-[1fr_15rem] sm:p-5">
      <div className="space-y-4">
        <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-surface px-3.5 py-2.5 text-ink/80">Wearable glucose sensor, needs a clinical validation partner and signal-processing expertise…</p>
        {[0, 1].map((i) => (   // lead cards drawn as placeholder lines: no invented unit or source
          <div key={i} className="space-y-2 rounded-2xl border border-line/10 bg-card p-4">
            <div className="h-3 w-1/2 rounded-full bg-ink/15" />
            <div className="h-2 w-1/3 rounded-full bg-ink/10" />
            <div className="ml-0.5 space-y-1.5 border-l-2 border-brand-400 py-0.5 pl-3"><div className="h-2 rounded-full bg-ink/10" /><div className="h-2 w-4/5 rounded-full bg-ink/10" /></div>
            <div className="h-4 w-24 rounded-full border border-line/15" />
          </div>
        ))}
      </div>
      <ul className="space-y-3 rounded-2xl bg-surface p-3.5">
        {Object.keys(AGENTS).map((id) => (
          <li key={id} className="flex items-center gap-2.5">
            <AgentBadge id={id} className="size-7" />
            <span className="min-w-0 flex-1 truncate font-medium">{AGENTS[id].name}</span>
            <Icon className="size-4 text-emerald-600 dark:text-emerald-400"><circle cx="12" cy="12" r="9" /><path d="m8.5 12 2.5 2.5 4.5-5" /></Icon>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Landing({ health, onStart }) {
  const counts = health && Object.values(health.domains)[0].counts
  return (
    <>
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[28rem] w-[56rem] -translate-x-1/2 animate-drift rounded-full bg-brand-200/30 blur-3xl dark:bg-brand-600/15" />
      </div>
      <TopBar onHome={() => window.scrollTo(0, 0)}>
        <a href="#agents" className="ml-auto hidden text-sm font-medium text-ink/70 hover:text-ink sm:block">How it works</a>
      </TopBar>

      <main className="mx-auto max-w-5xl px-4">
        <section className="animate-fade-up pt-16 text-center sm:pt-24">
          <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
            Find the right partners in Bern, <span className="text-brand-600 dark:text-brand-300">with sources</span>.
          </h1>
          {counts && (
            <p className="mt-5 text-ink/65 tabular-nums">{counts.units.toLocaleString('en-GB')} research units · {counts.people.toLocaleString('en-GB')} people · every claim linked to its page</p>
          )}
          <div className="mx-auto mt-10 max-w-2xl"><PromptBox onStart={onStart} ready={health !== null} /></div>
          <Preview />
        </section>

        <section id="agents" className="scroll-mt-20 py-24" aria-labelledby="agents-title">
          <h2 id="agents-title" className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">Four agents, one enquiry</h2>
          <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(AGENTS).map(([id, a], i) => (
              <li key={id} className="card animate-fade-up" style={{ animationDelay: `${i * 60}ms` }}>
                <div className="flex items-center justify-between"><AgentBadge id={id} className="size-10" /><span className="tag">{a.model}</span></div>
                <h3 className="mt-4 font-semibold">{a.name}</h3>
                <p className="hint mt-1">{a.line}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="border-t border-line/10">
        <p className="mx-auto max-w-5xl px-4 py-6 text-xs text-ink/55">Bern Economic Development Agency{health && <> · index build <code className="tabular-nums">{Object.values(health.domains)[0].build_id}</code></>}</p>
      </footer>
    </>
  )
}
