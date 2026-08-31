#!/usr/bin/env python3
"""Regression tests for the .dat scoresheet parser.

Runs on stdlib alone:  python3 test_scrape_results_dat.py

Each test here pins a failure mode that previously shipped silently-wrong data.
See SCORESHEET_PARSING.md.
"""

import unittest

from scrape_results_dat import (
    split_records, parse_record, merge_records, build_person_results,
    judge_columns, parse_round,
)

# A single-dance heat, a multi-dance heat, and a heat with a semi-final + final.
# Note Heat 20's row "Celino/Choque" carries number 178, which belongs to CHOQUE
# (the follow) -- the pro-am case that broke resolution.
DAT = "\r\n".join([
    "<1,2",
    "Heat 1: L-G Bronze 1 Fermé / Closed Bronze 1 RHYTHM Chacha",
    "|No.|10|18|24||1|Result|",
    "|550 Tierney/Tudorovsky|1|1|1||3|1|",
    "|551 Smith/Jones|2|2|2||3|2|",
    ">",
    "<1,2,3,4",
    "=Heat 10: Open Bronze RHYTHM 3-Dance (C/R/SW)",
    "Cha Cha",
    "|No.|10|18|24||1|1-2|Result|",
    "|550 Tierney/Tudorovsky|1|1|1||3||1|",
    "Rumba",
    "|No.|10|18|24||1|1-2|Result|",
    "|550 Tierney/Tudorovsky|1|1|1||3||1|",
    "Final summary",
    "|No.|C|R|Total|Result|",
    "|550 Tierney/Tudorovsky|1|1|2|1|",
    ">",
    "<5,6,7,8",
    "=Heat 20: Open Silver LATIN (C/R/S) - Semi-final",
    "|No.|10|18|24|Total|Recall|",
    "|178 Celino/Choque|R|R|R|3|Recall|",
    "|179 Ng/Patel|R||R|2||",
    ">",
    "<5,6",
    "=Heat 20: Open Silver LATIN (C/R/S)",
    "|No.|10|18|24||1|Result|",
    "|178 Celino/Choque|1|1|1||3|1|",
    ">",
    "",
])

PERSONS = [
    {"id": "1", "fullName": "Tierney, Ann (550)", "number": "550"},
    {"id": "2", "fullName": "Tudorovsky, Veycheslav", "number": None},
    {"id": "3", "fullName": "Smith, Al (551)", "number": "551"},
    {"id": "4", "fullName": "Jones, Bo", "number": None},
    {"id": "5", "fullName": "Choque, Omar (178)", "number": "178"},
    {"id": "6", "fullName": "Celino, Valerie", "number": None},
    {"id": "7", "fullName": "Ng, Kim (179)", "number": "179"},
    {"id": "8", "fullName": "Patel, Ravi", "number": None},
]
NUMBER_MAP = {"550": "Tierney, Ann", "551": "Smith, Al",
              "178": "Choque, Omar", "179": "Ng, Kim"}


def build():
    recs = [parse_record(r) for r in split_records(DAT)]
    return merge_records([r for r in recs if r])


class TestSingleDanceHeats(unittest.TestCase):
    """Trap 1: single-dance heats used to be swallowed as dances of the prior heat."""

    def test_single_dance_heat_is_its_own_heat(self):
        results = build()
        self.assertIn("Heat 1|L-G Bronze 1 Fermé / Closed Bronze 1 RHYTHM Chacha", results)

    def test_single_dance_heat_has_exactly_one_dance(self):
        heat = build()["Heat 1|L-G Bronze 1 Fermé / Closed Bronze 1 RHYTHM Chacha"]
        self.assertEqual(len(heat["dances"]), 1)

    def test_single_dance_heat_gets_a_final_summary(self):
        # buildHeatRanking() in com.html renders nothing without finalSummary.
        heat = build()["Heat 1|L-G Bronze 1 Fermé / Closed Bronze 1 RHYTHM Chacha"]
        self.assertEqual(len(heat["finalSummary"]), 2)
        self.assertEqual(heat["finalSummary"][0]["placement"], "1")

    def test_single_dance_heat_is_not_absorbed_by_neighbours(self):
        results = build()
        multi = results["Heat 10|Open Bronze RHYTHM 3-Dance (C/R/SW)"]
        self.assertEqual([d["dance"] for d in multi["dances"]], ["Cha Cha", "Rumba"])


class TestPartnerResolution(unittest.TestCase):
    """Trap 2: the back number is often the FOLLOW's, not the first-listed dancer's."""

    def test_both_partners_get_the_placement(self):
        people = build_person_results(build(), NUMBER_MAP, PERSONS)
        self.assertIn("Celino, Valerie", people)
        self.assertIn("Choque, Omar", people)

    def test_unnumbered_partner_gets_the_right_placement(self):
        people = build_person_results(build(), NUMBER_MAP, PERSONS)
        entry = [e for e in people["Celino, Valerie"]
                 if e["heat"] == "Heat 20" and e["placement"]][0]
        self.assertEqual(entry["placement"], "1")

    def test_no_raw_lead_slash_follow_keys(self):
        people = build_person_results(build(), NUMBER_MAP, PERSONS)
        self.assertEqual([k for k in people if "/" in k], [])


class TestRounds(unittest.TestCase):
    def test_round_suffix_stripped_from_event(self):
        # Or results never join heat_events.json / participants.json.
        event, rnd = parse_round('Open Silver LATIN (C/R/S) - Semi-final')
        self.assertEqual(event, 'Open Silver LATIN (C/R/S)')
        self.assertEqual(rnd, 'Semi-final')

    def test_bare_final_without_dash_is_recognised(self):
        event, rnd = parse_round('Open Silver LATIN (C/R/S) Final')
        self.assertEqual(event, 'Open Silver LATIN (C/R/S)')
        self.assertEqual(rnd, 'Final')

    def test_named_first_round_is_stripped(self):
        # National 2026 spells the opening round "First Round"; leaving it on the
        # event name kept 7 events from ever joining the schedule.
        event, rnd = parse_round('A-JV Bronze / Bronze LATIN SOLO Rumba - First Round')
        self.assertEqual(event, 'A-JV Bronze / Bronze LATIN SOLO Rumba')
        self.assertEqual(rnd, 'First Round')

    def test_event_ending_in_heat_is_not_mistaken_for_a_round(self):
        # "Bronze Western Heat" is a real event name, not a round marker.
        event, rnd = parse_round('G-D Bronze Western Heat')
        self.assertEqual(event, 'G-D Bronze Western Heat')
        self.assertEqual(rnd, '')

    def test_rounds_collapse_to_one_key(self):
        results = build()
        keys = [k for k in results if k.startswith("Heat 20|")]
        self.assertEqual(len(keys), 1)

    def test_unmarked_record_wins_as_the_final(self):
        heat = build()["Heat 20|Open Silver LATIN (C/R/S)"]
        self.assertEqual(heat["round"], "")
        self.assertEqual(heat["finalSummary"][0]["placement"], "1")

    def test_earlier_round_rosters_retained(self):
        heat = build()["Heat 20|Open Silver LATIN (C/R/S)"]
        self.assertEqual(sorted(r["round"] for r in heat["rounds"]), ["", "Semi-final"])

    def test_eliminated_competitor_credited_with_furthest_round(self):
        # Ng/Patel danced the semi and did not advance -> no placement anywhere.
        people = build_person_results(build(), NUMBER_MAP, PERSONS)
        entry = [e for e in people["Ng, Kim"] if e["heat"] == "Heat 20"][0]
        self.assertEqual(entry["placement"], "")
        self.assertEqual(entry["reachedRound"], "Semi-final")


class TestJudgeColumns(unittest.TestCase):
    def test_skating_columns_are_not_judges(self):
        # Columns after the blank separator (1, 1-2, 1-3) are skating-system totals.
        header = ["No.", "10", "18", "24", "", "1", "1-2", "Result"]
        self.assertEqual([j for _, j in judge_columns(header)], ["10", "18", "24"])

    def test_recall_header_stops_at_total(self):
        header = ["No.", "10", "18", "24", "Total", "Recall"]
        self.assertEqual([j for _, j in judge_columns(header)], ["10", "18", "24"])

    def test_scored_header_stops_at_avg(self):
        header = ["Names", "10", "18", "24", "Avg.", "Place"]
        self.assertEqual([j for _, j in judge_columns(header)], ["10", "18", "24"])


class TestNonHeatRecords(unittest.TestCase):
    def test_combined_event_records_are_rejected_not_mangled(self):
        rec = "<1,2\r\n=Combined Event: Combined event award for: Pro-Am 9-Dance\r\n" \
              "Final places\r\n|Number|WA|TA|Total|Place|\r\n|326 A/B|1|1|2|1|"
        self.assertIsNone(parse_record(rec))


if __name__ == "__main__":
    unittest.main(verbosity=2)
