from __future__ import annotations

import argparse
import logging
import sys
import time

from .config import Config, ConfigError
from .diagnose import diagnose
from .ics import IcsFetchError, IcsParseError
from .sync import run


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="calendar-sync")
    p.add_argument("--log-level", default=None, help="override LOG_LEVEL env var")
    sub = p.add_subparsers(dest="command")

    sync_p = sub.add_parser("sync", help="run a sync (default)")
    sync_p.add_argument("--dry-run", action="store_true", help="log actions without making changes")

    diag_p = sub.add_parser("diagnose", help="inspect why a specific event did or didn't sync")
    diag_p.add_argument("fragment", help="case-insensitive substring of uid or summary")

    args = p.parse_args(argv)
    if args.command is None:
        args.command = "sync"
        args.dry_run = False
    return args


def _run_sync(args, cfg, log) -> int:
    started = time.monotonic()
    result = run(cfg, dry_run=args.dry_run)
    duration = time.monotonic() - started
    log.info(
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


def _run_diagnose(args, cfg) -> int:
    code, text = diagnose(cfg, args.fragment)
    print(text, file=sys.stderr if code != 0 else sys.stdout)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=(args.log_level or "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("calendar_sync")

    try:
        cfg = Config.from_env()
        logging.getLogger().setLevel((args.log_level or cfg.log_level).upper())
        if args.command == "diagnose":
            return _run_diagnose(args, cfg)
        return _run_sync(args, cfg, log)
    except (ConfigError, IcsFetchError, IcsParseError) as e:
        log.error("%s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
