#!/usr/bin/env python3
"""
Computes a structured diff between the previously-committed competition data and a
freshly-scraped version, and appends it to a persistent per-competition log
(scrape_log.json) that the website can render (see scrape-log.html).

Pure/importable — no side effects other than the append performed by log_scrape_diff().
Used by scrape_national2026.py before it overwrites participants.json/heat_events.json.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def _entry_key(entry):
    """A participant entry's identity for change-detection: which heat/event/partner/awards,
    not the raw dict — field order or extra keys shouldn't register as a change."""
    return (
        entry.get('heat', ''),
        entry.get('event', ''),
        entry.get('partner') or '',
        entry.get('awards') or '',
    )


def _entries_for_keys(keys):
    return sorted(
        (
            dict(
                heat=k[0],
                event=k[1],
                partner=(k[2] or None),
                awards=(k[3] or None) if len(k) > 3 else None,
            )
            for k in keys
        ),
        key=lambda d: (d['event'], d['partner'] or '', d.get('awards') or '')
    )


def _participant_entries(participants, name):
    """All of a participant's current heats, formatted like addedEntries/removedEntries —
    used for participants who are wholly new or wholly gone, so "added"/"removed" in the
    log shows which heats they were in, not just the name."""
    entries = participants.get(name, {}).get('entries', [])
    return _entries_for_keys({_entry_key(e) for e in entries})


def compute_diff(old_participants, new_participants, old_heat_events, new_heat_events):
    """Both *_participants args are the participants.json shape: {name: {entries: [...]}}.
    Both *_heat_events args are the heat_events.json shape: [{event, competitors, ...}, ...].
    Returns a JSON-serializable dict; every list is complete (not truncated) since this is
    an audit record, not a terminal printout — truncate for display, not for storage."""
    old_participants = old_participants or {}
    new_participants = new_participants or {}
    old_heat_events = old_heat_events or []
    new_heat_events = new_heat_events or []

    old_names = set(old_participants.keys())
    new_names = set(new_participants.keys())

    changed_participants = []
    for name in sorted(old_names & new_names):
        old_entries = old_participants[name].get('entries', [])
        new_entries = new_participants[name].get('entries', [])
        old_keys = {_entry_key(e) for e in old_entries}
        new_keys = {_entry_key(e) for e in new_entries}
        if old_keys != new_keys:
            # Which specific heats were added/removed, not just the count — a participant
            # can gain and drop the same number of entries and that'd otherwise look like
            # no real change. Keyed by (heat, event, partner); heat is blank for this
            # scraper's source format, so event (+ partner if any) is the meaningful part.
            changed_participants.append({
                'name': name,
                'oldEntryCount': len(old_entries),
                'newEntryCount': len(new_entries),
                'addedEntries': _entries_for_keys(new_keys - old_keys),
                'removedEntries': _entries_for_keys(old_keys - new_keys),
            })

    old_event_names = {he.get('event') for he in old_heat_events}
    new_event_names = {he.get('event') for he in new_heat_events}

    old_roster = {he.get('event'): sorted(he.get('competitors', [])) for he in old_heat_events}
    new_roster = {he.get('event'): sorted(he.get('competitors', [])) for he in new_heat_events}

    roster_changed = []
    for name in sorted(old_event_names & new_event_names):
        old_c, new_c = set(old_roster.get(name, [])), set(new_roster.get(name, []))
        if old_c != new_c:
            roster_changed.append({
                'event': name,
                'added': sorted(new_c - old_c),
                'removed': sorted(old_c - new_c),
            })

    # Wholly-new/wholly-gone participants carry their heats too, same shape as
    # addedEntries/removedEntries on a changed participant — so "added" doesn't mean just
    # a name showed up, it shows what they're actually entered in.
    added_names = sorted(new_names - old_names)
    removed_names = sorted(old_names - new_names)

    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'participants': {
            'oldCount': len(old_names),
            'newCount': len(new_names),
            'added': [{'name': n, 'entries': _participant_entries(new_participants, n)} for n in added_names],
            'removed': [{'name': n, 'entries': _participant_entries(old_participants, n)} for n in removed_names],
            'changed': changed_participants,
        },
        'events': {
            'oldCount': len(old_heat_events),
            'newCount': len(new_heat_events),
            'oldUniqueCount': len(old_event_names),
            'newUniqueCount': len(new_event_names),
            'added': sorted(new_event_names - old_event_names),
            'removed': sorted(old_event_names - new_event_names),
            'rosterChanged': roster_changed,
        },
    }


def has_changes(diff):
    """True if a diff record represents any real change (vs. an identical re-scrape)."""
    p, e = diff['participants'], diff['events']
    return bool(p['added'] or p['removed'] or p['changed'] or e['added'] or e['removed'] or e['rosterChanged'])


def log_scrape_diff(output_dir, diff, max_entries=200):
    """Append `diff` to output_dir/scrape_log.json, newest last. Caps the log at
    max_entries (dropping the oldest) so the file doesn't grow without bound across
    years of re-scrapes; 200 is generously beyond what a manually-triggered scraper
    for one competition will ever accumulate in practice."""
    log_path = Path(output_dir) / 'scrape_log.json'
    if log_path.exists():
        with open(log_path) as f:
            try:
                log = json.load(f)
            except json.JSONDecodeError:
                log = []
    else:
        log = []

    log.append(diff)
    if len(log) > max_entries:
        log = log[-max_entries:]

    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2)

    return log_path
