// Small toast notifications: const toast = useToast(); toast.success('Saved'); toast.error(err.message)
import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { CheckCircle2, AlertCircle, X } from 'lucide-react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(1)

  const remove = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), [])
  const push = useCallback(
    (type, message) => {
      const id = nextId.current++
      setToasts((t) => [...t.slice(-3), { id, type, message }])          // keep at most 4 on screen
      window.setTimeout(() => remove(id), type === 'error' ? 6000 : 3500)
    },
    [remove]
  )
  const api = useMemo(() => ({ success: (m) => push('success', m), error: (m) => push('error', m) }), [push])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-[100] flex w-[340px] flex-col gap-2" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-2.5 rounded-[10px] border px-3.5 py-3 text-[13px] shadow-lg ${
              t.type === 'error' ? 'border-accent/40 bg-white text-ink' : 'border-secondary/30 bg-white text-ink'
            }`}
          >
            {t.type === 'error' ? (
              <AlertCircle size={16} className="mt-0.5 shrink-0 text-accent" />
            ) : (
              <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-secondary" />
            )}
            <span className="flex-1">{t.message}</span>
            <button onClick={() => remove(t.id)} className="text-ink/40 hover:text-ink" aria-label="Dismiss">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
