import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './ui/App.jsx'
import ErrorBoundary from './ui/ErrorBoundary.jsx'

function installGlobalDebug() {
  // eslint-disable-next-line no-console
  console.info('[App] Debug logging enabled')
  window.addEventListener('error', (e) => {
    // eslint-disable-next-line no-console
    console.error('[window.onerror]', e.message, e.error)
  })
  window.addEventListener('unhandledrejection', (e) => {
    // eslint-disable-next-line no-console
    console.error('[unhandledrejection]', e.reason)
  })
  if (typeof window.fetch === 'function') {
    const origFetch = window.fetch.bind(window)
    window.fetch = async (...args) => {
      const [input, init] = args
      // eslint-disable-next-line no-console
      console.debug('[fetch] →', input, init)
      const t0 = performance.now()
      try {
        const res = await origFetch(...args)
        const t1 = performance.now()
        // eslint-disable-next-line no-console
        console.debug('[fetch] ←', res.status, res.url, `${Math.round(t1 - t0)}ms`)
        return res
      } catch (err) {
        const t1 = performance.now()
        // eslint-disable-next-line no-console
        console.error('[fetch] ×', input, `${Math.round(t1 - t0)}ms`, err)
        throw err
      }
    }
  }
}

installGlobalDebug()

const root = createRoot(document.getElementById('root'))
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
)
