import { useEffect, useState } from 'react'
import { bridge } from './bridge'

// A placeholder until T8 builds the History window: one request shows the relay works.
export default function HistoryPage(): React.JSX.Element {
  const [count, setCount] = useState<number | null>(null)
  useEffect(() => {
    bridge.request('list_history', { query: '', limit: 200 }).then((entries) => {
      setCount((entries as unknown[]).length)
    })
  }, [])
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">LocalFlow</h1>
      <p>{count === null ? 'Loading History…' : `${count} Entries`}</p>
    </main>
  )
}
