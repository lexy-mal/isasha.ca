# Scoresheet parsing — findings and gotchas

Hard-won notes about how CompMngr publishes results, and the traps that cost us a
silently-wrong dataset. Read this before touching `scrape_results_dat.py` or writing
a scraper for a new competition.

Written 2026-08-30 after National 2026.

---

## TL;DR

- **Parse the `.dat` file, not the CGI HTML.** `scrape_results_dat.py` is the
  supported path. 2 requests instead of ~1000, and structurally unambiguous.
- **Never trust a scrape that "succeeded".** Both failures below produced clean runs
  with zero errors and plausible-looking JSON. Always check coverage against
  `heat_events.json`.

---

## Where the data lives

For a competition at `/{slug}/`:

| File | What it is |
|---|---|
| `{slug}_ScoresheetsByPerson.htm` | Lookup **form**, not an index. Holds the competitor `<select>` (`value="{id}={Name (Number)}"`) and the judge roster. |
| `{slug}_scoresheetsbyperson.dat` | **Every scoresheet, in one file.** Directly downloadable. |
| `/cgi-bin/ScoresheetHandler.pl` | Renders one person's sheets from the `.dat`. Accepts GET as well as POST. |

The directory has an open Apache autoindex, so you can list it. `national2025/` and
`national2024/` follow the same convention if historical data is ever wanted.

Both files are needed: the `.dat` has the marks but **no competitor names or judge
names** — only ids and back numbers. The `.htm` supplies `id → name` and the judge
roster.

**Encodings differ.** The `.htm` is fine as ISO-8859-1; the `.dat` is **windows-1252**
and must be decoded as `cp1252` (it contains `Fermé`, `Débutant`, `Renée`). Decoding
the `.dat` as ISO-8859-1 mangles the 0x80–0x9F range.

**A browser User-Agent is required.** Default curl/urllib UAs get a Mod Security
`406 Not Acceptable`.

---

## Trap 1 — the HTML parser silently dropped ~80% of heats

**This is why `scrape_results_flexible.py` is no longer used.**

CompMngr renders a *single-dance heat heading* and a *dance sub-heading* with
identical markup:

```html
<!-- a single-dance HEAT -->
<font size="3"><strong><em>Heat 1: L-C* Argent Ouvert / Open Silver RHYTHM Chacha</em></strong></font>

<!-- a DANCE inside a multi-dance heat -->
<font size="3"><strong><em>Cha Cha</em></strong></font>
```

Only the `font size` differs (4 for multi-dance heat headings, 3 for both of the
above), and `HTMLParser` sees the same `<strong><em>` nesting either way. Worse, in
`scrape_results_flexible.py` `handle_data` fills `_em_buf` *before* `_strong_buf`, so
for a single-dance heat `_strong_buf` ends up empty — the `</strong>` handler never
matches `Heat N:` and the heading is consumed as a **dance name belonging to the
previous heat**.

Effect: every single-dance heat vanished.

| | Heats captured | Scheduled |
|---|---|---|
| National 2026 | 473 | 2,683 |
| Imperial Cup 2026 | 494 | 1,278 |

**The tell:** in `results.json`, count dances per heat. Imperial Cup's distribution was
`{2:151, 3:184, 4:21, 5:79, 6:15}` — **no heats with exactly 1 dance**. A real
dancesport competition is mostly single-dance heats. If that bucket is empty or tiny,
the parser is broken.

The `.dat` has no such ambiguity: multi-dance events are flagged with a leading `=`.

---

## Trap 2 — the back number is not necessarily the first-listed dancer

A scoresheet row looks like:

```
|178 Celino/Choque|R||R|R|R|4|Recall|
```

It is tempting to read `178` as the **lead's** number and resolve `parts[0]`
(`Celino`) from it. That is wrong: in pro-am the number belongs to whichever partner
is registered with it, which is frequently the **follow** — here `178` is
`Choque, Omar`.

The original code credited the numbered person and then *skipped* resolving position 0,
so `Celino, Valerie` got no placement for a heat she placed 4th in. This cost **2,683
placement badges** on National 2026 alone.

**Correct approach** (`build_person_results` in `scrape_results_dat.py`): take the
numbered person *and independently* resolve every surname in the row against the
people the `.dat` says were in that record, accepting only unambiguous matches.

Only ~55% of competitors have a back number at all (524 of 956 at Nationals), so
number-based resolution alone can never cover the field. The `.dat`'s per-record
person-id list is what closes the gap — the HTML path never had it.

---

## `.dat` format

```
<118,122
Heat 1: L-G Bronze 1 Fermé / Closed Bronze 1 RHYTHM Chacha
|No.|10|18|24|27|31||1|Result|
|550 Tierney/Tudorovsky|1|1|1|1|1||5|1|
>
```

- Record opens with `<` + a **comma-separated list of person ids** (the same ids as
  the `<option value>` in the `.htm`). This is the whole roster for that record.
- Line 2 is the heading. A leading **`=` means multi-dance**: dance-name lines and a
  `Final summary` section follow.
- Pipe-delimited rows, leading and trailing `|`, empty fields empty.
- Record closes with `>` on its own line.
- CRLF line endings.

**Judge columns**: numeric header cells *before* the first blank/non-numeric one.
The blank separator matters — the skating-system columns after it (`1`, `1-2`, `1-3`)
are also numeric and must not be mistaken for judges. Recall rounds have no blank
separator and end in `Total|Recall`.

**Non-heat records exist.** 34 of National 2026's 2,720 records are
`Combined Event: …` scholarship awards with no heat number. They cannot join the
schedule, so they are skipped — but the scraper *reports* the count rather than
dropping them silently. Keep it that way.

---

## Rounds

A heat that runs multiple rounds appears as several records:

```
=Heat 467: AC-16+ AMATEUR LATIN "NATIONAL CHAMP" (C/S/R/P/J) - Quarter-final
=Heat 467: AC-16+ AMATEUR LATIN "NATIONAL CHAMP" (C/S/R/P/J) - Semi-final
=Heat 467: AC-16+ AMATEUR LATIN "NATIONAL CHAMP" (C/S/R/P/J)
```

- **The unmarked record is the final.** There is no ` - Final` on it. (A bare
  ` Final` with no dash does occur occasionally, e.g. Heat 776 — match both.)
- The round marker must be **stripped from `event`**, or results will not join
  `heat_events.json` / `participants.json`, which carry no round suffix. It is kept
  separately in `round`.
- Rosters shrink per round (Heat 467: 36 → 24 → 12 dancers). Competitors eliminated
  before the final appear in **no** final summary, so they need the per-round rosters
  (`rounds[]`) to be credited as "Semi-finalist" / "Quarter-finalist" rather than
  showing a blank. That is what `reachedRound` on a `person_results` entry is for.

---

## One heat number ≠ one event

A single heat number hosts several divisions dancing simultaneously. Heat 776 carries
nine records across six distinct events. Always key on `heat|event`, never on heat
alone.

Related: some events in the scoresheets are absent from the heat list and vice versa
(2,675 National entries have no published scoresheet). This is genuine source
divergence, not a bug — don't "fix" it with fuzzy matching.

---

## How to sanity-check a results scrape

Run these before committing. All numbers below are National 2026's.

1. **Heat coverage** — `len(results.json)` against `len(heat_events.json)`.
   Expect the same order of magnitude (2,564 vs 2,683). 473 means a broken parser.
2. **Single-dance heats exist** — `Counter(len(v['dances']) for v in results.values())`
   must have a healthy `1` bucket.
3. **Outcome coverage** — share of `participants.json` entries with a placement or
   `reachedRound`. Expect ~75% of entries and ~88% of people. Anything near 17% means
   Trap 1; near 45% means Trap 2.
4. **Junk person keys** — `[k for k in person_results if k not in participants]`
   should be a handful (13), not hundreds. 508 means name resolution collapsed to raw
   `Lead/Follow` strings.
5. **Judges** — `judges.json` count should match the roster on the `.htm` (34).

A run that reports no errors proves nothing; both traps were silent.
