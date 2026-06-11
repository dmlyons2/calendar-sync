# calendar-sync

Mirror an Outlook calendar into a dedicated Google Calendar, reliably, including cancelled meetings.

## What this does

If you live in Google Calendar but have to follow an Outlook calendar (work, school, a shared team calendar), Google's built-in "subscribe by URL" almost works. It refreshes slowly (every 12–24 hours), and the bigger problem is that it doesn't reliably remove meetings that were cancelled, including individual cancelled occurrences of a recurring meeting. You end up with ghost events on your Google calendar.

`calendar-sync` replaces that subscription. It reads the Outlook calendar feed, writes events into a dedicated Google calendar you control, and removes cancelled meetings the way you'd expect.

## Is this for you?

This is for you if:

- You have an Outlook or Microsoft 365 calendar that can be published as an ICS link.
- You want it mirrored into Google Calendar.
- You're willing to spend about 30 minutes following step-by-step instructions.
- You have a computer that stays on most of the time, or access to a small server, so the sync can run on a schedule.

You do not need to know how to program. You will copy and paste commands. If that's new to you, that's fine. Every step says what to do and what success looks like.

## How it works

### What the script will and won't touch

The script is designed to be safe. Every event it creates on your Google calendar is invisibly tagged as "made by calendar-sync." When the script looks at your Google calendar, it only sees its own events. It can't read, change, or delete anything else.

The script also refuses to run against your main Google calendar (the one called "primary"). You'll set up a separate calendar just for synced events, so even in the worst case your personal events are not at risk.

### How it knows what changed

Every time the script writes an event to Google, it stamps a "fingerprint" on it: a short string computed from the event's title, time, recurrence, exception dates, and a few other fields. On the next run, the script reads the Outlook feed, computes the fingerprint fresh, and compares it to the fingerprint stored on the matching Google event. If they differ, the event gets updated. If they match, nothing happens.

This replaces an earlier approach that used the iCalendar `SEQUENCE` number, which is supposed to increase whenever an event changes. The problem: Outlook frequently changes events (for example, adding cancelled occurrences to a recurring meeting) without bumping `SEQUENCE`. Fingerprint comparison catches those changes; `SEQUENCE` comparison missed them.

## Before you start

You'll need:

- A computer running Linux, macOS, or Windows.
- Python 3.11 or newer. (Check by opening a terminal and running `python3 --version`. On Windows the command is often `py --version`.)
- A Google account.
- An Outlook or Microsoft 365 account whose calendar can be published. (Most personal `@outlook.com` accounts and many work accounts support this. Some work accounts disable publishing; check with your IT department if it's missing.)
- About 30 minutes.
- A place to run the script on a schedule: a computer that stays on, or a small always-on server.

## Setup

The instructions below assume Linux. Where macOS or Windows differs, look for a callout like this:

> **macOS:** do it this way instead.

### Step 1. Create a dedicated Google calendar

**What you're doing:** making a new, empty Google calendar that will hold the synced events.

**Why:** the script is configured to refuse your main ("primary") calendar, and you want synced events visually grouped anyway.

1. Open [Google Calendar](https://calendar.google.com) in a browser.
2. In the left sidebar, find **Other calendars** and click the **+** next to it.
3. Choose **Create new calendar**.
4. Name it something like `Work Outlook (synced)`. Click **Create calendar**.
5. Once it's created, click it in the sidebar, then click **Settings** (the gear icon → settings, or hover the calendar and click the three-dot menu).
6. Scroll to **Integrate calendar** and copy the **Calendar ID**. It looks like `abc123...@group.calendar.google.com`. Paste it somewhere temporary. You'll need it in Step 6.

**You should see:** a new empty calendar in the left sidebar, and a calendar ID copied to your clipboard.

<!-- screenshot: Google Calendar left sidebar showing "Other calendars" + → "Create new calendar" -->

### Step 2. Create a Google service account

**What you're doing:** creating a special Google "robot account" that the script will use to log into Google's API.

**Why:** the script needs to authenticate as something. A service account is a Google account that belongs to a program, not a person.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (top bar → project picker → **New project**). Name it `calendar-sync` or similar.
3. Inside the project, open the navigation menu → **APIs & Services** → **Library**. Search for **Google Calendar API** and click **Enable**.
4. Navigation menu → **IAM & Admin** → **Service Accounts** → **Create service account**. Name it `calendar-sync`. Click **Create and continue**, skip the optional role assignments, click **Done**.
5. Click the new service account, then the **Keys** tab → **Add key** → **Create new key** → **JSON** → **Create**. A `.json` file downloads.
6. Move that JSON file somewhere safe on the machine that will run the script. Common location: `~/.config/calendar-sync/service-account.json` on Linux/macOS, or `%USERPROFILE%\calendar-sync\service-account.json` on Windows.
7. Note the service account's email address (looks like `calendar-sync@your-project.iam.gserviceaccount.com`). You'll need it in Step 3.

**You should see:** a downloaded JSON file on your computer and the service account email noted somewhere.

<!-- screenshot: Google Cloud Console "Create service account" form -->
<!-- screenshot: Service account → Keys tab → "Add key" → JSON -->

### Step 3. Share the new calendar with the service account

**What you're doing:** giving the robot account permission to write to your Google calendar.

**Why:** by default the service account has no access to any calendar. You're granting it edit access on just this one.

1. Back in [Google Calendar](https://calendar.google.com), find your new calendar in the left sidebar.
2. Hover it, click the three-dot menu, choose **Settings and sharing**.
3. Scroll to **Share with specific people or groups** → **Add people and groups**.
4. Paste the service account email from Step 2.
5. In the **Permissions** dropdown, choose **Make changes to events**.
6. Click **Send**.

**You should see:** the service account email listed under "Share with specific people" with permission "Make changes to events."

<!-- screenshot: Google Calendar settings → "Share with specific people or groups" -->

### Step 4. Publish your Outlook calendar and copy the ICS link

**What you're doing:** asking Outlook to give you a URL that always contains your latest calendar.

**Why:** the script will fetch this URL on a schedule.

1. Open [Outlook on the web](https://outlook.live.com/calendar) and sign in.
2. Go to **Settings** (gear icon) → **Calendar** → **Shared calendars** → **Publish a calendar**.
3. Choose your main calendar.
4. Choose permission **Can view all details**.
5. Click **Publish**.
6. You'll see two links: an **HTML** link and an **ICS** link. Copy the **ICS** link. (It ends in `.ics`.)

**You should see:** an ICS link that ends in `.ics`, copied to your clipboard.

> **Work or school accounts:** if "Publish a calendar" is missing or greyed out, your IT department has disabled it. You'll need to ask them to enable calendar publishing, or this script can't work for that account.

<!-- screenshot: Outlook web → Settings → Calendar → Shared calendars → Publish a calendar -->

### Step 5. Install Python and download the project

**What you're doing:** putting the project files on your computer and creating an isolated Python environment for it.

**Why:** the isolated environment ("virtual environment") means installing this script's dependencies won't interfere with any other Python on your system.

```bash
git clone https://github.com/dmlyons2/calendar-sync.git ~/calendar-sync
cd ~/calendar-sync
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

**You should see:** a directory `~/calendar-sync` containing the project, and a final line from `pip` saying `Successfully installed calendar-sync-...`.

> **macOS:** the commands above work as written. If `python3.11` is not found, install it via Homebrew: `brew install python@3.11`.

> **Windows:** use these commands instead, in PowerShell:
>
> ```powershell
> git clone https://github.com/dmlyons2/calendar-sync.git $HOME\calendar-sync
> cd $HOME\calendar-sync
> py -3.11 -m venv .venv
> .venv\Scripts\pip install -e .
> ```

### Step 6. Create the configuration file

**What you're doing:** writing the three values the script needs (Outlook URL, Google calendar ID, path to the service account JSON) into a file.

**Why:** the script reads these from environment variables. Putting them in a file means you don't have to retype them, and the file can have restricted permissions so other users on the machine can't read your secrets.

Create the file `~/.config/calendar-sync/env` (Linux/macOS) or `%USERPROFILE%\calendar-sync\env` (Windows) with this content:

```dotenv
ICS_URL=https://outlook.office365.com/owa/calendar/.../calendar.ics
TARGET_CALENDAR_ID=abc123@group.calendar.google.com
GOOGLE_APPLICATION_CREDENTIALS=/home/you/.config/calendar-sync/service-account.json
```

Replace the three values with what you copied in earlier steps.

Restrict permissions so only you can read it:

```bash
mkdir -p ~/.config/calendar-sync
chmod 700 ~/.config/calendar-sync
chmod 600 ~/.config/calendar-sync/env ~/.config/calendar-sync/service-account.json
```

> **macOS:** same commands as Linux.

> **Windows:** `chmod` doesn't exist. Right-click the file → **Properties** → **Security** → restrict to your user. Or skip this step if you're the only user on the machine.

> **Advanced / system-wide install:** if you're deploying this on a server for multiple users or as a system service, the file can live at `/etc/calendar-sync/env` instead, and the project itself at `/opt/calendar-sync`. The "schedule it to run automatically" section below covers both layouts.

**You should see:** a file at the path above containing your three values, readable only by you.

### Step 7. Test in dry-run mode

**What you're doing:** running the script in "show me what you would do, but don't actually do it" mode.

**Why:** so you can confirm it can reach Outlook and Google and would do something sensible, before letting it touch your Google calendar.

```bash
set -a; source ~/.config/calendar-sync/env; set +a
.venv/bin/python -m calendar_sync sync --dry-run --log-level DEBUG
```

**You should see:** log lines describing what the script *would* do. Nothing has changed on your Google calendar yet. The output starts with a "starting sync" line, lists each create/update/delete action it would take, and ends with a "Sync complete" summary. For example, on a first run with 47 new events:

```
INFO calendar_sync.sync: starting sync (dry_run=True, target=…ndar.com)
DEBUG calendar_sync.sync: create uid=ABC@outlook.com recurrence_id=None summary='Team standup'
... (one DEBUG line per action) ...
INFO calendar_sync: Sync complete: 47 created, 0 updated, 0 deleted (0 cancelled, 0 vanished), 0 errors. Duration: 2.5s.
```

> **Windows:** PowerShell uses different syntax for env files. Use this instead:
>
> ```powershell
> Get-Content $HOME\calendar-sync\env | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }
> .venv\Scripts\python -m calendar_sync sync --dry-run --log-level DEBUG
> ```

### Step 8. Run it once for real

**What you're doing:** removing the `--dry-run` flag and letting the script actually write to Google.

```bash
.venv/bin/python -m calendar_sync
```

**You should see:** log lines saying it created some number of events, with no errors.

## Did it work?

1. Open [Google Calendar](https://calendar.google.com) in a browser.
2. Look at your new "Work Outlook (synced)" calendar. You should see your Outlook events on it.
3. Spot-check a few: do the times, titles, and recurrences look right? If a meeting in Outlook is cancelled for next Tuesday, is it gone (or correctly cancelled) on the Google copy?

If you don't see events, jump to **Troubleshooting** below.

## Schedule it to run automatically

The script doesn't run on its own. You schedule it. Pick the section for your operating system.

### Linux (cron)

Run `crontab -e` and add:

```cron
*/15 * * * * cd /home/you/calendar-sync && set -a && . /home/you/.config/calendar-sync/env && set +a && .venv/bin/python -m calendar_sync 2>&1 | /usr/bin/logger -t calendar-sync
```

Replace `/home/you` with your actual home directory (find it with `echo $HOME`). This runs every 15 minutes and sends the script's output to the system log.

> **Advanced / system-wide install:** if you put the project at `/opt/calendar-sync` and config at `/etc/calendar-sync/env`, the equivalent line is:
>
> ```cron
> */15 * * * * cd /opt/calendar-sync && set -a && . /etc/calendar-sync/env && set +a && .venv/bin/python -m calendar_sync 2>&1 | /usr/bin/logger -t calendar-sync
> ```

### macOS (launchd)

> *Starter recipe: this command has not been verified end-to-end on macOS. If it doesn't work for you, please [open an issue](https://github.com/dmlyons2/calendar-sync/issues).*

Create `~/Library/LaunchAgents/com.calendar-sync.plist` with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.calendar-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>cd $HOME/calendar-sync && set -a && . $HOME/.config/calendar-sync/env && set +a && .venv/bin/python -m calendar_sync</string>
    </array>
    <key>StartInterval</key><integer>900</integer>
    <key>StandardOutPath</key><string>/tmp/calendar-sync.log</string>
    <key>StandardErrorPath</key><string>/tmp/calendar-sync.err</string>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.calendar-sync.plist
```

### Windows (Task Scheduler)

> *Starter recipe: this command has not been verified end-to-end on Windows. If it doesn't work for you, please [open an issue](https://github.com/dmlyons2/calendar-sync/issues).*

In PowerShell as your normal user:

```powershell
$action = New-ScheduledTaskAction -Execute "$HOME\calendar-sync\.venv\Scripts\python.exe" -Argument "-m calendar_sync" -WorkingDirectory "$HOME\calendar-sync"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName "calendar-sync" -Action $action -Trigger $trigger
```

You will need to set the environment variables permanently for your user (Control Panel → System → Environment Variables) since Task Scheduler doesn't read your shell env file.

## Troubleshooting

- **`missing required env var`:** the script can't find your config values. If you're running by hand, make sure you ran the `set -a; source ...; set +a` line first. If you're running from cron, make sure the cron line includes the env-loading block.
- **`403 forbidden` from Google:** the service account isn't shared on the target calendar with "Make changes to events" permission. Re-do Step 3.
- **Events not deleting when removed from Outlook:** the script only looks at events within a sync window (default: 30 days back, 365 days ahead). Events outside that window are not touched. Adjust with `SYNC_LOOKBACK_DAYS` and `SYNC_LOOKAHEAD_DAYS` env vars.
- **`previous run still active`:** the previous run hasn't finished yet. Safe to ignore; the next cron tick will run normally.
- **`python: command not found`:** your system may call it `python3` instead. Try `python3 --version`. On Windows it's typically `py --version`.
- **I'm on Windows and cron doesn't exist:** that's expected. Use the **Windows (Task Scheduler)** section above.
- **How do I see what the script is doing?** On Linux with the cron line above, run `journalctl -t calendar-sync` (systemd) or `grep calendar-sync /var/log/syslog`. On macOS with launchd, check `/tmp/calendar-sync.log`. On Windows, Task Scheduler logs output to its own history view.

## Glossary

- **Service account:** a Google account that belongs to a program, not a person. Used so the script can authenticate without a human logging in.
- **ICS:** a plain-text file format for calendars (also called iCalendar). When you "publish" your Outlook calendar, Outlook produces an ICS file at a URL.
- **Virtual environment (venv):** an isolated copy of Python plus its installed libraries, kept inside one project's directory. Installing libraries into a venv doesn't affect the rest of your system.
- **Cron:** a Linux/macOS scheduler that runs commands at intervals you specify.
- **launchd:** macOS's preferred scheduler. Equivalent role to cron but native to macOS.
- **Task Scheduler:** Windows's built-in scheduler.
- **Env file:** a plain-text file with `KEY=VALUE` lines, holding configuration values your shell can load into environment variables.
- **Calendar ID:** Google's unique name for a specific calendar (e.g. `abc123@group.calendar.google.com`). Found in that calendar's settings.
- **EXDATE:** short for "exception date." In a recurring event, it's a date on which the event is cancelled for that one occurrence only (the rest of the series stays).
- **Dry run:** running the script with `--dry-run` so it prints what it *would* do without actually changing anything.
- **Content hash / fingerprint:** a short string computed from an event's fields, used to detect when an event has changed.

## For developers

```bash
pip install -e ".[dev]"
pytest
```

The reconciliation logic in `src/calendar_sync/reconcile.py` is a pure function: give it lists of `SourceEvent` and `TargetEvent` plus a `Window`, get back a list of `Action`s. Exercise it with new fixtures in `tests/fixtures/`. Keep I/O out of `reconcile.py`; `sync.py` is the only module that touches both `ics` and `google`.
