from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import threading
from typing import Any, Dict, List, Optional


@dataclass
class RunStatus:
    running: bool = False
    phase: Optional[str] = None  # 'fetch', 'rewrite', 'weather_fetch', 'weather_generate'
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


class Progress:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = RunStatus()

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def reset(self) -> None:
        with self._lock:
            self._state = RunStatus()

    def start(self) -> None:
        with self._lock:
            self._state = RunStatus(running=True, started_at=self._now())

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
            self._state.finished_at = self._now()
            if error:
                self._state.error = error
            # Clear current item so UI doesn't show stale info
            self._state.current_id = None
            self._state.current_title = None
            self._state.current_url = None

    def set_current(self, *, art_id: Optional[int], title: Optional[str], url: Optional[str]) -> None:
        with self._lock:
            self._state.current_id = art_id
            self._state.current_title = title
            self._state.current_url = url

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self._state)


progress = Progress()
