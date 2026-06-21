# Heat Countdown Feature Design
**Date:** 2026-06-21  
**Feature:** Per-participant countdown to next heat in detail view  
**File:** `public/projects/dance.html`

---

## Overview

Add a real-time countdown timer to the detail view header that shows when the selected participant's next heat is starting. The countdown updates every minute and displays in the detail header info section (below event count).

---

## Requirements

### Functional Requirements

1. **Per-Participant Countdown**
   - Show countdown only for the currently selected participant
   - Countdown is specific to their next upcoming heat

2. **Display Location**
   - Always visible in detail view header
   - Third line in `detail-header-info` container (below person name and event count)
   - Styled with accent color for visibility

3. **Update Frequency**
   - Update every 60 seconds (once per minute)
   - Fresh calculation each update to reflect passing time

4. **Time Parsing**
   - Parse heat times in format: `HH:MMAM/PM DayName` (e.g., "03:38PM Sunday")
   - Use browser's current date/time as reference
   - Calculate next occurrence of that day/time from today

5. **Edge Cases**
   - **Upcoming heat:** Display as "🕐 Next: Heat XXX in N mins"
   - **Heat < 1 min away:** Display as "🕐 Next: Heat XXX in <1 min"
   - **Heat starting now:** Display as "🕐 Next: Heat XXX starting now!"
   - **No upcoming heats:** Display as "✓ All events completed"

### Non-Functional Requirements

- No external dependencies (use browser Date API only)
- Efficient: single timer for all countdowns, not per-heat
- Graceful handling of edge cases (invalid times, missing data)

---

## Technical Design

### Time Calculation Logic

```javascript
function getNextHeatTime(entries) {
  // 1. Extract all heat times from participant entries
  const heatTimes = entries.map(entry => parseHeatTime(entry.time));
  
  // 2. For each heat, calculate next occurrence
  const upcomingHeats = heatTimes
    .map(ht => calculateNextOccurrence(ht))
    .filter(ht => ht > now)
    .sort((a, b) => a - b);
  
  // 3. Return earliest upcoming heat
  return upcomingHeats[0];
}

function parseHeatTime(timeString) {
  // Input: "03:38PM Sunday" or "06:54PM Sunday Later rounds: 5@07:07PM Sunday"
  // Extract: hour, minute, AM/PM, day name
  // Return: { hour, minute, meridiem, dayName }
}

function calculateNextOccurrence(parsedTime) {
  // Input: { hour: 3, minute: 38, meridiem: "PM", dayName: "Sunday" }
  // Logic:
  //   - Get index of dayName (0=Sunday, 1=Monday, ..., 6=Saturday)
  //   - Get today's day index
  //   - If today matches AND current time < heat time → use today
  //   - Otherwise → add days until next occurrence of that day
  // Return: Date object for next occurrence
}
```

### Update Mechanism

1. Create a single timer on page load: `setInterval(updateCountdown, 60000)`
2. Timer runs `updateCountdown()` every 60 seconds
3. `updateCountdown()` recalculates countdown for currently visible participant
4. Update DOM with new countdown text
5. Timer continues even when detail view is closed (no-op if no participant selected)

### DOM Structure

**Current detail header:**
```html
<div class="detail-header">
  <button class="detail-back-btn">←</button>
  <div class="detail-header-info">
    <div class="detail-person-name">Alice Smith</div>
    <div class="detail-event-count">5 events</div>
  </div>
</div>
```

**With countdown:**
```html
<div class="detail-header">
  <button class="detail-back-btn">←</button>
  <div class="detail-header-info">
    <div class="detail-person-name">Alice Smith</div>
    <div class="detail-event-count">5 events</div>
    <div class="detail-next-heat">🕐 Next: Heat 351 in 12 mins</div>
  </div>
</div>
```

### CSS Styling

Add to `<style>` section:
```css
.detail-next-heat {
  display: none;
  font-size: 0.9em;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 4px;
}

@media (max-width: 1024px) {
  .detail-next-heat {
    display: block;
  }
}
```

---

## Implementation Tasks

1. **Add helper functions** (in `<script>` section):
   - `parseHeatTime(timeString)` - extract hour, minute, AM/PM, day
   - `calculateNextOccurrence(parsedTime)` - find next occurrence date
   - `getNextHeatForPerson(personData)` - get next heat + time
   - `formatCountdown(nextHeatTime)` - format as "N mins" or "starting now" etc.

2. **Initialize countdown timer** on page load:
   - `setInterval(updateDetailCountdown, 60000)` 
   - Call immediately on first load (no 60s wait)

3. **Update on participant selection**:
   - Call `updateDetailCountdown()` immediately when `selectParticipant()` is called
   - Ensures countdown shows instantly, not after 60s

4. **Add countdown element to DOM**:
   - In `selectParticipant()`, create/update `<div class="detail-next-heat">`
   - Insert into `detail-header-info` container

5. **Handle all edge cases**:
   - Invalid time formats → skip that heat
   - Past dates → filter out
   - No upcoming heats → show completion message

---

## Testing Scenarios

1. **Upcoming heat in N minutes** → verify countdown displays and decreases
2. **Heat starting now** → verify "starting now!" message shows
3. **Last event just completed** → verify "All events completed" shows
4. **Participant with multiple heats** → verify showing earliest heat
5. **Navigate between participants** → verify countdown updates instantly
6. **Time passes to next minute** → verify countdown updates (not just on interval)

---

## Success Criteria

- ✓ Countdown appears in detail header for any selected participant
- ✓ Time is accurate (matches actual next heat time)
- ✓ Updates every 60 seconds with fresh calculation
- ✓ Handles all edge cases gracefully (no errors, meaningful display)
- ✓ No performance impact (single global timer, efficient calculations)
- ✓ Responsive: works on mobile and desktop detail views
