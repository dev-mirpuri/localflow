import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from 'react'
import { bridge } from './bridge'

const LIMIT = 200
const COPIED_MS = 1400
const COLLAPSE_MS = 120
const DELETE_PAUSE_MS = 400 // The next row can land under the pointer (DESIGN.md, rule 1).
const UNCLEANED_TIP = "Cleanup didn't finish, so this is the raw transcript."

type Entry = {
  id: number
  created_at: string
  clean_text: string
  target_app: string
  status: 'ok' | 'raw_fallback'
}

// Listened for from module load, because config can arrive before React subscribes.
let hotkey: string | null = null
const hotkeyListeners = new Set<() => void>()
bridge.onEvent((message) => {
  if (message.type !== 'config') return
  hotkey = String(message.hotkey)
  hotkeyListeners.forEach((listener) => listener())
})

function subscribeHotkey(listener: () => void): () => void {
  hotkeyListeners.add(listener)
  return () => hotkeyListeners.delete(listener)
}

function dayLabel(date: Date): string {
  const today = new Date()
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)
  if (date.toDateString() === today.toDateString()) return 'Today'
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'
  const year = date.getFullYear() === today.getFullYear() ? undefined : 'numeric'
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year
  })
}

// Entries arrive newest first, so each day's Entries are already together.
function byDay(entries: Entry[]): [string, Entry[]][] {
  const days = new Map<string, Entry[]>()
  for (const entry of entries) {
    const label = dayLabel(new Date(entry.created_at))
    if (days.has(label)) days.get(label)!.push(entry)
    else days.set(label, [entry])
  }
  return [...days]
}

const short = (text: string): string =>
  text.length > 40 ? `${text.slice(0, 40).trimEnd()}…` : text

export default function HistoryPage(): React.JSX.Element {
  const [entries, setEntries] = useState<Entry[] | null>(null)
  const key = useSyncExternalStore(subscribeHotkey, () => hotkey)
  const [leaving, setLeaving] = useState<number[]>([])
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const copiedTimer = useRef(0)
  const deletePaused = useRef(false)

  useEffect(() => {
    bridge.request('list_history', { query: '', limit: LIMIT }).then((data) => {
      setEntries(data as Entry[])
    })
    return bridge.onEvent((message) => {
      if (message.type !== 'result') return
      const entry = message.entry as Entry // Before the list arrives, the list will hold it.
      setEntries((all) => all && [entry, ...all.filter((e) => e.id !== entry.id)].slice(0, LIMIT))
    })
  }, [])

  async function copy(entry: Entry): Promise<void> {
    await bridge.copy(entry.clean_text.trimEnd()) // "Copied" only once the write succeeded.
    setCopiedId(entry.id)
    clearTimeout(copiedTimer.current)
    copiedTimer.current = window.setTimeout(() => setCopiedId(null), COPIED_MS)
  }

  function remove(entry: Entry, byKeyboard: boolean): void {
    if (deletePaused.current) return
    const list = (entries ?? []).filter((e) => e.id === entry.id || !leaving.includes(e.id))
    const at = list.findIndex((e) => e.id === entry.id)
    const neighbour = list[at + 1] ?? list[at - 1] // Keyboard focus moves there, not to the top.
    deletePaused.current = true
    const resume = (): void => {
      deletePaused.current = false
      clearTimeout(timer)
      window.removeEventListener('pointermove', onMove)
    }
    const onMove = (event: PointerEvent): void => {
      if (event.movementX || event.movementY) resume()
    }
    const timer = window.setTimeout(resume, DELETE_PAUSE_MS)
    window.addEventListener('pointermove', onMove)
    bridge.request('delete_entry', { id: entry.id })
    setLeaving((ids) => [...ids, entry.id])
    window.setTimeout(() => {
      setEntries((all) => all && all.filter((e) => e.id !== entry.id))
      setLeaving((ids) => ids.filter((id) => id !== entry.id))
      if (byKeyboard && neighbour) document.getElementById(`copy-${neighbour.id}`)?.focus()
    }, COLLAPSE_MS)
  }

  return (
    <main className="h-screen overflow-y-auto bg-ground px-3 pb-3 font-sans text-text [scrollbar-color:var(--color-line)_transparent] [scrollbar-width:thin] selection:bg-primary selection:text-black">
      {entries?.length === 0 && (
        <p className="grid h-full place-items-center pb-8 text-sm text-dim">
          <span>
            Hold{' '}
            {key ? (
              <kbd className="mx-0.5 rounded border border-line bg-raised px-1.5 py-0.5 font-sans text-xs text-text">
                {key.replace(/\b\w/g, (letter) => letter.toUpperCase())}
              </kbd>
            ) : (
              'your Hotkey'
            )}{' '}
            and speak
          </span>
        </p>
      )}
      {byDay(entries ?? []).map(([day, dayEntries]) => (
        <section key={day} className="max-w-[calc(62ch+1.5rem)] pt-3.5 text-sm first:pt-0">
          <h2 className="sticky top-0 z-10 bg-ground px-3 py-1.5 text-[13px] leading-[18px] font-semibold">
            {day}
          </h2>
          <ul>
            {dayEntries.map((entry) => (
              <Row
                key={entry.id}
                entry={entry}
                copied={copiedId === entry.id}
                leaving={leaving.includes(entry.id)}
                onCopy={() => copy(entry).catch(() => {})} // No "Copied" when the write fails.
                onDelete={(byKeyboard) => remove(entry, byKeyboard)}
              />
            ))}
          </ul>
        </section>
      ))}
      <p role="status" className="sr-only">
        {copiedId === null ? '' : 'Copied'}
      </p>
    </main>
  )
}

type RowProps = {
  entry: Entry
  copied: boolean
  leaving: boolean
  onCopy: () => void
  onDelete: (byKeyboard: boolean) => void
}

function Row({ entry, copied, leaving, onCopy, onDelete }: RowProps): React.JSX.Element {
  const [expanded, setExpanded] = useState(false)
  const [overflows, setOverflows] = useState(false)
  const text = useRef<HTMLParagraphElement>(null)

  useLayoutEffect(() => {
    if (expanded) return // Expanded text doesn't overflow, but it still needs its toggle.
    const element = text.current!
    const check = (): void => setOverflows(element.scrollHeight > element.clientHeight + 1)
    const observer = new ResizeObserver(check)
    observer.observe(element)
    return () => observer.disconnect()
  }, [expanded])

  const toggle = (): void => setExpanded(!expanded)
  const time = new Date(entry.created_at).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit'
  })
  const action =
    'h-7 cursor-pointer rounded-sm focus-visible:outline-2 focus-visible:outline-primary'

  return (
    <li
      className={`grid transition-[grid-template-rows,opacity] duration-[120ms] ease-out motion-reduce:transition-none ${leaving ? 'pointer-events-none grid-rows-[0fr] opacity-0' : 'grid-rows-[1fr]'}`}
    >
      <div className="group min-h-0 overflow-hidden rounded-lg px-3 py-2.5 transition-colors duration-100 hover:bg-raised">
        <p
          ref={text}
          onClick={() => overflows && !window.getSelection()?.toString() && toggle()}
          className={`leading-[21px] whitespace-pre-line ${expanded ? '' : 'line-clamp-2'}`}
        >
          {entry.clean_text}
        </p>
        <div className="mt-1 flex items-center gap-x-3 text-xs leading-[18px] text-dim">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3">
            <span className="tabular-nums">{time}</span>
            {entry.target_app && <span>{entry.target_app.replace(/\.exe$/i, '')}</span>}
            {entry.status === 'raw_fallback' && (
              <span title={UNCLEANED_TIP} className="rounded-sm border border-line px-1.5">
                uncleaned<span className="sr-only">: {UNCLEANED_TIP}</span>
              </span>
            )}
            {overflows && (
              <button
                type="button"
                onClick={toggle}
                aria-expanded={expanded}
                aria-label={`${expanded ? 'Show less' : 'Show all'}: ${short(entry.clean_text)}`}
                className={action}
              >
                {expanded ? 'Show less' : 'Show all'}
              </button>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-5">
            <button
              type="button"
              id={`copy-${entry.id}`}
              onClick={onCopy}
              aria-label={`Copy: ${short(entry.clean_text)}`}
              className={`${action} min-w-10 text-left ${copied ? 'text-primary' : 'text-text'}`}
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              type="button"
              onClick={(event) => onDelete(event.currentTarget.matches(':focus-visible'))}
              aria-label={`Delete: ${short(entry.clean_text)}`}
              className={`${action} opacity-0 group-focus-within:opacity-100 group-hover:opacity-100`}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </li>
  )
}
