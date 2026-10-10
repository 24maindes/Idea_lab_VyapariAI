// Live "is this price fair?" hint under the price field. Hidden when the check fails or there is nothing to say.
import { useEffect, useState } from 'react'
import { checkPrice } from '../api/analysis'

const STYLE = {
  'Great deal': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Fair: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Slightly high': 'bg-amber-50 text-amber-800 border-amber-200',
  Overpaying: 'bg-red-50 text-red-700 border-red-200',
}

export default function FairPriceChip({ productId, price, date }) {
  const [result, setResult] = useState(null)

  useEffect(() => {
    setResult(null)
    if (!productId || !(Number(price) > 0)) return undefined
    let alive = true
    const timer = window.setTimeout(() => {
      checkPrice({ productId, price, date })
        .then((r) => alive && setResult(r))
        .catch(() => alive && setResult(null))             // on any failure the chip simply stays hidden
    }, 400)                                                 // debounce: wait until the user stops typing
    return () => {
      alive = false
      window.clearTimeout(timer)
    }
  }, [productId, price, date])

  if (!result || !result.hasMarketData || !result.verdict) return null
  return (
    <div className={`mt-1.5 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] ${STYLE[result.verdict]}`}>
      <span className="font-semibold">{result.verdict}</span>
      <span className="opacity-80">· {result.message}</span>
    </div>
  )
}
