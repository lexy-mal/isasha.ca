# Skill / proficiency levels

How the "Sort: Level" control on the events list decides which event is a higher
level than another. Implemented as `SKILL_LEVELS` + `getEventSkillLevel()` in
`com.html`.

Companion docs: [AGE_CATEGORIES.md](AGE_CATEGORIES.md) (age is a separate axis),
[EVENT_DIVISIONS.md](EVENT_DIVISIONS.md) (division/prestige is a third axis).

## The key finding: the letter code is not a level

The obvious-looking candidate is the letter after the first hyphen —
`G-**D**`, `L-**C**`, `AC-**C**`. It is **not** a proficiency, and an earlier
implementation that assumed `A=Beginner, B=Bronze, C=Silver, D=Gold` produced
meaningless ordering.

Cross-tabulating all 3885 events (both competitions) against the proficiency
words in the event text shows every letter spans every proficiency:

| Code | Proficiency words it appears with (count) |
|---|---|
| `A` | Silver 16, Open 15, Closed 15, Bronze 10, Newcomer 3 |
| `C` | Closed 70, Bronze 66, Open 39, Newcomer 27, Silver 10 |
| `E` | Open 130, Closed 81, Silver 77, Bronze 72, Gold 33 |
| `F` | Closed 68, Silver 61, Open 57, Bronze 22, Gold 17 |

If `E` were "Gold-tier" it would not carry 72 Bronze events. The letters are a
section/scheduling or style-track code of unknown meaning; they are excluded from
both age and level parsing.

Also note the **first** segment is only ever `A`, `AC`, `G`, or `L` across all
3885 events — a style/division grouping, never a level. Reading it as a level
(as an earlier version did) buckets nearly everything into one meaningless group.

## Where the level actually lives

In the event **text**. Two naming conventions appear:

- `national2026` — bilingual pairs: `Ouvert / Open`, `Argent / Silver`,
  `Or / Gold`, `Fermé / Closed`, `Débutant / Beginner`
- `impercup2026` — English only, modifier + metal: `Closed Bronze`,
  `Open Silver`, `Closed Gold`, `Open Bronze 1`

Matching is done on the **English** half. Verified across the data that every
French token always co-occurs with its English counterpart (`Or`→`Gold` 0
exceptions, `Argent`→`Silver` 0, `Ouvert`→`Open` 0, `Fermé`→`Closed` 0), so the
ambiguous bare French `Or` never needs to be matched. `Débutant` is the one
exception — it appears 36 times without `Beginner` (paired with `Newcomer`
instead), so it is matched directly.

## The ladder

| Rank | Level | Notes |
|---|---|---|
| 0 | Newcomer / Beginner | `Newcomer`, `Beginner`, `Débutant` |
| 1 | Pre-Bronze | `Pre-Bronze`, `Pré-Bronze`, `Pré-Br.` — **must** precede Bronze, see below |
| 2 | Bronze | |
| 3 | Silver | `Silver`, `Argent` |
| 4 | Gold | `Gold` (`Or` always paired) |
| 5 | Novice | Amateur ladder |
| 6 | Pre-Championship | `Pre-Champ` |
| 7 | Open | **Only when no metal is named** — see below |
| 8 | Championship | `Championship(s)`, `Championnat`, `NATIONAL CHAMP`. **Only when no metal is named** — see below |
| 9 | Five Star | Multi-dance championship tier |
| — | *unranked* | Showcases, `Challenge Cup`, `Grand Trophy`. Sort **last in both directions** |

### Why Pre-Bronze needs its own tier

`"Pre-Bronze"` contains a word-boundary `"Bronze"`, so a plain `/\bBronze\b/i`
matches it. Before this tier existed, **158 events at a level below Bronze
ranked identically to Bronze**. Pre-Bronze is therefore tested *before* Bronze
in the lookup order, and matched with `/\bPr[ée]-?\s*Br(?:onze|\.)/i` to cover
`Pré-Bronze/Pre-Bronze`, `Pre-Bronze 1`, and the abbreviated `Pré-Br.` form.

Combined events (`AC-15- Pré-Br. & Bronze/Pre-Br. & Bronze AMATEUR BALLROOM`)
rank at the **lower bound** (Pre-Bronze), since that's the entry floor — the
same convention as `15 & Under` sorting by its floor.

### Why "Open" and "Championship" are both modifiers and levels

Per USA Dance, the progression is *Pre-Bronze, Bronze, Open Bronze, Silver, Open
Silver, Gold, Open Gold* — so **`Open` is normally a modifier, not a rank**:
"Open Gold is still Gold level skill, it simply is not restricted to syllabus
steps." Dancers then graduate past the syllabus into standalone Open events, and
the same source lists *Open Gold **& Open Championship*** as the final tiers.

`Championship` behaves the same way: it is very often just title decoration on
an event whose real level is a metal (`G-D Closed Bronze 1 Pro-Am CLUB Salsa
Championship` is a **Bronze** event).

So the parser resolves both by precedence: **a named metal always wins**.
`Open Bronze` and `…Salsa Championship` both rank as Bronze (2), with Open
recorded as a modifier. Ranks 7 and 8 are reached only when the event names no
metal at all — `A-15- Ouvert / Open BALLROOM SOLO` (graduated post-syllabus) and
`AC-JV2 AMATEUR BALLROOM "NATIONAL CHAMP"` (top competitive tier) respectively.

Championship outranks bare Open, so `AC-AD Open Amateur BALLROOM Championship`
ranks as Championship (8), not Open — an Open Championship is the pinnacle
event, not a plain Open.

This is why evaluation order ≠ rank order. `SKILL_LEVEL_LOOKUP_ORDER` checks
`[9, 6, 5, 0, 1, 2, 3, 4, 8, 7]`, encoding three rules: metals beat both Open and
Championship; Pre-Bronze precedes Bronze and Pre-Championship precedes
Championship (each is a substring of the other); and Championship precedes bare
Open, which is tested last of all.

### Tiebreaks within a rank

Sorted by `(rank, sublevel, openRank)`:

1. **`sublevel`** — trailing digit in `Bronze 1` / `Bronze 2` / `Bronze 3`.
2. **`openRank`** — Closed (0) before Open (1), matching *Bronze, Open Bronze,
   Silver*.

## Verified output

Ascending sort is monotonic by rank across **all** events in both competitions
(2655 national2026, 1224 impercup2026), verified against the live parser.

Coverage: **3652 / 3879 events (94%)** carry a recognisable level, distributed:

| Rank | Level | Events |
|---|---|---|
| 0 | Newcomer / Beginner | 182 |
| 1 | Pre-Bronze | 158 |
| 2 | Bronze | 959 |
| 3 | Silver | 1163 |
| 4 | Gold | 782 |
| 5 | Novice | 13 |
| 6 | Pre-Championship | 55 |
| 7 | Open | 270 |
| 8 | Championship | 55 |
| 9 | Five Star | 15 |
| — | unranked | 227 |

The 227 unranked are genuinely levelless — showcase titles (`"Americano"`,
`"Caribbean Blue" - Ballet`) and `Challenge Cup` / `Grand Trophy` events.

## Caveat on merging two ladders

Ranks 0–4 (Newcomer→Gold) are the **Pro-Am syllabus** ladder; ranks 5–6
(Novice, Pre-Champ) are the **amateur** ladder. They are not strictly
comparable — an amateur Novice is not "better than" a Pro-Am Gold, they are
different tracks. They are merged into one monotonic scale so a single sort
control works, with the amateur tiers placed above the syllabus metals. If this
ever needs to be exact, split into two sorts or sort by division first.

## Sources

- [Pro-Am Event Rules – USA Dance Nationals](https://usadancenationals.org/pro-am-event-rules/) — Pre-Bronze / Bronze / Open Bronze / Silver / Open Silver / Gold / Open Gold
- [Closed vs. Open Routines for Pro-Am Ballroom Dancers](https://dancelifesuccess.com/navigating-the-dance-progression-dilemma-closed-vs-open-routines-for-pro-am-ballroom-dancers/) — Closed = syllabus figures, Open = unrestricted choreography
- [Levels of Ballroom Dancing: Bronze to Gold](https://www.justdanzehouston.com/post/levels-of-ballroom-dancing) — what each metal demands
- [Progressing to next syllabus level (or to open)](https://www.dance-forums.com/threads/progressing-to-next-syllabus-level-or-to-open.52845/) — "Open Gold is still Gold level skill"

Levels are **not** standardised across organizers — Newcomer, Bronze, Silver,
Gold and Open do not mean the same thing everywhere. This ladder is calibrated to
the two competitions in this repo.
