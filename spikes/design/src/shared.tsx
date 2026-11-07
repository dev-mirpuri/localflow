import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import type { Entry } from './data'

export type OvalState = 'listening' | 'handsfree' | 'processing' | 'error'

// Search and immediate delete over the fake entries.
export function useHistory(initial: Entry[]) {
  const [entries, setEntries] = useState(initial)
  const [query, setQuery] = useState('')
  const q = query.trim().toLowerCase()
  const visible = entries.filter((e) => e.text.toLowerCase().includes(q))
  const days = [...new Set(visible.map((e) => e.dayLong))].map((day) =>
    visible.filter((e) => e.dayLong === day)
  )
  const remove = (id: number) => setEntries((all) => all.filter((e) => e.id !== id))
  return { days, query, setQuery, remove, isEmpty: entries.length === 0 }
}

export function useCopy(text: string) {
  const [copied, setCopied] = useState(false)
  const timer = useRef(0)
  useEffect(() => () => window.clearTimeout(timer.current), [])
  const copy = () => {
    navigator.clipboard?.writeText(text).catch(() => {})
    setCopied(true)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setCopied(false), 1400)
  }
  return { copied, copy }
}

// Two lines by default; click to expand, but only when there is more to show.
export function ClampedText({ className, children }: { className?: string; children: ReactNode }) {
  const [expanded, setExpanded] = useState(false)
  const [canExpand, setCanExpand] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)
  useLayoutEffect(() => {
    if (expanded) return
    const el = ref.current!
    const check = () => setCanExpand(el.scrollHeight > el.clientHeight + 1)
    check()
    const observer = new ResizeObserver(check)
    observer.observe(el)
    return () => observer.disconnect()
  }, [expanded])
  return (
    <button
      type="button"
      disabled={!canExpand}
      aria-expanded={canExpand ? expanded : undefined}
      onClick={() => setExpanded(!expanded)}
      className={`block w-full text-left ${canExpand ? 'cursor-pointer' : 'cursor-text select-text'}`}
    >
      <span
        ref={ref}
        className={`whitespace-pre-line ${expanded ? 'block' : 'line-clamp-2'} ${className ?? ''}`}
      >
        {children}
      </span>
    </button>
  )
}

// One 0-1 level 20 times a second, like the Engine's level message, spread across the bars.
function voiceLevel(t: number) {
  const syllable = Math.abs(Math.sin(t * 7.1)) * 0.6 + Math.abs(Math.sin(t * 3.3 + 1)) * 0.4
  const phrase = Math.sin(t * 0.9) > -0.55 ? 1 : 0.08
  return Math.sqrt(syllable) * phrase
}

export function Bars({
  state,
  count,
  className
}: {
  state: OvalState
  count: number
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const middle = (count - 1) / 2
  useEffect(() => {
    const bars = [...ref.current!.children] as HTMLElement[]
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (state === 'processing') {
      bars.forEach((bar) => (bar.style.height = ''))
      return
    }
    const paint = () => {
      const level = still ? 0.6 : voiceLevel(performance.now() / 1000)
      bars.forEach((bar, i) => {
        const weight = 1 - (Math.abs(i - middle) / (middle + 1)) * 0.7
        const wobble = still ? 1 : 0.75 + 0.25 * Math.sin(performance.now() / 90 + i * 2.4)
        bar.style.height = `calc(var(--bar-min) + (var(--bar-max) - var(--bar-min)) * ${(level * weight * wobble).toFixed(3)})`
      })
    }
    paint()
    const id = window.setInterval(paint, 50)
    return () => window.clearInterval(id)
  }, [state, middle])
  return (
    <div ref={ref} data-state={state} aria-hidden className={`bars ${className ?? ''}`}>
      {Array.from({ length: count }, (_, i) => (
        <span key={i} data-dot={Math.abs(i - middle) <= 1 ? '' : undefined} />
      ))}
    </div>
  )
}

export function IconX() {
  return (
    <svg
      viewBox="0 0 16 16"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden
    >
      <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" />
    </svg>
  )
}

export function IconCheck() {
  return (
    <svg
      viewBox="0 0 16 16"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M2.5 8.5l3.5 3.5 7.5-8" />
    </svg>
  )
}

export function WinFrame({
  className,
  height,
  children
}: {
  className: string
  height: number
  children: ReactNode
}) {
  return (
    <div
      className={`@container flex w-full flex-col overflow-hidden rounded-lg shadow-[0_18px_50px_rgb(0_0_0/0.45)] ${className}`}
      style={{ height }}
    >
      <div
        className="flex h-9 shrink-0 items-center justify-between pl-3.5 text-[13px]"
        aria-hidden
      >
        <span>LocalFlow</span>
        <span className="flex h-full">
          {['M3 8h10', 'M3.5 3.5h9v9h-9z', 'M3.5 3.5l9 9M12.5 3.5l-9 9'].map((d) => (
            <span key={d} className="grid w-11 place-items-center">
              <svg
                viewBox="0 0 16 16"
                width="11"
                height="11"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.1"
              >
                <path d="M0 0" />
                <path d={d} />
              </svg>
            </span>
          ))}
        </span>
      </div>
      {children}
    </div>
  )
}

// The Oval on the two kinds of app it floats over, plus one running through a real sequence.
export function OvalGallery({ render }: { render: (state: OvalState) => ReactNode }) {
  const rows: [OvalState, string][] = [
    ['listening', 'Listening'],
    ['handsfree', 'Hands-free'],
    ['processing', 'Processing'],
    ['error', 'Error']
  ]
  return (
    <section aria-label="Oval states">
      <h2 className="mb-2 text-sm font-medium">Oval</h2>
      <div className="grid grid-cols-[84px_1fr_1fr] items-center gap-1.5 text-sm">
        {rows.map(([state, label]) => (
          <div key={state} className="contents">
            <span>{label}</span>
            <div className="grid h-20 place-items-center rounded bg-[#1b1d20]">{render(state)}</div>
            <div className="grid h-20 place-items-center rounded bg-[#f4f4f2]">{render(state)}</div>
          </div>
        ))}
        <span>In sequence</span>
        <div className="col-span-2">
          <OvalSequence render={render} />
        </div>
      </div>
    </section>
  )
}

function OvalSequence({ render }: { render: (state: OvalState) => ReactNode }) {
  const [step, setStep] = useState(0)
  const steps: { state: OvalState; ms: number; hidden?: boolean }[] = [
    { state: 'listening', ms: 3200 },
    { state: 'processing', ms: 1500 },
    { state: 'processing', ms: 900, hidden: true }
  ]
  const current = steps[step]
  useEffect(() => {
    const id = window.setTimeout(() => setStep((s) => (s + 1) % steps.length), current.ms)
    return () => window.clearTimeout(id)
  }, [step, current.ms, steps.length])
  return (
    <div className="grid h-24 place-items-center rounded bg-[#6b7076]">
      <div
        className={`transition-[opacity,scale] duration-200 ease-out ${current.hidden ? 'scale-95 opacity-0' : ''}`}
      >
        {render(current.state)}
      </div>
    </div>
  )
}
