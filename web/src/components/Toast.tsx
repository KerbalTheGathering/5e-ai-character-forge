import { createContext, useContext, useState, ReactNode, useCallback } from 'react';

type Toast = { id: number; message: string; type?: 'success'|'error'|'info' };
const ToastCtx = createContext<{ push:(msg:string,type?:Toast['type'])=>void }|null>(null);

export function ToastProvider({ children }: { children: ReactNode }){
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Date.now() + Math.random();
    setToasts(t => [...t, { id, message, type }]);
    setTimeout(()=> setToasts(t => t.filter(x=>x.id!==id)), 3000);
  },[]);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div style={{position:'fixed', right:16, bottom:16, display:'flex', flexDirection:'column', gap:8, zIndex:1000}}>
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast(){
  const ctx = useContext(ToastCtx); if (!ctx) throw new Error('ToastProvider missing');
  return ctx;
}

