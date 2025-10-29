import React from 'react'

export function SkeletonLine({ width = '100%', className = '' }) {
  return (
    <div className={`animate-pulse rounded bg-slate-200 dark:bg-slate-700 h-3 ${className}`} style={{ width }} />
  )
}

export function SkeletonCard({ lines = 4 }) {
  return (
    <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-800 p-4 space-y-2 animate-pulse">
      <SkeletonLine width="60%" />
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine key={i} width={`${90 - i * 10}%`} />
      ))}
    </div>
  )
}

