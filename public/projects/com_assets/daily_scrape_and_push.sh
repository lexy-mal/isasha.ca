#!/usr/bin/env bash
# Daily job: scrape National 2026 entries, diff against the last commit, and push
# to main only if something actually changed (so Cloudflare Pages only redeploys on
# real data changes). Self-expires after STOP_DATE by disabling its systemd timer
# (and removing any leftover crontab line).
#
# Scheduled by: systemd --user timer isasha-daily-scrape.timer (OnCalendar 06:00).
# Also historically installed via crontab (2026-08-17); that path is broken on this
# host because /usr/bin/crontab lost its setgid bit — prefer the systemd timer.
# Expires: 2026-08-31 (day after Nationals ends).

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
SCRAPER_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRAPER_DIR/daily_scrape.log"
DATA_DIR="$SCRAPER_DIR/national2026"
LOCK_FILE="$SCRAPER_DIR/daily_scrape.lock"
HEAT_LISTS_URL="http://www.comp-mngr.com/national2026/national2026_HeatLists.htm"
export HEAT_LISTS_URL

# cron/systemd timers run with a bare environment, so the GNOME keyring SSH agent
# that holds the passphrase for the GitHub deploy key isn't wired up automatically.
# Point at the same per-user agent socket explicitly; this only works if the desktop
# session has been unlocked at least once since boot (which unlocks the keyring).
export SSH_AUTH_SOCK="/run/user/1000/keyring/ssh"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"; }

# Pull BEFORE any STOP_DATE / scrape logic, then re-exec so we run the on-disk script
# (including an updated STOP_DATE) rather than a stale in-memory copy. This is what
# broke on 2026-08-25: local main never pulled the STOP_DATE extension to Aug 31, so
# the old Aug 24 expiry fired and skipped the scrape.
if [[ "${1:-}" != "--already-synced" ]]; then
    cd "$REPO_DIR"
    if git pull --ff-only origin main >> "$LOG_FILE" 2>&1; then
        log "Synced with origin/main before scrape."
    else
        log "git pull --ff-only failed — continuing with local tree (may be ahead or diverged)."
    fi
    exec "$0" --already-synced
fi

# TODO: derive STOP_DATE from competitions.json (national2026 endDate + 1 day)
# instead of hardcoding — so extending the competition calendar can't leave cron
# on a stale expiry again. Fallback below keeps today's behavior if unset.
# Hardcoded fallback: day after Nationals (endDate 2026-08-30).
STOP_DATE="2026-08-31"

# Serialize cron + systemd (or overlapping manual runs) so two scrapes can't race on git.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "Another scrape holds $LOCK_FILE — exiting."
    exit 0
fi

uninstall_schedule() {
    # Prefer systemd (the supported scheduler). Crontab removal is best-effort: on this
    # host /usr/bin/crontab is not setgid, so user crontab edits often fail with EACCES.
    if systemctl --user disable --now isasha-daily-scrape.timer >> "$LOG_FILE" 2>&1; then
        log "Disabled isasha-daily-scrape.timer."
    else
        log "Could not disable isasha-daily-scrape.timer (may not be installed)."
    fi
    if crontab -l 2>/dev/null | grep -qF "daily_scrape_and_push.sh"; then
        if crontab -l 2>/dev/null | grep -vF "daily_scrape_and_push.sh" | crontab - 2>>"$LOG_FILE"; then
            log "Removed daily_scrape_and_push.sh from crontab."
        else
            log "Failed to edit crontab (is /usr/bin/crontab missing setgid?). Remove the line manually."
        fi
    fi
}

if [[ "$(date +%F)" > "$STOP_DATE" ]]; then
    log "Past STOP_DATE ($STOP_DATE) — uninstalling schedule and exiting."
    uninstall_schedule
    exit 0
fi

log "Starting daily scrape."
cd "$SCRAPER_DIR"

if ! python3 scrape_data_flexible.py national2026 >> "$LOG_FILE" 2>&1; then
    log "Scrape FAILED (see log above). Not committing/pushing."
    exit 1
fi

cd "$REPO_DIR"

# scrape_log.json gets a new entry appended on every run, even a no-op one, so it must
# NOT be part of the "did anything change" check — only the data files themselves decide
# that. scrape_log.json still rides along in the commit once a real change triggers one.
if git diff --quiet -- "$DATA_DIR/participants.json" "$DATA_DIR/heat_events.json"; then
    log "No changes since last scrape — skipping commit/push (scrape_log.json left uncommitted until next real change)."
    exit 0
fi

node scripts/stamp-version.js >> "$LOG_FILE" 2>&1
git add "$DATA_DIR/participants.json" "$DATA_DIR/heat_events.json" "$DATA_DIR/scrape_log.json" public/projects/com_assets/version.json
if ! git commit -m "chore: daily scrape update ($(date +%F))

Automated daily scrape via cron. See scrape-log.html for the diff." >> "$LOG_FILE" 2>&1; then
    log "git commit FAILED — leaving working tree as-is for manual inspection."
    exit 1
fi

if ! git push git@github.com:lexy-mal/isasha.ca.git main >> "$LOG_FILE" 2>&1; then
    log "git push FAILED (commit succeeded locally, not yet on origin/main — likely an SSH auth issue, check SSH_AUTH_SOCK/keyring). Will retry next run."
    exit 1
fi

log "Committed and pushed daily scrape update."
