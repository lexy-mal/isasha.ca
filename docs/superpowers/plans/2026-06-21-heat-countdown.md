# Heat Countdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real-time countdown timer in the detail view header showing when a participant's next heat starts, updating every 60 seconds.

**Architecture:** Add three helper functions to parse and calculate heat times, initialize a global 60-second timer on page load, and update the countdown DOM element whenever a participant is selected or the timer fires.

**Tech Stack:** Vanilla JavaScript (Date API), no external dependencies. Modifying `public/projects/dance.html` only.

---

## File Structure

### Modified Files
- **`public/projects/dance.html`** (Main implementation)
  - Add CSS rule for `.detail-next-heat` styling
  - Add three helper functions: `parseHeatTime()`, `calculateNextOccurrence()`, `getNextHeatForPerson()`
  - Add `updateDetailCountdown()` function
  - Add format helper: `formatCountdownTime()`
  - Initialize global timer in `loadData()`
  - Call countdown update in `selectParticipant()`
  - Create DOM element for countdown in `selectParticipant()`

---

## Implementation Tasks

### Task 1: Add CSS Styling for Countdown Element

**Files:**
- Modify: `public/projects/dance.html` (in `<style>` section, after line 645)

- [ ] **Step 1: Add CSS rule for countdown display**

In the `<style>` section, after the last media query closing brace (around line 645), add:

```css
        .detail-next-heat {
            display: none;
            font-size: 0.9em;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 4px;
            font-weight: 500;
        }

        @media (max-width: 1024px) {
            .detail-next-heat {
                display: block;
            }
        }
```

- [ ] **Step 2: Verify styling in browser** (after full implementation)

---

### Task 2: Add Helper Function - Parse Heat Time

**Files:**
- Modify: `public/projects/dance.html` (in `<script>` section, before `trackEvent()` function)

- [ ] **Step 1: Add parseHeatTime() helper function**

After the `formatName()` function (around line 722), add:

```javascript
        // Parse heat time from format: "03:38PM Sunday" or "06:54PM Sunday Later rounds: 5@07:07PM Sunday"
        function parseHeatTime(timeString) {
            if (!timeString) return null;
            
            // Match first occurrence of HH:MMAM/PM DayName
            const match = timeString.match(/(\d{1,2}):(\d{2})(AM|PM)\s+(\w+)/);
            if (!match) return null;
            
            return {
                hour: parseInt(match[1]),
                minute: parseInt(match[2]),
                meridiem: match[3],
                dayName: match[4]
            };
        }
```

- [ ] **Step 2: Test parsing works** (visual inspection in browser console later)

---

### Task 3: Add Helper Function - Calculate Next Occurrence

**Files:**
- Modify: `public/projects/dance.html` (in `<script>` section, after parseHeatTime)

- [ ] **Step 1: Add calculateNextOccurrence() helper function**

After `parseHeatTime()`, add:

```javascript
        // Calculate next occurrence of a day/time combination
        function calculateNextOccurrence(parsedTime) {
            if (!parsedTime) return null;
            
            const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            const targetDayIndex = days.indexOf(parsedTime.dayName);
            
            if (targetDayIndex === -1) return null;
            
            const now = new Date();
            const todayIndex = now.getDay();
            
            // Convert to 24-hour format
            let hour = parsedTime.hour;
            if (parsedTime.meridiem === 'PM' && hour !== 12) {
                hour += 12;
            } else if (parsedTime.meridiem === 'AM' && hour === 12) {
                hour = 0;
            }
            
            // Create date for target day/time
            const result = new Date(now);
            result.setHours(hour, parsedTime.minute, 0, 0);
            
            // Calculate days to add
            let daysToAdd = targetDayIndex - todayIndex;
            if (daysToAdd < 0 || (daysToAdd === 0 && result <= now)) {
                daysToAdd += 7;
            }
            
            result.setDate(result.getDate() + daysToAdd);
            return result;
        }
```

- [ ] **Step 2: Verify logic handles edge cases** (testing in next task)

---

### Task 4: Add Helper Function - Get Next Heat for Person

**Files:**
- Modify: `public/projects/dance.html` (in `<script>` section, after calculateNextOccurrence)

- [ ] **Step 1: Add getNextHeatForPerson() helper function**

After `calculateNextOccurrence()`, add:

```javascript
        // Get next upcoming heat for a person
        function getNextHeatForPerson(personData) {
            if (!personData || !personData.entries || personData.entries.length === 0) {
                return null;
            }
            
            const now = new Date();
            const upcomingHeats = [];
            
            // Calculate next occurrence for each entry
            personData.entries.forEach(entry => {
                const parsed = parseHeatTime(entry.time);
                if (parsed) {
                    const nextTime = calculateNextOccurrence(parsed);
                    if (nextTime && nextTime > now) {
                        upcomingHeats.push({
                            heat: entry.heat,
                            time: nextTime,
                            originalTime: entry.time
                        });
                    }
                }
            });
            
            // Return earliest upcoming heat
            if (upcomingHeats.length === 0) {
                return null;
            }
            
            return upcomingHeats.sort((a, b) => a.time - b.time)[0];
        }
```

- [ ] **Step 2: Verify function returns correct data structure**

---

### Task 5: Add Helper Function - Format Countdown Time

**Files:**
- Modify: `public/projects/dance.html` (in `<script>` section, after getNextHeatForPerson)

- [ ] **Step 1: Add formatCountdownTime() helper function**

After `getNextHeatForPerson()`, add:

```javascript
        // Format countdown display text
        function formatCountdownTime(nextHeatTime) {
            if (!nextHeatTime) {
                return '✓ All events completed';
            }
            
            const now = new Date();
            const diffMs = nextHeatTime - now;
            const diffMins = Math.ceil(diffMs / 60000);
            
            if (diffMins < 1) {
                // Less than 1 minute - heat is starting now
                const heatNum = nextHeatTime.heat || '';
                return `🕐 Next: ${heatNum} starting now!`;
            } else if (diffMins === 1) {
                const heatNum = nextHeatTime.heat || '';
                return `🕐 Next: ${heatNum} in <1 min`;
            } else {
                const heatNum = nextHeatTime.heat || '';
                return `🕐 Next: ${heatNum} in ${diffMins} mins`;
            }
        }
```

- [ ] **Step 2: Test formatting with various time differences** (will test in full implementation)

---

### Task 6: Add Main Update Function - updateDetailCountdown()

**Files:**
- Modify: `public/projects/dance.html` (in `<script>` section, after formatCountdownTime)

- [ ] **Step 1: Add updateDetailCountdown() function**

After `formatCountdownTime()`, add:

```javascript
        // Update countdown display in detail header
        function updateDetailCountdown() {
            const currentName = document.getElementById('detailPersonName')?.textContent;
            if (!currentName || !participantsData[currentName]) {
                return;
            }
            
            const nextHeat = getNextHeatForPerson(participantsData[currentName]);
            const countdownText = nextHeat 
                ? formatCountdownTime(nextHeat)
                : '✓ All events completed';
            
            let countdownElement = document.getElementById('detailNextHeat');
            if (!countdownElement) {
                // Create element if it doesn't exist
                const headerInfo = document.querySelector('.detail-header-info');
                if (headerInfo) {
                    countdownElement = document.createElement('div');
                    countdownElement.id = 'detailNextHeat';
                    countdownElement.className = 'detail-next-heat';
                    headerInfo.appendChild(countdownElement);
                }
            }
            
            if (countdownElement) {
                countdownElement.textContent = countdownText;
            }
        }
```

- [ ] **Step 2: Verify function can find and update DOM elements**

---

### Task 7: Initialize Global Timer on Page Load

**Files:**
- Modify: `public/projects/dance.html` (in `loadData()` function, around line 790)

- [ ] **Step 1: Add timer initialization at end of loadData()**

In the `loadData()` function, after the closing brace of the try/catch block (around line 790), add this **before** the closing brace of the async function:

```javascript
                // Initialize countdown timer - updates every 60 seconds
                setInterval(updateDetailCountdown, 60000);
                // Call immediately on first load
                updateDetailCountdown();
```

Actually, find the exact location: After line 784 `displayParticipants();`, add before the closing `}` of the try block:

```javascript
            // Initialize countdown timer - updates every 60 seconds
            setInterval(updateDetailCountdown, 60000);
            // Call immediately on first load
            updateDetailCountdown();
```

- [ ] **Step 2: Verify timer starts without errors** (test in browser console)

---

### Task 8: Call Countdown Update on Participant Selection

**Files:**
- Modify: `public/projects/dance.html` (in `selectParticipant()` function, around line 881)

- [ ] **Step 1: Add countdown update call to selectParticipant()**

In the `selectParticipant()` function, after line 879 `addToRecentlyViewed(name);`, add:

```javascript
            // Update countdown timer immediately
            updateDetailCountdown();
```

This ensures the countdown displays instantly when a participant is selected, not waiting for the 60-second interval.

- [ ] **Step 2: Verify countdown appears when clicking participant** (browser test)

---

### Task 9: Test All Functionality

**Files:**
- Test: `public/projects/dance.html` (manual browser testing)

- [ ] **Step 1: Open dance page and load a participant**

Navigate to `/projects/dance.html`, search for a participant (e.g., "Smith"), and click to enter detail view.

**Expected:** Detail header shows person name, event count, and countdown line with clock emoji

- [ ] **Step 2: Verify countdown displays next heat correctly**

Check that countdown shows format: `🕐 Next: Heat XXX in N mins`

**Expected:** Shows correct heat number and reasonable time difference

- [ ] **Step 3: Test switching participants**

Click another participant in sidebar or search for new name.

**Expected:** Countdown updates immediately to new person's next heat

- [ ] **Step 4: Test edge case - participant with no upcoming heats**

Search for a participant (if available) with all past heats.

**Expected:** Shows `✓ All events completed`

- [ ] **Step 5: Test timer updates every minute**

Wait for 60 seconds and observe countdown number decreasing.

**Expected:** Countdown updates automatically (e.g., "12 mins" → "11 mins")

- [ ] **Step 6: Test "starting now" display**

(Optional advanced test) Modify browser time to simulate heat about to start, or wait until actual time is < 1 min away.

**Expected:** Shows `🕐 Next: Heat XXX starting now!`

---

### Task 10: Commit Implementation

**Files:**
- Modified: `public/projects/dance.html`

- [ ] **Step 1: Check git status**

```bash
git status
```

**Expected:** `public/projects/dance.html` shows as modified

- [ ] **Step 2: Review changes**

```bash
git diff public/projects/dance.html | head -100
```

**Expected:** Shows all the helper functions and timer initialization code

- [ ] **Step 3: Stage and commit**

```bash
git add public/projects/dance.html
git commit -m "feat: add per-participant heat countdown in detail header

- Add parseHeatTime() to extract hour/minute/meridiem/day from time string
- Add calculateNextOccurrence() to find next occurrence of day/time
- Add getNextHeatForPerson() to identify next upcoming heat
- Add formatCountdownTime() to format display text with edge cases
- Add updateDetailCountdown() to update DOM with current countdown
- Initialize 60-second timer on page load
- Update countdown immediately when participant selected
- Display countdown in detail header info (third line below event count)
- Handle edge cases: < 1 min, starting now, all completed

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Verify commit succeeded**

```bash
git log --oneline -1
```

**Expected:** Shows commit with message "feat: add per-participant heat countdown..."

- [ ] **Step 5: Push to GitHub**

```bash
git push git@github.com:lexy-mal/isasha.ca.git main
```

**Expected:** `To github.com:lexy-mal/isasha.ca.git ... main -> main`

---

## Notes

- **No external dependencies:** Uses only browser Date API
- **Single global timer:** All countdowns updated by one `setInterval()`, efficient
- **Graceful degradation:** If time parsing fails, that heat is skipped
- **Mobile responsive:** CSS uses media query to show/hide on mobile detail view
- **Timezone safe:** Uses browser's local time, no server-side date handling
- **Performance:** Calculation runs once per minute, minimal CPU impact

---

## Success Criteria

- ✅ Countdown appears in detail header for all participants
- ✅ Shows correct next heat and accurate time
- ✅ Updates every 60 seconds
- ✅ Handles edge cases: <1 min, starting now, all completed
- ✅ No console errors
- ✅ Works on mobile and desktop
- ✅ Code committed and pushed to GitHub
