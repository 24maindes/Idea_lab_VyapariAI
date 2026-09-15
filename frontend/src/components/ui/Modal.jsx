import { X } from 'lucide-react'
import { useEffect } from 'react'

export default function Modal({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-[#0F4C5C]/30">
      <button
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 cursor-default"
      />
      <div className="relative flex h-full w-full max-w-md flex-col bg-card shadow-xl animate-[slideIn_0.18s_ease-out]">
        <div className="flex items-center justify-between border-b border-[#E7E9E4] px-6 py-4">
          <h2 className="text-[18px] font-semibold text-primary">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-[8px] p-1.5 text-[#6B7A7E] hover:bg-[#F1F2EF]"
            aria-label="Close panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </div>
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(24px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
