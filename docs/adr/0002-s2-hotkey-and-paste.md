---
status: accepted
---

# Right Ctrl with the `keyboard` library, and clipboard paste restored after 200 ms

Spike S2 asked whether hold and double-tap feel right, and whether paste works everywhere I type (`keyboard` 0.13.5, `sounddevice` 0.5.6, default Realtek microphone through MME). We use Right Ctrl with a 250 ms hold and a 350 ms gap, and paste through the clipboard with Ctrl+V. The pass bar is met on the scored run and on my report of the six apps. The restore wait was not tested, so it stays unproven.

## Results

Hands-on results were reported by me after the runs. The numbers come from the spike's log, `spikes/hotkey-paste/results/s2.log`, which is local and not committed.

| Check | Result | Bar |
|---|---|---|
| 50 mixed presses, Right Ctrl, hold and double-tap both on | **0 misfires out of 50**; felt good | No misfires: met |
| Paste in Notepad, Chrome, VS Code, Slack, Windows Terminal, Claude Code | Worked in all six, as reported | All six: met |
| Three pasted lines | Stayed three lines; nothing ran or submitted | |
| Esc while recording, processing and idle | All three correct, as reported | |
| Typing lag | None felt | |
| First words with the mic opened on key-down | None clipped, as reported | |

**The scored run:** 18 holds, 10 taps, 12 double-taps, 5 cancels with another key and 5 cancels with Esc.

| Measure | Min | Median | Max |
|---|---|---|---|
| Hold length | 945 ms | 1,128 ms | 1,525 ms |
| Tap length | 54 ms | 71 ms | 82 ms |
| Gap between double-tap presses | 70 ms | 92 ms | 120 ms |

These sit far from the 250 ms and 350 ms limits, because the drill asked for a hold of about 1 s. So the run shows the normal gestures are classified correctly, not how close to the limits they can go.

**The earlier run:** an earlier drill was stopped after 17 presses with 3 mismatches, and isn't part of the 0 out of 50. Two asked for double-tap then Esc and logged a third tap, with no Esc. One asked for a hold and logged a 65 ms press. In each case the code classified the keys it logged correctly, which points to the wrong gesture rather than a misfire, but the log can't show what I meant to press.

**Other measurements:**

| Measure | Result |
|---|---|
| Hotkey callback, 1,826 key events | Median 0.005-0.007 ms per run, slowest 0.065 ms |
| Mic stream open after key-down, 9 clips | 49-61 ms |
| First audio callback after key-down, 9 clips | 100-112 ms |
| Clipboard save, 59 pastes | At most 1 ms, including a 1.1 MB clipboard |
| Clipboard read back after restore, 59 pastes | 58 identical; 1 differed only in the two history flags the spike overwrites |
| Paste wait for the hotkey to come up | One paste waited 117 ms |

The hotkey callback time leaves out any wait before Python runs the callback, so "no lag" rests on how typing felt. The first audio callback is an upper bound on lost audio, because the first buffer holds audio from before the callback.

**Limits of the log:**
- It doesn't record the target app, so it can't confirm the six apps one by one. The app run had 8 pastes, 4 one-line and 4 three-line, in what look like 4 pairs. Notepad also got both kinds in the drill. That accounts for both kinds in about 5 apps, not 6.
- It holds 9 mic clips, about 4 s apart in a 41 s run, against the 10 reported. It shows no press after a long idle, though the mic is closed and reopened for every press. The first clip's 61 ms open is at the top of the range, and first audio was 112 ms, the slowest.
- Pasted text was plain sentences with `\n` line breaks, not numbered lists.

## Decisions

- **Hotkey:** one key, default Right Ctrl, with hold and double-tap always both on, 250 ms hold and 350 ms gap.
- **Hotkey library:** `keyboard`, using `keyboard.hook(callback, suppress=True)`. Returning `False` swallows the event, so Esc is swallowed only while recording.
- **Microphone:** opens on key-down. No always-open stream or pre-roll buffer.
- **Paste:** set the clipboard, send Ctrl+V, restore the saved text after 200 ms. Other clipboard formats aren't restored; this is a known limitation. No typed-input fallback.
- **Restore wait:** 200 ms is the spike's untuned default, not a measured value. Revisit it if restores fail in daily use.
- **Line breaks:** numbered lists with line breaks are safe to paste in terminals, so they need no special handling. This rests on the three-line paste; a list has the same line breaks.

## For T3 and T4

- **Do no blocking work on the hook thread.** Opening the mic took 49-61 ms, so it belongs on another thread. The hook only updates state and queues work.
- **Track hotkey keys by name and other keys by scan code.** A name can change between down and up ("a" down, "A" up), which would leave a key stuck as held.
- **The hook sees our own Ctrl+V as ordinary keys.** The `keyboard` event doesn't say it was injected, so the spike ignores all keys while a flag is set, for 30 ms around the send.
- **Bound queue waits on the main thread.** On Windows, a blocking `queue.get()` with no timeout can't be interrupted by Ctrl+C.

## Rejected options

- **Typed input for apps where Ctrl+V fails:** no app needed it.
- **A different key or timings:** nothing misfired or felt wrong.

## Open

These were not run, because they're outside S2's pass bar.

- **Other single keys:** only Right Ctrl was tested.
- **The restore wait:** see the decision above. A wait too short pastes the old clipboard instead of the dictation.
- **Hold and double-tap limits:** see the scored run above.

The spike code is in `spikes/hotkey-paste/s2.py`.
