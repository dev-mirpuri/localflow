---
status: accepted
---

# Electron oval with `focusable: false` and `showInactive()`

Spike S3 asked whether an Electron window can appear, animate and take a click without stealing focus from Notepad (Electron 44.10.2). It can, so we keep the Electron oval as the brief describes it and don't need the tkinter fallback. The pass bar is met: focus held in 20 of 20 trials. The typed text was checked per pair of trials rather than per trial, as explained below.

## Results

Hands-on results were reported by me after the runs. The numbers come from the spike's logs and the saved Notepad text in `spikes/oval/results/`, which are local and not committed.

| Check | Result | Bar |
|---|---|---|
| Foreground stayed Notepad, 20 trials | **20 out of 20**; never left Notepad | Typing keeps landing in Notepad 20 out of 20: met |
| Typed text in Notepad | **10 clean `ab` lines covering the 20 trials**; no stray `a` or `b` | |
| Oval received focus or keystrokes | 0 focus events, 0 keys | |
| ✕ and ✓ | 20 out of 20 on the first press (10 of each) | |
| Mouse presses reaching the oval in the 15 s click-through check | 0; clicks went through to Notepad, as reported | |
| Animation | Smooth, with no real flicker, as reported | |

**The drill as run:** Notepad was maximized. The oval appeared, showed level bars for 1.2 s, then showed ✕ and ✓ until clicked, then dots for 1 s, then hid for 2 s. It was the same each trial. I typed one line across each two trials: `a`, ✓ on one oval, ✕ on the next, then `b` and Enter. The instructions asked for one line per trial, so the 10 lines are this drill as I ran it and not missing trials.

**What the typed text shows:** each `b` landed after two oval clicks, so focus was in Notepad after each even trial's click. It can't show a steal that recovered before the next key, such as a steal during an odd trial. Those moments rest on the foreground log. The log doesn't record keystrokes, so the mapping of lines to trials is as reported. The saved text has no line break after the last `ab`, so the final Enter isn't in the file.

**Frame rate,** counted with `requestAnimationFrame` in the oval:

| Measure | Result |
|---|---|
| Whole run | Median 118 fps |
| Per-trial medians | 103-120 fps; 15 of 20 trials at 119 or above |

**Other runs:** an earlier run was stopped after 2 trials when focus moved to Windows Terminal, and isn't scored. A full run just before the scored one also held focus in 20 of 20 trials, at a median 120 fps with 0 presses reaching the oval. It has no saved Notepad text, so it's supporting evidence only.

**Limits of the test:**
- The foreground log polls about every 15 ms (estimated, not measured), so a shorter steal could be missed.
- The number of clicks in the click-through check isn't logged, only that none reached the oval.
- Only Notepad was tested, on the main screen. Admin windows, full-screen apps and other monitors weren't run.
- The spike is a plain HTML page driven by timers and fake levels sent 20 times a second. It has no engine, real hotkey, React or Tailwind.

## Decisions

- **Oval window:** `frame: false`, `transparent: true`, `focusable: false`, `resizable: false`, `hasShadow: false`, `show: false`, then `setAlwaysOnTop(true, 'screen-saver')`.
- **Showing it:** `showInactive()` to show and `hide()` to hide, on the same window each time.
- **Clicks:** `setIgnoreMouseEvents(true)` except while ✕ and ✓ are visible. The spike didn't need `forward: true`.
- **Fallback:** no tkinter oval.

## For T6 and T7

- **An uncaught error in the main process opens a dialog, and that dialog takes focus.** The spike hit this when a timer called the window after it was destroyed (`Object has been destroyed`). Stop timers before quitting, or check `isDestroyed()`.
- **Hold the window at the pill's size.** The spike's window was exactly 190 × 44, 12 px above the work area's bottom edge. Clicks on any wider empty area weren't tested.

## Rejected options

- **Drawing the oval from Python with tkinter:** the Electron oval passed.

## Open

These were not run, because they're outside S3's pass bar.

- **Other apps and windows:** see the limits above.
- **The real page:** T7 still has to confirm the React and Tailwind oval animates as smoothly.

The spike code is in `spikes/oval/main.js`.
