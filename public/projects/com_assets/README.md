# Imperial Cup 2026 Dance Data

This directory contains data for the Imperial Cup 2026 dance competition.

## Files

- **participants.json** — Participant entries indexed by name
  - Format: `{ "Name": { "entries": [ { heat, event, time, session, partner } ] } }`
  - Contains all heats each participant is competing in

- **heat_events.json** — Heat event definitions
  - Format: `[ { heat, event, session, time, competitors } ]`
  - Lists all competitors in each heat
  - Sorted by heat number and event name

- **scrape_data.py** — Data scraper script
  - Fetches latest data from source website
  - Generates both JSON files
  - Validates data consistency

## Updating Data

When the source website is updated with new participants or heats:

```bash
cd public/projects/com_assets
python3 scrape_data.py
```

This will:
1. Fetch latest data from https://www.comp-mngr.com/impercup2026/ImperCup2026_HeatLists.htm
2. Parse participant entries and heat events
3. Generate updated `participants.json` and `heat_events.json`
4. Validate data consistency
5. Report summary statistics

**Note:** The script overwrites the existing JSON files, so commit any changes first if needed.

## Data Source

Data is scraped from the official Imperial Cup 2026 Heat Lists:
https://www.comp-mngr.com/impercup2026/ImperCup2026_HeatLists.htm

The script uses the official heat list HTML page as the authoritative source of truth.

## Statistics

Current dataset:
- 277 participants
- 3,162 total entries (heats)
- 420 unique heats
- 1,260 heat events

Last updated: 2026-06-19
