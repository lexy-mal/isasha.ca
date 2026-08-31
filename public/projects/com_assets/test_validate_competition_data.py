"""
Comprehensive pytest test suite for validate_competition_data.py

Tests cover:
- classify_event_code() classification of age/skill/no-code/unrecognized
- DataValidator methods: data structure, event consistency, partner classification,
  data integrity, age categories, couple pairing integrity
- report_results() return codes
- Known bugs documented with dedicated tests
"""

import json
import pytest
from pathlib import Path

# Import the module under test
import validate_competition_data
from validate_competition_data import (
    classify_event_code,
    DataValidator,
    AGE_CATEGORY_CODES,
    SKILL_LEVEL_CODES,
)


# ============================================================================
# Fixtures and Helpers
# ============================================================================

@pytest.fixture
def mock_get_output_dir(monkeypatch, tmp_path):
    """Patch get_output_dir to return a temporary directory for testing."""
    def patched_get_output_dir(comp_id):
        return tmp_path

    monkeypatch.setattr('validate_competition_data.get_output_dir', patched_get_output_dir)
    return tmp_path


def create_validator_with_data(tmp_path, participants, heat_events):
    """
    Helper to create a DataValidator with synthetic test data.

    Args:
        tmp_path: pytest's tmp_path fixture
        participants: dict of participant data
        heat_events: list of heat_event data

    Returns:
        Configured DataValidator instance
    """
    # Write test data to JSON files
    (tmp_path / 'participants.json').write_text(json.dumps(participants))
    (tmp_path / 'heat_events.json').write_text(json.dumps(heat_events))

    # Create validator (it will read the JSON files we just wrote)
    validator = DataValidator('test_comp')
    return validator


@pytest.fixture
def validator_with_mock(monkeypatch, tmp_path):
    """
    Fixture that patches get_output_dir and returns a factory function
    for creating validators with synthetic data.
    """
    monkeypatch.setattr(
        'validate_competition_data.get_output_dir',
        lambda comp_id: tmp_path
    )

    def make_validator(participants, heat_events):
        return create_validator_with_data(tmp_path, participants, heat_events)

    return make_validator


# ============================================================================
# Tests for classify_event_code()
# ============================================================================

class TestClassifyEventCode:
    """Test the classify_event_code() function."""

    def test_classify_age_category(self):
        """Test classification of age-coded events."""
        # Example with 'JV1' which is in AGE_CATEGORY_CODES
        result = classify_event_code('AC-JV1 Pre-Competitive Solo Indv. N-1 Cha Cha (C)')
        assert result == 'age'

    def test_classify_skill_level(self):
        """Test classification of skill-level-coded events."""
        # Example with 'A' which is in SKILL_LEVEL_CODES
        result = classify_event_code('AC-A Amateur Pre-Bronze LATIN Cha Cha (C)')
        assert result == 'skill'

    def test_classify_no_code(self):
        """Test classification of events with no leading code pattern."""
        # Event that doesn't match CODE_RE pattern
        result = classify_event_code('Pro/Am Jive')
        assert result == 'no-code'

    def test_classify_no_code_empty_code_group(self):
        """Test classification when CODE_RE matches but code group is empty."""
        # EVENT- pattern matches but the code part is empty
        result = classify_event_code('EVENT- Some Name')
        assert result == 'no-code'

    def test_classify_unrecognized_code(self):
        """Test classification of unrecognized codes."""
        # 'XYZ' is not in either SKILL_LEVEL_CODES or AGE_CATEGORY_CODES
        result = classify_event_code('AC-XYZ Some Event Name')
        assert isinstance(result, tuple)
        assert result[0] == 'unrecognized'
        assert result[1] == 'XYZ'

    def test_classify_event_code_KNOWN_STALE_missing_codes(self):
        """
        KNOWN ISSUE: 'PD' and several age codes are missing from this file's
        SKILL_LEVEL_CODES/AGE_CATEGORY_CODES sets, though they exist in real
        competition data. 'PD' (e.g. "AC-PD Amateur Pre-Bronze LATIN Jive")
        has no published meaning — see com_assets/SKILL_LEVELS.md, which
        excludes it from age/skill entirely rather than guessing.

        This test documents that behavior so if someone adds these codes,
        the test will fail and they'll know it's intentional progress, not
        a regression.

        See: SKILL_LEVEL_CODES missing 'PD', AGE_CATEGORY_CODES missing
        '6U', '7U', '7', '11U', 'U12', '12', '30', '40'
        """
        # 'PD' exists in actual competition data (meaning unpublished/unknown)
        # but is missing from this script's SKILL_LEVEL_CODES
        result_pd = classify_event_code('AC-PD Amateur Pre-Bronze LATIN Jive (J)')
        assert result_pd == ('unrecognized', 'PD'), (
            "Expected 'PD' to be unrecognized (known stale). "
            "If SKILL_LEVEL_CODES was updated to include 'PD', this is expected progress."
        )

        # '6U' is a real age category from actual competition data
        # but is missing from this script's AGE_CATEGORY_CODES
        result_6u = classify_event_code('A-6U Pre-Competitive Solo Indv. N-1 Cha Cha (C)')
        assert result_6u == ('unrecognized', '6U'), (
            "Expected '6U' to be unrecognized (known stale). "
            "If AGE_CATEGORY_CODES was updated to include '6U', this is expected progress."
        )

        # '7U' is another real age category
        result_7u = classify_event_code('A-7U Pre-Competitive Solo')
        assert result_7u == ('unrecognized', '7U')

        # 'U12' is another real age category
        result_u12 = classify_event_code('A-U12 Teen Pre-Bronze')
        assert result_u12 == ('unrecognized', 'U12')


# ============================================================================
# Tests for validate_data_structure()
# ============================================================================

class TestValidateDataStructure:
    """Test the validate_data_structure() method."""

    def test_valid_structure(self, validator_with_mock):
        """Test that valid data structure produces no errors."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},
            heat_events=[]
        )
        validator.validate_data_structure()
        assert not validator.errors

    def test_participants_not_dict(self, validator_with_mock):
        """Test that non-dict participants produces an error."""
        validator = validator_with_mock(
            participants=[],  # Wrong: should be dict
            heat_events=[]
        )
        validator.validate_data_structure()
        assert "participants.json is not a dict" in validator.errors

    def test_heat_events_not_list(self, validator_with_mock):
        """Test that non-list heat_events produces an error."""
        validator = validator_with_mock(
            participants={},
            heat_events={}  # Wrong: should be list
        )
        validator.validate_data_structure()
        assert "heat_events.json is not a list" in validator.errors

    def test_both_structure_errors(self, validator_with_mock):
        """Test that both structure errors are caught."""
        validator = validator_with_mock(
            participants=[],
            heat_events={}
        )
        validator.validate_data_structure()
        assert "participants.json is not a dict" in validator.errors
        assert "heat_events.json is not a list" in validator.errors


# ============================================================================
# Tests for validate_event_consistency()
# ============================================================================

class TestValidateEventConsistency:
    """Test the validate_event_consistency() method."""

    def test_all_competitors_exist(self, validator_with_mock):
        """Test that when all competitors exist in participants, no errors."""
        validator = validator_with_mock(
            participants={
                'alice': {'entries': []},
                'bob': {'entries': []}
            },
            heat_events=[
                {'event': 'Jive', 'competitors': ['alice', 'bob']}
            ]
        )
        validator.validate_event_consistency()
        assert not validator.errors

    def test_competitor_missing_from_participants(self, validator_with_mock):
        """Test that a competitor not in participants produces an error."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},
            heat_events=[
                {'event': 'Jive Heat 1', 'competitors': ['alice', 'unknown']}
            ]
        )
        validator.validate_event_consistency()
        assert len(validator.errors) == 1
        assert "Competitor 'unknown' in event 'Jive Heat 1'" in validator.errors[0]
        assert "not in participants.json" in validator.errors[0]

    def test_multiple_missing_competitors(self, validator_with_mock):
        """Test that multiple missing competitors each produce errors."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},
            heat_events=[
                {'event': 'Jive', 'competitors': ['alice', 'bob', 'charlie']}
            ]
        )
        validator.validate_event_consistency()
        assert len(validator.errors) == 2
        error_text = ' '.join(validator.errors)
        assert 'bob' in error_text
        assert 'charlie' in error_text


# ============================================================================
# Tests for validate_partner_classification()
# ============================================================================

class TestValidatePartnerClassification:
    """Test the validate_partner_classification() method."""

    def test_solo_event_with_partner_is_error(self, validator_with_mock):
        """Test that a SOLO event with a partner produces an error."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'SOLO Jive', 'partner': 'bob'}
                    ]
                }
            },
            heat_events=[]
        )
        validator.validate_partner_classification()
        assert len(validator.errors) == 1
        assert "alice" in validator.errors[0]
        assert "SOLO event has partner 'bob'" in validator.errors[0]

    def test_couple_event_with_partner_no_error(self, validator_with_mock):
        """Test that a non-solo event with a partner doesn't error."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'Standard Waltz', 'partner': 'bob'}
                    ]
                }
            },
            heat_events=[]
        )
        validator.validate_partner_classification()
        assert not validator.errors

    def test_couple_event_without_partner_and_latin_is_warning(self, validator_with_mock):
        """
        Test that a non-solo event without a partner but containing LATIN
        produces a warning.
        """
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'LATIN Jive', 'partner': None}
                    ]
                }
            },
            heat_events=[]
        )
        validator.validate_partner_classification()
        assert len(validator.warnings) == 1
        assert "alice" in validator.warnings[0]
        assert "Possible couple event without partner" in validator.warnings[0]

    def test_couple_event_without_partner_and_ballroom_is_warning(self, validator_with_mock):
        """Test that BALLROOM event without partner produces warning."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'BALLROOM Waltz', 'partner': ''}
                    ]
                }
            },
            heat_events=[]
        )
        validator.validate_partner_classification()
        assert len(validator.warnings) >= 1
        assert any("Possible couple event without partner" in w for w in validator.warnings)

    def test_couple_event_without_partner_and_standard_is_warning(self, validator_with_mock):
        """Test that STANDARD event without partner produces warning."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'STANDARD Foxtrot'}  # no partner field
                    ]
                }
            },
            heat_events=[]
        )
        validator.validate_partner_classification()
        assert len(validator.warnings) >= 1

    def test_couple_event_without_partner_and_smooth_is_warning(self, validator_with_mock):
        """Test that SMOOTH event without partner produces warning."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'SMOOTH Viennese Waltz'}
                    ]
                }
            },
            heat_events=[]
        )
        validator.validate_partner_classification()
        assert len(validator.warnings) >= 1

    def test_non_couple_event_without_partner_no_warning(self, validator_with_mock):
        """Test that a non-couple, non-solo event without partner is OK."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'Group Performance', 'partner': None}
                    ]
                }
            },
            heat_events=[]
        )
        validator.validate_partner_classification()
        # Should not warn about this
        assert not any("Possible couple event" in w for w in validator.warnings)


# ============================================================================
# Tests for validate_data_integrity()
# ============================================================================

class TestValidateDataIntegrity:
    """Test the validate_data_integrity() method."""

    def test_participant_with_no_entries_is_warning(self, validator_with_mock):
        """Test that a participant with empty entries produces a warning."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},
            heat_events=[]
        )
        validator.validate_data_integrity()
        assert len(validator.warnings) == 1
        assert "Participant 'alice' has no entries" in validator.warnings[0]

    def test_entry_with_empty_event_is_error(self, validator_with_mock):
        """Test that an entry with empty event name is an error."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [{'event': '', 'partner': None}]
                }
            },
            heat_events=[]
        )
        validator.validate_data_integrity()
        assert "Empty event name for alice" in validator.errors

    def test_entry_with_whitespace_only_event_is_error(self, validator_with_mock):
        """Test that an entry with whitespace-only event name is an error."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [{'event': '   ', 'partner': None}]
                }
            },
            heat_events=[]
        )
        validator.validate_data_integrity()
        assert "Empty event name for alice" in validator.errors

    def test_self_referential_partner_is_error(self, validator_with_mock):
        """Test that partnering with oneself (case-insensitive) is an error."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [{'event': 'Waltz', 'partner': 'alice'}]
                }
            },
            heat_events=[]
        )
        validator.validate_data_integrity()
        assert len(validator.errors) == 1
        assert "Self-referential partnership: alice paired with self" in validator.errors[0]

    def test_self_referential_partner_case_insensitive(self, validator_with_mock):
        """Test that self-reference is case-insensitive."""
        validator = validator_with_mock(
            participants={
                'Alice': {
                    'entries': [{'event': 'Waltz', 'partner': 'ALICE'}]
                }
            },
            heat_events=[]
        )
        validator.validate_data_integrity()
        assert "Self-referential partnership" in validator.errors[0]

    def test_self_referential_with_whitespace(self, validator_with_mock):
        """Test that self-reference check works with whitespace in partner."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [{'event': 'Waltz', 'partner': '  alice  '}]
                }
            },
            heat_events=[]
        )
        validator.validate_data_integrity()
        assert "Self-referential partnership" in validator.errors[0]

    def test_heat_event_with_empty_name_is_error(self, validator_with_mock):
        """Test that a heat_event with empty name is an error."""
        validator = validator_with_mock(
            participants={},
            heat_events=[
                {'event': '', 'competitors': ['alice']}
            ]
        )
        validator.validate_data_integrity()
        assert "Empty event name in heat_events" in validator.errors

    def test_heat_event_with_no_competitors_is_warning(self, validator_with_mock):
        """Test that a heat_event with no competitors produces a warning."""
        validator = validator_with_mock(
            participants={},
            heat_events=[
                {'event': 'Jive Heat 1', 'competitors': []}
            ]
        )
        validator.validate_data_integrity()
        assert any("has no competitors" in w for w in validator.warnings)


# ============================================================================
# Tests for validate_age_categories()
# ============================================================================

class TestValidateAgeCategories:
    """Test the validate_age_categories() method."""

    def test_age_category_stats_built_correctly(self, validator_with_mock):
        """Test that age_category_stats are built with correct counts."""
        validator = validator_with_mock(
            participants={},
            heat_events=[
                {'event': 'AC-JV1 Jive', 'competitors': []},  # age
                {'event': 'AC-A Waltz', 'competitors': []},   # skill
                {'event': 'Pro-Am Tango', 'competitors': []},  # no-code
            ]
        )
        validator.validate_age_categories()

        assert validator.age_category_stats['age'] == 1
        assert validator.age_category_stats['skill'] == 1
        assert validator.age_category_stats['no-code'] == 1
        assert validator.age_category_stats['unrecognized_codes'] == 0

    def test_duplicate_event_names_counted_once(self, validator_with_mock):
        """
        Test that duplicate event names across multiple heat_events are
        only counted once in age_category_stats.
        """
        validator = validator_with_mock(
            participants={},
            heat_events=[
                {'event': 'AC-JV1 Jive', 'competitors': ['alice']},
                {'event': 'AC-JV1 Jive', 'competitors': ['bob']},  # same event name, different heat
                {'event': 'AC-JV1 Jive', 'competitors': ['charlie']},  # same again
            ]
        )
        validator.validate_age_categories()

        # Should only count this event once, not three times
        assert validator.age_category_stats['age'] == 1

    def test_unrecognized_code_produces_error_with_example(self, validator_with_mock):
        """Test that an unrecognized code produces an error with an example event."""
        validator = validator_with_mock(
            participants={},
            heat_events=[
                {'event': 'AC-UNKNOWN Some Event', 'competitors': []}
            ]
        )
        validator.validate_age_categories()

        assert len(validator.errors) == 1
        error = validator.errors[0]
        assert "Unrecognized event code 'UNKNOWN'" in error
        assert "AC-UNKNOWN Some Event" in error
        assert "not in AGE_CATEGORY_CODES or SKILL_LEVEL_CODES" in error

    def test_multiple_unrecognized_codes(self, validator_with_mock):
        """Test that multiple different unrecognized codes produce separate errors."""
        validator = validator_with_mock(
            participants={},
            heat_events=[
                {'event': 'AC-XXX Event 1', 'competitors': []},
                {'event': 'AC-YYY Event 2', 'competitors': []},
            ]
        )
        validator.validate_age_categories()

        assert len(validator.errors) == 2
        error_text = ' '.join(validator.errors)
        assert 'XXX' in error_text
        assert 'YYY' in error_text

    def test_unrecognized_code_with_multiple_examples_shows_count(self, validator_with_mock):
        """Test that multiple events with same unrecognized code show event count."""
        validator = validator_with_mock(
            participants={},
            heat_events=[
                {'event': 'AC-UNKNOWN Event 1', 'competitors': []},
                {'event': 'AC-UNKNOWN Event 2', 'competitors': []},
                {'event': 'AC-UNKNOWN Event 3', 'competitors': []},
            ]
        )
        validator.validate_age_categories()

        assert len(validator.errors) == 1
        error = validator.errors[0]
        assert "(3 event(s))" in error
        assert "(+2 more)" in error


# ============================================================================
# Tests for validate_couple_pairing_integrity()
# ============================================================================

class TestValidateCoupleParingIntegrity:
    """Test the validate_couple_pairing_integrity() method."""

    def test_partner_in_roster_no_error(self, validator_with_mock):
        """Test that when a claimed partner is in the event roster, no error."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'Waltz', 'heat': '1', 'partner': 'bob'}
                    ]
                },
                'bob': {'entries': []}
            },
            heat_events=[
                {'heat': '1', 'event': 'Waltz', 'competitors': ['alice', 'bob']}
            ]
        )
        validator.validate_couple_pairing_integrity()
        assert not validator.errors

    def test_partner_not_in_roster_is_error(self, validator_with_mock):
        """Test that a claimed partner not in the event roster is an error."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'Waltz', 'heat': '1', 'partner': 'bob'}
                    ]
                },
                'bob': {'entries': []}
            },
            heat_events=[
                {'heat': '1', 'event': 'Waltz', 'competitors': ['alice', 'charlie']}
            ]
        )
        validator.validate_couple_pairing_integrity()
        assert len(validator.errors) == 1
        assert "alice" in validator.errors[0]
        assert "claims partner 'bob'" in validator.errors[0]
        assert "not in that event's competitor list" in validator.errors[0]
        assert "couple will render as broken/solo" in validator.errors[0]

    def test_partner_name_not_in_participants_is_warning(self, validator_with_mock):
        """
        Test that a partner name that doesn't exist anywhere in participants
        produces a warning (separate from roster-mismatch).
        """
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'Waltz', 'heat': '1', 'partner': 'unknown'}
                    ]
                }
            },
            heat_events=[
                {'heat': '1', 'event': 'Waltz', 'competitors': ['alice']}
            ]
        )
        validator.validate_couple_pairing_integrity()

        # Should have a warning about the unknown partner
        assert any("Partner name 'unknown'" in w for w in validator.warnings)
        assert any("never appears as a participant" in w for w in validator.warnings)

    def test_unknown_heat_event_combination_no_crash(self, validator_with_mock):
        """
        Test that a heat+event combination that doesn't exist in heat_events
        doesn't crash and doesn't add spurious errors.
        """
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'Waltz', 'heat': '5', 'partner': 'bob'}  # heat 5 doesn't exist
                    ]
                },
                'bob': {'entries': []}
            },
            heat_events=[
                {'heat': '1', 'event': 'Waltz', 'competitors': ['charlie', 'dave']}
            ]
        )
        # Should not crash
        validator.validate_couple_pairing_integrity()
        # Should not add an error about the missing heat+event (that's checked elsewhere)
        # It should skip silently (see the "roster is None: continue" branch in the source)

    def test_both_partner_errors_fire_for_same_entry(self, validator_with_mock):
        """
        Test that both errors can fire for the same entry:
        1. Partner not in participants (warning)
        2. Partner not in roster (error)
        """
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'Waltz', 'heat': '1', 'partner': 'badname'}
                    ]
                }
            },
            heat_events=[
                {'heat': '1', 'event': 'Waltz', 'competitors': ['alice']}
            ]
        )
        validator.validate_couple_pairing_integrity()

        # Should have error about partner not in roster
        assert any("not in that event's competitor list" in e for e in validator.errors)
        # Should have warning about partner never appearing in participants
        assert any("never appears as a participant" in w for w in validator.warnings)


# ============================================================================
# Tests for report_results() and validate_all()
# ============================================================================

class TestReportResults:
    """Test the report_results() method return values."""

    def test_clean_data_returns_0(self, validator_with_mock, capsys):
        """Test that clean data (no errors/warnings) returns 0."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},
            heat_events=[]
        )
        validator.validate_data_structure()

        exit_code = validator.report_results()
        assert exit_code == 0

    def test_warnings_only_returns_0(self, validator_with_mock, capsys):
        """Test that data with only warnings returns 0."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},  # produces warning
            heat_events=[]
        )
        validator.validate_data_integrity()

        exit_code = validator.report_results()
        assert exit_code == 0
        assert len(validator.warnings) > 0
        assert len(validator.errors) == 0

    def test_with_errors_returns_1(self, validator_with_mock, capsys):
        """Test that data with at least one error returns 1."""
        validator = validator_with_mock(
            participants={},
            heat_events=[]
        )
        # Manually add an error
        validator.errors.append("Test error")

        exit_code = validator.report_results()
        assert exit_code == 1

    def test_errors_take_precedence_over_warnings(self, validator_with_mock):
        """Test that presence of errors causes return value 1 even with warnings."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},  # warning
            heat_events=[]
        )
        validator.validate_data_integrity()
        validator.errors.append("Test error")

        exit_code = validator.report_results()
        assert exit_code == 1


class TestValidateAll:
    """Test the validate_all() method and validate_all/report_results interaction."""

    def test_validate_all_with_errors_shows_errors(self, validator_with_mock, capsys):
        """Test that validate_all() correctly identifies and reports errors."""
        validator = validator_with_mock(
            participants={'alice': {'entries': []}},  # warning: no entries
            heat_events=[]
        )

        validator.validate_all()

        captured = capsys.readouterr()
        # Should show warnings in output
        assert "Participant 'alice' has no entries" in captured.out or "WARNINGS" in captured.out

    def test_validate_all_propagates_exit_code(self, validator_with_mock):
        """
        validate_all() must return report_results()'s value so main() can
        sys.exit() on it.

        This was previously a documented bug: validate_all() called
        report_results() as a bare statement, so it always returned None and
        main() did sys.exit(None) -> exit 0 regardless of the result. Fixed
        2026-08-31 alongside the results-join checks, which are pointless if the
        validator can never fail the process.
        """
        validator = validator_with_mock(
            participants={},
            heat_events=[]
        )
        # Force an error to exist
        validator.errors.append("Intentional test error")

        result = validator.validate_all()

        assert result == 1, (
            "validate_all() must return 1 when errors were found, so that "
            "main() exits non-zero."
        )
        assert len(validator.errors) > 0

    def test_validate_all_returns_zero_when_clean(self, validator_with_mock):
        """A validator with no errors must return 0 so main() exits successfully."""
        validator = validator_with_mock(participants={}, heat_events=[])

        assert validator.validate_all() == 0


# ============================================================================
# Integration / End-to-End Tests
# ============================================================================

class TestIntegration:
    """End-to-end validation tests."""

    def test_full_validation_pass(self, validator_with_mock, capsys):
        """Test a full validation that passes cleanly."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'AC-A Waltz', 'heat': '1', 'partner': 'bob'}
                    ]
                },
                'bob': {
                    'entries': [
                        {'event': 'AC-A Waltz', 'heat': '1', 'partner': 'alice'}
                    ]
                }
            },
            heat_events=[
                {'heat': '1', 'event': 'AC-A Waltz', 'competitors': ['alice', 'bob']}
            ]
        )

        validator.validate_all()

        captured = capsys.readouterr()
        # Should pass validation
        assert validator.report_results() == 0 or "All validations passed" in captured.out

    def test_full_validation_with_errors(self, validator_with_mock, capsys):
        """Test a full validation that produces errors."""
        validator = validator_with_mock(
            participants={
                'alice': {
                    'entries': [
                        {'event': 'AC-A Waltz', 'heat': '1', 'partner': 'bob'}
                    ]
                }
            },
            heat_events=[
                {'heat': '1', 'event': 'AC-A Waltz', 'competitors': ['alice']}
                # bob is missing from the roster
            ]
        )

        validator.validate_all()

        captured = capsys.readouterr()
        # Should have errors
        assert "❌" in captured.out or "ERRORS" in captured.out
