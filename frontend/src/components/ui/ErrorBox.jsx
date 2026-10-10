import { AlertCircle, RefreshCw } from 'lucide-react'

export default function ErrorBox({ message, onRetry }) {
  return (
    <div className="mb-5 flex items-start gap-3 rounded-card border border-accent/30 bg-accent/5 p-4 text-[13px] text-ink">
      <AlertCircle size={18} className="mt-0.5 shrink-0 text-accent" />
      <div className="flex-1">
        <p className="font-medium">Something went wrong</p>
        <p className="text-[12px] text-ink/70">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="flex items-center gap-1 rounded-[8px] border border-black/10 bg-card px-3 py-1.5 text-[12px] font-medium">
          <RefreshCw size={12} /> Retry
        </button>
      )}
    </div>
  )
}
