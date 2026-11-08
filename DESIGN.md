---
name: LocalFlow
description: Neutral, quiet UI for a local dictation app that stays out of the way
colors:
  primary: "#7cb0ff"
  neutral-ground: "#18181a"
  neutral-raised: "#232326"
  neutral-line: "#36363b"
  neutral-text: "#ececee"
  neutral-dim: "#a3a3ab"
typography:
  body:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "21px"
  title:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: "18px"
  label:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: "18px"
  oval-message:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 400
rounded:
  sm: "4px"
  md: "8px"
  full: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "20px"
components:
  search-input:
    backgroundColor: "{colors.neutral-raised}"
    textColor: "{colors.neutral-text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    height: "36px"
  entry-row:
    textColor: "{colors.neutral-text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  entry-row-hover:
    backgroundColor: "{colors.neutral-raised}"
  day-label:
    backgroundColor: "{colors.neutral-ground}"
    textColor: "{colors.neutral-text}"
    typography: "{typography.title}"
    padding: "6px 12px"
  action-copy:
    textColor: "{colors.neutral-text}"
    typography: "{typography.label}"
    height: "28px"
  action-copied:
    textColor: "{colors.primary}"
    typography: "{typography.label}"
    height: "28px"
  action-delete:
    textColor: "{colors.neutral-dim}"
    typography: "{typography.label}"
    height: "28px"
  tag-uncleaned:
    textColor: "{colors.neutral-dim}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 6px"
  oval:
    backgroundColor: "{colors.neutral-ground}"
    textColor: "{colors.neutral-text}"
    rounded: "{rounded.full}"
    height: "32px"
    padding: "0 14px"
  oval-button:
    textColor: "{colors.neutral-dim}"
    rounded: "{rounded.full}"
    size: "26px"
  oval-button-finish:
    textColor: "{colors.primary}"
    rounded: "{rounded.full}"
    size: "26px"
---

# Design System: LocalFlow

Direction C from the design spike (`spikes/design`, route `/c`), plus always-visible Copy, stronger day labels and capped line length. There is one look and no themes.

## Overview

**Creative North Star: "Out of the Way"**

LocalFlow is used while attention is on another app, so the interface earns its calm by asking for nothing. The Oval appears only while it has something to say. The History window is opened to find and copy words, then closed.

Typography and spacing do the work. Colour is neutral graphite with one soft blue accent that marks only what is active or just confirmed. Convention is the commitment: patterns should feel familiar from Raycast, Linear and Wispr Flow, and from Windows itself.

**Key Characteristics:**
- Dark neutral ground, chosen because the app sits beside terminals and editors.
- The Windows system font, so no fonts are bundled.
- Rows separated by space, without cards or dividers.
- Motion only answers a state change, and stays quick.

## Colors

Neutral graphite with a single soft blue accent.

### Primary
- **Soft Signal Blue** (#7cb0ff): the caret, focus rings, text selection, search matches, "Copied" and the Oval's ✓. Nothing else.

### Neutral
- **Graphite Ground** (#18181a): the History window and the Oval.
- **Raised Graphite** (#232326): the search box, row hover and the key cap in the empty state.
- **Quiet Line** (#36363b): the search box border, the "uncleaned" tag border, the key cap border and the scrollbar thumb.
- **Near White** (#ececee): Entry text, day labels and Copy.
- **Soft Grey** (#a3a3ab): time, Target app, placeholder, the empty state line and Delete.

**The One Accent Rule.** Blue means active or just confirmed. It never decorates, and "uncleaned" and errors do not use it.

## Typography

**Body Font:** Segoe UI Variable Text (with Segoe UI, then sans-serif)

**Character:** The platform's own face. It reads as part of Windows and costs nothing to load.

### Hierarchy
- **Title** (600, 13px, 18px): day labels. They are landmarks in a list of up to 200 Entries, so they use Near White, unlike the Soft Grey metadata.
- **Body** (400, 14px, 21px): Entry text, search and the empty state. Lines are capped at about 75 characters.
- **Label** (400, 12px, 18px): time, Target app, tag, Copy and Delete. Times use tabular numerals.
- **Oval message** (400, 13px): the Oval's one line of text.

**The 75 Character Rule.** Entry text and its metadata row share a maximum width of 62ch, which is about 75 characters of this face at 14px (measured on the spike's sample text, because `ch` is the width of a zero and running text is narrower). The rest of a wide window stays empty.

## Layout

The History window is one column: the search box pinned at the top, then the scrolling list, newest first. Outer padding is 12px. Text is left-aligned.

- **Day groups:** a label sticks to the top of the list while its group scrolls, with 20px above it and 6px below.
- **Entries:** Entry text, then a metadata row of time, Target app and any tag, with actions at the end of the row. Text clamps to two lines and expands on click.
- **Narrow windows:** the metadata row wraps, and actions are never pushed out of view.
- **Empty state:** one line, centred in the list area.
- **The Oval:** bottom centre of the main screen, just above the taskbar.

## Elevation & Depth

Flat by default. Depth comes from tone: Raised Graphite on Graphite Ground, with no shadows in the History window beyond the one Windows draws. Only the Oval casts a shadow, because it floats over other apps.

### Shadow Vocabulary
- **Oval float** (`box-shadow: 0 0 0 1px rgb(255 255 255 / 0.14), 0 1px 4px rgb(0 0 0 / 0.3)`): a thin ring that holds its edge on dark apps, and a soft shadow that lifts it off light ones. The shadow stays inside the 6px margin of the Oval window (ADR-0003), so it never meets the window edge.

## Shapes

Gently rounded rows and fields (8px), small tags and key caps (4px), and a fully round Oval. No nested containers.

## Components

### Search box
- **Style:** Raised Graphite with a Quiet Line border, a 14px magnifier inside the left edge, and a placeholder of "Search history".
- **Focus:** the border turns Soft Signal Blue, and the caret is the same colour.

### Entry row
- **Style:** no fill at rest; Raised Graphite on hover, fading over 100ms.
- **Copy:** always visible, in Near White. It is why the window is open.
- **Delete:** Soft Grey, set apart from Copy, and shown only on row hover or keyboard focus. Layout space is reserved so nothing shifts.
- **Copied:** the Copy label swaps for about 1.4s in Soft Signal Blue, including under the pointer.
- **Tag:** "uncleaned" in Soft Grey with a Quiet Line border, and no accent.

### Empty state
One line in Soft Grey with the configured Hotkey in a key cap, for example "Hold `Right Ctrl` and speak".

### The Oval
The window never takes focus. Only ✕ and ✓ take clicks.
- **Listening:** 7 thin bars (2.5px wide, 3px gap) between 3px and 16px tall, following the Engine's level with 90ms linear transitions.
- **Hands-free:** the same, with ✕ in Soft Grey and ✓ in Soft Signal Blue, each with a 26px target.
- **Processing:** the same bars settle into 3 round 5px dots over 260ms (`cubic-bezier(0.16, 1, 0.3, 1)`). The dots then pulse in sequence on an 1100ms cycle.
- **Message:** one line of Near White text in the same shape, which widens to fit. See Wording.
- **Reduced motion:** bars hold still and dots stop pulsing.

## Do's and Don'ts

### Do:
- **Do** morph the same elements from bars to dots rather than swapping them.
- **Do** keep every action's layout space reserved, so hover never shifts a row.
- **Do** show the Oval only while it has something to say.

### Don't:
- **Don't** add a second accent, or use blue for decoration.
- **Don't** add cards, dividers between rows, or shadows in the History window.
- **Don't** give Delete the same emphasis as Copy.
- **Don't** add entrance animations or hover effects beyond the row fill.

## Rules for T8

The spike doesn't do these, so don't copy its behaviour on these points.

1. **Delete can't fire twice.** After a delete, ignore Delete until the pointer moves or about 400ms has passed, because the next row can land under the pointer. Add a collapse of about 120ms, and make the Copy and Delete targets 28px tall. Delete stays immediate, with no confirmation or undo.
2. **Search shows its match.** While a query is active, mark the match in Soft Signal Blue, and expand or clamp around it so the match is never hidden by the two-line clamp.
3. **The keyboard comes first.** Focus search when the window opens, make the list one Tab stop with arrow keys between Entries, and have Enter copy the selected Entry. No Delete-key shortcut.
4. **Entry text is text.** Render it as selectable text with a separate expand toggle only when it overflows, and don't toggle when a selection was made. Give actions full names for screen readers, such as "Copy: Running ten minutes late…".
5. **"Copied" means copied.** Show it only after the clipboard write succeeds.

## Wording

- **Oval errors name the fix,** for example "Ollama isn't running. Start Ollama and try again."
- **The "uncleaned" tag has a tooltip:** "Cleanup didn't finish, so this is the raw transcript."
- **Loading states are one line each in the Oval:** "Starting up…" and "Downloading speech model…".
