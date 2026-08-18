#!/usr/bin/env bash
# Daily cron job: scrape National 2026 entries, diff against the last commit, and push
# to main only if something actually changed (so Cloudflare Pages only redeploys on
# real data changes). Self-expires after STOP_DATE by removing its own crontab line.
#
# Installed by: crontab -l entry added 2026-08-17, runs daily at 6:00 AM local.
# Expires: 2026-08-24 (7 days) — after that this script removes its own cron line.

set -euo pipefail

STOP_DATE="2026-08-24"
REPO_DIR="/home/andrey/projects/isasha"
SCRAPER_DIR="$REPO_DIR/public/projects/com_assets"
LOG_FILE="$SCRAPER_DIR/daily_scrape.log"
DATA_DIR="$SCRAPER_DIR/national2026"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"; }

if [[ "$(date +%F)" > "$STOP_DATE" ]]; then
    log "Past STOP_DATE ($STOP_DATE) — removing self from crontab and exiting."
    crontab -l | grep -vF "daily_scrape_and_push.sh" | crontab -
    exit 0
fi

log "Starting daily scrape."
cd "$SCRAPER_DIR"

if ! python3 scrape_national2026.py >> "$LOG_FILE" 2>&1; then
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
git commit -m "chore: daily scrape update ($(date +%F))

Automated daily scrape via cron. See scrape-log.html for the diff."
git push git@github.com:lexy-mal/isasha.ca.git main

log "Committed and pushed daily scrape update."
