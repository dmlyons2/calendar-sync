from __future__ import annotations

import argparse
import logging
import sys
import time

from .config import Config
from .sync import run


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="calendar-sync")
    p.add_argument("--dry-run", action="store_true", help="log actions without making changes")
    p.add_argument("--log-level", default=None, help="override LOG_LEVEL env var")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    cfg = Config.from_env()
    level = (args.log_level or cfg.log_level).upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    started = time.monotonic()
    result = run(cfg, dry_run=args.dry_run)
    duration = time.monotonic() - started

    logging.getLogger("calendar_sync").info(
        "Sync complete: %d created, %d updated, %d deleted (%d cancelled, %d vanished), %d errors. Duration: %.1fs.",
        result.created,
        result.updated,
        result.deleted_cancelled + result.deleted_vanished,
        result.deleted_cancelled,
        result.deleted_vanished,
        result.errors,
        duration,
    )

    return 0 if result.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
