import React, { useEffect, useState, useMemo } from 'react'
import AudioPlayer from './AudioPlayer.jsx'
import { SkeletonCard } from './Skeleton.jsx'

function SplashScreen({ show }) {
  if (!show) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-slate-900">
      <div className="text-center">
        <div className="text-5xl mb-4">📰</div>
        <div className="text-xl font-semibold mb-2">Local News & Weather</div>
        <div className="flex items-center justify-center gap-2 text-slate-600 dark:text-slate-300">
          <span className="inline-block w-4 h-4 rounded-full border-2 border-slate-300 border-t-blue-600 animate-spin" aria-hidden="true"></span>
          <span>Loading…</span>
        </div>
      </div>
    </div>
  )
}

function PwaInstallPrompt() {
  const [deferred, setDeferred] = useState(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const dismissed = localStorage.getItem('pwa-install-dismissed')
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone
    if (isStandalone) return
    function onBeforeInstall(e) {
      e.preventDefault()
      if (dismissed) return // user dismissed recently
      setDeferred(e)
      setVisible(true)
    }
    function onInstalled() {
      setVisible(false)
      setDeferred(null)
    }
    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [])

  if (!visible) return null

  function install() {
    if (!deferred) return
    deferred.prompt()
    deferred.userChoice.finally(() => {
      setVisible(false)
      setDeferred(null)
    })
  }
  function dismiss() {
    try { localStorage.setItem('pwa-install-dismissed', String(Date.now())) } catch (_) {}
    setVisible(false)
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-40">
      <div className="mx-auto max-w-[1100px] rounded-xl shadow-lg border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-800 px-4 py-3 flex items-center gap-3">
        <div className="text-2xl">📲</div>
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">Install as an app</div>
          <div className="text-sm text-slate-600 dark:text-slate-300 truncate">Add to your home screen for faster access.</div>
        </div>
        <button onClick={dismiss} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700">Not now</button>
        <button onClick={install} className="px-3 py-2 rounded-md bg-blue-600 text-white">Install</button>
      </div>
    </div>
  )
}

function ThemeToggle() {
  const [isDark, setIsDark] = useState(false)
  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'))
  }, [])
  function toggle() {
    const next = !isDark
    setIsDark(next)
    const root = document.documentElement
    const body = document.body
    if (next) { root.classList.add('dark'); body && body.classList.add('dark') }
    else { root.classList.remove('dark'); body && body.classList.remove('dark') }
    try { localStorage.setItem('theme', next ? 'dark' : 'light') } catch (_) {}
  }
  const label = isDark ? 'Switch to light mode' : 'Switch to dark mode'
  return (
    <button
      onClick={toggle}
      title={label}
      aria-label={label}
      className="px-2 py-2 rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
    >
      {isDark ? '🌞' : '🌙'}
    </button>
  )
}

function ArticleChat({ articleId, initialAuthor }) {
  const [messages, setMessages] = useState([])
  const [author, setAuthor] = useState(initialAuthor || 'Local Desk')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    let ignore = false
    async function load() {
      setErr('')
      try {
        const res = await fetch(`/api/articles/${articleId}/chat`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (ignore) return
        setAuthor(data?.author || author)
        setMessages(Array.isArray(data?.messages) ? data.messages.map(m => ({ role: m.role === 'user' ? 'user' : 'ai', content: m.content })) : [])
      } catch (e) {
        if (!ignore) setErr('Failed to load conversation')
      }
    }
    load()
    return () => { ignore = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [articleId])

  async function send() {
    const msg = text.trim()
    if (!msg || busy) return
    setText('')
    setErr('')
    const history = messages.map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.content }))
    const next = [...messages, { role: 'user', content: msg }]
    setMessages(next)
    setBusy(true)
    try {
      const res = await fetch(`/api/articles/${articleId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAuthor(data?.author || author)
      const reply = (data?.reply || '').trim()
      setMessages(m => [...m, { role: 'ai', content: reply || '(no reply)' }])
    } catch (e) {
      if (e?.message?.includes('429')) setErr('You are sending messages too quickly. Please wait a moment.')
      else setErr('Failed to send message')
    } finally {
      setBusy(false)
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-900/40">
      <div className="px-3 py-2 border-b border-slate-200/60 dark:border-slate-700/60 text-sm text-slate-600 dark:text-slate-300 flex items-center">
        <div className="flex-1">Discuss with {author}</div>
        <button onClick={async ()=>{
          setErr('')
          try {
            const res = await fetch(`/api/articles/${articleId}/chat`, { method: 'DELETE' })
            if (!res.ok) throw new Error('HTTP '+res.status)
            setMessages([])
          } catch (e) {
            setErr('Failed to clear conversation')
          }
        }} className="text-xs px-2 py-1 rounded-md border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800">Clear</button>
      </div>
      <div className="p-3 space-y-2 max-h-64 overflow-auto">
        {messages.length === 0 && (
          <div className="text-sm text-slate-500">Start the conversation — ask a question about this article.</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`text-sm ${m.role === 'user' ? 'text-slate-900 dark:text-slate-100' : 'text-slate-800 dark:text-slate-200'}`}>
            <span className="font-medium mr-2">{m.role === 'user' ? 'You' : author}:</span>
            <span className="whitespace-pre-wrap">{m.content}</span>
          </div>
        ))}
      </div>
      <div className="p-3 border-t border-slate-200/60 dark:border-slate-700/60 flex items-start gap-2">
        <textarea value={text} onChange={e=>setText(e.target.value)} onKeyDown={onKey} rows={2} placeholder="Write a comment or question" className="flex-1 px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" />
        <button onClick={send} disabled={busy || !text.trim()} className={`px-3 py-2 rounded-md ${busy || !text.trim() ? 'bg-slate-400' : 'bg-blue-600 hover:bg-blue-700'} text-white`}>{busy ? 'Sending…' : 'Send'}</button>
      </div>
      {err && <div className="px-3 pb-2 text-xs text-red-500">{err}</div>}
    </div>
  )
}

function Header({ location, onRunNow, running, onOpenSettings }) {
  return (
    <header>
      <div className="h-1 bg-gradient-to-r from-blue-500 via-cyan-500 to-emerald-500" />
      <div className="bg-white/80 dark:bg-slate-900/80 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-slate-900/60 border-b border-slate-200/60 dark:border-slate-800">
        <div className="max-w-[1100px] mx-auto px-4 py-4 flex items-center gap-4">
          <div className="text-2xl">📰</div>
          <div className="flex-1 min-w-0">
            <div className="text-xl font-semibold truncate">Local News & Weather</div>
            <div className="text-sm text-slate-500 truncate">Powered by Ollama · {location || 'Resolving…'}</div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <ThemeToggle />
            <button disabled={running} onClick={onRunNow} className={`px-3 md:px-4 py-2 rounded-md ${running ? 'bg-slate-400' : 'bg-blue-600 hover:bg-blue-700'} text-white transition-colors`}>
              {running ? 'Running…' : 'Run Now'}
            </button>
            <button onClick={onOpenSettings} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition-colors">Settings</button>
          </div>
        </div>
      </div>
    </header>
  )
}

function Weather({ weather, tts }) {
  const days = weather?.forecast?.daily?.time?.length || 0
  const codes = weather?.forecast?.daily?.weathercode || []
  const dailyMax = weather?.forecast?.daily?.temperature_2m_max || []
  const dailyMin = weather?.forecast?.daily?.temperature_2m_min || []
  function iconFor(code) {
    const n = Number(code)
    if ([0].includes(n)) return '☀️ Clear'
    if ([1,2].includes(n)) return '🌤️ Partly Cloudy'
    if ([3].includes(n)) return '☁️ Cloudy'
    if ([45,48].includes(n)) return '🌫️ Fog'
    if ([51,53,55,56,57].includes(n)) return '🌦️ Drizzle'
    if ([61,63,65,66,67].includes(n)) return '🌧️ Rain'
    if ([71,73,75,77,85,86].includes(n)) return '❄️ Snow'
    if ([80,81,82].includes(n)) return '🌧️ Showers'
    if ([95,96,99].includes(n)) return '⛈️ Thunder'
    return '🌡️ Weather'
  }
  return (
    <section className="md:col-span-1 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700/60">
      <div className="p-5 border-b border-slate-200/60 dark:border-slate-700/60 flex items-center gap-2">
        <div className="text-2xl">☀️</div>
        <div className="font-semibold">Weather</div>
      </div>
      <div className="p-5 space-y-4">
        {weather?.updated_at && (
          <div className="text-sm text-slate-500">Updated: {new Date(weather.updated_at).toLocaleString()}</div>
        )}
        {weather?.report_note && (
          <div className="text-xs px-2 py-1 rounded bg-amber-100 text-amber-800 inline-block dark:bg-amber-900/40 dark:text-amber-300">{weather.report_note}</div>
        )}
        {weather?.report ? (
          <div className="prose dark:prose-invert max-w-none" dangerouslySetInnerHTML={{__html: weather.report.replaceAll('\n','<br/>')}} />
        ) : (
          <div className="text-slate-500">Weather report is generating…</div>
        )}
        {tts?.enabled && weather?.report && (
          <div className="mt-2">
            <AudioPlayer fetchUrl={`/api/tts/weather?${tts?.voice ? ('voice='+encodeURIComponent(tts.voice)+'&') : ''}ts=${encodeURIComponent(weather.updated_at||'')}`} />
          </div>
        )}
        {days > 0 && (
          <div className="mt-4 text-sm">
            <div className="font-medium mb-2">5‑Day Forecast</div>
            <div className="grid grid-cols-1 gap-2">
              {Array.from({ length: Math.min(days, 5) }).map((_, i) => (
                <div className="flex justify-between bg-slate-50 dark:bg-slate-900/50 rounded-md p-2" key={i}>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{iconFor(codes[i])?.split(' ')[0]}</span>
                    <div>
                      <div className="font-medium">{weather.forecast.daily.time[i]}</div>
                      <div className="text-slate-500 text-xs">{iconFor(codes[i])}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div>High: {weather.forecast.daily.temperature_2m_max[i]}°</div>
                    <div>Low: {weather.forecast.daily.temperature_2m_min[i]}°</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {weather?.latitude && weather?.longitude && (
          <div className="mt-4">
            <div className="font-medium mb-2">Radar</div>
            <div className="rounded-lg overflow-hidden border border-slate-200/60 dark:border-slate-700/60">
              <iframe title="radar" className="w-full" style={{height:'320px'}} src={`https://embed.windy.com/embed2.html?lat=${encodeURIComponent(weather.latitude)}&lon=${encodeURIComponent(weather.longitude)}&zoom=7&level=surface&overlay=radar&product=radar&menu=&message=&calendar=now&pressure=&type=map&location=coordinates&detail=&detailLat=${encodeURIComponent(weather.latitude)}&detailLon=${encodeURIComponent(weather.longitude)}&metricWind=default&metricTemp=default`} frameBorder="0" />
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function ArticleCard({ a, tts }) {
  const preview = useMemo(() => (a.preview || (a.ai_body || '')).slice(0, 500), [a])
  const hasMore = (a.ai_body || '').length > preview.length
  const [open, setOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  return (
    <article className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
      {a.image_url && <img src={a.image_url} alt="" className="w-full h-44 object-cover"/>}
      <div className="p-5">
        <div className="text-xs text-slate-500 flex gap-3 mb-1">
          <span>{a.published_at ? new Date(a.published_at).toLocaleString() : new Date(a.fetched_at).toLocaleString()}</span>
          {a.source && <span>• {a.source}</span>}
        </div>
        <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">{a.title}{a.rewrite_note && (<span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">{a.rewrite_note}</span>)}</h2>
        {a.byline && <div className="text-xs text-slate-500 mb-2">By {a.byline}</div>}
        <div className="text-slate-700 dark:text-slate-300 leading-relaxed">
          {a.ai_body ? (
            <>
              {!open && <div className="mb-2">{preview}{hasMore && '…'}</div>}
              {hasMore && (
                <button onClick={() => setOpen(v => !v)} className="text-blue-600 hover:underline">
                  {open ? 'Hide' : 'Read more'}
                </button>
              )}
              {open && <div className="mt-2" dangerouslySetInnerHTML={{__html: (a.ai_body || '').replaceAll('\n','<br/>')}} />}
            </>
          ) : (
            <div className="italic text-slate-500">AI rewrite pending…</div>
          )}
        </div>
        <div className="mt-3 text-sm">
          <a href={a.source_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">Source: View original article</a>
        </div>
        {tts?.enabled && a?.ai_body && (
          <div className="mt-3">
            <AudioPlayer fetchUrl={`/api/tts/article/${a.id}?${tts?.voice ? ('voice='+encodeURIComponent(tts.voice)+'&') : ''}ts=${encodeURIComponent(a.fetched_at||'')}`} />
          </div>
        )}
        {a?.ai_body && (
          <div className="mt-3">
            <button onClick={() => setChatOpen(v=>!v)} className="px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 text-sm hover:bg-slate-50 dark:hover:bg-slate-700/50">
              {chatOpen ? 'Hide Comments' : 'Comments'}
            </button>
          </div>
        )}
        {chatOpen && (
          <div className="mt-3">
            <ArticleChat articleId={a.id} initialAuthor={a.byline || 'Local Desk'} />
          </div>
        )}
      </div>
    </article>
  )
}

function LocationBar({ config, onChange }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(config?.location || '')
  useEffect(() => setValue(config?.location || ''), [config?.location])
  async function submit(e){
    e.preventDefault()
    const name = value.trim()
    if (!name) return
    await onChange(name)
    setEditing(false)
  }
  return (
    <div className="max-w-[1100px] mx-auto px-4 mt-4">
      {!editing ? (
        <div className="text-sm text-slate-600 dark:text-slate-300">Location: <span className="font-medium">{config?.location || 'Resolving…'}</span> <button className="ml-3 text-blue-600 hover:underline" onClick={() => setEditing(true)}>Change</button></div>
      ) : (
        <form onSubmit={submit} className="flex items-center gap-2">
          <input value={value} onChange={e=>setValue(e.target.value)} placeholder="City, State or ZIP" className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 flex-1"/>
          <button className="px-3 py-2 rounded-md bg-blue-600 text-white">Save</button>
          <button type="button" className="px-3 py-2 rounded-md bg-slate-200 dark:bg-slate-700" onClick={()=>setEditing(false)}>Cancel</button>
        </form>
      )}
    </div>
  )
}

export default function App() {
  const [config, setConfig] = useState(null)
  const [weather, setWeather] = useState(null)
  const [articles, setArticles] = useState([])
  const [tts, setTts] = useState(null)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const pageSize = 10
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showSplash, setShowSplash] = useState(true)

  async function loadAll() {
    const t0 = performance.now()
    try {
      const [cfgR, wR, aR, ttsR] = await Promise.all([
        fetch('/api/config').then(r => r.json()),
        fetch('/api/weather').then(r => r.json()),
        fetch(`/api/articles?page=${page}&limit=${pageSize}`).then(r => r.json()),
        fetch('/api/tts/settings').then(r => r.json()).catch(()=>null),
      ])
      setConfig(cfgR)
      setWeather(wR)
      if (ttsR) setTts(ttsR)
      const items = (aR.items || aR || []).map(a => ({
        ...a,
        title: a.title || a.source_title || 'Untitled',
      }))
      setArticles(items)
      setPages(aR.pages || Math.max(1, Math.ceil((aR.total || items.length) / pageSize)))
      // eslint-disable-next-line no-console
      console.info('[App] loadAll ok', `${Math.round(performance.now()-t0)}ms`, {
        articles: aR?.length ?? 0,
        weatherUpdated: wR?.updated_at || null,
        location: cfgR?.location || null,
      })
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[App] loadAll failed', err)
      throw err
    }
  }

  useEffect(() => {
    loadAll()
    const t = setInterval(loadAll, 30000)
    return () => clearInterval(t)
  }, [page])

  // Splash screen visible for ~5s
  useEffect(() => {
    const t = setTimeout(() => setShowSplash(false), 5000)
    return () => clearTimeout(t)
  }, [])

  async function loadStatus() {
    try {
      const s = await fetch('/api/status').then(r => r.json())
      setStatus(s)
      setRunning(!!s?.running)
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('[App] status failed', e)
    }
  }

  useEffect(() => {
    // Poll status frequently while running; otherwise slower
    loadStatus()
    const ivl = setInterval(loadStatus, running ? 1000 : 10000)
    return () => clearInterval(ivl)
  }, [running])

  async function onRunNow() {
    setRunning(true)
    try {
      await fetch('/api/run-now', { method: 'POST' })
      // Wait a bit for background processing
      setTimeout(loadAll, 3000)
      setTimeout(loadStatus, 500)
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('[App] run-now failed', e)
    } finally {
      setRunning(false)
    }
  }

  async function changeLocation(name) {
    try {
      await fetch('/api/location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location: name })
      })
      await loadAll()
      // Optionally trigger a fetch immediately
      await onRunNow()
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('[App] changeLocation error', e)
    }
  }

  const showSkeletons = (!articles || articles.length === 0) && (running || (status && status.phase))

  return (
    <>
      <SplashScreen show={showSplash} />
      <Header location={config?.location} running={running} onRunNow={onRunNow} onOpenSettings={() => setShowSettings(true)} />
      <div className="max-w-[1100px] mx-auto px-4 mt-3">
        <StatusBar status={status} />
      </div>
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} reloadAll={async () => { await loadAll(); await loadStatus(); }} />}
      <LocationBar config={config} onChange={changeLocation} />
      <main className="max-w-[1100px] mx-auto px-4 py-6">
        <div className="grid md:grid-cols-3 gap-6">
          <Weather weather={weather} tts={tts} />
          <section className="md:col-span-2 space-y-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700/60">
              <div className="p-5 border-b border-slate-200/60 dark:border-slate-700/60 flex items-center gap-2">
                <div className="text-2xl">🗞️</div>
                <div className="font-semibold">Latest Local News</div>
                <div className="ml-auto text-sm text-slate-500">Minimum per run: {config?.min_articles ?? 10}</div>
              </div>
            </div>
            <div className="flex items-center justify-between px-5 py-3">
              <div className="text-sm text-slate-500">Page {page} of {pages}</div>
              <div className="flex items-center gap-2">
                <button disabled={page<=1} onClick={()=>setPage(p=>Math.max(1,p-1))} className={`px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 ${page<=1 ? 'opacity-50' : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}>Prev</button>
                <button disabled={page>=pages} onClick={()=>setPage(p=>Math.min(pages,p+1))} className={`px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 ${page>=pages ? 'opacity-50' : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}>Next</button>
              </div>
            </div>
            {articles.length > 0 ? (
              articles.map(a => <ArticleCard key={a.id} a={a} tts={tts} />)
            ) : showSkeletons ? (
              <>
                <SkeletonCard lines={5} />
                <SkeletonCard lines={6} />
                <SkeletonCard lines={4} />
              </>
            ) : (
              <div className="text-slate-500">No articles yet. Use Run Now to start.</div>
            )}
          </section>
        </div>
      </main>
      <footer className="max-w-[1100px] mx-auto px-4 pb-12 text-sm text-slate-500">
        Built from free sources (RSS + Open‑Meteo). AI rewrites cite originals.
      </footer>
      <PwaInstallPrompt />
    </>
  )
}

function StatusBar({ status }) {
  if (!status) return null
  const running = !!status.running
  const phase = status.phase
  const total = status.total ?? 0
  const completed = status.completed ?? 0
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0
  const detail = status.detail || ''
  const nextRuns = (status.next_runs || []).slice(0, 3)

  return (
    <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-800 p-3 text-sm">
      {running ? (
        <div className="flex items-center gap-3 flex-wrap">
          <span className="inline-flex items-center gap-1 text-blue-700 dark:text-blue-300">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse"></span>
            Running
          </span>
          <span className="text-slate-600 dark:text-slate-300">Phase: {phase || 'starting'}</span>
          {detail && phase !== 'rewrite' && (
            <span className="text-slate-600 dark:text-slate-300">{detail}</span>
          )}
          {phase === 'rewrite' && (
            <div className="flex items-center gap-2 ml-auto w-full md:w-56">
              <div className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-blue-600" style={{ width: `${pct}%` }} />
              </div>
              <span className="tabular-nums text-slate-600 dark:text-slate-300">{completed}/{total}</span>
            </div>
          )}
          {phase === 'rewrite' && (detail || status.current_title) && (
            <div className="w-full text-slate-600 dark:text-slate-300">
              Now: {status.current_url ? (
                <a className="text-blue-600 hover:underline" href={status.current_url} target="_blank" rel="noreferrer">{status.current_title || detail}</a>
              ) : (
                <>{status.current_title || detail}</>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1 text-slate-700 dark:text-slate-200">
            Next runs:
          </span>
          <div className="flex items-center gap-3 flex-wrap">
            {nextRuns.length === 0 ? (
              <span className="text-slate-500">Not scheduled</span>
            ) : nextRuns.map((j, i) => (
              <span key={i} className="px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-700/60 text-slate-700 dark:text-slate-200">
                {new Date(j.next_run).toLocaleString()} ({j.id.replace('harvest_', '')})
              </span>
            ))}
          </div>
          <span className="ml-auto text-slate-500">Started: {status.started_at ? new Date(status.started_at).toLocaleTimeString() : '-'}</span>
          <span className="text-slate-500">Finished: {status.finished_at ? new Date(status.finished_at).toLocaleTimeString() : '-'}</span>
        </div>
      )}
    </div>
  )
}

function MaintenanceBar({ onAfterAction }) {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [limit, setLimit] = useState('0')

  async function dedup() {
    setBusy(true)
    setMsg('')
    try {
      const res = await fetch('/api/maintenance/dedup', { method: 'POST' }).then(r => r.json())
      if (res.status === 'ok') {
        setMsg(`Removed ${res.deleted} duplicate${res.deleted === 1 ? '' : 's'}.`)
      } else {
        setMsg('Dedup failed')
      }
      onAfterAction && onAfterAction()
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('dedup failed', e)
      setMsg('Dedup failed')
    } finally {
      setBusy(false)
    }
  }

  async function rewriteMissing() {
    setBusy(true)
    setMsg('')
    try {
      const lim = String(limit || '0').trim()
      const url = lim && lim !== '0' ? `/api/maintenance/rewrite-missing?limit=${encodeURIComponent(lim)}` : '/api/maintenance/rewrite-missing'
      await fetch(url, { method: 'POST' })
      setMsg('Rewrite queued. Watch progress above.')
      onAfterAction && onAfterAction()
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('rewrite-missing failed', e)
      setMsg('Rewrite queue failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-800 p-3 text-sm flex items-center gap-3 flex-wrap">
      <span className="text-slate-700 dark:text-slate-200">Maintenance:</span>
      <button onClick={dedup} disabled={busy} className={`px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 ${busy ? 'opacity-60' : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}>
        Deduplicate
      </button>
      <div className="flex items-center gap-2">
        <button onClick={rewriteMissing} disabled={busy} className={`px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 ${busy ? 'opacity-60' : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}>
          Rewrite Missing
        </button>
        <label className="text-slate-500">Limit</label>
        <input value={limit} onChange={e=>setLimit(e.target.value)} inputMode="numeric" pattern="[0-9]*" className="w-20 px-2 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" />
        <span className="text-slate-400">0 = all</span>
      </div>
      {msg && <span className="ml-auto text-slate-600 dark:text-slate-300">{msg}</span>}
    </div>
  )
}

function SettingsPanel({ onClose, reloadAll }) {
  const [form, setForm] = useState({
    ollama_base_url: '',
    ollama_model: '',
    temp_unit: 'F',
    tts_enabled: false,
    tts_base_url: '',
    tts_voice: '',
    tts_speed: 1.0,
  })
  const [models, setModels] = useState([])
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [voices, setVoices] = useState([])
  const [previewUrl, setPreviewUrl] = useState('')
  const [pvBusy, setPvBusy] = useState(false)
  // Maintenance state in Settings
  const [mBusy, setMBusy] = useState(false)
  const [mMsg, setMMsg] = useState('')
  const [mLimit, setMLimit] = useState('0')

  useEffect(() => {
    ;(async () => {
      try {
        const s = await fetch('/api/settings').then(r => r.json())
        const ts = await fetch('/api/tts/settings').then(r => r.json()).catch(()=>({}))
        setForm(f => ({
          ...f,
          ollama_base_url: s.ollama_base_url || '',
          ollama_model: s.ollama_model || '',
          temp_unit: s.temp_unit || 'F',
          tts_enabled: !!ts.enabled,
          tts_base_url: ts.base_url || 'http://tts:5500',
          tts_voice: ts.voice || '',
          tts_speed: ts.speed || 1.0,
        }))
        if (s.ollama_base_url) {
          const m = await fetch('/api/ollama/models?base_url=' + encodeURIComponent(s.ollama_base_url)).then(r => r.json())
          setModels(m.models || [])
        }
        const v = await fetch('/api/tts/voices' + (ts.base_url ? ('?base_url='+encodeURIComponent(ts.base_url)) : '')).then(r => r.json()).catch(()=>null)
        if (v && Array.isArray(v.voices)) setVoices(v.voices)
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('settings load failed', e)
      }
    })()
  }, [])

  async function testOllama() {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch('/api/ollama/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ base_url: form.ollama_base_url }) }).then(r => r.json())
      if (res.ok) {
        setModels(res.models || [])
        setTestResult({ ok: true, msg: 'Connected. Models loaded.' })
      } else {
        setTestResult({ ok: false, msg: res.error || 'Connection failed' })
      }
    } catch (e) {
      setTestResult({ ok: false, msg: String(e) })
    } finally {
      setTesting(false)
    }
  }

  async function saveSettings() {
    try {
      await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        ollama_base_url: form.ollama_base_url,
        ollama_model: form.ollama_model,
        temp_unit: form.temp_unit,
      }) })
      // Persist TTS settings separately
      await fetch('/api/tts/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        enabled: !!form.tts_enabled,
        base_url: form.tts_base_url,
        voice: form.tts_voice || null,
        speed: form.tts_speed || 1.0,
      }) })
      await reloadAll()
      onClose()
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('save settings failed', e)
    }
  }

  async function refreshVoices() {
    try {
      const v = await fetch('/api/tts/voices' + (form.tts_base_url ? ('?base_url='+encodeURIComponent(form.tts_base_url)) : '')).then(r=>r.json())
      setVoices(v.voices || [])
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('voice load failed', e)
    }
  }

  async function previewTts() {
    setPvBusy(true)
    setPreviewUrl('')
    try {
      const res = await fetch('/api/tts/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        text: 'This is a voice preview for Local News and Weather.',
        voice: form.tts_voice || null,
        base_url: form.tts_base_url || null,
      }) })
      if (!res.ok) throw new Error('preview failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      setPreviewUrl(url)
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('tts preview failed', e)
    } finally {
      setPvBusy(false)
    }
  }

  // Maintenance actions
  async function doDedup() {
    setMBusy(true)
    setMMsg('')
    try {
      const res = await fetch('/api/maintenance/dedup', { method: 'POST' }).then(r => r.json())
      if (res.status === 'ok') {
        setMMsg(`Removed ${res.deleted} duplicate${res.deleted === 1 ? '' : 's'}.`)
      } else {
        setMMsg('Dedup failed')
      }
      await reloadAll()
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('dedup failed', e)
      setMMsg('Dedup failed')
    } finally {
      setMBusy(false)
    }
  }

  async function doRewriteMissing() {
    setMBusy(true)
    setMMsg('')
    try {
      const lim = String(mLimit || '0').trim()
      const url = lim && lim !== '0' ? `/api/maintenance/rewrite-missing?limit=${encodeURIComponent(lim)}` : '/api/maintenance/rewrite-missing'
      await fetch(url, { method: 'POST' })
      setMMsg('Rewrite queued. Watch progress above.')
      await reloadAll()
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('rewrite-missing failed', e)
      setMMsg('Rewrite queue failed')
    } finally {
      setMBusy(false)
    }
  }

  async function autoDetect() {
    try {
      await fetch('/api/location/auto', { method: 'POST' })
      await fetch('/api/weather/refresh', { method: 'POST' })
      await reloadAll()
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('auto detect failed', e)
    }
  }

  async function saveLocation(e) {
    e.preventDefault()
    const name = e.target.elements.loc.value.trim()
    if (!name) return
    await fetch('/api/location', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: name }) })
    await fetch('/api/weather/refresh', { method: 'POST' })
    await reloadAll()
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-start justify-center p-4 overflow-y-auto">
      <div className="w-full max-w-2xl my-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/60 dark:border-slate-700/60 shadow-lg max-h-[85vh] overflow-y-auto">
        <div className="px-5 py-4 border-b border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
          <div className="font-semibold">Settings</div>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-900 dark:text-slate-300">✕</button>
        </div>
        <div className="p-5 space-y-6">
          <section>
            <div className="font-medium mb-2">Ollama</div>
            <div className="flex items-center gap-2">
              <input value={form.ollama_base_url} onChange={e=>setForm(f=>({...f, ollama_base_url: e.target.value}))} placeholder="http://host.docker.internal:11434" className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 flex-1" />
              <button onClick={testOllama} disabled={testing} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700">{testing ? 'Testing…' : 'Test'}</button>
            </div>
            {testResult && <div className={`mt-2 text-sm ${testResult.ok ? 'text-emerald-600' : 'text-red-600'}`}>{testResult.msg}</div>}
            <div className="mt-3">
              <label className="text-sm text-slate-600 dark:text-slate-300 mr-2">Model</label>
              <select value={form.ollama_model} onChange={e=>setForm(f=>({...f, ollama_model: e.target.value}))} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800">
                <option value="">(default)</option>
                {models.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </section>

          <section>
            <div className="font-medium mb-2">Text-to-Speech</div>
            <div className="flex items-center gap-3 mb-2">
              <label className="inline-flex items-center gap-2"><input type="checkbox" checked={!!form.tts_enabled} onChange={e=>setForm(f=>({...f, tts_enabled: e.target.checked}))}/> <span>Enable TTS</span></label>
            </div>
            <div className="flex items-center gap-2">
              <input value={form.tts_base_url} onChange={e=>setForm(f=>({...f, tts_base_url: e.target.value}))} placeholder="http://tts:5500" className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 flex-1" />
              <button onClick={refreshVoices} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700">Refresh Voices</button>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <label className="text-sm text-slate-600 dark:text-slate-300 mr-2">Voice</label>
              <select value={form.tts_voice} onChange={e=>setForm(f=>({...f, tts_voice: e.target.value}))} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800">
                <option value="">(auto)</option>
                {voices.map(v => <option key={v.name} value={v.name}>{(v.label||v.name)}{v.locale?` · ${v.locale}`:''}</option>)}
              </select>
              <button onClick={previewTts} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700" disabled={pvBusy || !form.tts_enabled}>{pvBusy ? 'Preview…' : 'Preview'}</button>
            </div>
            {previewUrl && (
              <div className="mt-2">
                <AudioPlayer src={previewUrl} />
              </div>
            )}
          </section>

          <section>
            <div className="font-medium mb-2">Maintenance</div>
            <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-800 p-3 text-sm flex items-center gap-3 flex-wrap">
              <button onClick={doDedup} disabled={mBusy} className={`px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 ${mBusy ? 'opacity-60' : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}>
                Deduplicate by Title
              </button>
              <div className="flex items-center gap-2">
                <button onClick={doRewriteMissing} disabled={mBusy} className={`px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 ${mBusy ? 'opacity-60' : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}>
                  Rewrite Missing
                </button>
                <label className="text-slate-500">Limit</label>
                <input value={mLimit} onChange={e=>setMLimit(e.target.value)} inputMode="numeric" pattern="[0-9]*" className="w-20 px-2 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800" />
                <span className="text-slate-400">0 = all</span>
              </div>
              {mMsg && <span className="ml-auto text-slate-600 dark:text-slate-300">{mMsg}</span>}
            </div>
            <div className="text-xs text-slate-500 mt-2">Dedup removes articles with the same title, keeping the most recently updated.</div>
          </section>

          <section>
            <div className="font-medium mb-2">Weather Units</div>
            <div className="flex items-center gap-3">
              <label className="inline-flex items-center gap-2"><input type="radio" name="unit" checked={(form.temp_unit||'F')==='F'} onChange={()=>setForm(f=>({...f, temp_unit:'F'}))}/> <span>Fahrenheit (°F)</span></label>
              <label className="inline-flex items-center gap-2"><input type="radio" name="unit" checked={(form.temp_unit||'F')==='C'} onChange={()=>setForm(f=>({...f, temp_unit:'C'}))}/> <span>Celsius (°C)</span></label>
            </div>
            <div className="text-xs text-slate-500 mt-1">Changing units triggers a fresh forecast fetch and AI weather report.</div>
          </section>

          <section>
            <div className="font-medium mb-2">Location</div>
            <div className="flex items-center gap-2">
              <form onSubmit={saveLocation} className="flex items-center gap-2 flex-1">
                <input name="loc" placeholder="City, State or ZIP" className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 flex-1" />
                <button className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700">Save</button>
              </form>
              <button onClick={autoDetect} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700">Auto‑detect</button>
            </div>
          </section>

          <div className="flex items-center justify-end gap-2">
            <button onClick={onClose} className="px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700">Cancel</button>
            <button onClick={saveSettings} className="px-3 py-2 rounded-md bg-blue-600 text-white">Save</button>
          </div>
        </div>
      </div>
    </div>
  )
}

