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

function Strip({ entry, onDelete }: { entry: Entry; onDelete: () => void }) {
  const { copied, copy } = useCopy(entry.text)
  return (
    <li className="relative overflow-hidden bg-a-strip px-4 pt-3 pb-2 text-a-ink">
      <ClampedText className="font-a-text text-[15px] leading-[22px]">{entry.text}</ClampedText>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-a-ui text-[14px] font-medium">
        <span className="whitespace-nowrap">To {entry.app}</span>
        {entry.uncleaned && <span className="a-tag">uncleaned</span>}
        <span className="ml-auto tabular-nums">{entry.time}</span>
        <button
          type="button"
          onClick={copy}
          className="a-action min-w-[52px] font-semibold"
          aria-live="polite"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="a-action ml-3 text-a-ink-soft hover:text-a-stamp"
        >
          Delete
        </button>
      </div>
      {copied && (
        <span aria-hidden className="a-stamp">
          Copied
        </span>
      )}
    </li>
  )
}

function History({ initial, height }: { initial: Entry[]; height: number }) {
  const { days, query, setQuery, remove, isEmpty } = useHistory(initial)
  return (
    <WinFrame className="bg-a-form font-a-ui text-a-ink a-world" height={height}>
      <div className="shrink-0 px-4 pb-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search history"
          aria-label="Search history"
          className="h-10 w-full border-2 border-a-ink bg-a-strip px-3 font-a-text text-[15px] text-a-ink placeholder:text-a-ink-soft"
        />
      </div>
      <div className="a-scroll min-h-0 flex-1 overflow-y-auto px-4 pb-4">
        {isEmpty ? (
          <p className="grid h-full place-items-center pb-10 text-center font-a-text text-[19px]">
            {HOTKEY_HINT}
          </p>
        ) : days.length === 0 ? (
          <p className="pt-8 text-center font-a-text text-[15px]">Nothing matches “{query}”</p>
        ) : (
          days.map((day) => (
            <section
              key={day[0].dayLong}
              className="mb-5 grid gap-x-3 last:mb-0 @[560px]:grid-cols-[84px_1fr]"
            >
              <h3 className="mb-1.5 self-start pt-0.5 text-[17px] leading-6 font-bold @[560px]:sticky @[560px]:top-0 @[560px]:mb-0">
                {day[0].dayShort}
              </h3>
              <ul className="flex min-w-0 flex-col gap-1.5">
                {day.map((entry) => (
                  <Strip key={entry.id} entry={entry} onDelete={() => remove(entry.id)} />
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
      <div className="a-oval bg-a-stamp px-5 font-a-ui text-[15px] font-semibold text-white">
        {ERROR_MESSAGE}
      </div>
    )
  }
  const handsfree = state === 'handsfree'
  return (
    <div className={`a-oval bg-a-form text-a-ink ${handsfree ? 'px-1.5' : 'px-5'}`}>
      {handsfree && (
        <button type="button" aria-label="Cancel" className="a-oval-button">
          <IconX />
        </button>
      )}
      <Bars state={state} count={5} className="a-bars" />
      {handsfree && (
        <button type="button" aria-label="Finish" className="a-oval-button bg-a-ink text-a-form">
          <IconCheck />
        </button>
      )}
    </div>
  )
}

export function DirectionA() {
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
