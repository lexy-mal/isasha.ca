# Dance Competition Event Divisions

This document describes the different competition divisions and categories found in ballroom dance events.

Division is one of **three independent axes** on an event:
[AGE_CATEGORIES.md](AGE_CATEGORIES.md) (who may enter),
[SKILL_LEVELS.md](SKILL_LEVELS.md) (proficiency), and division (this file).

Implemented as `getEventDivision()` in `com.html`.

> ⚠️ **Classification order matters.** `Championship` is very often just title
> decoration on an event whose real division is something else — e.g.
> `L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship` is a Five Star
> event, and `G-D Closed Bronze 1 Pro-Am CLUB Salsa Championship` is a CLUB
> event. Testing the generic word first mislabelled **28 of 50** matches, so the
> specific markers (Five Star, CLUB, NATIONAL, Rising Star, Prechamp) are checked
> first and `Championship` is the last resort before `Standard`.

## Verified counts (both competitions, 3885 unique events)

| Division | Events |
|---|---|
| Standard | 3450 |
| CLUB | 288 |
| Prechamp | 55 |
| NATIONAL | 51 |
| Championship | 22 |
| Five Star | 15 |
| PRO | 4 |
| Rising Star | 0 (not present in current data) |

## Division Types

### 1. **Standard** (Regular Competition Events)
Default competition events following standard skill level progression (A-H).
- Example: "A-15- Bronze BALLROOM SOLO"
- Most common category

### 2. **NATIONAL** (National-Level Events)
Events designated for national-level competition or with national scope.
- Example: "A-16+ Ouvert / Open BALLROOM SOLO NATIONAL"
- Typically at higher skill levels (Silver, Gold)
- More participants/prestige

### 3. **Championship** (Championship Events)
Formal championship competitions, often with multiple levels.
- Example: "AC-12+ IMPERIAL CUP Amateur Open BALLROOM Championship"
- Variations: Amateur Championship, Pro-Am Championship
- Higher stakes than standard events

### 4. **Five Star**
Specialized five-dance championship format.
- Example: "Imperial Cup Pro-Am Five Star LATIN Championship"
- Dancers compete across 5 related dances (e.g., all 5 Latin dances)
- Typically at higher skill levels

### 5. **CLUB** (Club Dances)
Non-ballroom partner dances competed at dance studios.
- Examples: Salsa, Bachata, Argentine Tango, Swing
- Example: "AC-C Open Bronze 1 CLUB Salsa"
- Can have sub-levels like "Bronze 1", "Bronze 2"

### 6. **PRO** (Professional Events)
Professional-only divisions (no amateur/student participation).
- Example: "PRO BALLROOM Championnat National Canadien"
- Highest skill level
- Rarest category

### 7. **Rising Star** (Future Reference)
Entry-level national events for rising competitors.
- Not currently in database, but standard division
- Lower skill levels (Beginner, Bronze)

### 8. **Prechamp** (Pre-Championship, Future Reference)
Events that serve as qualifying or preparation for championships.
- Not currently in database
- Intermediate level between Standard and Championship

## Skill Level Modifier: "Bronze 1", "Bronze 2", etc.

Some CLUB events use sub-levels:
- Bronze 1 (earlier Bronze)
- Bronze 2 (advanced Bronze)
- Similar to Pre-Bronze, Intermediate Bronze, Full Bronze progression

## Hierarchy (Typical)

From lowest to highest prestige/difficulty:
1. Standard (Regular events)
2. Rising Star (entry-level national)
3. Prechamp (pre-championship)
4. CLUB (specialty dances)
5. NATIONAL (national-level)
6. Championship (formal championships)
7. Five Star (multi-dance championships)
8. PRO (professional-only)

**Note:** This is approximate. Some CLUB events can be quite advanced, and Rising Star events may be prestigious despite beginner skill levels.
