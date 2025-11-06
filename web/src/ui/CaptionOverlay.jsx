import React, { useState, useEffect, useRef } from 'react'

/**
 * Parses SRT timestamp (HH:MM:SS,mmm) to seconds
 */
function parseSRTTime(timeStr) {
  const [time, millis] = timeStr.split(',')
  const [hours, minutes, seconds] = time.split(':').map(Number)
  return hours * 3600 + minutes * 60 + seconds + (Number(millis) / 1000)
}

/**
 * Parses SRT file content into structured data
 */
function parseSRT(srtContent) {
  const entries = []
  const blocks = srtContent.trim().split(/\n\s*\n/)
  
  for (const block of blocks) {
    const lines = block.trim().split('\n')
    if (lines.length < 3) continue
    
    const number = parseInt(lines[0])
    const timeLine = lines[1]
    const text = lines.slice(2).join(' ').trim()
    
    if (!timeLine.includes('-->')) continue
    
    const [startStr, endStr] = timeLine.split('-->').map(s => s.trim())
    const start = parseSRTTime(startStr)
    const end = parseSRTTime(endStr)
    
    entries.push({ number, start, end, text })
  }
  
  return entries.sort((a, b) => a.start - b.start)
}

export default function CaptionOverlay({ videoRef, srtUrl, broadcastId }) {
  const [captions, setCaptions] = useState([])
  const [currentCaption, setCurrentCaption] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!srtUrl || !broadcastId) {
      setLoading(false)
      return
    }

    async function loadCaptions() {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch(`/api/broadcast/${broadcastId}/srt`)
        if (!response.ok) {
          throw new Error(`Failed to load captions: ${response.status}`)
        }
        const srtContent = await response.text()
        const parsed = parseSRT(srtContent)
        setCaptions(parsed)
      } catch (err) {
        console.error('Failed to load captions:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadCaptions()
  }, [srtUrl, broadcastId])

  useEffect(() => {
    const video = videoRef?.current
    if (!video || captions.length === 0) return

    let animationFrameId = null
    let lastUpdateTime = -1
    
    function updateCaption() {
      const currentTime = video.currentTime
      
      // Skip if time hasn't changed significantly (avoid unnecessary updates)
      if (Math.abs(currentTime - lastUpdateTime) < 0.05) {
        animationFrameId = requestAnimationFrame(updateCaption)
        return
      }
      lastUpdateTime = currentTime
      
      // Subtract a small preview offset (0.2 seconds) to show captions slightly early
      // This helps because audio processing can have slight delays and viewers need time to read
      const previewOffset = 0.2
      const adjustedTime = Math.max(0, currentTime - previewOffset)
      
      // Find the caption entry that should be displayed at this time
      // Use a more lenient matching: show caption if we're within 0.2s of its start or end
      let activeCaption = captions.find(
        caption => adjustedTime >= caption.start && adjustedTime < caption.end
      )
      
      // If no exact match, check if we're close to a caption (for smoother transitions)
      if (!activeCaption) {
        activeCaption = captions.find(
          caption => {
            const timeToStart = Math.abs(adjustedTime - caption.start)
            const timeToEnd = Math.abs(adjustedTime - caption.end)
            // Show caption if we're within 0.2s of start or end
            return timeToStart < 0.2 || timeToEnd < 0.2
          }
        )
      }
      
      setCurrentCaption(activeCaption || null)
      
      // Continue updating with requestAnimationFrame for smoother sync
      animationFrameId = requestAnimationFrame(updateCaption)
    }

    // Use requestAnimationFrame for more frequent, smoother updates
    animationFrameId = requestAnimationFrame(updateCaption)
    
    // Also listen to seek events for immediate updates
    function handleSeek() {
      lastUpdateTime = -1 // Force update on seek
      updateCaption()
    }
    
    video.addEventListener('seeked', handleSeek)
    video.addEventListener('play', handleSeek)
    video.addEventListener('pause', handleSeek)
    
    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId)
      }
      video.removeEventListener('seeked', handleSeek)
      video.removeEventListener('play', handleSeek)
      video.removeEventListener('pause', handleSeek)
    }
  }, [videoRef, captions])

  if (loading) {
    return null // Don't show anything while loading
  }

  if (error) {
    return null // Silently fail - captions are optional
  }

  if (!currentCaption) {
    return null
  }

  return (
    <div className="absolute bottom-16 left-0 right-0 pointer-events-none z-10">
      <div className="bg-black/75 text-white px-6 py-3 rounded-lg mx-auto max-w-4xl text-center">
        <div className="text-lg font-medium leading-relaxed">
          {currentCaption.text}
        </div>
      </div>
    </div>
  )
}

