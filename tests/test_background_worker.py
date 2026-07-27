from contextlib import nullcontext

import pytest

from talent_radar.core.config import Settings
from talent_radar.services.background_worker import BackgroundWorker


def test_worker_does_not_enqueue_schedules_in_manual_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueued = []
    monkeypatch.setattr(
        "talent_radar.services.background_worker.SessionLocal",
        lambda: nullcontext(object()),
    )
    monkeypatch.setattr(
        "talent_radar.services.background_worker.enqueue_due_schedules",
        lambda _db: enqueued.append(True),
    )
    monkeypatch.setattr(
        "talent_radar.services.background_worker.next_queued_job",
        lambda _db: None,
    )
    worker = BackgroundWorker(
        Settings(
            _env_file=None,
            automatic_schedules_enabled=False,
            background_worker_enabled=False,
        )
    )

    worker.run_once()

    assert enqueued == []
