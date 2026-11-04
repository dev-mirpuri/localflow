import { ENTRIES, ERROR_MESSAGE, HOTKEY_HINT, type Entry } from './data'
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

// Subtitles give each speaker a colour; here each Target app gets one.
const APP_COLOURS: Record<string, string> = {
  WindowsTerminal: 'text-b-green',
  Code: 'text-b-cyan',
  slack: 'text-b-yellow',
  chrome: 'text-b-pink'
}

function Cue({ entry, onDelete }: { entry: Entry; onDelete: () => void }) {
  const { copied, copy } = useCopy(entry.text)
  return (
    <li className="b-cue grid grid-cols-[52px_1fr] gap-x-3">
      <time className="pt-[3px] font-b-time text-[13px] leading-[26px] text-b-dim tabular-nums">
        {entry.time}
      </time>
      <div className="min-w-0">
        <ClampedText className="text-[17px] leading-[29px] font-medium">
          <span className="b-caption">{entry.text}</span>
        </ClampedText>
        <div className="mt-1 flex min-h-7 flex-wrap items-center gap-x-3 text-[14px]">
          <span className={APP_COLOURS[entry.app] ?? 'text-white'}>{entry.app}</span>
          {entry.uncleaned && <span className="text-white">[uncleaned]</span>}
          <span
            className={`b-actions ml-auto flex items-center gap-6 ${copied ? 'b-actions-on' : ''}`}
          >
            <button type="button" onClick={copy} className="b-action" aria-live="polite">
              <svg
                viewBox="0 0 16 16"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                aria-hidden
              >
                <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" />
                <path d="M10.5 3v-.5h-8v8H3" strokeLinecap="round" />
              </svg>
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button type="button" onClick={onDelete} className="b-action b-action-delete">
              <svg
                viewBox="0 0 16 16"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                aria-hidden
              >
                <path d="M2.5 4.5h11M6 4.5V2.5h4v2M4 4.5l.7 9h6.6l.7-9" />
              </svg>
              Delete
            </button>
          </span>
        </div>
      </div>
    </li>
  )
}

function History({ initial, height }: { initial: Entry[]; height: number }) {
  const { days, query, setQuery, remove, isEmpty } = useHistory(initial)
  return (
    <WinFrame className="bg-b-frame font-b-text text-white b-world" height={height}>
      <div className="shrink-0 px-5 pb-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search history"
          aria-label="Search history"
          className="h-11 w-full bg-black px-3.5 text-[17px] font-medium text-white placeholder:text-b-dim"
        />
      </div>
      <div className="b-scroll min-h-0 flex-1 overflow-y-auto px-5 pb-5">
        {isEmpty ? (
          <p className="grid h-full place-items-center pb-10 text-center text-[22px] leading-[36px] font-medium">
            <span className="b-caption">{HOTKEY_HINT}</span>
          </p>
        ) : days.length === 0 ? (
          <p className="pt-8 text-center text-[17px] leading-[29px] font-medium">
            <span className="b-caption">Nothing matches “{query}”</span>
          </p>
        ) : (
          days.map((day) => (
            <section key={day[0].dayLong} className="mt-7 first:mt-1">
              <h3 className="mb-2.5 text-[26px] leading-8 font-bold tracking-[-0.01em] text-balance">
                {day[0].dayLong}
              </h3>
              <ul className="flex flex-col gap-2.5">
                {day.map((entry) => (
                  <Cue key={entry.id} entry={entry} onDelete={() => remove(entry.id)} />
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
    return (
      <div className="b-oval px-4 font-b-text text-[15px] font-medium text-b-yellow">
        {ERROR_MESSAGE}
      </div>
    )
  }
  const handsfree = state === 'handsfree'
  return (
    <div className={`b-oval text-white ${handsfree ? 'px-1' : 'px-4'}`}>
      {handsfree && (
        <button type="button" aria-label="Cancel" className="b-oval-button">
          <IconX />
        </button>
      )}
      <Bars state={state} count={9} className="b-bars" />
      {handsfree && (
        <button type="button" aria-label="Finish" className="b-oval-button bg-b-yellow text-black">
          <IconCheck />
        </button>
      )}
    </div>
  )
}

export function DirectionB() {
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
