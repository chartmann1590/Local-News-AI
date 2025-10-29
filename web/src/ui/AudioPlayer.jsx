import React, { useEffect, useRef, useState } from 'react'

function fmtTime(sec) {
  if (!isFinite(sec) || sec < 0) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function AudioPlayer({ fetchUrl, className }) {
  const audioRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [cur, setCur] = useState(0)
  const [dur, setDur] = useState(0)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const objectUrlRef = useRef('')
  const abortRef = useRef(null)

  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    function onTime() { setCur(a.currentTime || 0) }
    function onLoaded() { setDur(a.duration || 0) }
    function onEnded() { setPlaying(false); setCur(0) }
    function onError() { setErr('Audio failed to load'); setPlaying(false); setLoading(false) }
    a.addEventListener('timeupdate', onTime)
    a.addEventListener('loadedmetadata', onLoaded)
    a.addEventListener('ended', onEnded)
    a.addEventListener('error', onError)
    return () => {
      a.removeEventListener('timeupdate', onTime)
      a.removeEventListener('loadedmetadata', onLoaded)
      a.removeEventListener('ended', onEnded)
      a.removeEventListener('error', onError)
    }
  }, [fetchUrl])

  // Reset when source changes
  useEffect(() => {
    const a = audioRef.current
    if (a) {
      try { a.pause() } catch {}
      a.removeAttribute('src')
      try { a.load() } catch {}
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = ''
    }
    if (abortRef.current) {
      try { abortRef.current.abort() } catch {}
      abortRef.current = null
    }
    setCur(0); setDur(0); setPlaying(false); setErr(''); setLoading(false)
  }, [fetchUrl])

  function togglePlay() {
    const a = audioRef.current
    if (!a) return
    if (loading) return
    if (playing) {
      a.pause()
      setPlaying(false)
    } else {
      // If already have object URL, just play; otherwise fetch then play
      if (objectUrlRef.current) {
        a.play().then(() => { setErr(''); setPlaying(true) }).catch((e) => { setErr((e && e.name) || 'Play blocked'); setPlaying(false) })
        return
      }
      if (!fetchUrl) { setErr('No audio URL'); return }
      setLoading(true)
      setErr('')
      const ctrl = new AbortController()
      abortRef.current = ctrl
      fetch(fetchUrl, { signal: ctrl.signal, cache: 'no-store' })
        .then(res => {
          if (!res.ok) throw new Error('Load failed')
          return res.blob()
        })
        .then(blob => {
          const url = URL.createObjectURL(blob)
          objectUrlRef.current = url
          a.src = url
          try { a.load() } catch {}
          return a.play()
        })
        .then(() => {
          setLoading(false)
          setPlaying(true)
        })
        .catch(e => {
          if (e && e.name === 'AbortError') return
          setLoading(false)
          setPlaying(false)
          setErr('Audio failed to load')
        })
    }
  }

  function onSeek(e) {
    const a = audioRef.current
    if (!a) return
    const val = Number(e.target.value)
    a.currentTime = isFinite(val) ? val : 0
  }

  const remain = Math.max(0, (dur || 0) - (cur || 0))

  return (
    <div className={`flex items-center gap-3 ${className || ''}`}>
      <audio ref={audioRef} preload="none" />
      <button onClick={togglePlay} disabled={loading} className="px-2 py-1 rounded-md border border-slate-300 dark:border-slate-700 text-sm">
        {loading ? 'Loading…' : (playing ? 'Pause' : 'Play')}
      </button>
      <input type="range" min={0} max={Math.max(1, dur)} step={0.1} value={Math.min(cur, dur)} onChange={onSeek} className="flex-1" disabled={loading || !dur} />
      <div className="text-xs text-slate-600 dark:text-slate-300 tabular-nums">
        {fmtTime(cur)} / {fmtTime(dur)}
      </div>
      <div className="text-xs text-slate-400">
        −{fmtTime(remain)}
      </div>
      {err && <div className="text-xs text-red-500">{err}</div>}
    </div>
  )
}
