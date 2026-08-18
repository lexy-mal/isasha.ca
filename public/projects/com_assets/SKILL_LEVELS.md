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
| 1 | Bronze | |
| 2 | Silver | `Silver`, `Argent` |
| 3 | Gold | `Gold` (`Or` always paired) |
| 4 | Novice | Amateur ladder |
| 5 | Pre-Championship | `Pre-Champ` |
| 6 | Open | **Only when no metal is named** — see below |
| 7 | Five Star | Multi-dance championship tier |
| — | *unranked* | Showcases, `Challenge Cup`, `Grand Trophy`. Sort **last in both directions** |

### Why "Open" is both a modifier and a level

Per USA Dance, the progression is *Pre-Bronze, Bronze, Open Bronze, Silver, Open
Silver, Gold, Open Gold* — so **`Open` is normally a modifier, not a rank**:
"Open Gold is still Gold level skill, it simply is not restricted to syllabus
steps." Dancers then graduate past the syllabus into standalone Open events.

So the parser resolves it by precedence: **a named metal always wins**.
`Open Bronze` ranks as Bronze (1), with Open recorded as a modifier. Rank 6 is
reached only when the event names no metal at all (`A-15- Ouvert / Open BALLROOM
SOLO`) — the graduated post-syllabus tier.

This is why evaluation order ≠ rank order. `SKILL_LEVEL_LOOKUP_ORDER` checks
`[7, 5, 4, 0, 1, 2, 3, 6]`, testing bare Open last.

### Tiebreaks within a rank

Sorted by `(rank, sublevel, openRank)`:

1. **`sublevel`** — trailing digit in `Bronze 1` / `Bronze 2` / `Bronze 3`.
2. **`openRank`** — Closed (0) before Open (1), matching *Bronze, Open Bronze,
   Silver*.

## Verified output

Ascending sort is monotonic by rank across **all** events in both competitions
(2661 national2026, 1224 impercup2026), checked in-browser. The distinct ladder
Imperial Cup actually produces:

```
Newcomer (Closed) → Newcomer (Open) → Newcomer 1 → Newcomer 2
Bronze (Closed) → Bronze (Open) → Bronze 1 → Bronze 2 → Bronze 3
Silver (Closed) → Silver (Open) → Silver 1 → Silver 2
Gold (Closed) → Gold (Open) → Gold 1 → Gold 2
Novice 1 → Novice 2 → Pre-Championship → Open → Five Star → unranked
```

Coverage: **3622 / 3885 events (93%)** carry a recognisable level. The 263
unranked are genuinely levelless — showcase titles (`"Americano"`,
`"Caribbean Blue" - Ballet`) and `Challenge Cup` / `Grand Trophy` events.

## Caveat on merging two ladders

Ranks 0–3 (Newcomer→Gold) are the **Pro-Am syllabus** ladder; ranks 4–5
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
