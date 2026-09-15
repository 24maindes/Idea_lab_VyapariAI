import { Package, ShoppingCart, Boxes, AlertTriangle, PlusCircle, Truck, CheckCircle2 } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import Topbar from '../components/Topbar.jsx'
import StatCard from '../components/StatCard.jsx'

const priceTrend = [
  { week: 'Wk 1', price: 42 },
  { week: 'Wk 2', price: 44 },
  { week: 'Wk 3', price: 43 },
  { week: 'Wk 4', price: 46 },
  { week: 'Wk 5', price: 45 },
  { week: 'Wk 6', price: 48 },
]

const activity = [
  { icon: PlusCircle, text: 'Added new product — Basmati Rice 5kg', time: '2h ago' },
  { icon: ShoppingCart, text: 'Purchase recorded — 40kg Wheat', time: '5h ago' },
  { icon: Truck, text: 'Supplier added — Shree Traders', time: '1d ago' },
  { icon: CheckCircle2, text: 'Price checked — Sugar', time: '1d ago' },
]

export default function Dashboard() {
  return (
    <div>
      <Topbar title="Dashboard" />

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard icon={Package} label="Total Products" value="25" tint="primary" />
        <StatCard icon={ShoppingCart} label="Total Purchases" value="12" tint="secondary" />
        <StatCard icon={Boxes} label="Current Stock" value="240 kg" tint="secondary" />
        <StatCard icon={AlertTriangle} label="Price Alerts" value="3" tint="accent" />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-card border border-black/5 rounded-card shadow-sm p-4">
          <h2 className="text-[15px] font-semibold text-ink mb-1">Price Trend — Rice</h2>
          <p className="text-[12px] text-ink/50 mb-3">Purchase price over the last 6 weeks (₹/kg)</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceTrend} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
                <XAxis dataKey="week" tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #24323814', fontSize: 13 }}
                  formatter={(v) => [`₹${v}/kg`, 'Price']}
                />
                <Line type="monotone" dataKey="price" stroke="#0F4C5C" strokeWidth={2.5} dot={{ r: 3, fill: '#0F4C5C' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-card border border-black/5 rounded-card shadow-sm p-4">
          <h2 className="text-[15px] font-semibold text-ink mb-3">Recent Activity</h2>
          <ul className="space-y-3">
            {activity.map(({ icon: Icon, text, time }, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-[8px] bg-secondary/10 text-secondary flex items-center justify-center shrink-0 mt-0.5">
                  <Icon size={14} />
                </div>
                <div>
                  <p className="text-[13px] text-ink leading-snug">{text}</p>
                  <p className="text-[12px] text-ink/45">{time}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
