import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { OfflineIndicator } from './components/OfflineIndicator'

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register('/sw.js').catch(() => {
    // Service worker registration failed; app still works without it
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <OfflineIndicator />
    <App />
  </StrictMode>,
)
