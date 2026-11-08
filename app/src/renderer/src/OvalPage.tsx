import { useEffect, useState } from 'react'
import { bridge } from './bridge'

// A placeholder until T7 builds the Oval: it shows the latest state or error as text.
export default function OvalPage(): React.JSX.Element {
  const [text, setText] = useState('idle')
  useEffect(
    () =>
      bridge.onEvent((message) => {
        if (message.type === 'state') setText(String(message.state))
        if (message.type === 'error') setText(String(message.message))
      }),
    []
  )
  return (
    <div className="flex h-screen items-center justify-center truncate rounded-full bg-neutral-900 px-3 text-xs text-white">
      {text}
    </div>
  )
}
