import { useSearchParams } from 'react-router-dom'
import Topbar from '../components/Topbar.jsx'
import ChatPanel from '../components/advisor/ChatPanel.jsx'

export default function Advisor() {
  const [params] = useSearchParams()
  const productId = Number(params.get('productId')) || null
  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <Topbar title="AI Advisor" />
      <div className="mt-1 min-h-0 flex-1 overflow-hidden rounded-card border border-black/5 bg-card shadow-sm">
        <ChatPanel productId={productId} initialQuestion={params.get('q') || ''} />
      </div>
    </div>
  )
}
