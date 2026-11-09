import { useEffect, useLayoutEffect, useRef, useSyncExternalStore } from 'react'
import { bridge } from './bridge'

const ERROR_SHOWN_MS = 4000
const BAR_COUNT = 7 // oval.css sizes the bars' box for 7.
const MIDDLE = (BAR_COUNT - 1) / 2
const STARTUP: Record<string, string> = {
  loading: 'Starting up…',
  downloading: 'Downloading speech model…'
}

// What the Oval shows. It listens from the moment this module loads, before React renders,
// because the Engine starts once the page has loaded and may send "downloading" at once.
let view = { state: 'idle', error: null as string | null }
let errorTimer: number | undefined
let waiting: string[] = [] // Errors sent while another shows, such as several at startup.
const viewListeners = new Set<() => void>()

function setView(next: typeof view): void {
  view = next
  viewListeners.forEach((listener) => listener())
}

function showError(error: string | null): void {
  clearTimeout(errorTimer)
  if (error)
    errorTimer = window.setTimeout(() => showError(waiting.shift() ?? null), ERROR_SHOWN_MS)
  setView({ ...view, error })
}

bridge.onEvent((message) => {
  if (message.type === 'error') {
    const error = String(message.message)
    if (view.error && view.error !== error) {
      if (!waiting.includes(error)) waiting.push(error)
    } else showError(error) // The same one again restarts its timer.
  } else if (message.type === 'state') {
    // An error stays readable through the idle that follows it; any other state replaces it.
    const state = String(message.state)
    if (state !== 'idle') {
      clearTimeout(errorTimer)
      waiting = []
    }
    setView({ state, error: state === 'idle' ? view.error : null })
  }
})

function subscribe(listener: () => void): () => void {
  viewListeners.add(listener)
  return () => viewListeners.delete(listener)
}

export default function OvalPage(): React.JSX.Element {
  const { state, error } = useSyncExternalStore(subscribe, () => view)
  const pill = useRef<HTMLDivElement>(null)
  const message = error ?? STARTUP[state]
  const handsfree = state === 'handsfree' && !message
  const shown = Boolean(message) || ['listening', 'handsfree', 'processing'].includes(state)

  useLayoutEffect(() => {
    const width = pill.current?.getBoundingClientRect().width
    bridge.showOval(width ? { width, clickable: handsfree } : null)
  }, [state, message, handsfree])

  return (
    <div className="flex h-screen items-center justify-center">
      {shown && (
        <div
          ref={pill}
          className={`oval ${handsfree ? 'px-1' : 'px-3.5'}`}
          role="status"
          aria-label={message ? undefined : state}
        >
          {message ? (
            <span className="min-w-0 truncate">{message}</span>
          ) : (
            <>
              {handsfree && (
                <button
                  type="button"
                  aria-label="Cancel"
                  className="oval-button text-dim"
                  onClick={() => bridge.command('cancel')}
                >
                  <svg viewBox="0 0 16 16" {...ICON}>
                    <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" />
                  </svg>
                </button>
              )}
              <Bars processing={state === 'processing'} />
              {handsfree && (
                <button
                  type="button"
                  aria-label="Finish"
                  className="oval-button text-primary"
                  onClick={() => bridge.command('finish')}
                >
                  <svg viewBox="0 0 16 16" {...ICON}>
                    <path d="M2.5 8.5l3.5 3.5 7.5-8" />
                  </svg>
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

const ICON = {
  width: 14,
  height: 14,
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true
} as const

// The same 7 spans are level bars, then 3 of them become the processing dots.
function Bars({ processing }: { processing: boolean }): React.JSX.Element {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const bars = [...ref.current!.children] as HTMLElement[]
    const paint = (level: number, wobble: (i: number) => number): void => {
      bars.forEach((bar, i) => {
        const weight = 1 - (Math.abs(i - MIDDLE) / (MIDDLE + 1)) * 0.7
        const share = Math.min(1, level * weight * wobble(i)).toFixed(3)
        bar.style.height = `calc(var(--bar-min) + (var(--bar-max) - var(--bar-min)) * ${share})`
      })
    }
    if (processing) {
      bars.forEach((bar) => (bar.style.height = ''))
      return
    }
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      paint(0.6, () => 1) // Held still in a fixed shape.
      return
    }
    paint(0, () => 1)
    return bridge.onEvent((message) => {
      if (message.type !== 'level') return
      const now = performance.now()
      paint(Number(message.value), (i) => 0.75 + 0.25 * Math.sin(now / 90 + i * 2.4))
    })
  }, [processing])
  return (
    <div ref={ref} className="bars" data-processing={processing || undefined} aria-hidden>
      {Array.from({ length: BAR_COUNT }, (_, i) => (
        <span key={i} data-dot={Math.abs(i - MIDDLE) <= 1 || undefined} />
      ))}
    </div>
  )
}
