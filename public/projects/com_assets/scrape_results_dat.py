#!/usr/bin/env python3
"""
Competition Results Scraper (.dat source)

CompMngr publishes every scoresheet in a single pipe-delimited .dat file next to
the ScoresheetsByPerson page. Parsing that instead of driving the CGI once per
person is both faster (2 requests instead of ~1000) and MORE CORRECT: the HTML
path cannot reliably tell a single-dance heat heading from a dance sub-heading,
because CompMngr renders both as <strong><em>...</em></strong>, so it silently
dropped every single-dance heat. The .dat marks multi-dance events with a
leading '=' and needs no such guesswork.

Usage:
    python3 scrape_results_dat.py [competition_id]

Outputs results.json / person_results.json / judges.json, same schema as before.
"""

import sys
import re
import urllib.request
from collections import defaultdict

from config import get_config, get_output_dir
from scrape_results_flexible import (
    fetch, parse_index, parse_judges, save_json,
)

# Round markers appear as " - Semi-final", occasionally bare " Final", and as
# " - First Round" (7 National 2026 events, which went unstripped and so failed to
# join the schedule until this was added).
# They are stripped from `event` so results join to heat_events.json / participants.json,
# and preserved separately in `round`.
ROUND_RE = re.compile(
    r'\s*(?:-\s*)?(Quarter-?final|Semi-?final|Final|Round\s+\d+'
    r'|(?:First|Second|Third|Fourth)\s+Round)\s*$',
    re.IGNORECASE,
)

# Decisive round first: a heat's FINAL round is the record with no marker at all
# (verified against Heat 467/665, which carry Quarter-final + Semi-final + unmarked).
ROUND_RANK = {'': 0, 'Final': 1, 'Semi-final': 2, 'Quarter-final': 3, 'First Round': 4}


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"



def _clean(full_name):
    """'Abdullayeva, Safiya (101)' -> 'Abdullayeva, Safiya'"""
    return re.sub(r'\s*\(\d+\)\s*$', '', full_name).strip()


def _surname(name):
    return name.split(',')[0].strip().lower()


def round_progression(heat, pid):
    """Chronological (earliest -> latest) list of round labels a person actually
    danced in this heat, e.g. ['Quarter-final', 'Semi-final', 'Final']. Empty for
    single-round heats, where there is no recall history to show.

    heat['rounds'] is decisive-round-first (Final, then Semi-final, then
    Quarter-final -- see merge_records), so reverse it to get dance order.
    """
    rounds = heat.get('rounds') or []
    if len(rounds) < 2:
        return []
    chronological = list(reversed(rounds))
    return [rnd['round'] or 'Final' for rnd in chronological if pid in rnd['personIds']]


def build_person_results(results, number_map, persons):
    """Invert results.json to person_results.json.

    Unlike the HTML scraper's version, this resolves competitors using the person
    ids the .dat attaches to every record. Only ~55% of competitors have a back
    number, so number_map alone left the rest keyed by the raw "Lead/Follow"
    string instead of a real name; the id list closes that gap.
    """
    by_id = {p['id']: _clean(p['fullName']) for p in persons}
    id_by_name = {name: pid for pid, name in by_id.items()}
    person_results = defaultdict(list)
    placed = set()

    for heat in results.values():
        candidates = [by_id[i] for i in heat.get('personIds', []) if i in by_id]
        by_surname = defaultdict(list)
        for name in candidates:
            by_surname[_surname(name)].append(name)

        for row in heat.get('finalSummary', []):
            entry = {
                'heat': heat['heat'],
                'event': heat['event'],
                'placement': row['placement'],
                'number': row['number'],
                'names': row['names'],
                'dancePlacements': row.get('dances', {}),
            }

            parts = [p.strip() for p in row['names'].split('/')]
            resolved = []

            # The back number identifies ONE registered partner, but not reliably the
            # first-listed one -- in pro-am it is often the follow (e.g. row
            # "Celino/Choque" carries Choque's number). So take the numbered person if
            # we have them AND still resolve every surname in the row independently.
            numbered = number_map.get(row['number'])
            if numbered:
                resolved.append(numbered)

            # Resolve each surname against the people actually in this heat. Only
            # accept unambiguous hits, so two same-surname competitors in one heat
            # never get credited with each other's placement.
            for part in parts:
                if not part:
                    continue
                matches = by_surname.get(part.split()[-1].strip().lower(), [])
                if len(matches) == 1 and matches[0] not in resolved:
                    resolved.append(matches[0])

            if not resolved:
                resolved = [row['names']]

            for name in resolved:
                person_entry = dict(entry)
                pid = id_by_name.get(name)
                prog = round_progression(heat, pid) if pid else []
                if prog:
                    person_entry['rounds'] = prog
                person_results[name].append(person_entry)
                placed.add((name, heat['heat'], heat['event']))

    # Competitors knocked out in an earlier round never appear in a final summary, so
    # the loop above gives them nothing at all. Credit them with the furthest round
    # they actually danced, using the per-round person ids from the .dat.
    for heat in results.values():
        rounds = heat.get('rounds') or []
        if len(rounds) < 2:
            continue
        furthest = {}
        for rnd in rounds:
            rank = ROUND_RANK.get(rnd['round'], 9)
            for pid in rnd['personIds']:
                name = by_id.get(pid)
                if name and rank < furthest.get(name, (99, '', ''))[0]:
                    furthest[name] = (rank, rnd['round'] or 'Final', pid)
        for name, (_, round_name, pid) in furthest.items():
            if (name, heat['heat'], heat['event']) in placed:
                continue
            person_results[name].append({
                'heat': heat['heat'],
                'event': heat['event'],
                'placement': '',
                'reachedRound': round_name,
                'rounds': round_progression(heat, pid),
                'number': '',
                'names': name,
                'dancePlacements': {},
            })

    return dict(person_results)


def fetch_dat(url):
    """Download the .dat. CompMngr emits windows-1252, so decode it explicitly
    rather than going through fetch() (which assumes utf-8 then iso-8859-1 and
    would mangle the 0x80-0x9F range)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("cp1252", errors="replace")


def split_records(text):
    """Split the .dat into raw record bodies (the '<ids ... >' blocks)."""
    text = text.replace('\r\n', '\n')
    records = []
    for chunk in text.split('\n>'):
        chunk = chunk.strip()
        if chunk.startswith('<'):
            records.append(chunk)
    return records


def split_cells(line):
    """'|a|b||c|' -> ['a', 'b', '', 'c']"""
    return [c.strip() for c in line.strip().strip('|').split('|')]


def judge_columns(header):
    """Judge ids are the numeric header cells before the first non-numeric/blank one.

    Stops at the '' separator (skating-system columns 1, 1-2, 1-3 follow it) and at
    'Avg.'/'Total', so those are never mistaken for judges.
    """
    cols = []
    for i, cell in enumerate(header[1:], 1):
        if not re.fullmatch(r'\d+', cell):
            break
        cols.append((i, cell))
    return cols


def parse_round(heading):
    """('Heat 5: Foo - Semi-final') -> ('Heat 5: Foo', 'Semi-final')"""
    m = ROUND_RE.search(heading)
    if not m:
        return heading.strip(), ''
    return heading[:m.start()].strip(), normalize_round(m.group(1))


def normalize_round(label):
    """Fold spelling variants onto the canonical round names used by ROUND_RANK."""
    l = label.lower().replace('-', '').replace(' ', '')
    if l.startswith('quarter'):
        return 'Quarter-final'
    if l.startswith('semi'):
        return 'Semi-final'
    if l.startswith('final'):
        return 'Final'
    if l.startswith('round'):
        return label.strip()
    return label.strip()


def parse_row(cells, header):
    """One competitor row -> {number, names, marks, placement} or None."""
    m = re.match(r'(\d+)\s+(.+)', cells[0])
    if m:
        number, names = m.group(1), m.group(2).strip()
    else:
        number, names = '', cells[0]
    if not names:
        return None

    marks = {}
    for idx, jid in judge_columns(header):
        if idx < len(cells) and cells[idx]:
            marks[jid] = cells[idx]

    placement = cells[-1] if cells else ''
    if not re.fullmatch(r'\d+', placement):
        # Recall rounds end in 'Recall'/'' rather than a placement.
        placement = ''

    return {'number': number, 'names': names, 'marks': marks, 'placement': placement}


def parse_summary_row(cells, header):
    """Final-summary row -> {number, names, dances, total, placement}."""
    m = re.match(r'(\d+)\s+(.+)', cells[0])
    if m:
        number, names = m.group(1), m.group(2).strip()
    else:
        number, names = '', cells[0]
    if not names:
        return None

    dances, total = {}, ''
    for i, head in enumerate(header[1:], 1):
        if i >= len(cells):
            break
        if head.lower() in ('total', 'result', 'place'):
            if head.lower() == 'total':
                total = cells[i]
            continue
        if head:
            dances[head] = cells[i]

    placement = cells[-1] if cells else ''
    if not re.fullmatch(r'\d+', placement):
        placement = ''
    return {'number': number, 'names': names, 'dances': dances,
            'total': total, 'placement': placement}


def parse_record(record):
    """Parse one '<ids / heading / tables' block into a heat dict."""
    lines = [l for l in record.split('\n') if l.strip()]
    if len(lines) < 2:
        return None

    person_ids = [p for p in lines[0].lstrip('<').split(',') if p.strip()]
    raw_heading = lines[1]
    is_multi = raw_heading.startswith('=')
    heading = raw_heading.lstrip('=').strip()

    m = re.match(r'(Heat\s+\S+):\s*(.+)', heading)
    if not m:
        return None
    heat = m.group(1).strip()
    event_with_round = m.group(2).strip()
    event, round_label = parse_round(event_with_round)

    dances, final_summary = [], []
    cur_dance = None
    header = None
    in_summary = False

    for line in lines[2:]:
        if line.startswith('|'):
            cells = split_cells(line)
            if header is None:
                header = cells
                continue
            if cells[0] in ('No.', 'Names', ''):
                header = cells
                continue
            if in_summary:
                row = parse_summary_row(cells, header)
                if row:
                    final_summary.append(row)
            else:
                if cur_dance is None:
                    # Single-dance heat: the table follows the heading directly, with
                    # no dance sub-heading. Name it from the event's trailing token.
                    cur_dance = {'dance': event.split()[-1] if event.split() else 'Dance',
                                 'judges': [jid for _, jid in judge_columns(header)],
                                 'rows': []}
                    dances.append(cur_dance)
                if not cur_dance['judges']:
                    cur_dance['judges'] = [jid for _, jid in judge_columns(header)]
                row = parse_row(cells, header)
                if row:
                    cur_dance['rows'].append(row)
        else:
            section = line.strip()
            header = None
            if section.lower() == 'final summary':
                in_summary = True
                cur_dance = None
            else:
                in_summary = False
                cur_dance = {'dance': section, 'judges': [], 'rows': []}
                dances.append(cur_dance)

    # buildHeatRanking() in com.html renders nothing without finalSummary, so derive
    # one for single-dance heats from their only dance.
    if not final_summary and len(dances) == 1 and dances[0]['rows']:
        letter = (dances[0]['dance'] or 'D')[0].upper()
        for row in dances[0]['rows']:
            if row['placement']:
                final_summary.append({
                    'number': row['number'], 'names': row['names'],
                    'dances': {letter: row['placement']},
                    'total': row['placement'], 'placement': row['placement'],
                })

    return {
        'heat': heat,
        'event': event,
        'round': round_label,
        'multiDance': is_multi,
        'personIds': person_ids,
        'dances': dances,
        'finalSummary': final_summary,
    }


def merge_records(records):
    """Key by 'heat|event', keeping the decisive round's marks as the heat body.

    Earlier rounds are retained as a lightweight `rounds` roster (round name + the
    person ids who danced it) rather than their full mark tables — that is enough to
    say "reached the semi-final" for competitors who never appear in a final summary,
    without doubling the size of results.json.
    """
    groups = defaultdict(list)
    for rec in records:
        groups[f"{rec['heat']}|{rec['event']}"].append(rec)

    merged = {}
    for key, recs in groups.items():
        # Most decisive first: unmarked/Final, then Semi-final, then Quarter-final.
        recs.sort(key=lambda r: (ROUND_RANK.get(r['round'], 9), -len(r['finalSummary'])))
        primary = recs[0]
        primary['rounds'] = [
            {'round': r['round'], 'personIds': r['personIds']} for r in recs
        ]
        merged[key] = primary
    return merged


def main():
    comp_id = sys.argv[1] if len(sys.argv) > 1 else None
    config = get_config(comp_id)
    output_dir = get_output_dir(config['competition_id'])

    dat_url = config['results_dat_url']
    index_url = config['results_index_url']

    if not dat_url:
        print(f"No resultsDatUrl configured for {config['competition_id']} — skipping.",
              file=sys.stderr)
        return 0

    print(f"Fetching {config['competition_id']} scoresheet data...", file=sys.stderr)
    dat = fetch_dat(dat_url)
    print(f"  {len(dat)} chars", file=sys.stderr)

    persons, number_map, judges = [], {}, {}
    if index_url:
        print("Fetching competitor index (names + judges)...", file=sys.stderr)
        html = fetch(index_url)
        persons, number_map = parse_index(html)
        judges = parse_judges(html)
        print(f"  {len(persons)} competitors, {len(number_map)} numbered, "
              f"{len(judges)} judges", file=sys.stderr)

    raw = split_records(dat)
    print(f"Records: {len(raw)}", file=sys.stderr)

    parsed, skipped = [], []
    for rec in raw:
        got = parse_record(rec)
        if got:
            parsed.append(got)
        else:
            lines = rec.split('\n')
            skipped.append(lines[1].lstrip('=').strip() if len(lines) > 1 else '?')
    print(f"Parsed:  {len(parsed)}", file=sys.stderr)
    if skipped:
        # Combined-event awards carry no heat number, so they cannot join the schedule
        # the frontend renders. Report them rather than dropping them silently.
        print(f"Skipped: {len(skipped)} non-heat records", file=sys.stderr)
        for h in skipped[:3]:
            print(f"    e.g. {h[:76]}", file=sys.stderr)

    results = merge_records(parsed)
    print(f"Unique heat/event: {len(results)}", file=sys.stderr)

    person_results = build_person_results(results, number_map, persons)
    print(f"Persons with results: {len(person_results)}", file=sys.stderr)

    if not save_json(results, output_dir, "results.json"):
        return 1
    if not save_json(person_results, output_dir, "person_results.json"):
        return 1
    if judges and not save_json(judges, output_dir, "judges.json"):
        return 1

    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
