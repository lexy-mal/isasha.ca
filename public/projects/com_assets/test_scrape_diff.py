"""Tests for scrape_diff.py — the participant/event diff used to log what changed
between scrapes, rendered on the (password-gated) scrape-log.html page."""

import json
import pytest

from scrape_diff import compute_diff, has_changes, log_scrape_diff


def participant(entries):
    return {'entries': entries}


def entry(heat='', event='', partner=None):
    e = {'heat': heat, 'event': event}
    if partner:
        e['partner'] = partner
    return e


def heat_event(event, competitors):
    return {'event': event, 'competitors': competitors}


class TestComputeDiffParticipants:
    def test_no_change_is_no_change(self):
        old = {'A, Alice': participant([entry(event='E1')])}
        new = {'A, Alice': participant([entry(event='E1')])}
        diff = compute_diff(old, new, [], [])
        assert diff['participants']['added'] == []
        assert diff['participants']['removed'] == []
        assert diff['participants']['changed'] == []
        assert not has_changes(diff)

    def test_added_and_removed_participants(self):
        old = {'A, Alice': participant([]), 'B, Bob': participant([entry(event='E1')])}
        new = {'A, Alice': participant([]), 'C, Carl': participant([entry(event='E2')])}
        diff = compute_diff(old, new, [], [])
        assert diff['participants']['added'] == [
            {'name': 'C, Carl', 'entries': [{'heat': '', 'event': 'E2', 'partner': None}]}
        ]
        assert diff['participants']['removed'] == [
            {'name': 'B, Bob', 'entries': [{'heat': '', 'event': 'E1', 'partner': None}]}
        ]
        assert has_changes(diff)

    def test_added_and_removed_participants_list_all_their_heats(self):
        # A wholly new/gone participant's "entries" should be every heat they're in, not
        # just their name — sorted by event, and including partner where present.
        old = {'B, Bob': participant([
            entry(event='E1', partner='D, Dan'),
            entry(event='E2'),
        ])}
        new = {'C, Carl': participant([
            entry(event='E3'),
            entry(event='E4', partner='D, Dan'),
        ])}
        diff = compute_diff(old, new, [], [])

        added = diff['participants']['added']
        assert len(added) == 1
        assert added[0]['name'] == 'C, Carl'
        assert added[0]['entries'] == [
            {'heat': '', 'event': 'E3', 'partner': None},
            {'heat': '', 'event': 'E4', 'partner': 'D, Dan'},
        ]

        removed = diff['participants']['removed']
        assert len(removed) == 1
        assert removed[0]['name'] == 'B, Bob'
        assert removed[0]['entries'] == [
            {'heat': '', 'event': 'E1', 'partner': 'D, Dan'},
            {'heat': '', 'event': 'E2', 'partner': None},
        ]

    def test_changed_entry_list_detected_even_with_same_count(self):
        old = {'A, Alice': participant([entry(event='E1')])}
        new = {'A, Alice': participant([entry(event='E2')])}  # same count, different event
        diff = compute_diff(old, new, [], [])
        changed = diff['participants']['changed']
        assert len(changed) == 1
        c = changed[0]
        assert c['name'] == 'A, Alice'
        assert c['oldEntryCount'] == 1
        assert c['newEntryCount'] == 1
        assert c['addedEntries'] == [{'heat': '', 'event': 'E2', 'partner': None}]
        assert c['removedEntries'] == [{'heat': '', 'event': 'E1', 'partner': None}]

    def test_added_and_removed_entries_for_a_gain_and_a_drop(self):
        # "removed from heat 1, added to heats 2, 3, 4" — a participant can both drop and
        # pick up entries in the same scrape; both lists must be populated independently.
        old = {'A, Alice': participant([
            entry(heat='1', event='E1'),
            entry(heat='2', event='E2'),
        ])}
        new = {'A, Alice': participant([
            entry(heat='2', event='E2'),  # unchanged, must NOT appear in either list
            entry(heat='3', event='E3'),
            entry(heat='4', event='E4'),
        ])}
        diff = compute_diff(old, new, [], [])
        c = diff['participants']['changed'][0]
        assert c['removedEntries'] == [{'heat': '1', 'event': 'E1', 'partner': None}]
        added_events = sorted(e['event'] for e in c['addedEntries'])
        assert added_events == ['E3', 'E4']

    def test_partner_change_reflected_in_added_removed_entries(self):
        old = {'A, Alice': participant([entry(event='E1', partner='B, Bob')])}
        new = {'A, Alice': participant([entry(event='E1', partner='C, Carl')])}
        diff = compute_diff(old, new, [], [])
        c = diff['participants']['changed'][0]
        assert c['removedEntries'] == [{'heat': '', 'event': 'E1', 'partner': 'B, Bob'}]
        assert c['addedEntries'] == [{'heat': '', 'event': 'E1', 'partner': 'C, Carl'}]

    def test_added_removed_entries_empty_lists_when_unchanged(self):
        old = {'A, Alice': participant([entry(event='E1')])}
        new = {'A, Alice': participant([entry(event='E1')])}
        diff = compute_diff(old, new, [], [])
        assert diff['participants']['changed'] == []

    def test_reordered_entries_are_not_a_change(self):
        old = {'A, Alice': participant([entry(event='E1'), entry(event='E2')])}
        new = {'A, Alice': participant([entry(event='E2'), entry(event='E1')])}
        diff = compute_diff(old, new, [], [])
        assert diff['participants']['changed'] == []

    def test_partner_change_counts_as_changed(self):
        old = {'A, Alice': participant([entry(event='E1', partner='B, Bob')])}
        new = {'A, Alice': participant([entry(event='E1', partner='C, Carl')])}
        diff = compute_diff(old, new, [], [])
        assert len(diff['participants']['changed']) == 1

    def test_counts_reflect_totals(self):
        old = {'A, Alice': participant([])}
        new = {'A, Alice': participant([]), 'B, Bob': participant([])}
        diff = compute_diff(old, new, [], [])
        assert diff['participants']['oldCount'] == 1
        assert diff['participants']['newCount'] == 2


class TestComputeDiffEvents:
    def test_added_and_removed_events(self):
        old = [heat_event('E1', ['A, Alice'])]
        new = [heat_event('E2', ['A, Alice'])]
        diff = compute_diff({}, {}, old, new)
        assert diff['events']['added'] == ['E2']
        assert diff['events']['removed'] == ['E1']

    def test_roster_added_and_removed_for_same_event(self):
        old = [heat_event('E1', ['A, Alice', 'B, Bob'])]
        new = [heat_event('E1', ['A, Alice', 'C, Carl'])]
        diff = compute_diff({}, {}, old, new)
        rc = diff['events']['rosterChanged']
        assert len(rc) == 1
        assert rc[0]['event'] == 'E1'
        assert rc[0]['added'] == ['C, Carl']
        assert rc[0]['removed'] == ['B, Bob']

    def test_unchanged_roster_not_reported(self):
        old = [heat_event('E1', ['A, Alice', 'B, Bob'])]
        new = [heat_event('E1', ['B, Bob', 'A, Alice'])]  # different order, same set
        diff = compute_diff({}, {}, old, new)
        assert diff['events']['rosterChanged'] == []

    def test_event_count_vs_unique_count(self):
        # heat_events.json can (in principle) have the same event name appear more than
        # once across different heats; oldCount/newCount is raw list length, the
        # *UniqueCount fields are what added/removed/rosterChanged are computed over.
        old = [heat_event('E1', ['A, Alice']), heat_event('E1', ['B, Bob'])]
        new = [heat_event('E1', ['A, Alice'])]
        diff = compute_diff({}, {}, old, new)
        assert diff['events']['oldCount'] == 2
        assert diff['events']['newCount'] == 1
        assert diff['events']['oldUniqueCount'] == 1
        assert diff['events']['newUniqueCount'] == 1


class TestComputeDiffEdgeCases:
    def test_none_inputs_treated_as_empty(self):
        diff = compute_diff(None, {'A, Alice': participant([])}, None, [heat_event('E1', [])])
        assert diff['participants']['added'] == [{'name': 'A, Alice', 'entries': []}]
        assert diff['events']['added'] == ['E1']

    def test_first_ever_scrape_everything_is_added(self):
        new_p = {'A, Alice': participant([entry(event='E1')])}
        new_h = [heat_event('E1', ['A, Alice'])]
        diff = compute_diff({}, new_p, [], new_h)
        assert diff['participants']['added'] == [
            {'name': 'A, Alice', 'entries': [{'heat': '', 'event': 'E1', 'partner': None}]}
        ]
        assert diff['events']['added'] == ['E1']
        assert has_changes(diff)

    def test_timestamp_is_present_and_iso_format(self):
        diff = compute_diff({}, {}, [], [])
        # Just check it round-trips through fromisoformat without raising
        from datetime import datetime
        datetime.fromisoformat(diff['timestamp'])


class TestLogScrapeDiff:
    def test_creates_new_log_file(self, tmp_path):
        diff = compute_diff({}, {'A, Alice': participant([])}, [], [])
        log_path = log_scrape_diff(tmp_path, diff)
        assert log_path.exists()
        with open(log_path) as f:
            log = json.load(f)
        assert len(log) == 1
        assert log[0]['participants']['added'] == [{'name': 'A, Alice', 'entries': []}]

    def test_appends_to_existing_log(self, tmp_path):
        diff1 = compute_diff({}, {'A, Alice': participant([])}, [], [])
        log_scrape_diff(tmp_path, diff1)
        diff2 = compute_diff({}, {'B, Bob': participant([])}, [], [])
        log_path = log_scrape_diff(tmp_path, diff2)
        with open(log_path) as f:
            log = json.load(f)
        assert len(log) == 2
        assert log[-1]['participants']['added'] == [{'name': 'B, Bob', 'entries': []}]

    def test_caps_log_length_dropping_oldest(self, tmp_path):
        for i in range(5):
            diff = compute_diff({}, {f'P{i}, Name': participant([])}, [], [])
            log_scrape_diff(tmp_path, diff, max_entries=3)
        with open(tmp_path / 'scrape_log.json') as f:
            log = json.load(f)
        assert len(log) == 3
        # newest-last, oldest three dropped
        assert log[-1]['participants']['added'] == [{'name': 'P4, Name', 'entries': []}]
        assert log[0]['participants']['added'] == [{'name': 'P2, Name', 'entries': []}]

    def test_corrupt_existing_log_is_replaced_not_fatal(self, tmp_path):
        (tmp_path / 'scrape_log.json').write_text('not valid json{{{')
        diff = compute_diff({}, {'A, Alice': participant([])}, [], [])
        log_path = log_scrape_diff(tmp_path, diff)
        with open(log_path) as f:
            log = json.load(f)
        assert len(log) == 1


class TestHasChanges:
    def test_true_when_participant_added(self):
        diff = compute_diff({}, {'A, Alice': participant([])}, [], [])
        assert has_changes(diff)

    def test_false_when_nothing_changed(self):
        p = {'A, Alice': participant([entry(event='E1')])}
        h = [heat_event('E1', ['A, Alice'])]
        diff = compute_diff(p, p, h, h)
        assert not has_changes(diff)
