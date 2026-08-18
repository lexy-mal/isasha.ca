#!/usr/bin/env python3
"""
Competition Results Scraper
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
REQUEST_DELAY = 0.5   # seconds between POSTs (be polite)
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
        self.persons = []       # [{id, fullName, number}]
        self.number_map = {}    # number_str -> fullName (no trailing parens)
        self._in_select = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "select" and d.get("name") == "PERSON_LIST":
            self._in_select = True
        if tag != "option" or not self._in_select:
            return
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
            # store clean name without trailing (Num)
            clean = re.sub(r"\s*\(\d+\)\s*$", "", full).strip()
            self.number_map[number] = clean

    def handle_endtag(self, tag):
        if tag == "select":
            self._in_select = False


def parse_index(html):
    p = IndexParser()
    p.feed(html)
    return p.persons, p.number_map


def parse_judges(html):
    """Extract judge ID → name map from the 'List of Judges' section of the index page."""
    judges = {}
    # Match lines like: "01 Annie Lebedeva" (inside the List of Judges block)
    block = re.search(r'List of Judges(.+?)(?:</td>|</p>)', html, re.S | re.I)
    if not block:
        return judges
    for m in re.finditer(r'\b(\d{2})\s+([A-Z][^\n<]{2,50})', block.group(1)):
        jid, name = m.group(1), m.group(2).strip()
        if name.lower() != "scrutineer":
            judges[jid] = name
    return judges


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
            {"number":"239","names":"Abdullayeva/",
             "marks":{"03":"1",...},"placement":"1"}
          ]
        }
      ],
      "finalSummary": [
        {"number":"239","names":"Abdullayeva/",
         "dances":{"W":"1","T":"2"},"total":"5","placement":"1"}
      ]
    }
    """

    def __init__(self):
        super().__init__()
        self.heats = []
        self._cur_heat = None
        self._cur_dance = None
        self._in_table = False
        self._header_row = None
        self._cur_row = []
        self._cur_cell = ""
        self._cell_open = False
        self._in_summary = False
        self._tag_stack = []
        self._strong_buf = ""
        self._in_strong = False
        self._em_buf = ""
        self._in_em = False

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag == "strong":
            self._in_strong = True
            self._strong_buf = ""
        elif tag == "em":
            self._in_em = True
            self._em_buf = ""
        elif tag == "table":
            self._in_table = True
            self._header_row = None
            self._cur_row = []
        elif tag == "td" and self._in_table:
            self._cur_cell = ""
            self._cell_open = True
        elif tag == "tr" and self._in_table:
            self._cur_row = []
        elif tag == "br" and self._cell_open:
            self._cur_cell += " "

    def handle_endtag(self, tag):
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

        if tag == "strong":
            txt = self._strong_buf.strip()
            self._in_strong = False
            # "Heat 348: A-JV2 Solo Indv. ..."
            m = re.match(r"(Heat\s+\S+):\s*(.+)", txt)
            if m:
                if self._cur_heat:
                    self._finalize_heat()
                self._cur_heat = {
                    "heat": m.group(1).strip(),
                    "event": m.group(2).strip(),
                    "dances": [],
                    "finalSummary": []
                }
                self._cur_dance = None
            return

        if tag == "em":
            dance_name = self._em_buf.strip()
            self._in_em = False
            if dance_name and self._cur_heat is not None:
                self._in_summary = (dance_name.lower() == "final summary")
                if not self._in_summary:
                    self._cur_dance = {
                        "dance": dance_name,
                        "judges": [],
                        "rows": []
                    }
                    self._cur_heat["dances"].append(self._cur_dance)
            return

        if tag == "td" and self._in_table and self._cell_open:
            self._cur_row.append(self._cur_cell.strip())
            self._cell_open = False

        if tag == "tr" and self._in_table and self._cur_row:
            self._process_row(list(self._cur_row))
            self._cur_row = []

        if tag == "table":
            self._in_table = False
            self._header_row = None

    def handle_data(self, data):
        # em is inner tag so takes priority when both are active
        if self._in_em:
            self._em_buf += data
        elif self._in_strong:
            self._strong_buf += data
        elif self._cell_open:
            self._cur_cell += data

    def handle_entityref(self, name):
        # &nbsp; -> space
        ch = " " if name == "nbsp" else ""
        if self._in_em:
            self._em_buf += ch
        elif self._in_strong:
            self._strong_buf += ch
        elif self._cell_open:
            self._cur_cell += ch

    def handle_charref(self, name):
        try:
            ch = chr(int(name[1:], 16) if name.startswith('x') else int(name))
        except Exception:
            ch = ""
        if self._in_em:
            self._em_buf += ch
        elif self._in_strong:
            self._strong_buf += ch
        elif self._cell_open:
            self._cur_cell += ch

    def _process_row(self, row):
        cells = row
        if not cells or all(c in ("", "\xa0", "&nbsp") for c in cells):
            return

        # Single-cell row = dance name in numeric-score format
        # (all dances share one <table>; dance name precedes its header+data rows)
        if len(cells) == 1:
            dance_name = cells[0].strip()
            if dance_name and self._cur_heat is not None and not self._in_summary:
                self._cur_dance = {
                    "dance": dance_name,
                    "judges": [],
                    "rows": []
                }
                self._cur_heat["dances"].append(self._cur_dance)
                self._header_row = None  # next row is this dance's header
            return

        # "Names" as first cell = numeric-score column header
        if cells[0].strip() == "Names":
            self._header_row = cells
            return

        # First substantive row after table start = header (recall format)
        if self._header_row is None:
            self._header_row = cells
            return

        # Skip recall-format "No." header rows
        if cells[0].strip() in ("No.", "", "\xa0", "&nbsp"):
            return

        if self._in_summary:
            self._parse_summary_row(cells)
        elif self._header_row and self._header_row[0].strip() == "Names":
            self._parse_numeric_row(cells)
        else:
            self._parse_score_row(cells)

    def _judge_cols(self):
        """Return list of (col_index, judge_id) for the current header."""
        if not self._header_row:
            return []
        judges = []
        for i, h in enumerate(self._header_row[1:], 1):
            h_clean = h.strip()
            if h_clean in ("", "\xa0", "&nbsp"):
                break  # separator column
            # judge IDs are 2-digit numbers like "03", "04"
            if re.match(r"^\d+$", h_clean):
                judges.append((i, h_clean))
        return judges

    def _parse_score_row(self, cells):
        if not self._cur_dance or not self._header_row:
            return
        no_cell = cells[0].strip()
        m = re.match(r"(\d+)\s+(.+)", no_cell)
        if not m:
            return
        number, names = m.group(1), m.group(2).strip()

        judge_cols = self._judge_cols()
        if not self._cur_dance["judges"]:
            self._cur_dance["judges"] = [jid for _, jid in judge_cols]

        marks = {}
        for col_idx, jid in judge_cols:
            if col_idx < len(cells):
                v = cells[col_idx].strip()
                if v and v not in ("\xa0", "&nbsp"):
                    marks[jid] = v

        placement = cells[-1].strip() if cells else ""
        # Skip if placement is not numeric (e.g. blank rows)
        if not re.match(r"^\d+$", placement):
            return

        self._cur_dance["rows"].append({
            "number": number,
            "names": names,
            "marks": marks,
            "placement": placement
        })

    def _parse_numeric_row(self, cells):
        """Parse a data row in the numeric-score (Pre-Competitive) format.

        Header: Names | judge# | ... | Avg. | Place [| Overall | Place]
        The last dance in a heat has an 'Overall' column and two 'Place' columns;
        the second Place gives the overall heat placement, which populates finalSummary.
        """
        if not self._cur_dance or not self._header_row:
            return
        no_cell = cells[0].strip()
        m = re.match(r"(\d+)\s+(.+)", no_cell)
        if m:
            number, names = m.group(1), m.group(2).strip()
        else:
            # Own-scoresheet rows omit the couple number — use names as dedup key
            number, names = "", no_cell
        if not names:
            return

        place_indices = []
        overall_idx = None
        avg_idx = None
        for i, h in enumerate(self._header_row):
            h_lower = h.strip().lower()
            if h_lower == "avg.":
                avg_idx = i
            elif h_lower == "place":
                place_indices.append(i)
            elif h_lower == "overall":
                overall_idx = i

        dance_place = cells[place_indices[0]].strip() if place_indices and place_indices[0] < len(cells) else ""
        avg = cells[avg_idx].strip() if avg_idx is not None and avg_idx < len(cells) else ""

        if dance_place and re.match(r"^\d+$", dance_place):
            self._cur_dance["rows"].append({
                "number": number,
                "names": names,
                "marks": {},
                "placement": dance_place,
                "avg": avg
            })

        # Last dance: has Overall column + two Place columns → overall placement
        has_overall = overall_idx is not None and len(place_indices) >= 2
        if not has_overall:
            return
        overall_place = cells[place_indices[1]].strip() if place_indices[1] < len(cells) else ""
        if not re.match(r"^\d+$", overall_place):
            return

        # Gather per-dance placements already collected across all dances
        dance_placements = {}
        for d in self._cur_heat["dances"]:
            for row in d["rows"]:
                if row["number"] == number:
                    dance_placements[d["dance"]] = row["placement"]
                    break

        overall_score = cells[overall_idx].strip() if overall_idx < len(cells) else ""
        existing_keys = {(r["number"] or r["names"]) for r in self._cur_heat["finalSummary"]}
        if (number or names) not in existing_keys:
            self._cur_heat["finalSummary"].append({
                "number": number,
                "names": names,
                "dances": dance_placements,
                "total": overall_score,
                "placement": overall_place
            })

    def _parse_summary_row(self, cells):
        if not self._cur_heat or not self._header_row:
            return
        no_cell = cells[0].strip()
        m = re.match(r"(\d+)\s+(.+)", no_cell)
        if not m:
            return
        number, names = m.group(1), m.group(2).strip()

        # header: ["No.", "W","T","V","F","Q", "Total", "Result"]
        dance_cols = []
        for h in self._header_row[1:]:
            h_clean = h.strip()
            if h_clean.lower() in ("total", "result", "", "\xa0", "&nbsp"):
                break
            dance_cols.append(h_clean)

        dance_placements = {}
        for i, d in enumerate(dance_cols):
            col_idx = i + 1
            if col_idx < len(cells):
                v = cells[col_idx].strip()
                if v and v not in ("\xa0", "&nbsp"):
                    dance_placements[d] = v

        total_idx = len(dance_cols) + 1
        total = cells[total_idx].strip() if total_idx < len(cells) else ""
        placement = cells[-1].strip() if cells else ""

        if not re.match(r"^\d+$", placement):
            return

        self._cur_heat["finalSummary"].append({
            "number": number,
            "names": names,
            "dances": dance_placements,
            "total": total,
            "placement": placement
        })

    def _finalize_heat(self):
        if self._cur_heat:
            self.heats.append(self._cur_heat)
            self._cur_heat = None

    def get_heats(self):
        self._finalize_heat()
        return self.heats


def parse_scoresheet(html):
    p = ScoresheetParser()
    p.feed(html)
    return p.get_heats()


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
    - Per dance: keep version with most rows (most complete).
    - finalSummary: union by competitor number, keeping the most complete row per person.
    """
    merged = {}
    for heats in all_heats_list:
        for h in heats:
            key = f"{h['heat']}|{h['event']}"
            if key not in merged:
                merged[key] = {
                    "heat": h["heat"],
                    "event": h["event"],
                    "dances": [],
                    "finalSummary": []
                }
            existing = merged[key]

            # Merge dances — keep version with most rows per dance name
            existing_dances = {d["dance"]: d for d in existing["dances"]}
            for d in h["dances"]:
                if d["dance"] not in existing_dances or \
                   len(d["rows"]) > len(existing_dances[d["dance"]]["rows"]):
                    existing_dances[d["dance"]] = d
            existing["dances"] = list(existing_dances.values())

            # Merge finalSummary — union by number (or names for no-number rows)
            existing_summary = {(r["number"] or r["names"]): r for r in existing["finalSummary"]}
            for row in h.get("finalSummary", []):
                key = row["number"] or row["names"]
                # Keep row with more dance columns (more complete data)
                if key not in existing_summary or \
                   len(row.get("dances", {})) > len(existing_summary[key].get("dances", {})):
                    existing_summary[key] = row
            existing["finalSummary"] = list(existing_summary.values())

    return merged


def fill_missing_from_dances(results):
    """
    For heats where finalSummary is incomplete, reconstruct missing competitor
    entries from per-dance table rows.

    Identifies 'final-round' dances as those with the fewest non-zero rows
    (semi-final dances have more rows than final-only dances). Assigns available
    placement slots to missing competitors sorted by their total dance score.
    """
    added_total = 0
    for heat_key, heat in results.items():
        dances = [d for d in heat.get("dances", []) if d["rows"]]
        if not dances:
            continue

        # Final-round dances = those with the fewest rows (semi excluded by larger count)
        min_rows = min(len(d["rows"]) for d in dances)
        final_dances = [d for d in dances if len(d["rows"]) == min_rows]

        # Collect all competitors from final-round dance tables
        all_final = {}  # (number or names) -> {names, dances: {dance_name: placement}}
        for dance in final_dances:
            for row in dance["rows"]:
                num = row["number"] or row["names"]
                if num not in all_final:
                    all_final[num] = {"names": row["names"], "dances": {}}
                place = row.get("placement", "")
                if place and re.match(r"^\d+$", place):
                    all_final[num]["dances"][dance["dance"]] = place

        in_summary = {(r["number"] or r["names"]) for r in heat.get("finalSummary", [])}
        missing = {n: d for n, d in all_final.items()
                   if n not in in_summary and d["dances"]}

        if not missing:
            continue

        existing_placements = {
            int(row["placement"]) for row in heat["finalSummary"]
            if re.match(r"^\d+$", str(row.get("placement", "")))
        }

        # Total competitors = highest known placement or summary size + missing count
        max_place = max(
            max(existing_placements, default=0),
            len(in_summary)
        ) + len(missing)
        available_slots = sorted(set(range(1, max_place + 1)) - existing_placements)

        def total_score(data):
            vals = [int(v) for v in data["dances"].values()
                    if re.match(r"^\d+$", str(v))]
            return sum(vals) if vals else 9999

        sorted_missing = sorted(missing.items(), key=lambda kv: total_score(kv[1]))

        for (num, data), slot in zip(sorted_missing, available_slots):
            entry = {
                "number": num,
                "names": data["names"],
                "dances": data["dances"],
                "total": str(total_score(data)),
                "placement": str(slot),
                "reconstructed": True
            }
            heat["finalSummary"].append(entry)
            added_total += 1
            print(f"  Reconstructed {heat_key}: #{num} {data['names'].strip('/')} "
                  f"→ place {slot}", file=sys.stderr)

    return results, added_total


def build_surname_map(persons):
    """Build a last-name → fullName map for resolving follow partners."""
    smap = {}
    for p in persons:
        # fullName is "Last, First" or "Last, First (Num)"
        clean = re.sub(r"\s*\(\d+\)\s*$", "", p["fullName"]).strip()
        last = clean.split(",")[0].strip().lower()
        smap[last] = clean
    return smap


def build_person_results(results, number_map, surname_map=None):
    """
    Invert results.json to person_results.json (name-keyed).
    Resolves competitor number → clean full name via number_map.
    For couple entries (e.g. "Korzon/Agheeva"), adds results to BOTH
    lead (resolved via number) and follow (resolved via surname_map).
    """
    person_results = defaultdict(list)

    for heat_key, heat in results.items():
        for row in heat.get("finalSummary", []):
            number = row["number"]
            raw_names = row["names"]  # e.g. "Korzon/Agheeva" or "Abdullayeva/"

            # Resolve lead via number_map
            lead_full = number_map.get(number)

            # Split names: "Lead/Follow" or "Solo/" (trailing slash)
            parts = raw_names.rstrip("/").split("/")
            lead_surname = parts[0].strip().lower() if parts else ""
            follow_surname = parts[1].strip().lower() if len(parts) > 1 and parts[1].strip() else None

            entry = {
                "heat": heat["heat"],
                "event": heat["event"],
                "placement": row["placement"],
                "number": number,
                "names": raw_names,
                "dancePlacements": row.get("dances", {})
            }

            # Add for lead
            if lead_full:
                person_results[lead_full].append(entry)
            elif surname_map and lead_surname:
                resolved = surname_map.get(lead_surname, raw_names)
                person_results[resolved].append(entry)
            else:
                person_results[raw_names].append(entry)

            # Add for follow if present
            if follow_surname and surname_map:
                follow_full = surname_map.get(follow_surname)
                if follow_full and follow_full != lead_full:
                    person_results[follow_full].append(entry)

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
    judges = parse_judges(html)
    print(f"Found {len(persons)} competitors, {len(number_map)} with numbers, "
          f"{len(judges)} judges", file=sys.stderr)

    if not persons:
        print("ERROR: No persons found in index. Check INDEX_URL.", file=sys.stderr)
        return 1

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

    print("Filling missing results from dance tables...", file=sys.stderr)
    results, added = fill_missing_from_dances(results)
    print(f"Reconstructed {added} missing entries", file=sys.stderr)

    print("Building person results...", file=sys.stderr)
    surname_map = build_surname_map(persons)
    person_results = build_person_results(results, number_map, surname_map)
    print(f"Persons with results: {len(person_results)}", file=sys.stderr)

    save_json(results, "results.json")
    save_json(person_results, "person_results.json")
    save_json(judges, "judges.json")

    print("\nDone.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
