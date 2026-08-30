#!/usr/bin/env python3
"""
Flexible Competition Data Scraper
Fetches participant and heat event data from configurable competition URLs.

Usage:
    python3 scrape_data_flexible.py [competition_id]

If no competition_id provided, uses COMPETITION_ID from .env file.
"""

import json
import sys
import os
import urllib.request
import re
from html.parser import HTMLParser
from pathlib import Path
from config import get_config, get_output_dir
from scrape_diff import compute_diff, has_changes, log_scrape_diff


class DanceDataParser(HTMLParser):
    """Parses competition participant data from HTML"""

    def __init__(self):
        super().__init__()
        self.participants = {}
        self.current_person = None
        self.current_partner = None
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.current_cell = ""

    def handle_starttag(self, tag, attrs):
        if tag == 'strong':
            self.current_cell = ""
        elif tag == 'table':
            self.in_table = True
            self.table_rows = []
        elif tag == 'tr' and self.in_table:
            self.current_row = []
        elif tag == 'td' and self.in_table:
            self.current_cell = ""
        elif tag == 'br':
            self.current_cell += " "

    def handle_endtag(self, tag):
        if tag == 'strong':
            text = self.current_cell.strip()
            if 'Entries for' in text:
                self.current_person = text.replace('Entries for', '').strip()
                self.current_partner = None
                if self.current_person not in self.participants:
                    self.participants[self.current_person] = []
            elif text.startswith('With'):
                partner_text = text.replace('With', '').strip()
                self.current_partner = partner_text if partner_text else None
        if tag == 'td' and self.in_table:
            self.current_row.append(self.current_cell.strip())
        elif tag == 'tr' and self.in_table and self.current_row:
            if len(self.current_row) >= 4 and 'Session@Time' not in self.current_row[0]:
                self.table_rows.append(self.current_row)
            self.current_row = []
        elif tag == 'table':
            self.in_table = False
            if self.current_person and self.table_rows:
                for row in self.table_rows:
                    session_time = row[0]
                    heat = row[2]
                    event = row[3]
                    awards_raw = row[4].strip() if len(row) > 4 else ''
                    awards = awards_raw or None

                    if '@' in session_time:
                        session, time = session_time.split('@', 1)
                    else:
                        session = session_time
                        time = ''

                    entry = {
                        'heat': heat,
                        'event': event,
                        'time': time.strip(),
                        'session': session.strip(),
                        'partner': self.current_partner,
                        'awards': awards
                    }
                    self.participants[self.current_person].append(entry)
            self.table_rows = []

    def handle_data(self, data):
        self.current_cell += data


def fetch_html(url):
    """Fetch HTML from URL with timeout"""
    if not url:
        print(f"Error: URL not configured", file=sys.stderr)
        return None

    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read()
            # Try UTF-8 first, fall back to ISO-8859-1
            try:
                html = data.decode('utf-8')
            except UnicodeDecodeError:
                html = data.decode('iso-8859-1')
            return html
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def parse_participants(html):
    """Parse participant data from HTML"""
    parser = DanceDataParser()
    parser.feed(html)
    return parser.participants


def build_heat_events(participants):
    """Build heat_events from participants data"""
    heat_events_dict = {}

    for person, entries in participants.items():
        for entry in entries:
            heat = entry['heat']
            event = entry['event']
            key = (heat, event)

            if key not in heat_events_dict:
                heat_events_dict[key] = {
                    'heat': heat,
                    'event': event,
                    'session': entry['session'],
                    'time': entry['time'],
                    'awards': entry.get('awards'),
                    'competitors': []
                }
            elif not heat_events_dict[key].get('awards') and entry.get('awards'):
                heat_events_dict[key]['awards'] = entry['awards']

            if person not in heat_events_dict[key]['competitors']:
                heat_events_dict[key]['competitors'].append(person)

    heat_events = sorted(
        heat_events_dict.values(),
        key=lambda x: (
            int(re.match(r'\d+', x['heat'].replace('Heat ', '')).group()) if re.match(r'\d+', x['heat'].replace('Heat ', '')) else 0,
            x['event']
        )
    )

    return heat_events


def format_participants(participants):
    """Format participants for output"""
    formatted = {}
    for person, entries in participants.items():
        formatted_entries = []
        for entry in entries:
            formatted_entry = {
                'heat': entry['heat'],
                'event': entry['event'],
                'time': entry['time'],
                'session': entry['session'],
                'partner': entry.get('partner'),
                'awards': entry.get('awards')
            }
            formatted_entries.append(formatted_entry)

        formatted[person] = {
            'entries': formatted_entries
        }

    return formatted


def save_json(data, output_dir, filename):
    """Save data to JSON file"""
    try:
        filepath = output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved {filepath}")
    except Exception as e:
        print(f"Error saving {filename}: {e}", file=sys.stderr)
        return False
    return True


def validate_data(participants, heat_events):
    """Validate data consistency"""
    errors = []

    for heat_event in heat_events:
        for competitor in heat_event['competitors']:
            if competitor not in participants:
                errors.append(f"Competitor '{competitor}' in heat event but not in participants")

    heat_event_keys = set((he['heat'], he['event']) for he in heat_events)
    for person, entries in participants.items():
        for entry in entries:
            key = (entry['heat'], entry['event'])
            if key not in heat_event_keys:
                errors.append(f"Heat {entry['heat']} for {person} not in heat_events")

    return errors


def main():
    comp_id = sys.argv[1] if len(sys.argv) > 1 else None
    config = get_config(comp_id)
    output_dir = get_output_dir(config['competition_id'])

    print(f"Scraping {config['competition_id']} entry lists...", file=sys.stderr)
    html = fetch_html(config['heat_lists_url'])

    if not html:
        print("Failed to fetch HTML", file=sys.stderr)
        return 1

    print(f"Downloaded {len(html):,} bytes", file=sys.stderr)

    print("Parsing participant data...", file=sys.stderr)
    participants_raw = parse_participants(html)
    print(f"Found {len(participants_raw)} participants", file=sys.stderr)

    total_entries = sum(len(entries) for entries in participants_raw.values())
    print(f"Total entries: {total_entries:,}", file=sys.stderr)

    print("Building heat events...", file=sys.stderr)
    heat_events = build_heat_events(participants_raw)
    print(f"Built {len(heat_events)} heat events", file=sys.stderr)

    print("Validating data...", file=sys.stderr)
    errors = validate_data(participants_raw, heat_events)
    if errors:
        print(f"Validation errors found:", file=sys.stderr)
        for error in errors[:10]:
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more", file=sys.stderr)
    else:
        print("Data validation passed", file=sys.stderr)

    print("Formatting participants...", file=sys.stderr)
    participants_formatted = format_participants(participants_raw)

    # Diff against whatever was previously committed, BEFORE overwriting it, and log the
    # result so the website can show a history of what changed on the source site between
    # scrapes. Missing/corrupt prior files just diff as "everything added" (empty old side).
    print("Diffing against previous scrape...", file=sys.stderr)
    old_participants = {}
    old_participants_path = output_dir / 'participants.json'
    if old_participants_path.exists():
        try:
            with open(old_participants_path) as f:
                old_participants = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    old_heat_events = []
    old_heat_events_path = output_dir / 'heat_events.json'
    if old_heat_events_path.exists():
        try:
            with open(old_heat_events_path) as f:
                old_heat_events = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    diff = compute_diff(old_participants, participants_formatted, old_heat_events, heat_events)
    log_path = log_scrape_diff(output_dir, diff)
    if has_changes(diff):
        p, e = diff['participants'], diff['events']
        print(
            f"  Changes: participants {p['oldCount']}->{p['newCount']} "
            f"(+{len(p['added'])}/-{len(p['removed'])}/~{len(p['changed'])}), "
            f"events {e['oldUniqueCount']}->{e['newUniqueCount']} "
            f"(+{len(e['added'])}/-{len(e['removed'])}/~{len(e['rosterChanged'])} roster)",
            file=sys.stderr
        )
    else:
        print("  No changes since last scrape", file=sys.stderr)
    print(f"  Logged to {log_path}", file=sys.stderr)

    if not save_json(participants_formatted, output_dir, 'participants.json'):
        return 1
    if not save_json(heat_events, output_dir, 'heat_events.json'):
        return 1

    print("\nSummary:", file=sys.stderr)
    print(f"  Competition: {config['competition_id']}", file=sys.stderr)
    print(f"  Participants: {len(participants_formatted)}", file=sys.stderr)
    print(f"  Total entries: {total_entries:,}", file=sys.stderr)
    print(f"  Heat events: {len(heat_events)}", file=sys.stderr)
    print(f"  Total heats: {len(set(he['heat'] for he in heat_events))}", file=sys.stderr)
    print(f"  Output directory: {output_dir}", file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())
