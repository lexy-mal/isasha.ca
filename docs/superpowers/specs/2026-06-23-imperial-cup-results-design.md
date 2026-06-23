# Imperial Cup Results Feature Design
**Date:** 2026-06-23
**Feature:** Scrape scoresheet results and present them in dance.html + a new comparison page
**Files:** new `scrape_results.py`, new `results.json` / `person_results.json`, modified `public/projects/dance.html`, new `public/projects/results.html`

---

## Overview

The Imperial Cup 2026 results are published as per-person scoresheets behind a CGI form
(`ScoresheetHandler.pl`). We will scrape full judge-by-judge marks and final placements,
store them as JSON, integrate results into the existing `dance.html` person view, and build
a new `results.html` page for head-to-head comparison and an overall leaderboard.

---

## Source Mechanism (reverse-engineered)

**Index page:** `https://www.comp-mngr.com/impercup2026/ImperCup2026_ScoresheetsByPerson.htm`
- Contains a `<select name="PERSON_LIST">` with ~290 `<option value='ID=Name (Num)'>` entries.
- Example: `<option value='287=Abdullayeva, Safiya (239)'>` — `287` is the lookup ID,
  `239` is the competitor number that appears in score tables (`239 Abdullayeva/`).

**Retrieval:** HTTP `POST` to `http://www.comp-mngr.com/cgi-bin/ScoresheetHandler.pl` with:
- `DATA_FILE=<root>/impercup2026/impercup2026_scoresheetsbyperson.dat`
- `COMP_NAME=Imperial Cup Dancesport Championships`
- `PERSON_LIST=287=Abdullayeva, Safiya (239)`

**Scoresheet HTML structure:**
- Per heat: `<a name=label_N><strong>Heat 348: A-JV2 Solo Indv. Bronze BALLROOM (W/T/VW/F/Q)</strong>`
- Per dance within heat: `<a name=label_M><em>Waltz</em>` followed by `<table border="2">`:
  - Header row: `No.` | judge numbers (`03 04 09 10 11`) | `&nbsp` | skating recall columns (`1`, `1-2`, …) | `Result`
  - Data row per competitor: `239 Abdullayeva/` | mark per judge | `&nbsp` | recall counts | final placement
- Per-heat **Final summary** table: `No.` | dance abbreviations (`W T V F Q`) | `Total` | `Result`
  - Data row: competitor number+names | per-dance placement | total | final placement

**Critical finding:** A multi-couple heat's table lists **ALL competitors' rows** (full marks +
placements), not just the looked-up person. So heat rankings are fully recoverable, and scraping
all persons yields redundant heat data we can deduplicate.

**Name linking:** Score tables use `number Lead/Follow` (surnames only, e.g. `203 Korzon/Agheeva`).
The index `(Num)` parenthetical maps competitor number → full name. We build a
`number → fullName` map from the index page to link rows back to `participants.json` keys.

---

## Component 1: Scraper — `scrape_results.py`

New script in `public/projects/dance_assets/`, generalized for future competitions.

**Config block (top of file):**
```python
COMP_NAME  = "Imperial Cup Dancesport Championships"
INDEX_URL  = "https://www.comp-mngr.com/impercup2026/ImperCup2026_ScoresheetsByPerson.htm"
HANDLER_URL = "http://www.comp-mngr.com/cgi-bin/ScoresheetHandler.pl"
DATA_FILE  = "<root>/impercup2026/impercup2026_scoresheetsbyperson.dat"
REQUEST_DELAY = 0.5   # polite delay between POSTs
```

**Flow:**
1. Fetch index page; parse `<option>` entries → list of `{id, fullName, number}` and a
   `number → fullName` map.
2. For each person: POST, parse scoresheet into heats.
3. Merge all heats into a heat-keyed dict (dedupe — identical heat data from multiple sheets).
4. Build `person_results.json` by inverting heat data per competitor (matched to full names).
5. Validate (placements present, names map to `participants.json`) and save both JSON files.

**Resilience:** retry on failure, `REQUEST_DELAY` between requests, skip+log unparseable sheets,
print progress to stderr (mirrors existing `scrape_data.py` conventions).

**Run:** manual — `python3 scrape_results.py`.

---

## Component 2: Data Files (in `public/projects/dance_assets/`)

**`results.json`** — heat-centric:
```json
{
  "Heat 335": {
    "event": "AC-12+ Amateur Grand Trophy Challenge LA (C/J)",
    "dances": [
      {
        "dance": "Cha Cha",
        "judges": ["02","05","07","09","10"],
        "rows": [
          {"number":"203","names":"Korzon/Agheeva","marks":{"02":"1","05":"2","07":"1","09":"4","10":"2"},"placement":"1"}
        ]
      }
    ],
    "finalSummary": [
      {"number":"203","names":"Korzon/Agheeva","placement":"1"}
    ]
  }
}
```

**`person_results.json`** — name-keyed (matches `participants.json` keys):
```json
{
  "Agheeva, Maria": [
    {"heat":"Heat 335","event":"AC-12+ ...","placement":"1","number":"203","names":"Korzon/Agheeva"}
  ]
}
```

---

## Component 3: dance.html Integration

Loads `person_results.json` and `results.json` alongside existing data.

**Per-heat detail (feature #1 — heat rankings):**
- Show the person's **placement badge** (e.g. `🥇 1st`) in the event title/summary.
- Add an expandable **"Full ranking"** sub-section: all couples 1st→last with final placement,
  and an inner expandable for judge-by-judge marks (kept collapsed by default for readability).

**All Competitors block (new addition):**
- For each listed partner/other competitor, show their **placement details** in the shared heats
  (e.g. each shared event line gains a small placement badge), so you can see how they did,
  not just which events they shared.

**Graceful degradation:** if a heat/person has no results yet (future comps mid-event), show
nothing for results and leave existing schedule UI intact.

---

## Component 4: New Page — `results.html`

Standalone page styled consistently with `dance.html` (same dark theme / CSS variables).
Loads `results.json`, `person_results.json`, and `participants.json`.

**Head-to-head (feature #2):**
- Multi-select / add competitors (search box like dance.html).
- Side-by-side table: rows = heats (shared first, then all), columns = selected competitors,
  cells = placement; expandable to judge marks.

**Leaderboard (feature #3):**
- Aggregate per competitor: counts of 1st / 2nd / 3rd (medals), total events, best placements.
- Sortable table; default sort by gold → silver → bronze → events.

**Page presentation principle:** lead with placements; judge-by-judge marks live in expandable
detail to keep comparison views readable.

---

## Testing / Validation

1. Scraper: run, verify person count (~290) and that known heats (e.g. Heat 335) parse with all
   6+ rows and correct placements; validate names resolve to `participants.json`.
2. dance.html: select a known competitor → placement badge + full ranking render; All Competitors
   block shows placement details; no errors when results missing.
3. results.html: head-to-head shows correct placements for 2+ people across shared heats;
   leaderboard medal counts match spot-checked scoresheets.

---

## Success Criteria

- ✅ `scrape_results.py` produces valid `results.json` + `person_results.json`, generalized via config.
- ✅ dance.html shows per-heat placements, full heat rankings, and competitor placement details.
- ✅ results.html provides working head-to-head comparison and overall leaderboard.
- ✅ Judge-by-judge marks available but tucked into expandable detail.
- ✅ Graceful when results are absent.
