#!/usr/bin/env python3
"""
Imperial Cup 2026 Data Scraper
Fetches participant and heat event data from the source website and generates JSON files.

Usage:
    python3 scrape_data.py

This script:
1. Fetches data from https://www.comp-mngr.com/impercup2026/ImperCup2026_HeatLists.htm
2. Parses participant entries and their heats
3. Generates participants.json and heat_events.json
4. Validates data integrity
"""

import json
import sys
import os
import urllib.request
import re
from html.parser import HTMLParser
from collections import defaultdict

class DanceDataParser(HTMLParser):
    """Parses Imperial Cup 2026 participant data from HTML"""

    def __init__(self):
        super().__init__()
        self.participants = {}
        self.current_person = None
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
        if tag == 'strong' and 'Entries for' in self.current_cell:
            self.current_person = self.current_cell.replace('Entries for', '').strip()
            if self.current_person not in self.participants:
                self.participants[self.current_person] = []
        elif tag == 'td' and self.in_table:
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

                    if '@' in session_time:
                        session, time = session_time.split('@', 1)
                    else:
                        session = session_time
                        time = ''

                    entry = {
                        'heat': heat,
                        'event': event,
                        'time': time.strip(),
                        'session': session.strip()
                    }
                    self.participants[self.current_person].append(entry)
            self.table_rows = []

    def handle_data(self, data):
        self.current_cell += data


def fetch_html():
    """Fetch HTML from Imperial Cup website with timeout"""
    url = "https://www.comp-mngr.com/impercup2026/ImperCup2026_HeatLists.htm"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode('utf-8')
            return html
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        sys.exit(1)


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
                    'competitors': []
                }

            if person not in heat_events_dict[key]['competitors']:
                heat_events_dict[key]['competitors'].append(person)

    # Sort for consistent output
    heat_events = sorted(
        heat_events_dict.values(),
        key=lambda x: (
            # Extract heat number for proper sorting
            int(re.match(r'\d+', x['heat'].replace('Heat ', '')).group()) if re.match(r'\d+', x['heat'].replace('Heat ', '')) else 0,
            x['event']
        )
    )

    return heat_events


def is_couple_event(event_name):
    """Determine if event is a couple/partner event based on event code"""
    # Events starting with L- or G- are typically couple/partner events
    # A- events are solo individual events
    event_code = event_name.split()[0] if event_name else ''
    return event_code.startswith(('L-', 'G-'))


def find_partners(participants, heat_events):
    """Find partners for couple events by analyzing heat_events"""
    # For each participant and couple event, find who else is in that heat
    partners = {}  # (person, heat, event) -> partner_name

    for heat_event in heat_events:
        if is_couple_event(heat_event['event']):
            competitors = heat_event['competitors']
            # For couple events, people appear as pairs
            # Simple heuristic: if 2 people appear together in a couple event, they're partners
            if len(competitors) >= 2:
                # Just mark as needing a partner for now
                # The actual partner will be discovered when we see them in another event
                for competitor in competitors:
                    key = (competitor, heat_event['heat'], heat_event['event'])
                    partners[key] = None  # Will be filled in later

    return partners


def format_participants(participants, heat_events):
    """Format participants for output with partner detection"""
    # First pass: identify couple events and their participants
    couple_event_participants = {}  # (heat, event) -> set of participants

    for heat_event in heat_events:
        if is_couple_event(heat_event['event']):
            couple_event_participants[(heat_event['heat'], heat_event['event'])] = set(heat_event['competitors'])

    # Second pass: assign partners
    formatted = {}
    for person, entries in participants.items():
        formatted_entries = []
        for entry in entries:
            partner = None

            # If this is a couple event, try to find the partner
            if is_couple_event(entry['event']):
                heat_event_key = (entry['heat'], entry['event'])
                if heat_event_key in couple_event_participants:
                    competitors = couple_event_participants[heat_event_key]
                    # In couple events, typically 2 people per couple
                    # Find other people in this heat who also appear in couple events with this person
                    other_competitors = [c for c in competitors if c != person]
                    if other_competitors:
                        # Simple heuristic: pick the first other competitor as partner
                        # This works for standard couple events
                        partner = other_competitors[0]

            formatted_entry = {
                'heat': entry['heat'],
                'event': entry['event'],
                'time': entry['time'],
                'session': entry['session'],
                'partner': partner
            }
            formatted_entries.append(formatted_entry)

        formatted[person] = {
            'entries': formatted_entries
        }

    return formatted


def save_json(data, filename):
    """Save data to JSON file in the script's directory"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved {filepath}")
    except Exception as e:
        print(f"Error saving {filename}: {e}", file=sys.stderr)
        sys.exit(1)


def validate_data(participants, heat_events):
    """Validate data consistency"""
    errors = []

    # Check all competitors in heat_events exist in participants
    for heat_event in heat_events:
        for competitor in heat_event['competitors']:
            if competitor not in participants:
                errors.append(f"Competitor '{competitor}' in heat event but not in participants")

    # Check all heats in participants exist in heat_events
    heat_event_keys = set((he['heat'], he['event']) for he in heat_events)
    for person, entries in participants.items():
        for entry in entries:
            key = (entry['heat'], entry['event'])
            if key not in heat_event_keys:
                errors.append(f"Heat {entry['heat']} for {person} not in heat_events")

    return errors


def main():
    """Main scraping process"""
    print("Fetching Imperial Cup 2026 data...", file=sys.stderr)
    html = fetch_html()
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
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more", file=sys.stderr)
    else:
        print("Data validation passed", file=sys.stderr)

    print("Formatting participants...", file=sys.stderr)
    participants_formatted = format_participants(participants_raw, heat_events)

    # Save files
    save_json(participants_formatted, 'participants.json')
    save_json(heat_events, 'heat_events.json')

    print("\nSummary:", file=sys.stderr)
    print(f"  Participants: {len(participants_formatted)}", file=sys.stderr)
    print(f"  Total entries: {total_entries:,}", file=sys.stderr)
    print(f"  Heat events: {len(heat_events)}", file=sys.stderr)
    print(f"  Total heats: {len(set(he['heat'] for he in heat_events))}", file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())
