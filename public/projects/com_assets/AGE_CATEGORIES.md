# Age category codes

Every event name in `heat_events.json` starts with a code like `A-15-`, `AC-JV1`,
`G-F`, or `L-JU`. The prefix (`A`, `AC`, `G`, `L`) is a style/division grouping
(solo vs. couple, dance style track); the part after the first hyphen is what this
file is about — it's either an **age category** or a **non-age code** that happens
to sit in the same position.

Neither competition publishes a legend for these. This mapping was built by
(a) fetching the standard WDSF age-division definitions and (b) inspecting every
unique event name across **both** competitions (3885 events total). See Sources.

Implemented as `AGE_CATEGORY_MAP` in `com.html`. Companion doc:
[SKILL_LEVELS.md](SKILL_LEVELS.md) covers proficiency (Bronze/Silver/Gold), which
is a **separate axis** parsed from the event *text*, not from this code.

## Named age brackets

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
| `U12` | Under 12 | 0–12 | Explicit in the code |
| `YO` | Young Adult | ~19–25 | **Approximate** — appears alongside U21; no public definition distinguishes them |
| `AD` | Adult (combined) | 19+ | Not further subdivided for this event |
| `AD1`–`AD5` | Adult I–V | 19+, increasing | **Estimated only.** Split into 5 sub-groups with boundaries never published. Ordered AD1 < ... < AD5 on common Pro-Am convention (~10-year bands: 19–25 / 26–35 / 36–45 / 46–55 / 56+). Treat cutoffs as a guess |

## Numeric brackets

The trailing `+` / `-` in the event name carries the direction (`A-15-` = 15 and
under, `A-16+` = 16 and over).

> ⚠️ **Known fragility.** The parse regex `^[A-Za-z0-9]+-([A-Za-z0-9]*)` captures
> only the number and **discards the sign**, so direction is hardcoded per number
> in the map. Verified across both competitions that no number is currently used
> in both directions, so this is safe today — but a future competition adding e.g.
> `12-` (12 & under) alongside Imperial Cup's `12+` would be silently
> mis-classified. If that happens, capture the sign in the regex instead.

| Code | Source form | Label | Ages |
|---|---|---|---|
| `6U` | `A-6U` | 6 & Under | 0–6 |
| `7U` | `A-7U` | 7 & Under | 0–7 |
| `7` | `A-7-11` | Ages 7–11 | 7–11 |
| `11U` | `AC-11U` | 11 & Under | 0–11 |
| `12` | `A-12+` | 12 & Over | 12+ |
| `15` | `A-15-` | 15 & Under | 0–15 |
| `16` | `A-16+` | 16 & Over | 16+ |
| `19` | `A-19+` | 19 & Over | 19+ |
| `30` | `AC-30+` | 30 & Over | 30+ |
| `36` | `A-36+` | 36 & Over | 36+ |
| `40` | `AC-40+` | 40 & Over | 40+ |
| `50` | `A-50+` | 50 & Over | 50+ |

**Important:** the numeric codes and the named brackets (`JV1`...`AD5`) are two
*different, parallel* systems used for different event families — they don't nest
inside each other. A `16+` event is open-ended (any age 16 and up, including
adults); it is **not** `JV1`/`JR`/`YTH` combined. Don't merge them in the UI as if
one supersedes the other.

Sorting uses `minAge` as the primary key and `maxAge` as the tiebreak, so
brackets sharing a floor order correctly (Under 10 < Under 12 < 15 & Under, all
`minAge: 0`). Open-ended "& Over" brackets have no `maxAge`.

## Codes in the age slot that are NOT ages

`A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`, `JB`, `JU`, `PD` occupy the same position
but are excluded from the age filter/sort (`SKILL_LEVEL_CODES` in `com.html`).

> 🔴 **Correction (2026-08-18).** An earlier version of this file described
> `A`–`H` as "Pro-Am skill-level tiers (Bronze → Silver → Gold progression)".
> **That is wrong.** Cross-tabulating all 3885 events against the proficiency
> words in the event text shows every letter co-occurs with every proficiency —
> e.g. `E` appears with Open (130), Closed (81), Silver (77), Bronze (72) and
> Gold (33). They are **not** a proficiency ladder. Their real meaning is
> unknown; the evidence is consistent with a section/heat-grouping or
> style-track code. They were still correctly *excluded* from age, so no age
> output was ever wrong — but do not sort by them as if they were skill.
> Real proficiency lives in the event text: see [SKILL_LEVELS.md](SKILL_LEVELS.md).

`PD` (e.g. `AC-PD Amateur Pre-Bronze LATIN Jive`) has no published meaning either
— possibly Para Dance. Excluded rather than guessed.

## Events with no code at all

Professional/Open events (`PRO BALLROOM`, `WDC WORLD PROFESSIONAL LATIN`, …) and
some `G-`/`L-` solo events with a blank slot (e.g. `G- Or / Gold Milonga`) carry
no code. Treated as "No age category" in the UI.

## Coverage

Measured in-browser against the live parser:

| Competition | Events | With an age category |
|---|---|---|
| `national2026` | 2661 | 671 (25%) |
| `impercup2026` | 1224 | 459 (38%) |

The remainder are Pro-Am/section-coded or uncoded events that genuinely carry no
age bracket. Low coverage here is expected, not a parsing failure.

## Sources

- [Youth Division of DanceSport – WikiDanceSport](https://www.wikidancesport.com/wiki/youth-division-of-dancesport/)
- [Junior Division of DanceSport – WikiDanceSport](https://www.wikidancesport.com/wiki/junior-division-of-dancesport/)
- NDCA Pro/Am age division structure — general web search summary; no single
  canonical NDCA PDF confirmed the exact table.
- Exhaustive inspection of every unique event-name prefix across
  `national2026/heat_events.json` and `impercup2026/heat_events.json`.

If an organizer ever publishes an official legend, replace the estimates — `YO`,
`AD1`–`AD5` and `PD` are the weakest-confidence entries here.
