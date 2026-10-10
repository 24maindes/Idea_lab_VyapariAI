import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, RefreshCw, TrendingUp, TrendingDown, Minus, LineChart as LineIcon, Info } from 'lucide-react'
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell,
} from 'recharts'
import Topbar from '../components/Topbar.jsx'
import StatCard from '../components/StatCard.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import { useAppData } from '../context/AppDataContext.jsx'
import { getForecast, getModelTable, getRetrainStatus, retrainModels } from '../api/forecast'
import AskAiButton from '../components/AskAiButton.jsx'
import { pct, rupee, shortDate } from '../utils/format'

const MODEL_LABEL = { naive: 'Naive (yesterday)', linear: 'Linear Regression', rf: 'Random Forest', xgb: 'XGBoost', holt_winters: 'Holt-Winters' }
const DIRECTION = {
  Rising: { tone: 'bg-accent/10 text-accent', Icon: TrendingUp },
  Falling: { tone: 'bg-secondary/10 text-secondary', Icon: TrendingDown },
  Stable: { tone: 'bg-black/5 text-ink/70', Icon: Minus },
}

function ForecastTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  return (
    <div className="rounded-[8px] border border-black/10 bg-card p-3 text-[12px] shadow-sm">
      <p className="font-medium text-ink">{shortDate(r.date)}</p>
      {r.history != null && <p className="text-ink/70">Actual: {rupee(r.history)}</p>}
      {r.forecast != null && (
        <>
          <p className="text-accent">Forecast: {rupee(r.forecast)}</p>
          <p className="text-ink/50">Likely range: {rupee(r.band[0])} to {rupee(r.band[1])}</p>
        </>
      )}
    </div>
  )
}

export default function Forecast() {
  const { products, productsLoading } = useAppData()
  const toast = useToast()
  const linked = useMemo(() => products.filter((p) => p.referenceCommodity), [products])

  const [productId, setProductId] = useState(null)
  const [horizon, setHorizon] = useState(7)
  const [data, setData] = useState(null)
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [retrain, setRetrain] = useState({ state: 'idle' })
  const timer = useRef(null)

  useEffect(() => { if (productId === null && linked.length) setProductId(linked[0].id) }, [linked, productId])

  const load = () => {
    if (productId === null) return
    setLoading(true)
    setError('')
    getForecast(productId, horizon)
      .then((f) => {
        setData(f)
        return f.available ? getModelTable(f.commodity).then(setModels) : setModels([])
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [productId, horizon]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => window.clearInterval(timer.current), [])

  const startRetrain = async () => {
    try {
      await retrainModels(data?.commodity)
    } catch (e) {
      toast.error(e.message)
      return
    }
    setRetrain({ state: 'running' })
    timer.current = window.setInterval(async () => {          // poll every 2 seconds
      try {
        const s = await getRetrainStatus()
        if (s.state !== 'running') {
          window.clearInterval(timer.current)
          setRetrain(s)
          if (s.state === 'done') toast.success(s.message)
          else toast.error(s.message || 'Retraining failed')
          load()
        }
      } catch (e) {
        window.clearInterval(timer.current)
        setRetrain({ state: 'idle' })
        toast.error(e.message)
      }
    }, 2000)
  }

  // one row per date; band = [low, high] for the shaded area. The forecast line starts at the last real price so it connects.
  const chart = useMemo(() => {
    if (!data?.available) return []
    const rows = data.history.map((h) => ({ date: h.date, history: h.price }))
    const last = rows[rows.length - 1]
    last.forecast = last.history
    last.band = [last.history, last.history]
    data.forecast.forEach((f) => rows.push({ date: f.date, forecast: f.price, band: [f.low, f.high] }))
    return rows
  }, [data])

  const dir = DIRECTION[data?.direction] || DIRECTION.Stable
  const day7 = data?.available ? data.forecast[Math.min(6, data.forecast.length - 1)] : null
  const running = retrain.state === 'running'

  if (!productsLoading && linked.length === 0) {
    return (
      <div>
        <Topbar title="Forecast" />
        <div className="rounded-card border border-black/5 bg-card p-10 text-center shadow-sm">
          <LineIcon className="mx-auto mb-3 text-ink/30" size={28} />
          <p className="text-[14px] font-medium text-ink">No product is linked to a market commodity</p>
          <p className="mt-1 text-[12px] text-ink/60">Forecasts need a reference commodity. <Link className="text-secondary underline" to="/products">Link one on the Products page</Link>.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <Topbar title="Forecast" />

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] text-ink/55">Expected market price of the next days ({data?.unit ? `₹ per ${data.unit}` : '₹ per unit'}).</p>
        <div className="flex items-center gap-2">
          <div className="relative">
            <select value={productId ?? ''} onChange={(e) => setProductId(Number(e.target.value))}
              className="appearance-none rounded-[8px] border border-black/10 bg-card py-2 pl-3 pr-9 text-[14px] text-ink shadow-sm focus:outline-none focus:ring-2 focus:ring-secondary/40">
              {linked.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <ChevronDown size={15} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink/40" />
          </div>
          <div className="inline-flex rounded-[8px] border border-black/10 bg-card p-0.5">
            {[7, 14].map((h) => (
              <button key={h} onClick={() => setHorizon(h)} aria-pressed={horizon === h}
                className={`rounded-[6px] px-3 py-1.5 text-[13px] font-medium ${horizon === h ? 'bg-primary text-white' : 'text-ink/70 hover:bg-black/5'}`}>{h} days</button>
            ))}
          </div>
          {data?.available && <AskAiButton productId={data.productId} productName={data.productName} questionKey="forecast" />}
          <button onClick={startRetrain} disabled={running}
            className="flex items-center gap-1.5 rounded-[8px] border border-black/10 bg-card px-3 py-2 text-[13px] font-medium text-ink shadow-sm hover:bg-black/[0.03] disabled:opacity-60">
            <RefreshCw size={14} className={running ? 'animate-spin' : ''} /> {running ? 'Retraining...' : 'Retrain models'}
          </button>
        </div>
      </div>

      {error && <ErrorBox message={error} onRetry={load} />}

      {loading || !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20" />)}</div>
          <Skeleton className="h-80" />
        </div>
      ) : !data.available ? (
        <div className="rounded-card border border-black/5 bg-card p-10 text-center shadow-sm">
          <LineIcon className="mx-auto mb-3 text-ink/30" size={28} />
          <p className="text-[14px] font-medium text-ink">No forecast for {data.productName}</p>
          <p className="mx-auto mt-1 max-w-md text-[12px] text-ink/60">{data.reason}</p>
          <p className="mt-3 text-[12px]"><Link className="text-secondary underline" to="/products">Go to Products</Link></p>
        </div>
      ) : (
        <>
          <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard icon={LineIcon} label="Latest price" value={rupee(data.latestPrice)} tint="primary" />
            <StatCard icon={LineIcon} label={`Predicted in ${day7 ? 7 : horizon} days`} value={rupee(day7?.price)} tint="secondary" />
            <StatCard icon={data.changePct >= 0 ? TrendingUp : TrendingDown} label="Expected change" value={pct(data.changePct, 1)} tint={data.changePct >= 3 ? 'accent' : 'secondary'} />
            <div className="flex items-center gap-3 rounded-card border border-black/5 bg-card p-4 shadow-sm">
              <div className={`flex h-10 w-10 items-center justify-center rounded-[8px] ${dir.tone}`}><dir.Icon size={18} /></div>
              <div>
                <p className="text-[12px] text-ink/60">Direction</p>
                <span className={`mt-0.5 inline-block rounded-full px-2.5 py-0.5 text-[13px] font-semibold ${dir.tone}`}>{data.direction}</span>
              </div>
            </div>
          </div>

          <div className="mb-5 rounded-card border border-black/5 bg-card p-4 shadow-sm">
            <h2 className="mb-1 text-[15px] font-semibold text-ink">Price history and forecast</h2>
            <p className="mb-3 text-[12px] text-ink/50">Solid line: past market price. Dashed line: forecast. Shaded area: likely range (80%).</p>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chart} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} minTickGap={40} />
                  <YAxis domain={['auto', 'auto']} tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${v}`} />
                  <Tooltip content={<ForecastTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 13 }} />
                  <Area dataKey="band" name="Likely range" stroke="none" fill="#E9785B" fillOpacity={0.15} isAnimationActive={false} />
                  <Line dataKey="history" name="Actual price" stroke="#0F4C5C" strokeWidth={2.2} dot={false} isAnimationActive={false} />
                  <Line dataKey="forecast" name="Forecast" stroke="#E9785B" strokeWidth={2.2} strokeDasharray="6 4" dot={false} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
              <h2 className="mb-3 text-[15px] font-semibold text-ink">Model accuracy</h2>
              <p className="text-[12px] text-ink/60">Best model for {data.commodity}</p>
              <p className="text-[18px] font-semibold text-primary">{MODEL_LABEL[data.modelName] || data.modelName}</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-[8px] bg-bg p-3"><p className="text-[11px] text-ink/60">MAPE (average error)</p><p className="text-[16px] font-semibold text-ink">{data.mape != null ? `${data.mape.toFixed(2)}%` : '-'}</p></div>
                <div className="rounded-[8px] bg-bg p-3"><p className="text-[11px] text-ink/60">RMSE</p><p className="text-[16px] font-semibold text-ink">{data.rmse != null ? rupee(data.rmse) : '-'}</p></div>
              </div>
              <p className="mt-3 flex items-start gap-1.5 text-[11px] text-ink/50"><Info size={13} className="mt-0.5 shrink-0" />Forecasts are estimates from past market prices, not guarantees.</p>
            </div>

            <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
              <h2 className="mb-3 text-[15px] font-semibold text-ink">Model comparison</h2>
              <table className="w-full text-left text-[13px]">
                <thead><tr className="text-[11px] uppercase tracking-wide text-ink/50"><th className="py-1.5 font-medium">Model</th><th className="py-1.5 font-medium">MAPE</th><th className="py-1.5 font-medium">RMSE</th></tr></thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.modelName} className={`border-t border-black/5 ${m.isBest ? 'bg-secondary/10 font-medium' : ''}`}>
                      <td className="py-1.5">{MODEL_LABEL[m.modelName] || m.modelName}{m.isBest && <span className="ml-1 text-[11px] text-secondary">best</span>}</td>
                      <td className="py-1.5">{m.mape?.toFixed(2)}%</td><td className="py-1.5">{rupee(m.rmse)}</td>
                    </tr>
                  ))}
                  {models.length === 0 && <tr><td colSpan={3} className="py-3 text-center text-ink/50">No evaluation results yet.</td></tr>}
                </tbody>
              </table>
            </div>

            <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
              <h2 className="mb-3 text-[15px] font-semibold text-ink">MAPE by model (lower is better)</h2>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={models.map((m) => ({ name: MODEL_LABEL[m.modelName]?.split(' ')[0] || m.modelName, mape: m.mape, best: m.isBest }))} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#24323899' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#24323899' }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}%`, 'MAPE']} />
                    <Bar dataKey="mape" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                      {models.map((m) => <Cell key={m.modelName} fill={m.isBest ? '#2A7F8E' : '#0F4C5C55'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
