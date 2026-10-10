// Number of unread alerts for the sidebar badge. Refreshes on every route change and every 60 seconds.
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { getAlertCount } from '../api/anomalies'

export const ALERTS_CHANGED = 'vyapari-alerts-changed'      // pages dispatch this after marking alerts as read

export default function useUnreadAlerts() {
  const [count, setCount] = useState(0)
  const location = useLocation()

  useEffect(() => {
    let alive = true
    const load = () =>
      getAlertCount()
        .then((r) => alive && setCount(r.unread))
        .catch(() => {})                                       // a badge must never show an error
    load()
    const timer = window.setInterval(load, 60000)
    window.addEventListener(ALERTS_CHANGED, load)
    return () => {
      alive = false
      window.clearInterval(timer)
      window.removeEventListener(ALERTS_CHANGED, load)
    }
  }, [location.pathname])

  return count
}
