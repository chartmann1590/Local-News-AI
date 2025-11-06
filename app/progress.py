from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import threading
from typing import Any, Dict, List, Optional
import pytz


@dataclass
class RunStatus:
    running: bool = False
    phase: Optional[str] = None  # 'fetch', 'rewrite', 'weather_fetch', 'weather_generate', 'broadcast'
    detail: Optional[str] = None
    total: Optional[int] = None
    completed: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    # Current item (for rewrite phase)
    current_id: Optional[int] = None
    current_title: Optional[str] = None
    current_url: Optional[str] = None
    # Timeout tracking
    timeout_seconds: Optional[int] = None
    timeout_started_at: Optional[str] = None
    # Skip and fallback flags
    skip_current: bool = False
    fallback_current: bool = False


class Progress:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = RunStatus()

    def _now(self, tz: str | None = None) -> str:
        """Get current time as ISO string. If tz is provided, use that timezone, otherwise use location timezone."""
        if tz:
            try:
                tz_obj = pytz.timezone(tz)
                return datetime.now(tz_obj).isoformat()
            except Exception:
                pass
        # Fallback to location timezone instead of UTC
        try:
            from .geo import get_local_now
            return get_local_now().isoformat()
        except Exception:
            # Last resort: use America/New_York timezone instead of UTC
            try:
                tz = pytz.timezone("America/New_York")
                return datetime.now(tz).isoformat()
            except Exception:
                # Absolute last resort: use system local time
                return datetime.now().isoformat()
    
    def _get_timezone(self) -> str | None:
        """Get the configured location timezone."""
        try:
            from .geo import resolve_location
            cfg = resolve_location()
            return cfg.timezone if cfg and cfg.timezone else None
        except Exception:
            return None

    def reset(self) -> None:
        with self._lock:
            self._state = RunStatus()

    def start(self) -> None:
        with self._lock:
            tz = self._get_timezone()
            self._state = RunStatus(running=True, started_at=self._now(tz))

    def phase(self, name: str, detail: Optional[str] = None) -> None:
        with self._lock:
            self._state.phase = name
            self._state.detail = detail
            # Keep totals unless switching to a non-rewrite phase
            if name != 'rewrite':
                self._state.total = self._state.total if name == 'rewrite' else self._state.total
                self._state.completed = self._state.completed if name == 'rewrite' else self._state.completed

    def set_rewrite_total(self, total: int) -> None:
        with self._lock:
            self._state.total = int(total)
            self._state.completed = 0

    def inc_rewrite(self, n: int = 1) -> None:
        with self._lock:
            if self._state.completed is None:
                self._state.completed = 0
            self._state.completed += int(n)

    def finish(self, error: Optional[str] = None) -> None:
        with self._lock:
            self._state.running = False
            tz = self._get_timezone()
            self._state.finished_at = self._now(tz)
            if error:
                self._state.error = error
            # Clear current item so UI doesn't show stale info
            self._state.current_id = None
            self._state.current_title = None
            self._state.current_url = None
            # Clear timeout tracking
            self._state.timeout_seconds = None
            self._state.timeout_started_at = None

    def set_timeout(self, timeout_seconds: int) -> None:
        """Set timeout tracking for current operation."""
        with self._lock:
            tz = self._get_timezone()
            self._state.timeout_seconds = timeout_seconds
            self._state.timeout_started_at = self._now(tz)

    def clear_timeout(self) -> None:
        """Clear timeout tracking."""
        with self._lock:
            self._state.timeout_seconds = None
            self._state.timeout_started_at = None

    def is_timeout_exceeded(self) -> bool:
        """Check if current operation has exceeded its timeout."""
        with self._lock:
            if not self._state.timeout_seconds or not self._state.timeout_started_at:
                return False
            
            try:
                # Parse the timeout start time (ISO format)
                started_at_str = self._state.timeout_started_at
                if '+' in started_at_str or started_at_str.endswith('Z'):
                    # Has timezone info
                    started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                else:
                    # No timezone, assume local timezone
                    started_at = datetime.fromisoformat(started_at_str)
                
                # Get current time
                try:
                    from .geo import get_local_now
                    now = get_local_now()
                except Exception:
                    # Fallback to system time
                    now = datetime.now()
                
                # If started_at is timezone-naive, make now timezone-naive too
                if started_at.tzinfo is None and now.tzinfo is not None:
                    now = now.replace(tzinfo=None)
                elif started_at.tzinfo is not None and now.tzinfo is None:
                    # Try to make now aware (but this is less ideal)
                    try:
                        tz = self._get_timezone()
                        if tz:
                            tz_obj = pytz.timezone(tz)
                            now = tz_obj.localize(now) if now.tzinfo is None else now
                    except Exception:
                        pass
                
                # Calculate elapsed seconds
                elapsed = (now - started_at).total_seconds()
                return elapsed > self._state.timeout_seconds
            except Exception:
                # If we can't parse or calculate, assume not exceeded
                return False

    def set_current(self, *, art_id: Optional[int], title: Optional[str], url: Optional[str]) -> None:
        with self._lock:
            # Only clear flags if we're switching to a different article
            if self._state.current_id != art_id:
                self._state.skip_current = False
                self._state.fallback_current = False
            self._state.current_id = art_id
            self._state.current_title = title
            self._state.current_url = url

    def skip_current_item(self) -> None:
        """Mark current item to be skipped."""
        with self._lock:
            self._state.skip_current = True

    def fallback_current_item(self) -> None:
        """Mark current item to use fallback immediately."""
        with self._lock:
            self._state.fallback_current = True

    def clear_flags(self) -> None:
        """Clear skip and fallback flags without changing current article."""
        with self._lock:
            self._state.skip_current = False
            self._state.fallback_current = False

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self._state)


progress = Progress()
