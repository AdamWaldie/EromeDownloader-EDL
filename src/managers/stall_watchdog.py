"""Background watchdog that reports downloads which stop making progress.

A download is considered stalled when no new bytes have been recorded for
``STALL_TIMEOUT`` seconds. This turns a silent hang into a visible, actionable
log line that names the stuck file, instead of the run appearing to freeze.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from src.config import STALL_CHECK_INTERVAL, STALL_TIMEOUT


class StallWatchdog:
    """Track in-flight downloads and report any that stop making progress.

    The watchdog runs on a daemon thread and reports each stall once via the
    supplied ``log`` callback (``log(event, details)``).
    """

    def __init__(self, log: Callable[[str, str], None]) -> None:
        """Store the log callback and prepare the (not yet started) thread."""
        self._log = log
        self._active: dict[int, dict] = {}
        self._lock = threading.Lock()
        self._stalled: set[int] = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Start the watchdog thread."""
        self._thread.start()

    def stop(self) -> None:
        """Signal the watchdog to stop and wait briefly for it to exit."""
        self._stop.set()
        self._thread.join(timeout=STALL_CHECK_INTERVAL + 1)

    def start_download(self, task_id: int, name: str, total: int) -> None:
        """Register a download as in-flight."""
        with self._lock:
            self._active[task_id] = {
                "name": name,
                "last": time.time(),
                "downloaded": 0,
                "total": total,
            }
            self._stalled.discard(task_id)

    def record_progress(self, task_id: int, downloaded: int) -> None:
        """Record fresh progress, resetting the stall timer for this download."""
        with self._lock:
            info = self._active.get(task_id)
            if info is not None:
                info["downloaded"] = downloaded
                info["last"] = time.time()
                self._stalled.discard(task_id)

    def finish_download(self, task_id: int) -> None:
        """Mark a download as no longer in-flight."""
        with self._lock:
            self._active.pop(task_id, None)
            self._stalled.discard(task_id)

    def _run(self) -> None:
        """Periodically scan active downloads and report any that have stalled."""
        while not self._stop.wait(STALL_CHECK_INTERVAL):
            now = time.time()
            stalled_now = []
            with self._lock:
                for task_id, info in self._active.items():
                    idle = now - info["last"]
                    if idle >= STALL_TIMEOUT and task_id not in self._stalled:
                        self._stalled.add(task_id)
                        stalled_now.append(
                            (info["name"], idle, info["downloaded"]),
                        )

            # Log outside the lock so the live refresh never blocks progress
            # updates coming from the download threads.
            for name, idle, downloaded in stalled_now:
                self._log(
                    "Possible stall",
                    f"{name}: no progress for {int(idle)}s "
                    f"({downloaded} bytes downloaded so far)",
                )
