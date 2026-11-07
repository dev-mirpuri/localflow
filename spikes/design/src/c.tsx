import { ENTRIES, ERROR_MESSAGE, type Entry } from './data'
import {
  Bars,
  ClampedText,
  IconCheck,
  IconX,
  OvalGallery,
  useCopy,
  useHistory,
  WinFrame,
  type OvalState
} from './shared'

function Row({ entry, onDelete }: { entry: Entry; onDelete: () => void }) {
  const { copied, copy } = useCopy(entry.text)
  return (
    <li className="c-row rounded-lg px-3 py-2.5 transition-colors duration-100 hover:bg-c-raised">
      <ClampedText className="text-[14px] leading-[21px] text-c-text">{entry.text}</ClampedText>
      <div className="mt-1 flex min-h-6 flex-wrap items-center gap-x-3 text-[12px] text-c-dim">
        <span className="tabular-nums">{entry.time}</span>
        <span>{entry.app}</span>
        {entry.uncleaned && (
          <span className="rounded border border-c-line px-1.5 leading-[18px]">uncleaned</span>
        )}
        <span
          className={`c-actions ml-auto flex items-center gap-5 ${copied ? 'c-actions-on' : ''}`}
        >
          <button
            type="button"
            onClick={copy}
            className={`c-action ${copied ? 'text-c-accent' : ''}`}
            aria-live="polite"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button type="button" onClick={onDelete} className="c-action">
            Delete
          </button>
        </span>
      </div>
    </li>
  )
}

function History({ initial, height }: { initial: Entry[]; height: number }) {
  const { days, query, setQuery, remove, isEmpty } = useHistory(initial)
  return (
    <WinFrame className="bg-c-ground font-c text-c-text c-world" height={height}>
      <div className="shrink-0 px-3 pb-2">
        <div className="relative">
          <svg
            viewBox="0 0 16 16"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            aria-hidden
            className="pointer-events-none absolute top-[11px] left-3 text-c-dim"
          >
            <circle cx="7" cy="7" r="4.5" />
            <path d="M10.5 10.5L14 14" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search history"
            aria-label="Search history"
            className="h-9 w-full rounded-lg border border-c-line bg-c-raised pr-3 pl-8.5 text-[14px] text-c-text placeholder:text-c-dim"
          />
        </div>
      </div>
      <div className="c-scroll min-h-0 flex-1 overflow-y-auto px-3 pb-3">
        {isEmpty ? (
          <p className="grid h-full place-items-center pb-8 text-center text-[14px] text-c-dim">
            <span>
              Hold{' '}
              <kbd className="mx-0.5 rounded border border-c-line bg-c-raised px-1.5 py-0.5 font-c text-[12px] text-c-text">
                Right Ctrl
              </kbd>{' '}
              and speak
            </span>
          </p>
        ) : days.length === 0 ? (
          <p className="pt-8 text-center text-[14px] text-c-dim">Nothing matches “{query}”</p>
        ) : (
          days.map((day) => (
            <section key={day[0].dayLong} className="mt-3 first:mt-0">
              <h3 className="sticky top-0 z-10 bg-c-ground px-3 py-1.5 text-[12px] font-medium text-c-dim">
                {day[0].dayLong}
              </h3>
              <ul>
                {day.map((entry) => (
                  <Row key={entry.id} entry={entry} onDelete={() => remove(entry.id)} />
                ))}
              </ul>
            </section>
          ))
        )}
      </div>
    </WinFrame>
  )
}

function Oval({ state }: { state: OvalState }) {
  if (state === 'error') {
    return <div className="c-oval px-3.5 font-c text-[13px] text-c-text">{ERROR_MESSAGE}</div>
  }
  const handsfree = state === 'handsfree'
  return (
    <div className={`c-oval text-c-text ${handsfree ? 'px-1' : 'px-3.5'}`}>
      {handsfree && (
        <button
          type="button"
          aria-label="Cancel"
          className="c-oval-button text-c-dim hover:text-c-text"
        >
          <IconX />
        </button>
      )}
      <Bars state={state} count={7} className="c-bars" />
      {handsfree && (
        <button type="button" aria-label="Finish" className="c-oval-button text-c-accent">
          <IconCheck />
        </button>
      )}
    </div>
  )
}

export function DirectionC() {
  return (
    <main className="mx-auto grid max-w-[1392px] items-start gap-8 lg:grid-cols-[minmax(0,720px)_minmax(0,1fr)]">
      <section aria-label="History window">
        <h2 className="mb-2 text-sm font-medium">History window</h2>
        <History initial={ENTRIES} height={760} />
      </section>
      <div className="flex flex-col gap-8">
        <section aria-label="Empty state">
          <h2 className="mb-2 text-sm font-medium">Empty state</h2>
          <History initial={[]} height={220} />
        </section>
        <OvalGallery render={(state) => <Oval state={state} />} />
      </div>
    </main>
  )
}
