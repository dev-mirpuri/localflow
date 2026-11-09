import './assets/main.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import HistoryPage from './HistoryPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HistoryPage />
  </StrictMode>
)
