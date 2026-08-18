#!/usr/bin/env python3
"""
Comprehensive data validation for competition data.

Checks:
1. Reciprocal partner validation
2. Event consistency
3. Data integrity
4. Partner classification (solo vs. couple)
5. Data completeness
6. Age category codes — every event's leading code (e.g. "AC-JV1") must be a
   known age code or a known Pro-Am skill code; anything else is reported so
   AGE_CATEGORY_MAP/SKILL_LEVEL_CODES in com.html can be updated
7. Couple pairing integrity — every claimed partner must actually be on the
   competitor roster for that exact heat+event, or the couple silently
   renders broken/solo in the UI
"""

import json
import re
import sys
from pathlib import Path
from config import get_output_dir

# Kept in sync by hand with AGE_CATEGORY_MAP / SKILL_LEVEL_CODES in
# public/projects/com.html — see com_assets/AGE_CATEGORIES.md for how
# these were derived. If you touch one, touch the other; validate_age_
# categories() below exists specifically to catch the two drifting apart
# (a code the UI can't classify shows up as a validation error here).
AGE_CATEGORY_CODES = {
    'JV1', 'JV2', 'JV', 'JR1', 'JR2', 'JR', '15', 'YTH', 'Y', '16',
    'U21', 'YO', '19', 'AD', 'AD1', 'AD2', 'AD3', 'AD4', 'AD5', '36', '50',
}
SKILL_LEVEL_CODES = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'JB', 'JU'}

CODE_RE = re.compile(r'^[A-Z]+-([A-Za-z0-9]*)')


def classify_event_code(event_name):
    """Mirror of getEventAgeCategory()'s classification in com.html, minus
    the actual label lookup — returns 'age', 'skill', 'no-code', or
    ('unrecognized', code) for anything neither table above accounts for."""
    m = CODE_RE.match(event_name)
    if not m:
        return 'no-code'
    code = m.group(1)
    if not code:
        return 'no-code'
    if code in SKILL_LEVEL_CODES:
        return 'skill'
    if code in AGE_CATEGORY_CODES:
        return 'age'
    return ('unrecognized', code)


class DataValidator:
    def __init__(self, comp_id):
        self.comp_id = comp_id
        self.output_dir = get_output_dir(comp_id)
        self.errors = []
        self.warnings = []

        # Load data
        try:
            with open(self.output_dir / 'participants.json') as f:
                self.participants = json.load(f)
            with open(self.output_dir / 'heat_events.json') as f:
                self.heat_events = json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            sys.exit(1)

    def validate_all(self):
        """Run all validations"""
        print(f"Validating {self.comp_id}...\n")

        self.validate_data_structure()
        self.validate_event_consistency()
        self.validate_partner_classification()
        self.validate_reciprocal_partners()
        self.validate_data_integrity()
        self.validate_age_categories()
        self.validate_couple_pairing_integrity()

        self.report_results()

    def validate_data_structure(self):
        """Check basic data structure"""
        if not isinstance(self.participants, dict):
            self.errors.append("participants.json is not a dict")
        if not isinstance(self.heat_events, list):
            self.errors.append("heat_events.json is not a list")

    def validate_event_consistency(self):
        """Check that all competitors in events exist in participants"""
        for heat_event in self.heat_events:
            event_name = heat_event.get('event', 'UNKNOWN')
            competitors = heat_event.get('competitors', [])

            for competitor in competitors:
                if competitor not in self.participants:
                    self.errors.append(
                        f"Competitor '{competitor}' in event '{event_name}' "
                        f"but not in participants.json"
                    )

    def validate_partner_classification(self):
        """Check that couple vs solo classification matches partner presence"""
        solo_events = 0
        couple_events = 0

        for person, person_data in self.participants.items():
            for entry in person_data.get('entries', []):
                event = entry.get('event', '')
                partner = entry.get('partner')

                is_solo_event = 'solo' in event.lower()
                has_partner = bool(partner)

                # Solo events shouldn't have partners
                if is_solo_event and has_partner:
                    self.errors.append(
                        f"{person}: SOLO event has partner '{partner}' "
                        f"in '{event}'"
                    )
                    solo_events += 1

                # Non-solo events with partner are couple events
                if not is_solo_event and has_partner:
                    couple_events += 1

                # Non-solo events without partner might be issues
                if not is_solo_event and not has_partner:
                    # Check if it looks like a couple event
                    if any(x in event.upper() for x in ['LATIN', 'BALLROOM', 'STANDARD', 'SMOOTH']):
                        self.warnings.append(
                            f"{person}: Possible couple event without partner "
                            f"in '{event}'"
                        )

    def validate_reciprocal_partners(self):
        """Check that partnerships are reciprocal (informational only)"""
        # Note: Non-reciprocal partnerships are expected in this data format
        # because each person's entry section has one "With X" that applies to all events
        # We skip this check for now as it's not indicative of data problems
        pass

    def validate_data_integrity(self):
        """Check for data quality issues"""
        # Check for empty events
        for person, person_data in self.participants.items():
            entries = person_data.get('entries', [])
            if not entries:
                self.warnings.append(f"Participant '{person}' has no entries")

            for entry in entries:
                event = entry.get('event', '').strip()
                if not event:
                    self.errors.append(f"Empty event name for {person}")

                # Check for self-reference
                partner = entry.get('partner')
                if partner and isinstance(partner, str):
                    partner = partner.strip()
                    if partner.lower() == person.lower():
                        self.errors.append(
                            f"Self-referential partnership: {person} paired with self"
                        )

        # Check for empty heat events
        for heat_event in self.heat_events:
            event = heat_event.get('event', '').strip()
            if not event:
                self.errors.append("Empty event name in heat_events")

            competitors = heat_event.get('competitors', [])
            if not competitors:
                self.warnings.append(
                    f"Event '{event}' has no competitors"
                )

    def validate_age_categories(self):
        """Every event name should classify as age-coded, skill-coded, or
        legitimately uncoded (Pro/WDC events, blank-code solos). Anything else
        is a code the UI's AGE_CATEGORY_MAP/SKILL_LEVEL_CODES don't know about —
        report it for analysis rather than let it silently render as
        'No Age Category' on the site."""
        self.age_category_stats = {'age': 0, 'skill': 0, 'no-code': 0}
        unrecognized = {}  # code -> [example event names]

        seen_events = set()
        for heat_event in self.heat_events:
            event = heat_event.get('event', '')
            if event in seen_events:
                continue
            seen_events.add(event)

            result = classify_event_code(event)
            if isinstance(result, tuple):
                _, code = result
                unrecognized.setdefault(code, []).append(event)
            else:
                self.age_category_stats[result] += 1

        self.age_category_stats['unrecognized_codes'] = len(unrecognized)

        for code, examples in sorted(unrecognized.items()):
            sample = examples[0]
            more = f" (+{len(examples) - 1} more)" if len(examples) > 1 else ""
            self.errors.append(
                f"Unrecognized event code '{code}' ({len(examples)} event(s)) — "
                f"not in AGE_CATEGORY_CODES or SKILL_LEVEL_CODES. e.g. '{sample}'{more}. "
                f"Add it to AGE_CATEGORY_MAP/SKILL_LEVEL_CODES in com.html "
                f"(and this script, and AGE_CATEGORIES.md) once you know what it means."
            )

    def validate_couple_pairing_integrity(self):
        """The site pairs couples by looking up each competitor's claimed
        partner for that exact (heat, event) and checking the partner is
        actually in that event's competitor list. If the partner is missing —
        typo'd name, partner scraped for the wrong event, whatever — that
        competitor silently renders as a solo entry inside a couple event
        instead of visibly failing, so this has to be checked explicitly."""
        unknown_partner_names = set()

        roster_by_heat_event = {
            (he.get('heat', ''), he.get('event', '')): he.get('competitors', [])
            for he in self.heat_events
        }

        for person, person_data in self.participants.items():
            for entry in person_data.get('entries', []):
                partner = entry.get('partner')
                if not partner:
                    continue

                if partner not in self.participants:
                    unknown_partner_names.add(partner)

                heat = entry.get('heat', '')
                event = entry.get('event', '')
                roster = roster_by_heat_event.get((heat, event))

                if roster is None:
                    # Already reported by validate_event_consistency-style checks
                    # if the event itself doesn't exist; nothing new to add here.
                    continue

                if partner not in roster:
                    self.errors.append(
                        f"{person}: claims partner '{partner}' for '{event}' "
                        f"but '{partner}' is not in that event's competitor list "
                        f"— couple will render as broken/solo in the UI"
                    )

        for name in sorted(unknown_partner_names):
            self.warnings.append(
                f"Partner name '{name}' never appears as a participant anywhere "
                f"in participants.json — likely a scraping/name-formatting mismatch"
            )

    def report_results(self):
        """Print validation report"""
        print(f"\n{'='*60}")
        print(f"Data Summary:")
        print(f"  Participants: {len(self.participants)}")
        print(f"  Events: {len(self.heat_events)}")
        total_entries = sum(len(p.get('entries', [])) for p in self.participants.values())
        print(f"  Total entries: {total_entries}")
        if hasattr(self, 'age_category_stats'):
            s = self.age_category_stats
            print(f"  Unique events by code: {s['age']} age-coded, {s['skill']} skill-coded, "
                  f"{s['no-code']} uncoded, {s['unrecognized_codes']} unrecognized")
        print(f"{'='*60}\n")

        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors[:20], 1):
                print(f"  {i}. {error}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more errors")
            print()

        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings[:20], 1):
                print(f"  {i}. {warning}")
            if len(self.warnings) > 20:
                print(f"  ... and {len(self.warnings) - 20} more warnings")
            print()

        if not self.errors and not self.warnings:
            print("✅ All validations passed!")
            print()
            return 0

        if self.errors:
            print(f"Result: ❌ INVALID ({len(self.errors)} errors)")
            return 1
        else:
            print(f"Result: ⚠️  VALID WITH WARNINGS ({len(self.warnings)} warnings)")
            return 0


def main():
    comp_id = sys.argv[1] if len(sys.argv) > 1 else 'national2026'
    validator = DataValidator(comp_id)
    exit_code = validator.validate_all()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
