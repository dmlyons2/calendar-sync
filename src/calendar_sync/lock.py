from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager


class LockHeldError(RuntimeError):
    pass


@contextmanager
def single_run_lock(path: str):
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise LockHeldError(f"lock held: {path}") from e
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
