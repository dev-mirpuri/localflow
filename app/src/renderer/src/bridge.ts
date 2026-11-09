// The real bridge in Electron; in a normal browser, a Fake bridge with sample data that
// cycles the Oval's states, so the pages can be opened and screenshotted on their own.
const STEP_MS = 2000
const CYCLE: EngineMessage[] = [
  ...['loading', 'idle', 'listening', 'handsfree', 'processing', 'idle', 'downloading'].map(
    (state) => ({ type: 'state', state })
  ),
  { type: 'error', message: "Ollama isn't running. Start Ollama and try again." },
  { type: 'state', state: 'idle' }
]

// Times are relative to now so the day labels show Today, Yesterday and a date.
// Open the page with ?empty for the empty state.
const ago = (hours: number): string => new Date(Date.now() - hours * 3_600_000).toISOString()
const LONG =
  "Here's the plan for Thursday. First we freeze the release branch in the morning, then " +
  'run the full checklist on a clean machine, and if anything fails we fix it on dev before ' +
  "promoting. I'll write up the notes afterwards and send them round to everyone."
let entries = [
  [1, ago(0.2), 'Sounds good, see you at 4pm.', 'slack.exe', 'ok'],
  [2, ago(1), LONG, 'outlook.exe', 'ok'],
  [3, ago(25), 'Remember to update the release checklist.', 'code.exe', 'ok'],
  [4, ago(26), 'um so the build is green now', 'chrome.exe', 'raw_fallback'],
  [5, ago(75), 'Running ten minutes late, start without me.', 'slack.exe', 'ok']
]
  .map(([id, created_at, clean_text, target_app, status]) => {
    return { id, created_at, raw_text: clean_text, clean_text, target_app, status }
  })
  .filter(() => !location.search.includes('empty'))

function fakeBridge(): LocalFlow {
  const listeners = new Set<(message: EngineMessage) => void>()
  const emit = (message: EngineMessage): void => listeners.forEach((listener) => listener(message))
  let step = 0
  setTimeout(() => emit({ type: 'config', hotkey: 'right ctrl', launch_at_login: false }))
  setInterval(() => emit(CYCLE[step++ % CYCLE.length]), STEP_MS)
  setInterval(() => emit({ type: 'level', value: Math.round(Math.random() * 100) / 100 }), 50)
  return {
    onEvent(callback) {
      listeners.add(callback)
      return () => listeners.delete(callback)
    },
    async request(method, params) {
      if (method === 'delete_entry') entries = entries.filter((entry) => entry.id !== params.id)
      const query = String(params.query ?? '').toLowerCase()
      return entries.filter((entry) => String(entry.clean_text).toLowerCase().includes(query))
    },
    command: (name) => console.log('fake bridge: command', name),
    copy: (text) => navigator.clipboard.writeText(text),
    showOval: () => {}
  }
}

export const bridge = window.localflow ?? fakeBridge()
