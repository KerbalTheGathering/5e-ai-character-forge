import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ToastProvider } from './components/Toast'

const rootEl = document.getElementById('root')!

function attachInteractiveEffects() {
  const selector = '.btn, .nav-btn, .tab, .engine-toggle';
  // Cursor-following highlight for glass buttons
  document.addEventListener('pointermove', (e) => {
    const target = (e.target as Element).closest?.(selector) as HTMLElement | null;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    target.style.setProperty('--mx', `${e.clientX - rect.left}px`);
    target.style.setProperty('--my', `${e.clientY - rect.top}px`);
  });
  document.addEventListener(
    'pointerleave',
    (e) => {
      const target = (e.target as Element).closest?.(selector) as HTMLElement | null;
      if (!target) return;
      target.style.removeProperty('--mx');
      target.style.removeProperty('--my');
    },
    true
  );
}

createRoot(rootEl).render(
  <StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </StrictMode>
)

attachInteractiveEffects()
