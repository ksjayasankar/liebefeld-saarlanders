import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import App from './App.jsx'
import './index.css'

const root = document.getElementById('root')
// A render error (e.g. a non-http link from the API) replaces the page with the error text instead of a blank screen.
createRoot(root, { onUncaughtError: (e) => { root.textContent = `The page failed to render: ${e.message}` } })
  .render(<StrictMode><App /></StrictMode>)
