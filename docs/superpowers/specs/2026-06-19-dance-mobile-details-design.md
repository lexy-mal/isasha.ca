# Dance App Mobile Detail View Design

**Date:** 2026-06-19  
**Status:** Approved  
**Scope:** Improve mobile UX by showing participant details in a full-screen view instead of below the participant list

---

## Problem Statement

On mobile, when users click a participant name to see their details, the information appears in the main content area below the participant list. This requires scrolling down to see the details, making the interaction inconvenient and the content harder to discover.

## Goals

1. **Immediate visibility** — Details appear prominently without requiring scroll
2. **Full content access** — All details (stats, events, competitors) remain visible and scrollable
3. **Natural navigation** — Mobile users can seamlessly switch between participants and return to the list
4. **Consistent design** — Desktop layout unchanged; mobile gets enhanced UX only

## Design Overview

### Desktop (No Change)
- Two-column layout: sidebar list (left) + content area (right)
- Current behavior preserved

### Mobile (Breakpoint: max-width 768px)
- Clicking a participant triggers a **full-screen detail view**
- Participant list is hidden while detail view is active
- Back button returns to the list with search state preserved

---

## Mobile Detail View Structure

### Header
- **Back button** (←) — dismisses detail view, returns to participant list
- **Person name** — displayed next to back button
- **Event count** — small label showing number of events (e.g., "4 events")
- **Height:** ~56px, sticky/fixed at top
- **Styling:** Dark background (#1a1a1a), consistent with existing theme

### Scrollable Content Area
All content below the header is scrollable to ensure long competitor lists don't get cut off:

1. **Stats Grid** (unchanged styling)
   - Events, Partners, Solo, Competitors counts
   - 2 columns on mobile (vs 4 on desktop)

2. **Events List** (unchanged styling)
   - Each event shows: event name, heat label, time, competitors
   - All event details preserved

3. **Competitors List** (fully visible)
   - All competitors for each event listed
   - Partners and opponents clearly marked
   - **Key requirement:** No truncation at bottom of screen

### Transitions
- **Opening:** Fade-in animation when detail view appears
- **Closing:** Fade-out when back button is clicked
- **Smooth:** CSS transitions, 200-300ms duration

---

## Technical Implementation

### HTML Structure Changes
- Wrap existing detail content in a new container with class `.detail-overlay`
- Existing HTML structure remains unchanged; visibility controlled via CSS

### CSS Changes
- Add media query for `max-width: 768px`
- In mobile view:
  - `.detail-overlay` positioned as `fixed` full-screen layer
  - `.sidebar` and original content area hidden
  - Header positioned `sticky` at top
  - Content area scrollable with proper padding/spacing

### JavaScript Changes
- On participant click: add `active` class to `.detail-overlay` or toggle visibility
- Back button: remove `active` class, restore focus to previous participant in list
- Search state preserved during navigation

### State Management
- Track which participant is selected
- Preserve search filter when returning to list
- Clear selection when clearing search

---

## Edge Cases & Behavior

1. **Search while viewing details:** Search input remains accessible (either behind overlay or via top bar). Clicking a new result switches detail view.

2. **Return to list:** Back button restores:
   - Participant list visibility
   - Previous search filter
   - Scroll position in participant list (optional enhancement)

3. **Empty results:** If search yields no results, detail view closes automatically.

4. **Orientation change:** On mobile, changing from portrait to landscape (or vice versa) should smoothly adapt the layout.

---

## Success Criteria

- [ ] Participant details appear in full-screen view on mobile without scrolling the page
- [ ] All competitors are visible and scrollable within the detail view
- [ ] Back button smoothly returns to the participant list
- [ ] Search state is preserved when navigating between participants
- [ ] Desktop layout remains unchanged
- [ ] Animation is smooth (no jank)
- [ ] Responsive behavior tested on common mobile sizes (375px, 414px, 768px breakpoint)

---

## Files to Modify

- `public/projects/dance.html` — add CSS media queries, update HTML structure, add/modify JS handlers

---

## Timeline

- Implementation: 1 development session
- Testing: Manual testing on mobile devices/browser dev tools
