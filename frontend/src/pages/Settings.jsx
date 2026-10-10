import { useEffect, useState } from 'react'
import { Save, KeyRound, Store, SlidersHorizontal } from 'lucide-react'
import Topbar from '../components/Topbar.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import { apiFetch } from '../api/client'

// range of every setting (same limits as the backend, so errors are shown before saving)
const RULES = {
  targetMarginPct: { label: 'Target margin (%)', min: 0, max: 100, step: 1, help: 'The profit you would like on every sale.' },
  minMarginPct: { label: 'Minimum margin (%)', min: 0, max: 100, step: 1, help: 'Never sell with less profit than this.' },
  leadTimeDays: { label: 'Supplier delivery time (days)', min: 0, max: 30, step: 1, help: 'How many days a supplier takes to deliver.' },
  coverDays: { label: 'Stock to keep (days)', min: 1, max: 90, step: 1, help: 'How many days of sales you want in stock.' },
  anomalyThresholdPct: { label: 'Price alert limit (%)', min: 5, max: 50, step: 1, help: 'Alert when a price is this far from the market price.' },
  zCutoff: { label: 'Alert sensitivity (z-score)', min: 1.5, max: 4, step: 0.1, help: 'Lower = more alerts, higher = fewer alerts. 2.5 is a good start.' },
}
const SHOP_TYPES = ['Kirana Store', 'General Store', 'Grocery', 'Supermarket', 'Vegetable Shop', 'Other']
const input = 'w-full rounded-[8px] border border-black/15 bg-white px-3 py-2 text-[14px] text-ink focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary/20'

function Card({ icon: Icon, title, children }) {
  return (
    <div className="mb-5 rounded-card border border-black/5 bg-card p-5 shadow-sm">
      <h2 className="mb-4 flex items-center gap-2 text-[15px] font-semibold text-ink"><Icon size={16} className="text-secondary" />{title}</h2>
      {children}
    </div>
  )
}

export default function Settings() {
  const { shop, saveShop } = useAuth()
  const toast = useToast()
  const [form, setForm] = useState(null)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [pw, setPw] = useState({ oldPassword: '', newPassword: '', confirm: '' })
  const [pwError, setPwError] = useState('')
  const [pwSaving, setPwSaving] = useState(false)

  useEffect(() => { if (shop) setForm({ ...shop }) }, [shop])
  if (!form) return null

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.shopName?.trim()) e.shopName = 'Shop name is required'
    Object.entries(RULES).forEach(([k, r]) => {
      const v = Number(form[k])
      if (form[k] === '' || Number.isNaN(v)) e[k] = 'Enter a number'
      else if (v < r.min || v > r.max) e[k] = `Must be between ${r.min} and ${r.max}`
    })
    if (!e.minMarginPct && !e.targetMarginPct && Number(form.minMarginPct) > Number(form.targetMarginPct)) e.minMarginPct = 'Minimum margin cannot be higher than the target margin'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const save = async (e) => {
    e.preventDefault()
    if (saving || !validate()) return
    setSaving(true)
    try {
      const body = { shopName: form.shopName.trim(), shopType: form.shopType || null, location: (form.location || '').trim() || null, language: form.language }
      Object.keys(RULES).forEach((k) => { body[k] = Number(form[k]) })
      await saveShop(body)
      toast.success('Settings saved')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const changePassword = async (e) => {
    e.preventDefault()
    setPwError('')
    if (pw.newPassword.length < 6) return setPwError('The new password must have at least 6 characters.')
    if (pw.newPassword !== pw.confirm) return setPwError('The new passwords do not match.')
    setPwSaving(true)
    try {
      await apiFetch('/api/auth/password', { method: 'PUT', body: { oldPassword: pw.oldPassword, newPassword: pw.newPassword } })
      setPw({ oldPassword: '', newPassword: '', confirm: '' })
      toast.success('Password changed')
    } catch (err) {
      setPwError(err.message)
    } finally {
      setPwSaving(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <Topbar title="Settings" />
      <form onSubmit={save} noValidate>
        <Card icon={Store} title="Shop">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="text-[13px] font-medium text-ink/80">Shop name
              <input className={`${input} mt-1.5 ${errors.shopName ? '!border-accent' : ''}`} value={form.shopName || ''} onChange={(e) => set('shopName', e.target.value)} />
              {errors.shopName && <span className="text-[12px] font-normal text-accent">{errors.shopName}</span>}
            </label>
            <label className="text-[13px] font-medium text-ink/80">Shop type
              <select className={`${input} mt-1.5`} value={form.shopType || ''} onChange={(e) => set('shopType', e.target.value)}>
                <option value="">Select</option>{SHOP_TYPES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            <label className="text-[13px] font-medium text-ink/80">Location
              <input className={`${input} mt-1.5`} value={form.location || ''} onChange={(e) => set('location', e.target.value)} />
            </label>
            <label className="text-[13px] font-medium text-ink/80">Advisor language
              <select className={`${input} mt-1.5`} value={form.language} onChange={(e) => set('language', e.target.value)}>
                <option value="en">English</option><option value="hi">हिन्दी (Hindi)</option><option value="mr">मराठी (Marathi)</option>
              </select>
            </label>
          </div>
        </Card>

        <Card icon={SlidersHorizontal} title="Business rules">
          <p className="mb-4 text-[12px] text-ink/55">These numbers change the advice you get: how much to buy, what to sell at, and when to raise a price alert.</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {Object.entries(RULES).map(([k, r]) => (
              <label key={k} className="text-[13px] font-medium text-ink/80">{r.label}
                <input type="number" min={r.min} max={r.max} step={r.step} className={`${input} mt-1.5 ${errors[k] ? '!border-accent' : ''}`} value={form[k] ?? ''} onChange={(e) => set(k, e.target.value)} />
                <span className="block text-[11px] font-normal text-ink/45">{r.help} ({r.min} to {r.max})</span>
                {errors[k] && <span className="text-[12px] font-normal text-accent">{errors[k]}</span>}
              </label>
            ))}
          </div>
        </Card>

        <button type="submit" disabled={saving} className="mb-8 flex items-center gap-2 rounded-[8px] bg-primary px-5 py-2.5 text-[14px] font-medium text-white hover:bg-[#0c3e4a] disabled:opacity-60">
          <Save size={15} /> {saving ? 'Saving...' : 'Save settings'}
        </button>
      </form>

      <form onSubmit={changePassword} noValidate>
        <Card icon={KeyRound} title="Change password">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <label className="text-[13px] font-medium text-ink/80">Current password<input type="password" autoComplete="current-password" className={`${input} mt-1.5`} value={pw.oldPassword} onChange={(e) => setPw({ ...pw, oldPassword: e.target.value })} /></label>
            <label className="text-[13px] font-medium text-ink/80">New password<input type="password" autoComplete="new-password" className={`${input} mt-1.5`} value={pw.newPassword} onChange={(e) => setPw({ ...pw, newPassword: e.target.value })} /></label>
            <label className="text-[13px] font-medium text-ink/80">Repeat new password<input type="password" autoComplete="new-password" className={`${input} mt-1.5`} value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></label>
          </div>
          {pwError && <p className="mt-3 text-[12px] text-accent">{pwError}</p>}
          <button type="submit" disabled={pwSaving || !pw.oldPassword} className="mt-4 rounded-[8px] border border-black/15 bg-white px-4 py-2 text-[13px] font-medium text-ink hover:bg-black/5 disabled:opacity-50">{pwSaving ? 'Changing...' : 'Change password'}</button>
        </Card>
      </form>
    </div>
  )
}
