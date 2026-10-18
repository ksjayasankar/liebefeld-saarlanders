const BASE = import.meta.env.VITE_API_BASE
if (typeof BASE !== 'string') throw new Error('VITE_API_BASE must be set (web/.env)')

export const apiUrl = (path) => `${BASE}${path}`

// GET when body is undefined, POST JSON otherwise. Non-2xx throws an Error carrying detail and request_id.
export async function api(path, body) {
  const init = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
  const res = await fetch(apiUrl(path), init)
  const data = await res.json()
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail, null, 2)
    throw Object.assign(new Error(`${res.status} ${res.statusText}\n${detail}`), { requestId: data.request_id })
  }
  return data
}
