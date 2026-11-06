# Release checklist

Work through this on `dev` before promoting to `main`. Each ticket that adds something visible adds its checks here.

## Dictate from a console (T4a)

Run `uv run localflow-engine dictate` from `engine/`, wait for "Ready", then in each of Notepad, Chrome, VS Code, Slack, Windows Terminal and Claude Code:

- [ ] Hold Right Ctrl, say a sentence, release: the Cleaned text lands at the cursor with one trailing space, within about 1.5 s of release for one or two sentences.
- [ ] Double-tap Right Ctrl, speak, tap again: the text lands once the key is up.
- [ ] A spoken numbered list keeps its line breaks, and nothing runs or submits in the terminals.
- [ ] Copy some text first: after the paste, Ctrl+V gives that text again.
- [ ] Hold Right Ctrl and press another key: nothing is pasted, and the other key still types.
- [ ] Double-tap, then press Esc: nothing is pasted and the app doesn't see the Esc. Esc while idle still reaches the app.
- [ ] One quick tap: nothing is pasted.
- [ ] The console's level bar moves with your voice while recording.
- [ ] Hands-free left running finishes by itself after 3 minutes and pastes.
