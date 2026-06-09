# calendar-sync

One-way sync from an Outlook published `.ics` feed to a dedicated Google Calendar.

Google's native "subscribe by URL" only refreshes external ICS feeds every 12–24 hours, and — more importantly — does not reliably remove cancelled meetings, including single cancelled occurrences of recurring meetings. This script replaces that subscription by pushing events into a calendar I control, with correct cancellation handling.

## Safety model

The script can **only** see, modify, or delete Google events that it previously created. Every event it writes is stamped with `extendedProperties.private.syncSource = "outlook-ics"`, and every read query filters on that tag at the API level. It cannot touch unrelated events on the target calendar, and it is configured to refuse a `TARGET_CALENDAR_ID` of `primary`.

## Setup

### 1. Create a dedicated Google Calendar

In Google Calendar (web), create a new calendar named e.g. "UW Outlook (synced)". Note its calendar ID from settings.

### 2. Create a Google service account

1. In a Google Cloud project, enable the Google Calendar API.
2. Create a service account, download its JSON key.
3. In Google Calendar settings → the dedicated calendar → Share with specific people → add the service account's email address with permission **"Make changes to events"**.

### 3. Get the Outlook ICS URL

In Outlook web → Calendar settings → Shared calendars → Publish a calendar. Choose **Can view all details**. Copy the **ICS link** (not the HTML link).

### 4. Install

```bash
git clone https://github.com/<you>/calendar-sync.git /opt/calendar-sync
cd /opt/calendar-sync
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

### 5. Configure

Copy `.env.example` to `/etc/calendar-sync/env` and fill in:

```dotenv
ICS_URL=https://outlook.office365.com/owa/calendar/.../calendar.ics
TARGET_CALENDAR_ID=abc123@group.calendar.google.com
GOOGLE_APPLICATION_CREDENTIALS=/etc/calendar-sync/service-account.json
```

Protect the secrets:

```bash
sudo chmod 600 /etc/calendar-sync/env /etc/calendar-sync/service-account.json
```

### 6. Test in dry-run mode

```bash
set -a; source /etc/calendar-sync/env; set +a
.venv/bin/python -m calendar_sync --dry-run --log-level DEBUG
```

Review the logged actions. Nothing has changed yet.

### 7. Run once for real

```bash
.venv/bin/python -m calendar_sync
```

### 8. Install cron

`crontab -e`:

```cron
*/15 * * * * cd /opt/calendar-sync && set -a && . /etc/calendar-sync/env && set +a && .venv/bin/python -m calendar_sync 2>&1 | /usr/bin/logger -t calendar-sync
```

`cron`'s default mail-on-output behavior is disabled here because we pipe to `syslog`. To restore email-on-error, drop the `| logger` pipe.

## Troubleshooting

- **"missing required env var"** — env vars aren't being loaded by cron. Make sure the `set -a && . /etc/calendar-sync/env && set +a` block in the cron line is intact, or use a wrapper script.
- **`403 forbidden` from Google** — the service account isn't shared on the target calendar with "Make changes to events" permission.
- **Events not deleting when removed from Outlook** — check the sync window (`SYNC_LOOKBACK_DAYS` / `SYNC_LOOKAHEAD_DAYS`). Vanish-detection is bounded.
- **"previous run still active"** — a previous invocation is still running. Safe to ignore; the next cron tick will run normally.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The reconciliation logic in `src/calendar_sync/reconcile.py` is a pure function — exercise it with new fixtures in `tests/fixtures/` to add behavior. Avoid adding I/O to `reconcile.py`; keep `sync.py` as the only module that touches both `ics` and `google`.
