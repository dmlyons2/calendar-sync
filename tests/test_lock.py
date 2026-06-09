import multiprocessing
import time
from pathlib import Path

import pytest

from calendar_sync.lock import LockHeldError, single_run_lock


def _hold_lock(lock_path: str, hold_seconds: float, ready_event):
    with single_run_lock(lock_path):
        ready_event.set()
        time.sleep(hold_seconds)


def test_lock_acquired_and_released(tmp_path: Path):
    lock_path = str(tmp_path / "test.lock")
    with single_run_lock(lock_path):
        pass
    with single_run_lock(lock_path):
        pass


def test_lock_blocks_second_holder(tmp_path: Path):
    lock_path = str(tmp_path / "test.lock")
    ready = multiprocessing.Event()
    p = multiprocessing.Process(target=_hold_lock, args=(lock_path, 2.0, ready))
    p.start()
    try:
        ready.wait(timeout=5)
        with pytest.raises(LockHeldError):
            with single_run_lock(lock_path):
                pass
    finally:
        p.join(timeout=5)
