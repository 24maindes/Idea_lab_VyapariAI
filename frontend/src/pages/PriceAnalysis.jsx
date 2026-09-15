import { useState } from 'react'
import { AlertTriangle, CheckCircle2, ChevronDown } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import Topbar from '../components/Topbar.jsx'

const productData = {
  Rice: { purchase: 48, reference: 45, unit: 'kg' },
  Wheat: { purchase: 32, reference: 34, unit: 'kg' },
  Sugar: { purchase: 41, reference: 41, unit: 'kg' },
  Oil: { purchase: 128, reference: 120, unit: 'L' },
}

export default function PriceAnalysis() {
  const [product, setProduct] = useState('Rice')
  const { purchase, reference, unit } = productData[product]
  const diff = purchase - reference
  const isHigher = diff > 0
  const isEqual = diff === 0

  const chartData = [{ name: product, Purchase: purchase, Reference: reference }]

  return (
    <div>
      <Topbar title="Price Analysis" />

      <div className="flex items-center justify-between mb-5">
        <p className="text-[13px] text-ink/55">
          Compare your purchase price against a reference market price. This is a static comparison, not a prediction.
        </p>

        <div className="relative">
          <select
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            className="appearance-none bg-card border border-black/10 rounded-[8px] pl-3 pr-9 py-2 text-[14px] text-ink shadow-sm focus:outline-none focus:ring-2 focus:ring-secondary/40"
          >
            {Object.keys(productData).map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <ChevronDown size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40 pointer-events-none" />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-5">
        <div className="bg-card border border-black/5 rounded-card shadow-sm p-4">
          <p className="text-[12px] text-ink/60 mb-1">Your Purchase Price</p>
          <p className="text-[20px] font-semibold text-ink">₹{purchase}/{unit}</p>
        </div>
        <div className="bg-card border border-black/5 rounded-card shadow-sm p-4">
          <p className="text-[12px] text-ink/60 mb-1">Reference Market Price</p>
          <p className="text-[20px] font-semibold text-ink">₹{reference}/{unit}</p>
        </div>
        <div className="bg-card border border-black/5 rounded-card shadow-sm p-4">
          <p className="text-[12px] text-ink/60 mb-1">Difference</p>
          <p className={`text-[20px] font-semibold ${isHigher ? 'text-accent' : 'text-secondary'}`}>
            {diff > 0 ? '+' : ''}₹{diff}/{unit}
          </p>
        </div>
      </div>

      <div
        className={`flex items-center gap-2.5 rounded-card border px-4 py-3 mb-5 text-[13px]
          ${isEqual ? 'bg-secondary/5 border-secondary/20 text-secondary' : isHigher ? 'bg-accent/5 border-accent/20 text-accent' : 'bg-secondary/5 border-secondary/20 text-secondary'}
        `}
      >
        {isEqual ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
        <span className="font-medium">
          {isEqual
            ? 'Purchase price matches the reference market price.'
            : isHigher
            ? 'Purchase price is higher than the reference market price.'
            : 'Purchase price is lower than the reference market price.'}
        </span>
      </div>

      <div className="bg-card border border-black/5 rounded-card shadow-sm p-4">
        <h2 className="text-[15px] font-semibold text-ink mb-1">Price Comparison</h2>
        <p className="text-[12px] text-ink/50 mb-3">Purchase price vs reference price for {product}</p>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: -15, bottom: 0 }} barGap={10}>
              <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #24323814', fontSize: 13 }}
                formatter={(v) => [`₹${v}/${unit}`, '']}
              />
              <Legend wrapperStyle={{ fontSize: 13 }} />
              <Bar dataKey="Purchase" fill="#0F4C5C" radius={[6, 6, 0, 0]} barSize={48} />
              <Bar dataKey="Reference" fill="#E9785B" radius={[6, 6, 0, 0]} barSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
