// Small centered "Are you sure?" dialog used before deleting things.
import { AlertTriangle } from 'lucide-react'

export default function ConfirmModal({ open, title, message, confirmLabel = 'Delete', busy = false, onConfirm, onCancel }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-ink/40 px-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-card bg-white p-5 shadow-card">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent/10">
            <AlertTriangle size={18} className="text-accent" />
          </div>
          <div>
            <h3 className="text-[16px] font-semibold text-ink">{title}</h3>
            <p className="mt-1 text-[13px] text-ink/70">{message}</p>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onCancel} disabled={busy} className="rounded-control border border-ink/15 bg-white px-4 py-2 text-[14px] font-medium text-ink hover:bg-ink/5 disabled:opacity-50">
            Cancel
          </button>
          <button onClick={onConfirm} disabled={busy} className="rounded-control bg-accent px-4 py-2 text-[14px] font-medium text-white hover:bg-[#d96745] disabled:opacity-50">
            {busy ? 'Working...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
