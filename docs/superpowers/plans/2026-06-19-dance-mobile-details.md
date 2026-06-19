# Dance Mobile Detail View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display participant details in a full-screen overlay on mobile instead of inline below the participant list, improving UX and making all details (especially competitors) easily accessible.

**Architecture:** Modify the existing single-file HTML structure to add a CSS media query that repositions the detail content into a fixed full-screen overlay when on mobile (max-width: 768px). JavaScript manages the overlay state (show/hide) and back button navigation. Desktop layout remains unchanged. The detail content scrolls within the overlay to ensure all competitors and events are visible without page-level scrolling.

**Tech Stack:** Vanilla JavaScript, CSS media queries, no new dependencies

---

## File Structure

**Modified:**
- `public/projects/dance.html` — Add CSS media query rules, update HTML structure with overlay wrapper, enhance JS with overlay state management

---

## Implementation Tasks

### Task 1: Add HTML Structure for Detail Overlay

**Files:**
- Modify: `public/projects/dance.html:476-481` (content-area div)

**Context:** The existing `content-area` div displays details. We'll wrap it in a new `.detail-overlay` container and add a header with back button.

- [ ] **Step 1: Read the current content-area structure**

Open `public/projects/dance.html` and locate the `<div class="content-area">` (around line 476). The structure is:
```html
<div class="content-area">
    <div id="contentDisplay">
        <div class="loading">Loading data...</div>
    </div>
</div>
```

- [ ] **Step 2: Replace with overlay container structure**

Replace the `content-area` div with:

```html
<div class="detail-overlay">
    <div class="detail-header">
        <button class="detail-back-btn" onclick="closeDetailView()">←</button>
        <div class="detail-header-info">
            <div class="detail-person-name" id="detailPersonName"></div>
            <div class="detail-event-count" id="detailEventCount"></div>
        </div>
    </div>
    <div class="detail-content" id="contentDisplay">
        <div class="loading">Loading data...</div>
    </div>
</div>
```

**Why:** This structure provides:
- Header container with back button and person info
- Separate detail-content scrollable area
- IDs for JS to update header text
- Clear separation of concerns

- [ ] **Step 3: Verify HTML structure**

Check that the new `<div class="detail-overlay">` and nested elements are properly placed. The `id="contentDisplay"` moves into `.detail-content` so existing JS continues to work.

- [ ] **Step 4: Commit**

```bash
git add public/projects/dance.html
git commit -m "feat: add overlay HTML structure for mobile detail view"
```

---

### Task 2: Add CSS Styles for Desktop (Default)

**Files:**
- Modify: `public/projects/dance.html:450` (end of `<style>` section, before media queries)

**Context:** Add base CSS for the overlay elements. On desktop, the overlay should be hidden and the layout unchanged.

- [ ] **Step 1: Add base detail-overlay styles**

Before the existing `@media (max-width: 1024px)` query, add:

```css
/* Detail overlay - hidden by default (desktop view) */
.detail-overlay {
    display: none;
}

.detail-header,
.detail-back-btn,
.detail-header-info,
.detail-person-name,
.detail-event-count {
    display: none;
}
```

**Why:** Desktop keeps the current layout. The overlay elements exist in HTML but are hidden via CSS.

- [ ] **Step 2: Verify styles don't affect desktop layout**

Save and check in a desktop browser that the page layout hasn't changed—content-area should still display on the right side next to the sidebar.

- [ ] **Step 3: Commit**

```bash
git add public/projects/dance.html
git commit -m "feat: add base CSS for detail overlay (hidden on desktop)"
```

---

### Task 3: Add Mobile Media Query Styles

**Files:**
- Modify: `public/projects/dance.html:430` (update the existing `@media (max-width: 1024px)` block)

**Context:** Replace the desktop media query with mobile-specific rules that show the overlay as full-screen.

- [ ] **Step 1: Locate the existing media query**

Find `@media (max-width: 1024px)` around line 412. This is where mobile styles are defined.

- [ ] **Step 2: Update media query to max-width 768px**

Change the breakpoint from 1024px to 768px to provide more room on tablets for the two-column layout:

```css
@media (max-width: 768px) {
```

- [ ] **Step 3: Add detail-overlay styles inside the media query**

After the existing `.main-content` and `.sidebar` rules, add:

```css
/* Mobile detail overlay styles */
.detail-overlay {
    display: none; /* Hidden by default */
    position: fixed;
    inset: 0;
    background: var(--bg-primary);
    z-index: 1000;
    flex-direction: column;
}

.detail-overlay.active {
    display: flex;
}

.detail-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--bg-tertiary);
    position: sticky;
    top: 0;
    z-index: 1001;
    flex-shrink: 0;
}

.detail-back-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: transparent;
    border: none;
    color: var(--accent);
    font-size: 20px;
    cursor: pointer;
    transition: opacity 0.2s ease;
    flex-shrink: 0;
}

.detail-back-btn:active {
    opacity: 0.7;
}

.detail-header-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-width: 0; /* Allow text truncation */
}

.detail-person-name {
    display: block;
    font-size: 1em;
    font-weight: 600;
    color: var(--accent);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.detail-event-count {
    display: block;
    font-size: 0.75em;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.detail-content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
}

/* Hide sidebar and main-content when overlay is active */
.detail-overlay.active ~ .main-content,
.detail-overlay.active ~ .sidebar {
    display: none;
}
```

**Why:**
- `position: fixed; inset: 0;` makes the overlay full-screen
- `.active` class toggles visibility
- Header is sticky so back button stays accessible while scrolling
- Content area is flex and scrollable
- iOS smooth scrolling enabled

- [ ] **Step 4: Verify mobile styles**

Save and test on mobile viewport (375px width in browser dev tools):
- Overlay should not be visible yet (no `.active` class)
- Layout should show sidebar above content (single column)

- [ ] **Step 5: Commit**

```bash
git add public/projects/dance.html
git commit -m "feat: add mobile media query styles for detail overlay"
```

---

### Task 4: Add JavaScript Function to Show/Hide Overlay

**Files:**
- Modify: `public/projects/dance.html:533-537` (selectParticipant function)

**Context:** Update the `selectParticipant` function to show the detail overlay on mobile and update header text.

- [ ] **Step 1: Locate selectParticipant function**

Find the function around line 533:
```javascript
function selectParticipant(name, element) {
    document.querySelectorAll('.participant-item').forEach(el => el.classList.remove('active'));
    if (element) element.classList.add('active');
    displayPersonDetails(name);
}
```

- [ ] **Step 2: Add overlay opening logic**

Replace the function with:

```javascript
function selectParticipant(name, element) {
    document.querySelectorAll('.participant-item').forEach(el => el.classList.remove('active'));
    if (element) element.classList.add('active');
    
    // Show overlay on mobile
    const overlay = document.querySelector('.detail-overlay');
    if (window.innerWidth <= 768) {
        overlay.classList.add('active');
    }
    
    // Update header text
    const entryCount = participantsData[name].entries.length;
    document.getElementById('detailPersonName').textContent = name;
    document.getElementById('detailEventCount').textContent = `${entryCount} event${entryCount !== 1 ? 's' : ''}`;
    
    displayPersonDetails(name);
}
```

**Why:**
- Checks viewport width to determine if on mobile
- Adds `.active` class to show overlay
- Updates header with person name and event count

- [ ] **Step 3: Test the function exists and is called**

Search for other calls to `selectParticipant` (line 664 in `searchAndSelect`). Verify it's called in two places:
1. From participant list click
2. From competitor name click in `searchAndSelect`

Both should trigger the overlay on mobile.

- [ ] **Step 4: Commit**

```bash
git add public/projects/dance.html
git commit -m "feat: add JavaScript to show overlay on mobile"
```

---

### Task 5: Add JavaScript Function to Close Overlay

**Files:**
- Modify: `public/projects/dance.html:672-677` (clearSearch function area)

**Context:** Add a new `closeDetailView()` function and update `clearSearch()` to close the overlay.

- [ ] **Step 1: Add closeDetailView function**

Before the `clearSearch()` function (around line 672), add:

```javascript
function closeDetailView() {
    const overlay = document.querySelector('.detail-overlay');
    overlay.classList.remove('active');
}
```

**Why:** This function is called by the back button (from HTML: `onclick="closeDetailView()"`)

- [ ] **Step 2: Update clearSearch to close overlay**

Locate the `clearSearch()` function and update it:

```javascript
function clearSearch() {
    document.getElementById('searchInput').value = '';
    displayParticipants();
    closeDetailView(); // Close overlay when clearing search
    document.getElementById('contentDisplay').innerHTML =
        '<div class="no-results"><div class="no-results-icon">→</div><div>Select a participant</div></div>';
}
```

**Why:** Clearing search should close the detail view and show the empty state.

- [ ] **Step 3: Verify closeDetailView is called from back button**

Confirm that the HTML back button has `onclick="closeDetailView()"`. It should from Task 1.

- [ ] **Step 4: Commit**

```bash
git add public/projects/dance.html
git commit -m "feat: add closeDetailView function and update clearSearch"
```

---

### Task 6: Add Smooth Transitions

**Files:**
- Modify: `public/projects/dance.html:430-450` (detail-overlay CSS)

**Context:** Add CSS transitions for smooth fade-in/fade-out of the overlay.

- [ ] **Step 1: Update detail-overlay CSS with transition**

In the `.detail-overlay` base rule (added in Task 2), update to:

```css
.detail-overlay {
    display: none;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.detail-overlay.active {
    display: flex;
    opacity: 1;
}
```

**Why:** Fade transition (opacity 0 → 1) over 300ms creates smooth appearance.

- [ ] **Step 2: Add header and content transitions**

In the media query (Task 3), add:

```css
.detail-header {
    animation: slideDown 0.3s ease;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.detail-content {
    animation: fadeIn 0.3s ease 0.1s both;
}

@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}
```

**Why:** Header slides down slightly, content fades in with a stagger, creating a smooth entrance.

- [ ] **Step 3: Test transitions in mobile view**

- Open in mobile viewport (375px)
- Click a participant
- Observe smooth fade-in and slide animation (should take ~300ms)
- Click back button
- Observe smooth fade-out

- [ ] **Step 4: Commit**

```bash
git add public/projects/dance.html
git commit -m "feat: add smooth fade/slide transitions for overlay"
```

---

### Task 7: Handle Orientation Change and Resize

**Files:**
- Modify: `public/projects/dance.html:680` (after loadData call)

**Context:** Add a resize listener to close the overlay when switching from mobile to desktop view.

- [ ] **Step 1: Add resize event listener**

Before the `loadData()` call at the end of the script (line 680), add:

```javascript
// Close overlay when resizing above mobile breakpoint
window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
        const overlay = document.querySelector('.detail-overlay');
        overlay.classList.remove('active');
    }
});
```

**Why:** If user rotates device from portrait to landscape (or resizes browser), overlay closes and two-column layout is restored.

- [ ] **Step 2: Test resize behavior**

- Open in mobile view with a detail overlay shown
- Resize/rotate to desktop width (> 768px)
- Overlay should disappear and sidebar should reappear

- [ ] **Step 3: Commit**

```bash
git add public/projects/dance.html
git commit -m "feat: close overlay on resize above mobile breakpoint"
```

---

### Task 8: Test All Interactions

**Files:**
- Test: Manual testing, no automated tests for HTML project

**Testing Checklist:**

- [ ] **Step 1: Desktop (1200px+ viewport)**

- Open dance.html in desktop viewport
- Verify two-column layout (sidebar + content) is unchanged
- Click participants in list
- Verify details appear on right side (no overlay)
- Search and filter work as before
- No visual regressions

- [ ] **Step 2: Tablet (768px - 1024px viewport)**

- Resize to 768px
- Verify switch to single-column layout
- Click a participant
- **Expected:** Sidebar hides, detail overlay shows with back button
- Verify header shows participant name and event count
- Scroll through all competitors
- All competitors are visible (not cut off at bottom)
- Click back button
- **Expected:** Overlay closes, sidebar reappears with participant still selected
- Verify previous search filter is preserved

- [ ] **Step 3: Mobile (375px viewport)**

- Resize to 375px (iPhone size)
- Search for a participant
- Click their name
- **Expected:** Full-screen overlay with:
  - Back button top-left
  - Person name + event count top-right
  - Scrollable detail content
- Scroll down to see all stats, events, competitors
- Verify smooth scroll with no jank
- Click back button
- **Expected:** Overlay fades out smoothly, sidebar reappears
- Search input is still visible and populated

- [ ] **Step 4: Transition animation test**

- Open mobile view
- Click a participant
- Watch for smooth fade-in (should not be instant)
- Click back button
- Watch for smooth fade-out
- Estimate: should take ~300ms total

- [ ] **Step 5: Orientation change test**

- Open in mobile portrait (375px)
- Show detail overlay
- Rotate/resize to landscape (667px or wider)
- **Expected:** Overlay closes, two-column layout appears (if > 768px), or single-column if still < 768px

- [ ] **Step 6: Edge cases**

- **Empty search:** Search for a name, click detail, close overlay, clear search → sidebar reappears with results cleared
- **Click competitor:** In detail view, click a competitor name → overlay closes, new participant detail loads
- **Scroll preservation:** Open detail, scroll down to bottom, go back, reopen same participant → starts at top (acceptable)

- [ ] **Step 7: Accessibility check**

- Back button is keyboard accessible (should be a button, not a span)
- Overlay closes on Escape key (optional enhancement, not in spec)

- [ ] **Step 8: Final commit with test results**

```bash
git commit --allow-empty -m "test: manual testing complete for mobile detail overlay

Tested on:
- Desktop (1200px+): Layout unchanged, no regressions
- Tablet (768px-1024px): Overlay appears/closes correctly
- Mobile (375px): Full-screen overlay works, all content scrollable
- Transitions: Smooth fade/slide animations
- Orientation: Overlay closes on resize > 768px
- Edge cases: Search state preserved, competitor clicks work
✓ All success criteria met"
```

---

### Task 9: Final Review and Polish

**Files:**
- Modify: `public/projects/dance.html` (final review)

- [ ] **Step 1: Check for any console errors**

Open browser dev tools (F12), go to Console tab, and reload the page. Verify:
- No JavaScript errors
- No CSS warnings
- Network tab shows all assets load

- [ ] **Step 2: Verify media query breakpoints**

Confirm:
- `@media (max-width: 768px)` is used for mobile styles
- Desktop is default (no media query required)
- Tablet (768px-1024px) shows single-column with overlay support

- [ ] **Step 3: Check CSS variable usage**

Verify all new CSS uses theme variables:
- `var(--bg-primary)`, `var(--bg-secondary)`, `var(--bg-tertiary)`
- `var(--text-primary)`, `var(--text-secondary)`
- `var(--accent)`

No hardcoded colors (should all be vars).

- [ ] **Step 4: Verify no unwanted side effects**

- Desktop view: completely unchanged
- Previous mobile (1024px breakpoint): now uses new overlay
- All existing JS functions still work
- Search/filter unaffected

- [ ] **Step 5: Final commit**

```bash
git add public/projects/dance.html
git commit -m "feat: complete mobile detail view implementation

Implements full-screen detail overlay on mobile (max-width: 768px):
- Clicking a participant shows details in fixed full-screen view
- Header with back button, name, and event count
- Scrollable content showing all stats, events, and competitors
- Smooth fade/slide transitions (300ms)
- Overlay closes on back button or resize > 768px
- Desktop layout unchanged
- Search state preserved during navigation

All success criteria met:
✓ Details appear in full-screen view without page scroll
✓ All competitors visible and scrollable
✓ Back button smoothly returns to participant list
✓ Search state preserved
✓ Desktop unchanged
✓ Smooth animations
✓ Tested on mobile, tablet, desktop viewports

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Summary

**9 tasks total:**
1. HTML structure (overlay wrapper, header, back button)
2. Base CSS (hide overlay on desktop)
3. Mobile media query styles (full-screen positioning)
4. Show overlay JS (selectParticipant update)
5. Close overlay JS (new closeDetailView function)
6. Smooth transitions (CSS animations)
7. Resize handler (close overlay > 768px)
8. Manual testing (all viewports and interactions)
9. Final review and polish

**Expected duration:** 2-3 hours for full implementation + testing

**Key files modified:** Only `public/projects/dance.html` (single file)

**Rollback safety:** All changes in one file, easy to revert if needed
