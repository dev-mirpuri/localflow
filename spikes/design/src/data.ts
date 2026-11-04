// Fake History. Target apps are process names, because that is what the Engine records.
export type Entry = {
  id: number
  dayShort: string
  dayLong: string
  time: string
  app: string
  text: string
  uncleaned?: boolean
}

const today = { dayShort: 'Today', dayLong: 'Today' }
const yesterday = { dayShort: 'Yesterday', dayLong: 'Yesterday' }
const monday = { dayShort: 'Mon 2 Nov', dayLong: 'Monday 2 November' }
const friday = { dayShort: 'Fri 30 Oct', dayLong: 'Friday 30 October' }

export const ENTRIES: Entry[] = [
  {
    id: 15,
    ...today,
    time: '16:48',
    app: 'WindowsTerminal',
    text: 'Rename the level event to mic_level everywhere and run the protocol tests again. If any of them fail, show me the output before you fix anything.'
  },
  {
    id: 14,
    ...today,
    time: '16:12',
    app: 'slack',
    text: 'Running ten minutes late, start without me.'
  },
  {
    id: 13,
    ...today,
    time: '15:37',
    app: 'Code',
    text: "The double-tap window feels too tight on my keyboard. Can you log the gap between the first release and the second press for a day, without changing the 350 millisecond threshold, so we can decide from real numbers? Keep the text out of the logs, since those should only have timings and error types. Then add a small script that prints the median and the 95th percentile from the log file, and don't add a dependency for it."
  },
  {
    id: 12,
    ...today,
    time: '14:05',
    app: 'chrome',
    text: 'How do I see which process is holding GPU memory on Windows?'
  },
  {
    id: 11,
    ...today,
    time: '11:20',
    app: 'WindowsTerminal',
    uncleaned: true,
    text: 'so the migration fails on the second run because the table already exists and I think we want, no wait, create table if not exists there, and also check whether the index gets created twice'
  },
  {
    id: 10,
    ...yesterday,
    time: '18:02',
    app: 'Obsidian',
    text: 'Things to check before the release:\n1. Quit unloads the model.\n2. The tray icon survives a restart.\n3. A second launch opens the window.'
  },
  {
    id: 9,
    ...yesterday,
    time: '15:44',
    app: 'Code',
    text: 'This function does two things. Split the part that groups entries by day into its own function and give it a test for the day boundary at midnight, because that is the only part that can really break.'
  },
  { id: 8, ...yesterday, time: '10:31', app: 'chrome', text: 'Thanks, that fixed it.' },
  {
    id: 7,
    ...yesterday,
    time: '09:15',
    app: 'slack',
    text: 'Morning. I pushed the fix for the paste delay. Can someone try it on a machine with a different keyboard layout?'
  },
  {
    id: 6,
    ...monday,
    time: '17:26',
    app: 'OUTLOOK',
    text: 'Hi Sam, Thursday at 4pm works for me. I will send the notes the day before so we can skip the walkthrough and go straight to the open questions.'
  },
  {
    id: 5,
    ...monday,
    time: '13:50',
    app: 'WindowsTerminal',
    text: "Look at why the oval window flashes white the first time it opens. I think it's the background colour before the page loads, but check that before you change anything. It has to stay transparent, and it must not take focus from the app underneath, so don't touch the window flags that the spike already proved."
  },
  { id: 4, ...monday, time: '09:02', app: 'Notion', text: 'Move the search work to next week.' },
  { id: 3, ...friday, time: '16:39', app: 'slack', text: 'Have a good weekend, everyone.' },
  {
    id: 2,
    ...friday,
    time: '14:11',
    app: 'Code',
    text: 'Add a comment here saying why the clipboard restore waits 200 milliseconds, and say that the number has not been measured yet.'
  },
  {
    id: 1,
    ...friday,
    time: '10:47',
    app: 'chrome',
    text: 'What is the difference between a process name and a window title in the Win32 API, and which one is more stable across app updates?'
  }
]

export const HOTKEY_HINT = 'Hold Right Ctrl and speak'
export const ERROR_MESSAGE = "Ollama isn't running"
