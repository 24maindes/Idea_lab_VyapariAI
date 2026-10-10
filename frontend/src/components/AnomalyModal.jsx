// Shown after saving a purchase that looks abnormal. The purchase IS already saved: the user can keep it or undo it.
import { AlertTriangle } from 'lucide-react'

const SEVERITY = {
  high: 'bg-accent text-white',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-ink/10 text-ink/70',
}

export default function AnomalyModal({ anomaly, busy, onKeep, onUndo }) {
  if (!anomaly) return null
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-ink/40 px-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-card bg-white p-5 shadow-card">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/10">
            <AlertTriangle size={20} className="text-accent" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-[16px] font-semibold text-ink">This price looks unusual</h3>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${SEVERITY[anomaly.severity] || SEVERITY.low}`}>
                {anomaly.severity}
              </span>
            </div>
            <p className="mt-1.5 text-[13px] text-ink/75">{anomaly.message}</p>
            <p className="mt-2 text-[12px] text-ink/50">
              The purchase is saved. If you typed the price wrongly, undo it and enter it again.
            </p>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onUndo} disabled={busy} className="rounded-control border border-accent/40 bg-white px-4 py-2 text-[14px] font-medium text-accent hover:bg-accent/5 disabled:opacity-50">
            {busy ? 'Working...' : 'Undo (delete this purchase)'}
          </button>
          <button onClick={onKeep} disabled={busy} className="rounded-control bg-primary px-4 py-2 text-[14px] font-medium text-white hover:bg-[#0c3e4a] disabled:opacity-50">
            Keep purchase
          </button>
        </div>
      </div>
    </div>
  )
}
