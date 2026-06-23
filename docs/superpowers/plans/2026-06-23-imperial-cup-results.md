# Imperial Cup Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape full judge-by-judge scoresheet results, integrate placements into dance.html, and build a new results.html comparison/leaderboard page.

**Architecture:** New Python scraper POSTs to the CGI handler for each of ~290 competitors, deduplicates heat data, and writes two JSON files. dance.html loads these for inline placement display. results.html is a standalone dark-themed page for head-to-head and leaderboard views.

**Tech Stack:** Python 3 stdlib only (scraper), Vanilla JS + existing CSS variables (frontend), no new dependencies.

**Spec:** `docs/superpowers/specs/2026-06-23-imperial-cup-results-design.md`

---

## File Structure

### New Files
- **`public/projects/dance_assets/scrape_results.py`** — scraper: fetch index, POST per person, parse + dedupe heats, write JSON
- **`public/projects/dance_assets/results.json`** — heat-centric: `{ "Heat N": { event, dances:[{dance, judges, rows:[{number,names,marks,placement}]}], finalSummary:[{number,names,placement}] } }`
- **`public/projects/dance_assets/person_results.json`** — name-keyed: `{ "Last, First": [{heat, event, placement, names}] }`
- **`public/projects/results.html`** — standalone comparison + leaderboard page

### Modified Files
- **`public/projects/dance.html`** — load results JSON, add placement badges + full ranking expansion, add placements to All Competitors block

---

## Phase 1: Scraper

### Task 1: Write scrape_results.py — index parser

**Files:**
- Create: `public/projects/dance_assets/scrape_results.py`

- [ ] **Step 1: Create the file with config block and index parser**

```python
#!/usr/bin/env python3
"""
Imperial Cup Results Scraper
Fetches scoresheet data for all competitors and produces results.json + person_results.json.

Usage: python3 scrape_results.py
Config: edit the CONFIG block below to reuse for future competitions.
"""

import json, sys, os, time, re, urllib.request, urllib.parse
from html.parser import HTMLParser
from collections import defaultdict

# ── CONFIG ──────────────────────────────────────────────────────────────────
COMP_NAME    = "Imperial Cup Dancesport Championships"
INDEX_URL    = "https://www.comp-mngr.com/impercup2026/ImperCup2026_ScoresheetsByPerson.htm"
HANDLER_URL  = "http://www.comp-mngr.com/cgi-bin/ScoresheetHandler.pl"
DATA_FILE    = "<root>/impercup2026/impercup2026_scoresheetsbyperson.dat"
REQUEST_DELAY = 0.5   # seconds between POSTs
MAX_RETRIES   = 3
# ────────────────────────────────────────────────────────────────────────────

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch(url, data=None):
    """GET or POST with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=data,
                headers={"User-Agent": UA,
                         "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            print(f"  retry {attempt+1}: {e}", file=sys.stderr)
            time.sleep(1)


class IndexParser(HTMLParser):
    """Parses <option value='ID=Name (Num)'> entries from index page."""
    def __init__(self):
        super().__init__()
        self.persons = []          # [{id, fullName, number}]
        self.number_map = {}       # number_str -> fullName

    def handle_starttag(self, tag, attrs):
        if tag != "option":
            return
        d = dict(attrs)
        val = d.get("value", "")
        # format: "287=Abdullayeva, Safiya (239)"
        m = re.match(r"(\d+)=(.+)", val)
        if not m:
            return
        pid, full = m.group(1), m.group(2).strip()
        # extract trailing (Num) if present
        nm = re.search(r"\((\d+)\)\s*$", full)
        number = nm.group(1) if nm else None
        self.persons.append({"id": pid, "fullName": full, "number": number})
        if number:
            self.number_map[number] = full


def parse_index(html):
    p = IndexParser()
    p.feed(html)
    return p.persons, p.number_map
```

- [ ] **Step 2: Run a quick smoke test**

```bash
cd public/projects/dance_assets
python3 -c "
import scrape_results as s
html = s.fetch(s.INDEX_URL)
persons, nmap = s.parse_index(html)
print(f'Persons: {len(persons)}, number_map entries: {len(nmap)}')
print('Sample:', persons[0])
"
```

Expected output: `Persons: ~290, number_map entries: ~250+` and a sample dict.

---

### Task 2: Write scoresheet parser

**Files:**
- Modify: `public/projects/dance_assets/scrape_results.py`

- [ ] **Step 1: Add ScoresheetParser class**

Append to the file:

```python
class ScoresheetParser(HTMLParser):
    """
    Parses one person's scoresheet HTML into a list of heat dicts.

    Output structure per heat:
    {
      "heat": "Heat 348",
      "event": "A-JV2 Solo Indv. Bronze BALLROOM (W/T/VW/F/Q)",
      "dances": [
        {
          "dance": "Waltz",
          "judges": ["03","04","09","10","11"],
          "rows": [
            {"number":"239","names":"Abdullayeva/","marks":{"03":"1",...},"placement":"1"}
          ]
        }
      ],
      "finalSummary": [
        {"number":"239","names":"Abdullayeva/","dances":{"W":"1","T":"1"},"total":"5","placement":"1"}
      ]
    }
    """

    def __init__(self):
        super().__init__()
        self.heats = []
        self._cur_heat = None      # dict being built
        self._cur_dance = None     # dict being built
        self._in_table = False
        self._header_row = None    # list of header cell strings
        self._cur_row = []
        self._cur_cell = ""
        self._cell_open = False
        self._in_summary = False   # True while parsing Final summary table
        self._label_next = None    # "heat" | "dance" | None

    # ── tag handlers ──

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "a":
            name = ad.get("name", "")
            if name.startswith("label_"):
                self._label_next = name
        elif tag == "table":
            self._in_table = True
            self._header_row = None
            self._cur_row = []
        elif tag == "td" and self._in_table:
            self._cur_cell = ""
            self._cell_open = True
        elif tag == "tr" and self._in_table:
            self._cur_row = []
        elif tag == "br":
            self._cur_cell += " "

    def handle_endtag(self, tag):
        if tag == "strong":
            txt = self._cur_cell.strip()
            m = re.match(r"(Heat\s+\S+):\s+(.+)", txt)
            if m:
                # flush previous heat
                if self._cur_heat:
                    self.heats.append(self._cur_heat)
                self._cur_heat = {
                    "heat": m.group(1),
                    "event": m.group(2).strip(),
                    "dances": [],
                    "finalSummary": []
                }
                self._cur_dance = None
            return

        if tag == "em":
            dance_name = self._cur_cell.strip()
            if dance_name and self._cur_heat:
                self._in_summary = (dance_name.lower() == "final summary")
                if not self._in_summary:
                    self._cur_dance = {"dance": dance_name, "judges": [], "rows": []}
                    self._cur_heat["dances"].append(self._cur_dance)
            return

        if tag == "td" and self._in_table and self._cell_open:
            self._cur_row.append(self._cur_cell.strip())
            self._cell_open = False

        if tag == "tr" and self._in_table and self._cur_row:
            self._process_row(self._cur_row)
            self._cur_row = []

        if tag == "table":
            self._in_table = False
            self._header_row = None

    def handle_data(self, data):
        self._cur_cell += data

    # ── row processing ──

    def _process_row(self, row):
        # Skip empty or whitespace-only rows
        cells = [c for c in row]
        if not cells:
            return

        # First row after table open is header
        if self._header_row is None:
            self._header_row = cells
            return

        # skip rows with no useful data
        no_val = cells[0] in ("", "No.", "&nbsp", "\xa0")
        if no_val:
            return

        if self._in_summary:
            self._parse_summary_row(cells)
        else:
            self._parse_score_row(cells)

    def _parse_score_row(self, cells):
        if not self._cur_dance or not self._header_row:
            return
        # header: ["No.", "03","04",..., "&nbsp", recall_cols..., "Result"]
        # find judge columns (before the &nbsp separator)
        judges = []
        sep_idx = None
        for i, h in enumerate(self._header_row[1:], 1):
            if h in ("&nbsp", "\xa0", ""):
                sep_idx = i
                break
            judges.append(h)

        if not self._cur_dance["judges"]:
            self._cur_dance["judges"] = judges

        # parse competitor number+names from first cell
        no_cell = cells[0]
        m = re.match(r"(\d+)\s+(.+)", no_cell)
        if not m:
            return
        number, names = m.group(1), m.group(2).strip()

        marks = {}
        for i, j in enumerate(judges):
            col_idx = i + 1  # offset by "No." column
            if col_idx < len(cells):
                v = cells[col_idx].strip()
                if v and v not in ("&nbsp", "\xa0"):
                    marks[j] = v

        placement = cells[-1].strip() if cells else ""

        self._cur_dance["rows"].append({
            "number": number,
            "names": names,
            "marks": marks,
            "placement": placement
        })

    def _parse_summary_row(self, cells):
        if not self._cur_heat or not self._header_row:
            return
        no_cell = cells[0]
        m = re.match(r"(\d+)\s+(.+)", no_cell)
        if not m:
            return
        number, names = m.group(1), m.group(2).strip()

        # header: ["No.", "W","T","V","F","Q", "Total", "Result"]
        dance_cols = self._header_row[1:-2] if len(self._header_row) > 3 else []
        dance_placements = {}
        for i, d in enumerate(dance_cols):
            col_idx = i + 1
            if col_idx < len(cells):
                v = cells[col_idx].strip()
                if v and v not in ("&nbsp", "\xa0"):
                    dance_placements[d] = v

        total = cells[-2].strip() if len(cells) >= 2 else ""
        placement = cells[-1].strip() if cells else ""

        self._cur_heat["finalSummary"].append({
            "number": number,
            "names": names,
            "dances": dance_placements,
            "total": total,
            "placement": placement
        })

    def get_heats(self):
        if self._cur_heat:
            self.heats.append(self._cur_heat)
            self._cur_heat = None
        return self.heats


def parse_scoresheet(html):
    p = ScoresheetParser()
    p.feed(html)
    return p.get_heats()
```

- [ ] **Step 2: Test parser on cached scoresheet**

```bash
cd public/projects/dance_assets
python3 -c "
import scrape_results as s
html = open('/tmp/agheeva.html').read()
heats = s.parse_scoresheet(html)
import json
print(json.dumps(heats[0], indent=2))
"
```

Expected: valid JSON for Heat 335 with 6+ rows in dances[0].rows, each with number/names/marks/placement.

---

### Task 3: Write main scrape loop and JSON output

**Files:**
- Modify: `public/projects/dance_assets/scrape_results.py`

- [ ] **Step 1: Append merge + output functions**

```python
def post_scoresheet(person):
    """POST for one person's scoresheet."""
    payload = urllib.parse.urlencode({
        "DATA_FILE": DATA_FILE,
        "COMP_NAME": COMP_NAME,
        "PERSON_LIST": f"{person['id']}={person['fullName']}"
    }).encode()
    return fetch(HANDLER_URL, data=payload)


def merge_heats(all_heats_list):
    """
    Deduplicate heats from multiple scoresheets.
    For each (heat, dance), keep the row-set with the most rows (most complete).
    """
    merged = {}  # "Heat N" -> heat dict
    for heats in all_heats_list:
        for h in heats:
            key = h["heat"]
            if key not in merged:
                merged[key] = {"heat": h["heat"], "event": h["event"],
                               "dances": [], "finalSummary": []}
            existing = merged[key]

            # Merge dances
            existing_dances = {d["dance"]: d for d in existing["dances"]}
            for d in h["dances"]:
                if d["dance"] not in existing_dances or \
                   len(d["rows"]) > len(existing_dances[d["dance"]]["rows"]):
                    existing_dances[d["dance"]] = d
            existing["dances"] = list(existing_dances.values())

            # Merge finalSummary (keep largest)
            if len(h.get("finalSummary", [])) > len(existing["finalSummary"]):
                existing["finalSummary"] = h["finalSummary"]

    return merged


def build_person_results(results, number_map):
    """
    Invert results.json to person_results.json.
    Attempts to match competitor number → full name from number_map.
    Falls back to raw names from scoresheet.
    """
    person_results = defaultdict(list)

    for heat_key, heat in results.items():
        for row in heat.get("finalSummary", []):
            number = row["number"]
            full_name = number_map.get(number)

            # Try to resolve to "Last, First" format matching participants.json
            if full_name:
                # number_map stores the full option text: "Abdullayeva, Safiya (239)"
                # strip trailing (Num)
                resolved = re.sub(r"\s*\(\d+\)\s*$", "", full_name).strip()
            else:
                resolved = row["names"]  # fallback: "Abdullayeva/"

            person_results[resolved].append({
                "heat": heat_key,
                "event": heat["event"],
                "placement": row["placement"],
                "number": number,
                "names": row["names"],
                "dancePlacements": row.get("dances", {})
            })

    return dict(person_results)


def save_json(data, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {path} ({len(data)} entries)", file=sys.stderr)


def main():
    print("Fetching competitor index...", file=sys.stderr)
    html = fetch(INDEX_URL)
    persons, number_map = parse_index(html)
    print(f"Found {len(persons)} competitors, {len(number_map)} with numbers", file=sys.stderr)

    all_heats_list = []
    failed = []

    for i, person in enumerate(persons):
        name = person["fullName"]
        print(f"[{i+1}/{len(persons)}] {name}", file=sys.stderr, end="  ")
        try:
            html = post_scoresheet(person)
            heats = parse_scoresheet(html)
            all_heats_list.append(heats)
            print(f"→ {len(heats)} heats", file=sys.stderr)
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)
            failed.append(name)
        time.sleep(REQUEST_DELAY)

    if failed:
        print(f"\nFailed ({len(failed)}): {failed}", file=sys.stderr)

    print("\nMerging heats...", file=sys.stderr)
    results = merge_heats(all_heats_list)
    print(f"Unique heats: {len(results)}", file=sys.stderr)

    print("Building person results...", file=sys.stderr)
    person_results = build_person_results(results, number_map)
    print(f"Persons with results: {len(person_results)}", file=sys.stderr)

    save_json(results, "results.json")
    save_json(person_results, "person_results.json")

    print("\nDone.", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the scraper (will take ~3 min for ~290 persons)**

```bash
cd public/projects/dance_assets
python3 scrape_results.py
```

Expected stderr: progress lines per person, final `Saved results.json (N entries)` and `Saved person_results.json (N entries)`.

- [ ] **Step 3: Spot-check output**

```bash
python3 -c "
import json
r = json.load(open('public/projects/dance_assets/results.json'))
pr = json.load(open('public/projects/dance_assets/person_results.json'))
# Check Heat 335 has correct rows
h335 = r.get('Heat 335')
print('Heat 335 dances:', [d['dance'] for d in h335['dances']])
print('Heat 335 finalSummary count:', len(h335['finalSummary']))
print('First place:', h335['finalSummary'][0] if h335['finalSummary'] else 'none')
# Check Agheeva in person_results
ag = pr.get('Agheeva, Maria')
print('Agheeva results count:', len(ag) if ag else 0)
"
```

Expected: Heat 335 has Cha Cha + Jive, finalSummary with 6+ rows, placement "1" for Korzon/Agheeva. Agheeva has several results entries.

- [ ] **Step 4: Commit scraper and data**

```bash
git add public/projects/dance_assets/scrape_results.py \
        public/projects/dance_assets/results.json \
        public/projects/dance_assets/person_results.json
git commit -m "feat: add results scraper and scraped data for Imperial Cup 2026

scrape_results.py: generalized scoresheet scraper with config block.
Parses per-heat judge marks and final placements for all ~290 competitors.
Deduplicates heat data across all person scoresheets.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: dance.html Integration

### Task 4: Load results data

**Files:**
- Modify: `public/projects/dance.html`

- [ ] **Step 1: Add resultsData and personResultsData globals alongside existing globals**

Find:
```javascript
        let participantsData = {};
        let heatEventsData = [];
        let sortedParticipants = [];
```

Add below:
```javascript
        let resultsData = {};         // heat-centric: results.json
        let personResultsData = {};   // name-keyed: person_results.json
```

- [ ] **Step 2: Fetch results JSON in loadData()**

Find the existing Promise.all fetch block:
```javascript
                const [participantsRes, heatEventsRes] = await Promise.all([
                    fetch('dance_assets/participants.json'),
```

Replace with:
```javascript
                const [participantsRes, heatEventsRes, resultsRes, personResultsRes] = await Promise.all([
                    fetch('dance_assets/participants.json'),
                    fetch('dance_assets/heat_events.json'),
                    fetch('dance_assets/results.json').catch(() => ({ json: () => ({}) })),
                    fetch('dance_assets/person_results.json').catch(() => ({ json: () => ({}) }))
                ]);
```

Then after the existing `heatEventsData = await heatEventsRes.json();` line add:
```javascript
                resultsData = await resultsRes.json();
                personResultsData = await personResultsRes.json();
```

- [ ] **Step 3: Verify no errors after loading**

Open `public/projects/dance.html` in a browser (serve locally), check console — no fetch errors.

---

### Task 5: Add placement badge helper + per-heat placement display

**Files:**
- Modify: `public/projects/dance.html`

- [ ] **Step 1: Add getPersonPlacement() helper after formatName()**

```javascript
        // Get placement string for a person in a specific heat
        function getPersonPlacement(personName, heatKey) {
            const results = personResultsData[personName] || [];
            const entry = results.find(r => r.heat === heatKey);
            return entry ? entry.placement : null;
        }

        // Format placement as medal emoji + ordinal
        function formatPlacement(placement) {
            if (!placement) return '';
            const n = parseInt(placement);
            if (isNaN(n)) return placement;
            const medal = n === 1 ? '🥇' : n === 2 ? '🥈' : n === 3 ? '🥉' : null;
            const suffix = n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th';
            return medal ? `${medal} ${n}${suffix}` : `${n}${suffix}`;
        }
```

- [ ] **Step 2: Add placement badge to event title in displayPersonDetails()**

Find the event item HTML generation (around `html += \`<div class="event-item collapsed${completedClass}"`):

Find this line inside the event title:
```javascript
                html += `
                    <div class="event-title">
                        <span style="flex: 1;">
                            <span class="event-toggle">▶</span>
                            ${info.event}
                        </span>
                        <span class="heat-label">${info.heat}</span>
                    </div>
                `;
```

Replace with:
```javascript
                const placement = getPersonPlacement(name, info.heat);
                const placementBadge = placement
                    ? `<span style="margin-left:8px;font-size:0.85em;opacity:0.9;">${formatPlacement(placement)}</span>`
                    : '';
                html += `
                    <div class="event-title">
                        <span style="flex: 1;">
                            <span class="event-toggle">▶</span>
                            ${info.event}${placementBadge}
                        </span>
                        <span class="heat-label">${info.heat}</span>
                    </div>
                `;
```

- [ ] **Step 3: Verify placement badges appear**

Select a competitor who competed (e.g. search "Agheeva") — each heat row should show 🥇/🥈/🥉 or Nth badge.

---

### Task 6: Add expandable full heat ranking

**Files:**
- Modify: `public/projects/dance.html`

- [ ] **Step 1: Add buildHeatRanking() helper**

Add after `formatPlacement()`:

```javascript
        // Build full heat ranking HTML (all competitors, sorted by placement)
        function buildHeatRanking(heatKey) {
            const heat = resultsData[heatKey];
            if (!heat || !heat.finalSummary || heat.finalSummary.length === 0) return '';

            const sorted = [...heat.finalSummary].sort((a, b) => {
                const pa = parseInt(a.placement) || 999;
                const pb = parseInt(b.placement) || 999;
                return pa - pb;
            });

            let html = `<div class="heat-ranking" style="margin-top:12px;padding-top:12px;border-top:1px solid var(--bg-tertiary);">`;
            html += `<div style="font-size:0.8em;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Full Ranking</div>`;

            sorted.forEach(row => {
                const place = parseInt(row.placement) || 0;
                const medal = place === 1 ? '🥇' : place === 2 ? '🥈' : place === 3 ? '🥉' : `${place}.`;
                const danceParts = Object.entries(row.dances || {})
                    .map(([d, p]) => `<span style="opacity:0.7;font-size:0.8em;">${d}:${p}</span>`)
                    .join(' ');
                // Try to resolve names to clickable links
                html += `
                    <div style="display:flex;align-items:baseline;gap:8px;padding:5px 0;border-bottom:1px solid var(--bg-tertiary);">
                        <span style="min-width:28px;font-weight:600;">${medal}</span>
                        <span style="flex:1;font-size:0.9em;">${row.names}</span>
                        <span style="display:flex;gap:6px;flex-wrap:wrap;">${danceParts}</span>
                    </div>
                `;
            });

            html += `</div>`;
            return html;
        }
```

- [ ] **Step 2: Inject ranking into event-meta section**

In `displayPersonDetails()`, find where `event-meta` is built (the collapsible detail section per heat). It currently ends with something like:

```javascript
                html += `
                    <div class="event-meta" style="display: none;">
```

Find the closing of the event-meta div for each heat and append the ranking before it closes. Look for the pattern ending the meta section and add:

```javascript
                        ${buildHeatRanking(info.heat)}
```

Specifically find `</div>\n                ` closing the event-meta and add the ranking call just before the last `</div>`. The exact insertion point is after the existing meta fields (time, session, competitor count) and before the closing `</div>` of event-meta.

- [ ] **Step 3: Verify full ranking appears when heat is expanded**

Expand a heat for a multi-competitor event — should see "Full Ranking" section with all couples and placements.

---

### Task 7: Add placement details to All Competitors block

**Files:**
- Modify: `public/projects/dance.html`

- [ ] **Step 1: Show partner placement in couple box**

Find the couple box rendering in the partners section:
```javascript
                        Object.values(uniqueEvents).forEach(evt => {
                            const isCoupleEvent = ...
```

Replace the event line rendering (the `<span>🕐 ${evt.time}</span>` line) for the **partners** section:

```javascript
                        Object.values(uniqueEvents).forEach(evt => {
                            const isCoupleEvent = evt.event.toLowerCase().includes('couple') || evt.event.toLowerCase().includes('mixed');
                            const coupleCount = isCoupleEvent ? Math.ceil(evt.competitors / 2) : null;
                            const countText = isCoupleEvent
                                ? `👩‍💃 ${coupleCount} couple${coupleCount !== 1 ? 's' : ''}`
                                : `👥 ${evt.competitors} participant${evt.competitors !== 1 ? 's' : ''}`;
                            // Look up partner's placement in this heat
                            const partnerPlacement = getPersonPlacement(partner, evt.heat);
                            const partnerBadge = partnerPlacement
                                ? `<span style="font-weight:600;color:var(--accent);margin-left:auto;">${formatPlacement(partnerPlacement)}</span>`
                                : '';
                            html += `
                                <div style="margin-left: 0; margin-bottom: 6px; padding: 8px; background: var(--bg-primary); border-left: 3px solid var(--accent); border-radius: 2px; font-size: 0.85em;">
                                    <div style="color: var(--text-primary); font-weight: 500; display:flex; align-items:center;">${evt.event}${partnerBadge}</div>
                                    <div style="color: var(--text-secondary); font-size: 0.8em; display: flex; gap: 12px; margin-top: 4px;">
                                        <span>🕐 ${evt.time}</span>
                                        <span>${countText}</span>
                                    </div>
                                </div>
`;
                        });
```

- [ ] **Step 2: Show placement for solo competitors in other competitors block**

In the solo competitor rendering section (last `Object.values(uniqueEvents).forEach(evt => {` in the other-competitors loop), add placement lookup similarly:

```javascript
                                const soloPlacement = getPersonPlacement(competitor, evt.heat);
                                const soloBadge = soloPlacement
                                    ? `<span style="font-weight:600;color:var(--accent);margin-left:auto;">${formatPlacement(soloPlacement)}</span>`
                                    : '';
```

And update the event name line to include `${soloBadge}`.

- [ ] **Step 3: Commit dance.html changes**

```bash
git add public/projects/dance.html
git commit -m "feat: integrate results into dance.html

- Load results.json and person_results.json alongside existing data
- Show placement badge (🥇 1st, 🥈 2nd…) in each event title
- Add expandable full heat ranking in event detail
- Show placement for partners and other competitors in All Competitors block
- Graceful degradation: all results features no-op when data missing

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: results.html

### Task 8: Create results.html skeleton with shared styles and data loading

**Files:**
- Create: `public/projects/results.html`

- [ ] **Step 1: Create the file with dark theme, CSS variables matching dance.html, and data loading**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Imperial Cup 2026 — Results</title>
    <style>
        /* ── Design tokens (match dance.html) ── */
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a26;
            --text-primary: #e8e8f0;
            --text-secondary: #8888aa;
            --accent: #00d9ff;
            --accent-dim: rgba(0,217,255,0.2);
            --gold: #ffd700;
            --silver: #c0c0c0;
            --bronze: #cd7f32;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Segoe UI', system-ui, sans-serif;
            min-height: 100vh;
        }

        .page-header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--bg-tertiary);
            padding: 24px 32px;
        }
        .page-header h1 {
            font-size: 1.8em;
            color: var(--accent);
            letter-spacing: 0.05em;
        }
        .page-header .subtitle {
            color: var(--text-secondary);
            font-size: 0.9em;
            margin-top: 4px;
        }
        .nav-links {
            margin-top: 12px;
            display: flex;
            gap: 16px;
        }
        .nav-links a {
            color: var(--accent);
            text-decoration: none;
            font-size: 0.85em;
            opacity: 0.8;
        }
        .nav-links a:hover { opacity: 1; }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px;
        }

        /* ── Tabs ── */
        .tabs {
            display: flex;
            gap: 0;
            border-bottom: 2px solid var(--bg-tertiary);
            margin-bottom: 32px;
        }
        .tab-btn {
            padding: 12px 24px;
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 1em;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
            transition: color 0.2s, border-color 0.2s;
        }
        .tab-btn.active {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* ── Search / person chips ── */
        .search-box {
            position: relative;
            margin-bottom: 16px;
        }
        .search-box input {
            width: 100%;
            padding: 10px 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--bg-tertiary);
            border-radius: 4px;
            color: var(--text-primary);
            font-size: 1em;
        }
        .search-box input:focus {
            outline: none;
            border-color: var(--accent);
        }
        .search-dropdown {
            position: absolute;
            top: 100%;
            left: 0; right: 0;
            background: var(--bg-secondary);
            border: 1px solid var(--bg-tertiary);
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 10;
            display: none;
        }
        .search-dropdown.open { display: block; }
        .search-result-item {
            padding: 8px 16px;
            cursor: pointer;
            font-size: 0.9em;
        }
        .search-result-item:hover { background: var(--bg-tertiary); }

        .selected-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 24px;
        }
        .chip {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            background: var(--accent-dim);
            border: 1px solid var(--accent);
            border-radius: 20px;
            font-size: 0.85em;
            color: var(--accent);
        }
        .chip button {
            background: none;
            border: none;
            color: var(--accent);
            cursor: pointer;
            font-size: 1em;
            line-height: 1;
            opacity: 0.7;
        }
        .chip button:hover { opacity: 1; }

        /* ── Comparison table ── */
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        .comparison-table th {
            background: var(--bg-secondary);
            padding: 10px 14px;
            text-align: left;
            border-bottom: 2px solid var(--accent-dim);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 0.05em;
        }
        .comparison-table td {
            padding: 10px 14px;
            border-bottom: 1px solid var(--bg-tertiary);
            vertical-align: top;
        }
        .comparison-table tr:hover td { background: var(--bg-secondary); }
        .placement-cell {
            font-weight: 600;
            text-align: center;
        }
        .placement-cell.gold { color: var(--gold); }
        .placement-cell.silver { color: var(--silver); }
        .placement-cell.bronze { color: var(--bronze); }
        .placement-cell.other { color: var(--text-secondary); }
        .placement-cell.dnc { color: var(--bg-tertiary); font-style: italic; }

        /* ── Leaderboard ── */
        .leaderboard-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        .leaderboard-table th {
            background: var(--bg-secondary);
            padding: 10px 14px;
            text-align: left;
            border-bottom: 2px solid var(--accent-dim);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 0.05em;
            cursor: pointer;
            user-select: none;
        }
        .leaderboard-table th:hover { color: var(--accent); }
        .leaderboard-table th.sorted { color: var(--accent); }
        .leaderboard-table td {
            padding: 10px 14px;
            border-bottom: 1px solid var(--bg-tertiary);
        }
        .leaderboard-table tr:hover td { background: var(--bg-secondary); }
        .leaderboard-table .rank-col {
            text-align: center;
            color: var(--text-secondary);
            width: 40px;
        }
        .medal-count {
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .medal-count .m { font-size: 1.1em; }
        .medal-count .n {
            font-size: 0.9em;
            min-width: 20px;
            text-align: right;
        }
        .name-link {
            cursor: pointer;
            color: var(--accent);
        }
        .name-link:hover { text-decoration: underline; }

        .empty-state {
            text-align: center;
            color: var(--text-secondary);
            padding: 48px;
        }
        .loading {
            text-align: center;
            color: var(--text-secondary);
            padding: 48px;
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="page-header">
        <h1>Imperial Cup 2026 — Results</h1>
        <div class="subtitle">June 19–21, 2026 · Full scoresheet results</div>
        <div class="nav-links">
            <a href="dance.html">← Schedule & Participants</a>
        </div>
    </div>

    <div class="container">
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('leaderboard')">🏆 Leaderboard</button>
            <button class="tab-btn" onclick="switchTab('headtohead')">⚔️ Head-to-Head</button>
        </div>

        <div id="tab-leaderboard" class="tab-content active">
            <div class="loading" id="leaderboardLoading">Loading results…</div>
        </div>

        <div id="tab-headtohead" class="tab-content">
            <div class="search-box">
                <input type="text" id="h2hSearch" placeholder="Search competitor to add…" autocomplete="off"
                    oninput="onH2HSearch(this.value)" onfocus="onH2HSearch(this.value)">
                <div class="search-dropdown" id="h2hDropdown"></div>
            </div>
            <div class="selected-chips" id="selectedChips"></div>
            <div id="h2hTable"><div class="empty-state">Add two or more competitors above to compare.</div></div>
        </div>
    </div>

    <script>
        let resultsData = {};
        let personResultsData = {};
        let sortedNames = [];
        let selectedPeople = [];
        let lbSortCol = 'gold';
        let lbSortAsc = false;

        async function loadData() {
            try {
                const [rRes, prRes] = await Promise.all([
                    fetch('dance_assets/results.json'),
                    fetch('dance_assets/person_results.json')
                ]);
                resultsData = await rRes.json();
                personResultsData = await prRes.json();
                sortedNames = Object.keys(personResultsData).sort();
                buildLeaderboard();
            } catch (e) {
                document.getElementById('leaderboardLoading').textContent = 'Error loading results: ' + e.message;
            }
        }

        function switchTab(name) {
            document.querySelectorAll('.tab-btn').forEach((b, i) => {
                b.classList.toggle('active', ['leaderboard','headtohead'][i] === name);
            });
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + name).classList.add('active');
        }

        function formatName(name) {
            if (!name || !name.includes(',')) return name;
            const [last, first] = name.split(',').map(n => n.trim());
            return `${first} ${last}`;
        }

        function placementClass(p) {
            const n = parseInt(p);
            if (n === 1) return 'gold';
            if (n === 2) return 'silver';
            if (n === 3) return 'bronze';
            if (!isNaN(n)) return 'other';
            return 'dnc';
        }

        function placementDisplay(p) {
            const n = parseInt(p);
            if (!p || isNaN(n)) return '–';
            const medal = n === 1 ? '🥇' : n === 2 ? '🥈' : n === 3 ? '🥉' : null;
            const sfx = n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th';
            return medal ? `${medal} ${n}${sfx}` : `${n}${sfx}`;
        }

        // ── Leaderboard ────────────────────────────────────────────────────
        function buildLeaderboard() {
            const rows = [];
            for (const [name, entries] of Object.entries(personResultsData)) {
                let gold = 0, silver = 0, bronze = 0, top5 = 0, total = entries.length;
                for (const e of entries) {
                    const p = parseInt(e.placement);
                    if (p === 1) gold++;
                    else if (p === 2) silver++;
                    else if (p === 3) bronze++;
                    if (p <= 5) top5++;
                }
                rows.push({ name, gold, silver, bronze, top5, total });
            }

            sortLeaderboard(rows, lbSortCol, lbSortAsc);

            let html = `
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th class="rank-col">#</th>
                        <th>Competitor</th>
                        <th class="${lbSortCol==='gold'?'sorted':''}" onclick="resortLb('gold')">🥇 Gold ${lbSortCol==='gold'?'↓':''}</th>
                        <th class="${lbSortCol==='silver'?'sorted':''}" onclick="resortLb('silver')">🥈 Silver ${lbSortCol==='silver'?'↓':''}</th>
                        <th class="${lbSortCol==='bronze'?'sorted':''}" onclick="resortLb('bronze')">🥉 Bronze ${lbSortCol==='bronze'?'↓':''}</th>
                        <th class="${lbSortCol==='top5'?'sorted':''}" onclick="resortLb('top5')">Top 5 ${lbSortCol==='top5'?'↓':''}</th>
                        <th class="${lbSortCol==='total'?'sorted':''}" onclick="resortLb('total')">Events ${lbSortCol==='total'?'↓':''}</th>
                    </tr>
                </thead>
                <tbody>
            `;
            rows.forEach((r, i) => {
                html += `<tr>
                    <td class="rank-col">${i+1}</td>
                    <td><span class="name-link" onclick="goToDancePage('${r.name}')">${formatName(r.name)}</span></td>
                    <td style="text-align:center;color:var(--gold);font-weight:600;">${r.gold || '–'}</td>
                    <td style="text-align:center;color:var(--silver);font-weight:600;">${r.silver || '–'}</td>
                    <td style="text-align:center;color:var(--bronze);font-weight:600;">${r.bronze || '–'}</td>
                    <td style="text-align:center;">${r.top5 || '–'}</td>
                    <td style="text-align:center;color:var(--text-secondary);">${r.total}</td>
                </tr>`;
            });
            html += `</tbody></table>`;

            document.getElementById('tab-leaderboard').innerHTML = html;
        }

        function sortLeaderboard(rows, col, asc) {
            rows.sort((a, b) => {
                if (col === 'gold')   return asc ? a.gold - b.gold : b.gold - a.gold || b.silver - a.silver || b.bronze - a.bronze;
                if (col === 'silver') return asc ? a.silver - b.silver : b.silver - a.silver || b.gold - a.gold;
                if (col === 'bronze') return asc ? a.bronze - b.bronze : b.bronze - a.bronze || b.silver - a.silver;
                if (col === 'top5')   return asc ? a.top5 - b.top5 : b.top5 - a.top5;
                if (col === 'total')  return asc ? a.total - b.total : b.total - a.total;
                return 0;
            });
        }

        function resortLb(col) {
            if (lbSortCol === col) lbSortAsc = !lbSortAsc;
            else { lbSortCol = col; lbSortAsc = false; }
            buildLeaderboard();
        }

        function goToDancePage(name) {
            window.location.href = `dance.html?search=${encodeURIComponent(name)}`;
        }

        // ── Head-to-head ───────────────────────────────────────────────────
        function onH2HSearch(query) {
            const q = query.trim().toLowerCase();
            const dd = document.getElementById('h2hDropdown');
            if (!q) { dd.classList.remove('open'); return; }

            const matches = sortedNames
                .filter(n => n.toLowerCase().includes(q) || formatName(n).toLowerCase().includes(q))
                .filter(n => !selectedPeople.includes(n))
                .slice(0, 20);

            if (!matches.length) { dd.classList.remove('open'); return; }

            dd.innerHTML = matches.map(n =>
                `<div class="search-result-item" onclick="addPerson('${n}')">${formatName(n)}</div>`
            ).join('');
            dd.classList.add('open');
        }

        function addPerson(name) {
            if (selectedPeople.includes(name)) return;
            selectedPeople.push(name);
            document.getElementById('h2hSearch').value = '';
            document.getElementById('h2hDropdown').classList.remove('open');
            renderChips();
            buildH2HTable();
        }

        function removePerson(name) {
            selectedPeople = selectedPeople.filter(n => n !== name);
            renderChips();
            buildH2HTable();
        }

        function renderChips() {
            document.getElementById('selectedChips').innerHTML = selectedPeople.map(n => `
                <div class="chip">
                    ${formatName(n)}
                    <button onclick="removePerson('${n}')">×</button>
                </div>
            `).join('');
        }

        function buildH2HTable() {
            const el = document.getElementById('h2hTable');
            if (selectedPeople.length < 2) {
                el.innerHTML = '<div class="empty-state">Add two or more competitors above to compare.</div>';
                return;
            }

            // Collect all heats any selected person competed in; shared first
            const heatSets = selectedPeople.map(n =>
                new Set((personResultsData[n] || []).map(e => e.heat))
            );
            const sharedHeats = [...heatSets[0]].filter(h => heatSets.every(s => s.has(h)));
            const allHeats = [...new Set(selectedPeople.flatMap(n =>
                (personResultsData[n] || []).map(e => e.heat)
            ))].sort((a, b) => {
                const na = parseInt(a.replace('Heat ', '')) || 0;
                const nb = parseInt(b.replace('Heat ', '')) || 0;
                return na - nb;
            });

            // Build lookup map
            const lookup = {};
            selectedPeople.forEach(name => {
                (personResultsData[name] || []).forEach(e => {
                    if (!lookup[e.heat]) lookup[e.heat] = {};
                    lookup[e.heat][name] = e;
                });
            });

            let html = `<table class="comparison-table">
                <thead><tr>
                    <th>Heat</th>
                    <th>Event</th>
                    ${selectedPeople.map(n => `<th>${formatName(n)}</th>`).join('')}
                </tr></thead><tbody>`;

            let lastSection = null;
            allHeats.forEach(heat => {
                const isShared = sharedHeats.includes(heat);
                const section = isShared ? 'shared' : 'other';
                if (section !== lastSection) {
                    const label = isShared ? '⚔️ Shared Heats' : 'Other Heats';
                    html += `<tr><td colspan="${2 + selectedPeople.length}" style="padding:12px 14px 4px;font-size:0.75em;font-weight:600;text-transform:uppercase;color:var(--text-secondary);letter-spacing:0.1em;background:var(--bg-secondary);">${label}</td></tr>`;
                    lastSection = section;
                }

                const event = resultsData[heat]?.event || (lookup[heat] ? Object.values(lookup[heat])[0]?.event : '');
                html += `<tr>
                    <td style="color:var(--text-secondary);white-space:nowrap;">${heat}</td>
                    <td style="font-size:0.85em;">${event}</td>
                    ${selectedPeople.map(n => {
                        const entry = lookup[heat]?.[n];
                        if (!entry) return `<td class="placement-cell dnc">–</td>`;
                        const cls = placementClass(entry.placement);
                        return `<td class="placement-cell ${cls}">${placementDisplay(entry.placement)}</td>`;
                    }).join('')}
                </tr>`;
            });

            html += `</tbody></table>`;
            el.innerHTML = html;
        }

        // Close dropdown on outside click
        document.addEventListener('click', e => {
            if (!e.target.closest('.search-box')) {
                document.getElementById('h2hDropdown').classList.remove('open');
            }
        });

        loadData();
    </script>
</body>
</html>
```

- [ ] **Step 2: Add navigation link from dance.html to results.html**

In `public/projects/dance.html`, find the page header or top nav area and add a link to results.html. Find the `<h1>` or title area and add after it:

```html
<a href="results.html" style="font-size:0.75em; color:var(--accent); text-decoration:none; opacity:0.8;">🏆 View Results →</a>
```

- [ ] **Step 3: Test results.html in browser**

Serve locally, open results.html. Verify:
- Leaderboard loads with names, gold/silver/bronze counts
- Sorting by column works
- Head-to-head: search for "Agheeva", add, search for "Korzon", add — shared heat shows both placements side by side
- Clicking a name in leaderboard goes to dance.html

---

## Phase 4: Polish and Finalize

### Task 9: GA injection and final commit

**Files:**
- Run GA inject script
- Commit and push

- [ ] **Step 1: Run GA injection script to add analytics to results.html**

```bash
node scripts/inject-ga.js
```

- [ ] **Step 2: Final check — git status**

```bash
git status
git diff --stat
```

- [ ] **Step 3: Commit and push**

```bash
git add public/projects/results.html public/projects/dance.html \
        public/projects/dance_assets/results.json \
        public/projects/dance_assets/person_results.json \
        public/projects/dance_assets/scrape_results.py
git commit -m "feat: add Imperial Cup 2026 results — leaderboard, head-to-head, integrated placements

- scrape_results.py: generalized scoresheet scraper (config block for future comps)
- results.json + person_results.json: full judge marks + final placements for all heats
- dance.html: placement badges per event, full heat ranking expansion,
  competitor placement details in All Competitors block
- results.html: sortable leaderboard (gold/silver/bronze) + head-to-head comparison

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push git@github.com:lexy-mal/isasha.ca.git main
```

---

## Notes

- **Name matching:** `person_results.json` keys are stripped of trailing `(Num)` to match `participants.json` format. A small number of solo-only competitors (studios, teams) may not appear in `participants.json` — that's fine.
- **Scraper resilience:** `REQUEST_DELAY=0.5` keeps load light. Re-running is safe (overwrites JSON). For future comps change the 4 CONFIG vars at the top.
- **Graceful degradation:** All results calls in dance.html use optional chaining / empty fallbacks, so the page is fully functional even without results files.
- **Head-to-head "shared first":** heats where all selected competitors appear are shown first for easy comparison; others follow sorted by heat number.
