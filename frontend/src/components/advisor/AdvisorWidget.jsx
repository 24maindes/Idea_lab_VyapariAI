// Floating "Ask AI" button + chat window, available on every page except the Advisor page itself.
// Other pages can open it with a question:  openAdvisor({ productId, question })
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { MessageCircle, X } from 'lucide-react'
import ChatPanel from './ChatPanel'

export const openAdvisor = (detail = {}) => window.dispatchEvent(new CustomEvent('vyapari-open-advisor', { detail }))

export default function AdvisorWidget() {
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [request, setRequest] = useState({ productId: null, question: '', nonce: 0 })

  useEffect(() => {
    const handler = (e) => {
      setRequest({ productId: e.detail?.productId ?? null, question: e.detail?.question ?? '', nonce: Date.now() })
      setOpen(true)
    }
    window.addEventListener('vyapari-open-advisor', handler)
    return () => window.removeEventListener('vyapari-open-advisor', handler)
  }, [])

  if (location.pathname === '/advisor') return null
  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[560px] max-h-[calc(100vh-7rem)] w-[400px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-card border border-black/10 bg-card shadow-2xl" role="dialog" aria-label="AI advisor">
          <button onClick={() => setOpen(false)} aria-label="Close" className="absolute right-2 top-2 z-10 hidden rounded-full p-1 text-ink/40 hover:bg-black/5 sm:hidden"><X size={16} /></button>
          <ChatPanel compact productId={request.productId} initialQuestion={request.question} key={request.nonce} />
        </div>
      )}
      <button onClick={() => setOpen((o) => !o)} aria-label={open ? 'Close advisor' : 'Open advisor'} aria-expanded={open}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-white shadow-lg transition-transform hover:scale-105">
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </>
  )
}
