# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

The UI is React in an Electron renderer, shipped as a Windows desktop app. There is no website and no other OS.

## Users

Developers on Windows with a capable NVIDIA GPU (at least 6 GB VRAM) who dictate into whatever they are working in: terminals, Claude Code, editors, Slack, browsers. The project's author is the first user, and people like them are real users too. It ships as a public GitHub release with no first-run wizard, so the README, error messages and empty state have to make sense to a stranger.

While dictating, their attention is on the Target app, not on LocalFlow: they want the words at the cursor. They open the History window to find and copy something they said earlier.

## Product Purpose

Press one global Hotkey in any app, speak, and cleaned, punctuated text lands at the cursor. Speech recognition and cleanup both run on the user's own GPU. History keeps every Dictation so it can be copied later.

Success is that the user stops thinking about the tool: text arrives within about 1.5 s for a sentence or two, and nothing they finish saying is lost.

## Positioning

A free, fully local take on Wispr Flow for Windows. Three claims, held equally:

- **Local:** no cloud and no account. Nothing else on the PC can reach the Engine.
- **Free:** no subscription.
- **Simple:** one Hotkey, an Oval and a History. No stats, streaks, themes or settings screen.

It is honest about the trade: a small model on a local GPU handles light cleanup well but is not as strong at heavy rewording as Wispr Flow's cloud models.

## Operating Context

- The Oval appears over any app while the user is working in it, and must never take focus. It shows Recording, processing and short errors, then disappears. A Recording can run for up to 3 minutes.
- The History window is an ordinary window, opened from the tray, for search and copy. Closing it hides it; the app stays in the tray.
- `config.json` is edited by hand; there is no settings screen.
- Machine requirement: NVIDIA GPU with at least 6 GB VRAM. There is no CPU mode; anything else gets a clear error. Ollama is a separate install, and Parakeet downloads on first run.

## Capabilities and Constraints

[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) is the source of truth for scope. Section 2 is the whole of v1, and section 5 says what is on each screen. [GLOSSARY.md](GLOSSARY.md) sets terminology, including in UI copy: Oval, Hotkey, Dictation, Entry, Target app, Cancel versus Discard.

- English only, Windows only.
- One look only, with no themes.
- No settings screen, first-run wizard, accounts, stats, raw transcript view or audio playback. Don't design around these or the brief's Later list.
- Delete is immediate, with no confirmation or undo.
- Only clipboard text is restored after a paste, and admin windows can't be pasted into. These are known limitations, not bugs to design around.
- The Fake bridge lets both pages run in a normal browser with sample data, which is how UI gets screenshotted.

**Undecided:** "LocalFlow" is still a working name.

## Brand Commitments

The name is provisional (see above). No logo or brand assets exist: `app/resources/icon.png` is still Electron's default icon, not an identity.

## Evidence on Hand

- Measured spike results: [ADR-0001](docs/adr/0001-s1-speech-and-cleanup-models.md) (speech and cleanup), [ADR-0002](docs/adr/0002-s2-hotkey-and-paste.md) (Hotkey and paste), [ADR-0003](docs/adr/0003-s3-oval-focus.md) (Oval focus).
- Recorded eval clips in `eval/` for scoring cleanup.

There are no testimonials, user counts, press or public benchmarks. Don't invent them. Only cite performance numbers that an ADR or the log records.

## Product Principles

1. **The Target app comes first.** LocalFlow appears only as long as it has something to say, and never competes for focus or attention.
2. **Never lose what was said.** When something fails, degrade to raw text, a saved Entry or `last-failed.wav`, and say so briefly.
3. **If it isn't in section 2, it doesn't exist.** Prefer removing to adding, in the UI as much as in the code.
4. **Say plainly what's true.** Errors name the actual cause and fix. Claims about privacy and quality stay within what the system really does.

## Accessibility & Inclusion

No formal requirement beyond ordinary good practice. Typing less is part of why people dictate, so as a soft goal the app's own flows should stay light on keyboard and pointer work.
