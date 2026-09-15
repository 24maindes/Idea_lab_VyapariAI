import { Bell, User } from 'lucide-react'

function todayLabel() {
  return new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export default function Topbar({ title }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-[24px] font-semibold text-ink">{title}</h1>

      <div className="flex items-center gap-4">
        <span className="text-[13px] text-ink/60">{todayLabel()}</span>

        <button className="w-9 h-9 rounded-[8px] bg-card border border-black/5 flex items-center justify-center shadow-sm hover:bg-black/[0.02]">
          <Bell size={16} className="text-ink/70" />
        </button>

        <div className="flex items-center gap-2 bg-card border border-black/5 rounded-[8px] px-2.5 py-1.5 shadow-sm">
          <div className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center">
            <User size={13} className="text-white" />
          </div>
          <span className="text-[13px] font-medium text-ink">Ramesh Kirana</span>
        </div>
      </div>
    </div>
  )
}
