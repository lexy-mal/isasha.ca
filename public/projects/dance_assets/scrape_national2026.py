#!/usr/bin/env python3
"""
National 2026 Entry Scraper
Extracts participant data from the entry lists page (JavaScript-hidden divs).
"""

import json
import sys
import urllib.request
import re
from pathlib import Path
from config import get_config, get_output_dir

def fetch_html(url):
    """Fetch HTML from URL"""
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
            try:
                html = data.decode('utf-8')
            except UnicodeDecodeError:
                html = data.decode('iso-8859-1')
            return html
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def extract_table_divs(html):
    """Extract all TABLE_CODE divs from HTML"""
    pattern = r'<div id="(TABLE_CODE_\d+)"[^>]*>(.+?)</div>'
    matches = re.findall(pattern, html, re.DOTALL)
    return matches


def parse_entry_div(table_id, content):
    """Parse a single entry div to extract person and events"""
    # Extract person name from "Entries for X"
    person_match = re.search(r'<strong>Entries for\s+(.+?)</strong>', content)
    if not person_match:
        return None

    person = person_match.group(1).strip()

    # Extract partner from "With Y"
    partner_match = re.search(r'<strong>With\s+(.+?)</strong>', content)
    partner = partner_match.group(1).strip() if partner_match else None

    # Extract events from table rows
    event_pattern = r'<tr><td>(.+?)</td></tr>'
    events = re.findall(event_pattern, content)

    # Remove "Event" header (appears as first row in each person's section)
    events = [e for e in events if e.strip() != 'Event']

    if not events:
        return None

    return {
        'person': person,
        'partner': partner,  # Partner info - will be filtered per event
        'events': events
    }


def build_participants(entries):
    """Build participants.json from extracted entries"""
    participants = {}

    for entry in entries:
        if not entry:
            continue

        person = entry['person']
        partner = entry['partner']

        if person not in participants:
            participants[person] = {'entries': []}

        # Add entry for each event
        for event in entry['events']:
            # Determine if solo or couple event
            is_solo = 'solo' in event.lower()
            # Include partner info only if it's NOT a solo event
            event_partner = partner if not is_solo else None

            participants[person]['entries'].append({
                'heat': '',  # Not available in National 2026 format
                'event': event,
                'time': '',  # Not available
                'session': '',  # Not available
                'partner': event_partner
            })

    return participants


def build_heat_events(entries):
    """Build heat_events.json from extracted entries"""
    heat_events = {}

    for entry in entries:
        if not entry:
            continue

        person = entry['person']
        partner = entry['partner']

        for event in entry['events']:
            # Use event as key since we don't have heat numbers
            key = event

            if key not in heat_events:
                heat_events[key] = {
                    'heat': '',  # Not available
                    'event': event,
                    'session': '',  # Not available
                    'time': '',  # Not available
                    'competitors': []
                }

            if person not in heat_events[key]['competitors']:
                heat_events[key]['competitors'].append(person)

    # Convert to list and sort by event name
    heat_events_list = sorted(heat_events.values(), key=lambda x: x['event'])

    return heat_events_list


def save_json(data, output_dir, filename):
    """Save data to JSON file"""
    try:
        filepath = output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved {filepath}")
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}", file=sys.stderr)
        return False


def main():
    config = get_config('national2026')
    output_dir = get_output_dir('national2026')

    print("Fetching National 2026 entry lists...", file=sys.stderr)
    html = fetch_html(config['heat_lists_url'])

    if not html:
        print("Failed to fetch HTML", file=sys.stderr)
        return 1

    print(f"Downloaded {len(html):,} bytes", file=sys.stderr)

    print("Extracting entry divs...", file=sys.stderr)
    table_divs = extract_table_divs(html)
    print(f"Found {len(table_divs)} entry divs", file=sys.stderr)

    print("Parsing entries...", file=sys.stderr)
    entries = [parse_entry_div(table_id, content) for table_id, content in table_divs]
    entries = [e for e in entries if e]  # Filter out None values
    print(f"Parsed {len(entries)} valid entries", file=sys.stderr)

    print("Building participants...", file=sys.stderr)
    participants = build_participants(entries)
    print(f"Built {len(participants)} participants", file=sys.stderr)

    total_entries = sum(len(p['entries']) for p in participants.values())
    print(f"Total event entries: {total_entries:,}", file=sys.stderr)

    print("Building heat events...", file=sys.stderr)
    heat_events = build_heat_events(entries)
    print(f"Built {len(heat_events)} events", file=sys.stderr)

    # Save files
    if not save_json(participants, output_dir, 'participants.json'):
        return 1
    if not save_json(heat_events, output_dir, 'heat_events.json'):
        return 1

    print("\nSummary:", file=sys.stderr)
    print(f"  Participants: {len(participants)}", file=sys.stderr)
    print(f"  Events: {len(heat_events)}", file=sys.stderr)
    print(f"  Total entries: {total_entries:,}", file=sys.stderr)
    print(f"  Output directory: {output_dir}", file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())
