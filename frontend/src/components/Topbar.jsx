import { Bell, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import useUnreadAlerts from '../hooks/useUnreadAlerts.js'

function todayLabel() {
  return new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export default function Topbar({ title }) {
  const { shop, user } = useAuth()
  const navigate = useNavigate()
  const unread = useUnreadAlerts()

  return (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-[24px] font-semibold text-ink">{title}</h1>

      <div className="flex items-center gap-4">
        <span className="text-[13px] text-ink/60">{todayLabel()}</span>

        <button
          onClick={() => navigate('/alerts')}
          aria-label={unread ? `${unread} unread alerts` : 'Alerts'}
          className="relative w-9 h-9 rounded-[8px] bg-card border border-black/5 flex items-center justify-center shadow-sm hover:bg-black/[0.02]"
        >
          <Bell size={16} className="text-ink/70" />
          {unread > 0 && (
            <span className="absolute -right-1 -top-1 min-w-[16px] rounded-full bg-accent px-1 text-[10px] font-semibold leading-4 text-white">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </button>

        <div className="flex items-center gap-2 bg-card border border-black/5 rounded-[8px] px-2.5 py-1.5 shadow-sm">
          <div className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center">
            <User size={13} className="text-white" />
          </div>
          <span className="text-[13px] font-medium text-ink">{shop?.shopName || user?.fullName || 'My Shop'}</span>
        </div>
      </div>
    </div>
  )
}
