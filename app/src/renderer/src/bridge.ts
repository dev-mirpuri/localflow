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

let entries = [
  [1, '2026-11-08T09:12:00+00:00', 'Sounds good, see you at 4pm.', 'slack.exe', 'ok'],
  [2, '2026-11-08T08:40:00+00:00', 'Remember to update the release checklist.', 'code.exe', 'ok'],
  [3, '2026-11-07T17:05:00+00:00', 'um so the build is green now', 'chrome.exe', 'raw_fallback']
].map(([id, created_at, clean_text, target_app, status]) => {
  return { id, created_at, raw_text: clean_text, clean_text, target_app, status }
})

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
