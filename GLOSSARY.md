# LocalFlow

A local dictation app for Windows: speak in any app, and cleaned-up text lands at the cursor.

## Language

### Parts

**App**:
LocalFlow's own desktop program, with its tray icon, History window and Oval.
_Avoid_: Using "app" for the program being typed into

**Engine**:
The part of LocalFlow that listens for the Hotkey and turns speech into pasted text.
_Avoid_: Backend, server

**Target app**:
The program holding the focused text box when text is pasted.
_Avoid_: App, focused app, active app

**Oval**:
The small on-screen indicator showing what a Dictation is doing.
_Avoid_: Pill, bar, Flow Bar

### Dictating

**Hotkey**:
The global key that starts and finishes a Recording.
_Avoid_: Shortcut, keybind

**Dictation**:
One complete pass from starting a Recording to its text being pasted.
_Avoid_: Session, utterance

**Push-to-talk**:
Dictating while holding the Hotkey down.
_Avoid_: Hold mode

**Hands-free**:
Dictating after a double-tap of the Hotkey, without holding anything down.
_Avoid_: Toggle mode, locked mode

**Recording**:
The audio captured for one Dictation.
_Avoid_: Clip, except for eval audio

**Cancel**:
Throwing away the Recording in progress because of something the user pressed.
_Avoid_: Abort, using "discard" for this

**Discard**:
The Engine throwing a Recording away on its own because it was an accidental tap, too short, silent or only filler words.
_Avoid_: Using "cancel" for this

### Text

**Transcript**:
The text speech recognition produces from a Recording, before cleanup.
_Avoid_: Raw text, except for the stored field

**Cleaned text**:
The rewritten Transcript produced by cleanup.
_Avoid_: Final text, polished text

**Raw fallback**:
Using the Transcript in place of Cleaned text because cleanup failed or its output was rejected.
_Avoid_: Uncleaned, except as the label shown in the History window

### History

**Entry**:
One saved Dictation in History.
_Avoid_: Item, record, using "dictation" for the saved row

**History**:
The saved Entries, newest first, shown in the History window.
_Avoid_: Hub, log
