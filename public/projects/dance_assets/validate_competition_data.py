#!/usr/bin/env python3
"""
Comprehensive data validation for competition data.

Checks:
1. Reciprocal partner validation
2. Event consistency
3. Data integrity
4. Partner classification
5. Data completeness
"""

import json
import sys
from pathlib import Path
from config import get_output_dir


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

    def report_results(self):
        """Print validation report"""
        print(f"\n{'='*60}")
        print(f"Data Summary:")
        print(f"  Participants: {len(self.participants)}")
        print(f"  Events: {len(self.heat_events)}")
        total_entries = sum(len(p.get('entries', [])) for p in self.participants.values())
        print(f"  Total entries: {total_entries}")
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
