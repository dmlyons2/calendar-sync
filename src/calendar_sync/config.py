from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    ics_url: str
    target_calendar_id: str
    google_credentials_path: str
    lookback_days: int
    lookahead_days: int
    default_tz: str
    log_level: str

    @classmethod
    def from_env(cls) -> Config:
        def required(name: str) -> str:
            v = os.environ.get(name)
            if not v:
                raise ConfigError(f"missing required env var: {name}")
            return v

        target = required("TARGET_CALENDAR_ID")
        if target.lower() == "primary":
            raise ConfigError(
                "TARGET_CALENDAR_ID must not be 'primary'; create a dedicated calendar"
            )

        return cls(
            ics_url=required("ICS_URL"),
            target_calendar_id=target,
            google_credentials_path=required("GOOGLE_APPLICATION_CREDENTIALS"),
            lookback_days=int(os.environ.get("SYNC_LOOKBACK_DAYS", "30")),
            lookahead_days=int(os.environ.get("SYNC_LOOKAHEAD_DAYS", "365")),
            default_tz=os.environ.get("DEFAULT_TZ", "America/Los_Angeles"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
