#!/usr/bin/env bash
# Daily cron job: scrape National 2026 entries, diff against the last commit, and push
# to main only if something actually changed (so Cloudflare Pages only redeploys on
# real data changes). Self-expires after STOP_DATE by removing its own crontab line.
#
# Installed by: crontab -l entry added 2026-08-17, runs daily at 6:00 AM local.
# Expires: 2026-08-31 (day after Nationals ends) — after that this script removes its own cron line.

set -uo pipefail

STOP_DATE="2026-08-31"
REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
SCRAPER_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRAPER_DIR/daily_scrape.log"
DATA_DIR="$SCRAPER_DIR/national2026"
HEAT_LISTS_URL="http://www.comp-mngr.com/national2026/national2026_HeatLists.htm"
export HEAT_LISTS_URL

# cron runs with a bare environment, so the GNOME keyring SSH agent that holds the
# passphrase for the GitHub deploy key isn't wired up automatically the way it is in an
# interactive login shell. Point at the same per-user agent socket explicitly; this only
# works if the desktop session has been unlocked at least once since boot (which unlocks
# the keyring) — if the machine gets rebooted and nobody logs in, push will fail here.
export SSH_AUTH_SOCK="/run/user/1000/keyring/ssh"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"; }

if [[ "$(date +%F)" > "$STOP_DATE" ]]; then
    log "Past STOP_DATE ($STOP_DATE) — removing self from crontab and exiting."
    crontab -l | grep -vF "daily_scrape_and_push.sh" | crontab -
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

git add "$DATA_DIR/participants.json" "$DATA_DIR/heat_events.json" "$DATA_DIR/scrape_log.json"
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
