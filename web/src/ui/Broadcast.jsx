import React, { useState, useEffect, useRef } from 'react'
import CaptionOverlay from './CaptionOverlay'

export default function Broadcast() {
  const [broadcast, setBroadcast] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [regenerating, setRegenerating] = useState(false)
  const [videoUrl, setVideoUrl] = useState(null)
  const videoRef = useRef(null)

  useEffect(() => {
    loadBroadcast()
  }, [])

  async function loadBroadcast() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/broadcast/latest')
      if (!res.ok) {
        if (res.status === 404) {
          setError('No broadcast available yet. The broadcast will be generated automatically at scheduled intervals.')
          setBroadcast(null)
          return
        }
        throw new Error(`HTTP ${res.status}`)
      }
      const data = await res.json()
      setBroadcast(data)
      if (data.id) {
        setVideoUrl(`/api/broadcast/${data.id}/video`)
      }
    } catch (e) {
      console.error('Failed to load broadcast', e)
      setError('Failed to load broadcast: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRegenerate() {
    if (!confirm('Regenerate the broadcast? This may take several minutes.')) {
      return
    }
    setRegenerating(true)
    setError(null)
    try {
      const res = await fetch('/api/broadcast/regenerate', { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      alert('Broadcast regeneration started. This may take several minutes. The page will refresh automatically when complete.')
      
      // Poll for new broadcast every 10 seconds
      const pollInterval = setInterval(async () => {
        try {
          const latestRes = await fetch('/api/broadcast/latest')
          if (latestRes.ok) {
            const latest = await latestRes.json()
            // Check if this is a new broadcast (different ID or newer timestamp)
            if (!broadcast || latest.id !== broadcast.id || 
                (latest.created_at && broadcast.created_at && latest.created_at > broadcast.created_at)) {
              clearInterval(pollInterval)
              await loadBroadcast()
              alert('New broadcast is ready!')
            }
          }
        } catch (e) {
          console.error('Polling failed', e)
        }
      }, 10000)
      
      // Stop polling after 10 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        setRegenerating(false)
      }, 600000)
      
    } catch (e) {
      console.error('Failed to regenerate broadcast', e)
      setError('Failed to start regeneration: ' + e.message)
      setRegenerating(false)
    }
  }

  function formatDuration(seconds) {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'N/A'
    try {
      const date = new Date(dateStr)
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch (e) {
      return dateStr
    }
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700/60 p-8">
        <div className="text-center">
          <div className="inline-block w-8 h-8 rounded-full border-4 border-slate-300 border-t-blue-600 animate-spin mb-4"></div>
          <div className="text-slate-600 dark:text-slate-300">Loading broadcast...</div>
        </div>
      </div>
    )
  }

  if (error && !broadcast) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700/60 p-8">
        <div className="text-center">
          <div className="text-4xl mb-4">📺</div>
          <div className="text-xl font-semibold mb-2">News Broadcast</div>
          <div className="text-slate-600 dark:text-slate-300 mb-4">{error}</div>
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className={`px-4 py-2 rounded-md ${
              regenerating
                ? 'bg-slate-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            } text-white`}
          >
            {regenerating ? 'Regenerating...' : 'Generate Broadcast Now'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
      <div className="p-5 border-b border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-2xl">📺</div>
          <div>
            <div className="font-semibold">News Broadcast</div>
            {broadcast?.created_at && (
              <div className="text-sm text-slate-500">
                Created: {formatDate(broadcast.created_at)} • Duration: {formatDuration(broadcast.duration_seconds)} • {broadcast.article_count || 0} articles
                {broadcast.includes_weather && ' • Weather included'}
              </div>
            )}
          </div>
        </div>
        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className={`px-4 py-2 rounded-md text-sm ${
            regenerating
              ? 'bg-slate-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          } text-white`}
        >
          {regenerating ? 'Regenerating...' : 'Regenerate'}
        </button>
      </div>

      <div className="p-5">
        {error && (
          <div className="mb-4 p-3 rounded-md bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
            {error}
          </div>
        )}

        {videoUrl ? (
          <>
            <div className="mb-4 rounded-lg overflow-hidden border border-slate-200/60 dark:border-slate-700/60 bg-slate-900 relative">
              <video
                ref={videoRef}
                controls
                crossOrigin="anonymous"
                className="w-full"
                style={{ maxHeight: '600px' }}
                src={videoUrl}
              >
                Your browser does not support the video tag.
              </video>
              {broadcast?.srt_path && broadcast?.id && (
                <CaptionOverlay
                  videoRef={videoRef}
                  srtUrl={broadcast.srt_path}
                  broadcastId={broadcast.id}
                />
              )}
            </div>

            {broadcast?.transcript && (
              <div className="mt-6">
                <div className="text-lg font-semibold mb-3">Transcript</div>
                <div className="bg-slate-50 dark:bg-slate-900/40 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <div className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {broadcast.transcript}
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12 text-slate-500">
            Video not available
          </div>
        )}
      </div>
    </div>
  )
}

