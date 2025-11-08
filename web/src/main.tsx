import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ToastProvider } from './components/Toast'

const rootEl = document.getElementById('root')!

const Fallback = (
  <StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </StrictMode>
)

;(async () => {
  try {
    const rq = await import('@tanstack/react-query')
    const dev = await import('@tanstack/react-query-devtools')
    const qc = new rq.QueryClient()
    createRoot(rootEl).render(
      <StrictMode>
        <rq.QueryClientProvider client={qc}>
          <ToastProvider>
            <App />
          </ToastProvider>
          <dev.ReactQueryDevtools initialIsOpen={false} />
        </rq.QueryClientProvider>
      </StrictMode>
    )
  } catch {
    createRoot(rootEl).render(Fallback)
  }
})()
