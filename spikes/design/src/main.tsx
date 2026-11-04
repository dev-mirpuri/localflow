import { createRoot } from 'react-dom/client'
import { DirectionA } from './a'
import { DirectionB } from './b'
import { DirectionC } from './c'
import './index.css'

const routes = [
  { href: '/a', label: 'A: Wire', page: <DirectionA /> },
  { href: '/b', label: 'B: Caption', page: <DirectionB /> },
  { href: '/c', label: 'C: Plain', page: <DirectionC /> }
]
const route = routes.find((r) => window.location.pathname.startsWith(r.href)) ?? routes[0]
if (window.location.pathname === '/') window.history.replaceState(null, '', '/a')
document.title = route.label

createRoot(document.getElementById('root')!).render(
  <div className="min-h-screen bg-spike px-4 py-5 text-white lg:px-8">
    <nav
      aria-label="Directions"
      className="mx-auto mb-5 flex max-w-[1392px] gap-1 text-sm font-medium"
    >
      {routes.map((r) => (
        <a
          key={r.href}
          href={r.href}
          aria-current={r === route ? 'page' : undefined}
          className={`rounded px-3 py-1.5 ${r === route ? 'bg-white text-black' : 'text-white hover:bg-white/15'}`}
        >
          {r.label}
        </a>
      ))}
    </nav>
    {route.page}
  </div>
)
