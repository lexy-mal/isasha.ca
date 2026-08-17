# Age category codes

Every event name in `heat_events.json` starts with a code like `A-15-`, `AC-JV1`,
`G-F`, or `L-JU`. The prefix (`A`, `AC`, `G`, `L`) is a style/division grouping
(solo vs. couple, dance style track); the part after the hyphen is what this
file is about — it's either an **age category** or a **Pro-Am skill level**,
and the two are easy to confuse because they're both short letter/number codes
sitting in the same position.

Neither `national2026`'s own entry-list page nor its site has a published
legend for these — this mapping was built by (a) fetching the standard WDSF
age-division definitions and (b) inspecting every event name in the actual
scraped data to separate genuine age codes from skill-level codes. See
Sources at the bottom.

## Age category codes (used for the age filter/sort/tooltip)

| Code | Plain-English label | Approx. ages | Confidence |
|---|---|---|---|
| `JV1` | Juvenile I | Under 10 | Standard WDSF definition |
| `JV2` | Juvenile II | 10–11 | Standard WDSF definition |
| `JV` | Juvenile (combined) | Under 12 | Same span as JV1+JV2, not split for this event |
| `JR1` | Junior I | 12–13 | Standard WDSF definition |
| `JR2` | Junior II | 14–15 | Standard WDSF definition |
| `JR` | Junior (combined) | 12–15 | Same span as JR1+JR2, not split for this event |
| `YTH` | Youth | 16–18 | Standard WDSF definition |
| `Y` | Youth (shorthand) | 16–18 | Same as YTH — solo/mixed events under `A-`/`G-` use the single-letter form |
| `U21` | Under 21 | 19–20 | Standard WDSF definition |
| `YO` | Young Adult | ~19–20 | **Approximate** — appears alongside U21 in this data; no public definition distinguishes them, treated as the same tier |
| `AD` | Adult (combined) | 19+ | Not further subdivided for this event |
| `AD1`–`AD5` | Adult I–V | 19+, increasing | **Estimated only.** This competition splits its adult bracket into 5 sub-groups but never publishes the boundaries. Ordered AD1 < AD2 < ... < AD5 (youngest to oldest) based on common Pro-Am convention (e.g. NDCA-style ~10-year bands: 19–25 / 26–35 / 36–45 / 46–55 / 56+), but treat the exact cutoffs as a guess |
| `15` (shown as `A-15-`) | 15 & Under | 0–15 | Explicit in the code itself (trailing `-`) |
| `16` (shown as `A-16+`) | 16 & Over | 16+ | Explicit in the code itself (trailing `+`) |
| `19` | 19 & Over | 19+ | Explicit |
| `36` | 36 & Over | 36+ | Explicit |
| `50` | 50 & Over | 50+ | Explicit |

**Important:** the numeric codes (`15`, `16`, `19`, `36`, `50`) and the named
brackets (`JV1`...`AD5`) are two *different, parallel* systems used for
different event families in this same competition — they don't nest inside
each other. A `16+` event is open-ended (any age 16 and up, including
adults); it is **not** the same thing as `JV1`/`JR`/`YTH` combined. Don't
merge them in the UI as if one supersedes the other.

## Skill-level codes (NOT age — do not sort/filter these as age)

`A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`, `JB`, `JU` all appear in the exact same
position as the age codes above, but every event using them is a **Pro-Am**
event (student dancing with a professional partner), and none of them mention
an age anywhere in the name — e.g. `AC-A Bronze Fermé / Closed Bronze PRO-AM
SMOOTH...`, `G-F Argent 1 Fermé / Closed Silver 1 BALLROOM...`. These are
skill-level tiers (Bronze → Silver → Gold progression), not age brackets.
Pro-Am students can be any age, so these events have no meaningful age
category — they're excluded from the age filter/sort as "No age category."

## Events with no code at all

13 events have no leading age/level code:
- 6 are Professional/Open events (`PRO BALLROOM`, `PRO LATIN`, `PRO RHYTHM`,
  `PRO SMOOTH`, `WDC WORLD PROFESSIONAL BALLROOM`, `WDC WORLD PROFESSIONAL
  LATIN`) — professional dancers, adults by definition, but not assigned a
  numeric/named age bracket in the data.
- 7 are `G-`/`L-` prefixed solo events with a blank code (e.g. `G- Or / Gold
  Milonga`) — the age slot in the name is simply empty for these.

Both groups are treated as "No age category" in the UI.

## Sources

- [Youth Division of DanceSport – WikiDanceSport](https://www.wikidancesport.com/wiki/youth-division-of-dancesport/)
- [Junior Division of DanceSport – WikiDanceSport](https://www.wikidancesport.com/wiki/junior-division-of-dancesport/)
- NDCA Pro/Am age division structure (age-threshold letters A/B/C/S1-S4, with
  organizers free to subdivide further) — general web search summary, no
  single canonical NDCA PDF page confirmed the exact table.
- Manual inspection of every unique event-name prefix in
  `national2026/heat_events.json` (31 distinct codes total) to classify each
  as age vs. skill-level vs. uncoded, cross-checked against the dance style
  wording already present in each event name (Bronze/Silver/Gold, Fermé/
  Closed, Ouvert/Open, PRO-AM, etc.).

If the organizer ever publishes an official legend (rules PDF, entry-list
key), replace the estimates above — `YO` and `AD1`–`AD5` in particular are
the weakest-confidence entries here.
