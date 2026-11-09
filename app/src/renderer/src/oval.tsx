import './assets/main.css'
import './assets/oval.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import OvalPage from './OvalPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <OvalPage />
  </StrictMode>
)
