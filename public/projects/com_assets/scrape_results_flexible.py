#!/usr/bin/env python3
"""
Flexible Competition Results Scraper  ***SUPERSEDED — see scrape_results_dat.py***

DO NOT USE THIS TO SCRAPE RESULTS. It is retained because scrape_results_dat.py
reuses its index/judge/save helpers, and for reference.

Why: CompMngr renders a single-dance heat heading and a dance sub-heading with the
same <strong><em> markup, so this parser cannot tell them apart and silently folds
single-dance heats into the previous heat as if they were dances. That dropped ~80%
of heats (National 2026: 473 of 2,683; Imperial Cup: 494 of 1,278) with no error.
It also needs one CGI request per competitor (~956) instead of 2.

See SCORESHEET_PARSING.md for the full write-up.

Fetches scoresheet data from configurable competition URLs.

Usage:
    python3 scrape_results_flexible.py [competition_id]

If no competition_id provided, uses COMPETITION_ID from .env file.
"""

import json
import sys
import os
import time
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from collections import defaultdict
from config import get_config, get_output_dir

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch(url, data=None, max_retries=3):
    """GET or POST with retries"""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data,
                headers={"User-Agent": UA,
                         "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=30) as r:
                response_data = r.read()
                # Try UTF-8 first, fall back to ISO-8859-1
                try:
                    return response_data.decode("utf-8")
                except UnicodeDecodeError:
                    return response_data.decode("iso-8859-1", errors="replace")
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"  retry {attempt+1}: {e}", file=sys.stderr)
            time.sleep(1)


class IndexParser(HTMLParser):
    """Parses <option value='ID=Name (Num)'> entries from index page"""

    def __init__(self):
        super().__init__()
        self.persons = []
        self.number_map = {}
        self._in_select = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "select" and d.get("name") == "PERSON_LIST":
            self._in_select = True
        if tag != "option" or not self._in_select:
            return
        val = d.get("value", "")
        m = re.match(r"(\d+)=(.+)", val)
        if not m:
            return
        pid, full = m.group(1), m.group(2).strip()
        nm = re.search(r"\((\d+)\)\s*$", full)
        number = nm.group(1) if nm else None
        self.persons.append({"id": pid, "fullName": full, "number": number})
        if number:
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
    """Extract judge ID → name map from the 'List of Judges' section"""
    judges = {}
    block = re.search(r'List of Judges(.+?)(?:</td>|</p>)', html, re.S | re.I)
    if not block:
        return judges
    for m in re.finditer(r'\b(\d{2})\s+([A-Z][^\n<]{2,50})', block.group(1)):
        jid, name = m.group(1), m.group(2).strip()
        if name.lower() != "scrutineer":
            judges[jid] = name
    return judges


class ScoresheetParser(HTMLParser):
    """Parses one person's scoresheet HTML into a list of heat dicts"""

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
        if self._in_em:
            self._em_buf += data
        elif self._in_strong:
            self._strong_buf += data
        elif self._cell_open:
            self._cur_cell += data

    def handle_entityref(self, name):
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

        if len(cells) == 1:
            dance_name = cells[0].strip()
            if dance_name and self._cur_heat is not None and not self._in_summary:
                self._cur_dance = {
                    "dance": dance_name,
                    "judges": [],
                    "rows": []
                }
                self._cur_heat["dances"].append(self._cur_dance)
                self._header_row = None
            return

        if cells[0].strip() == "Names":
            self._header_row = cells
            return

        if self._header_row is None:
            self._header_row = cells
            return

        if cells[0].strip() in ("No.", "", "\xa0", "&nbsp"):
            return

        if self._in_summary:
            self._parse_summary_row(cells)
        elif self._header_row and self._header_row[0].strip() == "Names":
            self._parse_numeric_row(cells)
        else:
            self._parse_score_row(cells)

    def _judge_cols(self):
        if not self._header_row:
            return []
        judges = []
        for i, h in enumerate(self._header_row[1:], 1):
            h_clean = h.strip()
            if h_clean in ("", "\xa0", "&nbsp"):
                break
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
        if not re.match(r"^\d+$", placement):
            return

        self._cur_dance["rows"].append({
            "number": number,
            "names": names,
            "marks": marks,
            "placement": placement
        })

    def _parse_numeric_row(self, cells):
        if not self._cur_dance or not self._header_row:
            return
        no_cell = cells[0].strip()
        m = re.match(r"(\d+)\s+(.+)", no_cell)
        if m:
            number, names = m.group(1), m.group(2).strip()
        else:
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

        has_overall = overall_idx is not None and len(place_indices) >= 2
        if not has_overall:
            return
        overall_place = cells[place_indices[1]].strip() if place_indices[1] < len(cells) else ""
        if not re.match(r"^\d+$", overall_place):
            return

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


def post_scoresheet(person, config):
    """POST for one person's scoresheet"""
    payload = urllib.parse.urlencode({
        "DATA_FILE": config['results_data_file'],
        "COMP_NAME": config['competition_id'],
        "PERSON_LIST": f"{person['id']}={person['fullName']}"
    }).encode()
    return fetch(config['results_cgi_url'], data=payload, max_retries=config['max_retries'])


def merge_heats(all_heats_list):
    """Deduplicate heats from multiple scoresheets"""
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

            existing_dances = {d["dance"]: d for d in existing["dances"]}
            for d in h["dances"]:
                if d["dance"] not in existing_dances or \
                   len(d["rows"]) > len(existing_dances[d["dance"]]["rows"]):
                    existing_dances[d["dance"]] = d
            existing["dances"] = list(existing_dances.values())

            existing_summary = {(r["number"] or r["names"]): r for r in existing["finalSummary"]}
            for row in h.get("finalSummary", []):
                key = row["number"] or row["names"]
                if key not in existing_summary or \
                   len(row.get("dances", {})) > len(existing_summary[key].get("dances", {})):
                    existing_summary[key] = row
            existing["finalSummary"] = list(existing_summary.values())

    return merged


def fill_missing_from_dances(results):
    """Reconstruct missing competitor entries from per-dance table rows"""
    added_total = 0
    for heat_key, heat in results.items():
        dances = [d for d in heat.get("dances", []) if d["rows"]]
        if not dances:
            continue

        min_rows = min(len(d["rows"]) for d in dances)
        final_dances = [d for d in dances if len(d["rows"]) == min_rows]

        all_final = {}
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


def build_person_results(results, number_map):
    """Invert results.json to person_results.json"""
    person_results = defaultdict(list)

    for heat_key, heat in results.items():
        for row in heat.get("finalSummary", []):
            number = row["number"]
            raw_names = row["names"]

            lead_full = number_map.get(number)

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

            if lead_full:
                person_results[lead_full].append(entry)
            else:
                person_results[raw_names].append(entry)

            if follow_surname and follow_surname != lead_surname:
                person_results[raw_names].append(entry)

    return dict(person_results)


def save_json(data, output_dir, filename):
    """Save data to JSON file"""
    try:
        filepath = output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved {filepath} ({len(data)} entries)", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}", file=sys.stderr)
        return False


def main():
    comp_id = sys.argv[1] if len(sys.argv) > 1 else None
    config = get_config(comp_id)
    output_dir = get_output_dir(config['competition_id'])

    if not config['results_index_url']:
        print(f"No RESULTS_INDEX_URL configured for {config['competition_id']}", file=sys.stderr)
        print(f"Skipping results scraping. To enable, set RESULTS_INDEX_URL in .env", file=sys.stderr)
        return 0

    print(f"Fetching {config['competition_id']} competitor index...", file=sys.stderr)
    html = fetch(config['results_index_url'], max_retries=config['max_retries'])
    persons, number_map = parse_index(html)
    judges = parse_judges(html)
    print(f"Found {len(persons)} competitors, {len(number_map)} with numbers, "
          f"{len(judges)} judges", file=sys.stderr)

    if not persons:
        print("ERROR: No persons found in index. Check RESULTS_INDEX_URL.", file=sys.stderr)
        return 1

    all_heats_list = []
    failed = []

    for i, person in enumerate(persons):
        name = person["fullName"]
        print(f"[{i+1}/{len(persons)}] {name}", file=sys.stderr, end="  ")
        try:
            html = post_scoresheet(person, config)
            heats = parse_scoresheet(html)
            all_heats_list.append(heats)
            print(f"→ {len(heats)} heats", file=sys.stderr)
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)
            failed.append(name)
        time.sleep(config['request_delay'])

    if failed:
        print(f"\nFailed ({len(failed)}): {failed}", file=sys.stderr)

    print("\nMerging heats...", file=sys.stderr)
    results = merge_heats(all_heats_list)
    print(f"Unique heats: {len(results)}", file=sys.stderr)

    print("Filling missing results from dance tables...", file=sys.stderr)
    results, added = fill_missing_from_dances(results)
    print(f"Reconstructed {added} missing entries", file=sys.stderr)

    print("Building person results...", file=sys.stderr)
    person_results = build_person_results(results, number_map)
    print(f"Persons with results: {len(person_results)}", file=sys.stderr)

    if not save_json(results, output_dir, "results.json"):
        return 1
    if not save_json(person_results, output_dir, "person_results.json"):
        return 1
    if not save_json(judges, output_dir, "judges.json"):
        return 1

    print(f"\nSummary:", file=sys.stderr)
    print(f"  Competition: {config['competition_id']}", file=sys.stderr)
    print(f"  Output directory: {output_dir}", file=sys.stderr)
    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
