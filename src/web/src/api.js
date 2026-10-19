const BASE = import.meta.env.VITE_API_BASE
if (typeof BASE !== 'string') throw new Error('VITE_API_BASE must be set (web/.env)')

export const apiUrl = (path) => `${BASE}${path}`
const JSON_POST = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

// Non-2xx throws an Error carrying detail and request_id.
async function fail(res) {
  const data = await res.json()
  const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail, null, 2)
  throw Object.assign(new Error(`${res.status} ${res.statusText}\n${detail}`), { requestId: data.request_id })
}

// GET when body is undefined, the file itself when it is a File (PDF upload), JSON otherwise.
export async function api(path, body) {
  const init = body === undefined ? {}
    : body instanceof File ? { method: 'POST', headers: { 'Content-Type': 'application/pdf' }, body }
    : JSON_POST(body)
  const res = await fetch(apiUrl(path), init)
  if (!res.ok) await fail(res)
  return res.json()
}

// The NDJSON search stream (D-30): every step goes to onStep; returns the result line, throws on the error line.
export async function stream(path, body, onStep) {
  const res = await fetch(apiUrl(path), JSON_POST(body))
  if (!res.ok) await fail(res)
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) throw new Error('the search stream ended without a result')
    const lines = (buffer + value).split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      const e = JSON.parse(line)
      if (e.step === 'result') return e.result
      if (e.step === 'error') throw Object.assign(new Error(e.detail), { requestId: e.request_id })
      onStep(e)
    }
  }
}
