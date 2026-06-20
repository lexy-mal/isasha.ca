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
                self.current_partner = None  # Reset partner for new person
                if self.current_person not in self.participants:
                    self.participants[self.current_person] = []
            elif text.startswith('With'):
                # Extract partner name (or None if empty)
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
                        'partner': self.current_partner  # Use the extracted partner
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


def format_participants(participants, heat_events=None):
    """Format participants for output (partner info extracted from HTML)"""
    formatted = {}
    for person, entries in participants.items():
        formatted_entries = []
        for entry in entries:
            formatted_entry = {
                'heat': entry['heat'],
                'event': entry['event'],
                'time': entry['time'],
                'session': entry['session'],
                'partner': entry.get('partner')  # Use partner extracted from HTML
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
    participants_formatted = format_participants(participants_raw)

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
