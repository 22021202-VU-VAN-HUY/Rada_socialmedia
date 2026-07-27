from __future__ import annotations

import logging
import threading

from talent_radar.core.config import Settings
from talent_radar.core.database import SessionLocal
from talent_radar.services.collection import enqueue_due_schedules, next_queued_job, run_job


logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_loop,
            name="talent-radar-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=max(5, self.settings.background_poll_seconds + 1))

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Background worker iteration failed")
            self._stop_event.wait(self.settings.background_poll_seconds)

    def run_once(self) -> None:
        with SessionLocal() as db:
            if self.settings.automatic_schedules_enabled:
                enqueue_due_schedules(db)
            job = next_queued_job(db)
            if job is not None:
                run_job(db, self.settings, job)
