// Upload a CSV: choose file -> "Check file" (dry run, nothing saved) -> fix errors -> "Import".
import { useRef, useState } from 'react'
import { Upload, Download, FileText, CheckCircle2, XCircle } from 'lucide-react'
import Modal from './ui/Modal.jsx'

const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function upload(kind, file, params) {
  const form = new FormData()
  form.append('file', file)
  const q = new URLSearchParams(params).toString()
  const token = localStorage.getItem('vyapariToken')
  const res = await fetch(`${BASE}/api/import/${kind}?${q}`, { method: 'POST', body: form, headers: token ? { Authorization: `Bearer ${token}` } : {} })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not read the file')
  return data
}

export async function downloadTemplate(kind) {
  const token = localStorage.getItem('vyapariToken')
  const res = await fetch(`${BASE}/api/import/template/${kind}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${kind}_template.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

export default function ImportModal({ kind, title, onClose, onImported, showSupplierOption = false }) {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [createSuppliers, setCreateSuppliers] = useState(false)
  const [skipInvalid, setSkipInvalid] = useState(false)
  const inputRef = useRef(null)

  const opts = (dryRun) => ({ dryRun, createMissingSuppliers: createSuppliers, skipInvalid })

  const run = async (dryRun) => {
    if (!file || busy) return
    setBusy(true); setError('')
    try {
      const r = await upload(kind, file, opts(dryRun))
      setResult(r)
      if (r.imported) onImported?.(r)
    } catch (e) {
      setError(e.message); setResult(null)
    } finally {
      setBusy(false)
    }
  }

  const pick = (f) => { setFile(f); setResult(null); setError('') }
  const canImport = result && !result.imported && result.rowsValid > 0 && (result.rowsInvalid === 0 || skipInvalid)

  return (
    <Modal open title={title} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex items-center justify-between rounded-[8px] bg-bg p-3 text-[12px] text-ink/70">
          <span>Use a CSV file (UTF-8). The first row must be the column names.</span>
          <button onClick={() => downloadTemplate(kind)} className="flex items-center gap-1 font-medium text-secondary hover:underline"><Download size={13} />Template</button>
        </div>

        <button type="button" onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files[0]) pick(e.dataTransfer.files[0]) }}
          className="flex w-full flex-col items-center gap-1 rounded-[10px] border-2 border-dashed border-black/15 p-6 text-[13px] text-ink/60 hover:border-secondary hover:bg-secondary/5">
          {file ? <><FileText size={22} className="text-secondary" /><span className="font-medium text-ink">{file.name}</span><span className="text-[11px]">{(file.size / 1024).toFixed(1)} KB - click to change</span></>
            : <><Upload size={22} /><span>Click to choose a file, or drop it here</span></>}
        </button>
        <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => e.target.files[0] && pick(e.target.files[0])} data-testid="csv-input" />

        {showSupplierOption && (
          <label className="flex items-center gap-2 text-[13px] text-ink"><input type="checkbox" checked={createSuppliers} onChange={(e) => { setCreateSuppliers(e.target.checked); setResult(null) }} />Create suppliers that do not exist yet</label>
        )}
        <label className="flex items-center gap-2 text-[13px] text-ink"><input type="checkbox" checked={skipInvalid} onChange={(e) => setSkipInvalid(e.target.checked)} />Skip rows with errors and import the rest</label>

        {error && <p className="text-[12px] text-accent">{error}</p>}

        {result && (
          <div className={`rounded-[8px] border p-3 text-[13px] ${result.imported ? 'border-secondary/30 bg-secondary/5' : result.errors.length ? 'border-accent/30 bg-accent/5' : 'border-secondary/30 bg-secondary/5'}`}>
            <p className="flex items-center gap-1.5 font-medium text-ink">
              {result.imported || !result.errors.length ? <CheckCircle2 size={15} className="text-secondary" /> : <XCircle size={15} className="text-accent" />}
              {result.message}
            </p>
            <p className="mt-1 text-[12px] text-ink/60">{result.rowsTotal} rows - {result.rowsValid} valid - {result.rowsInvalid} with errors</p>
            {result.errors.length > 0 && (
              <div className="mt-2 max-h-44 overflow-y-auto rounded-[6px] bg-white">
                <table className="w-full text-left text-[12px]">
                  <thead className="sticky top-0 bg-bg text-ink/50"><tr><th className="px-2 py-1">Row</th><th className="px-2 py-1">Field</th><th className="px-2 py-1">Problem</th></tr></thead>
                  <tbody>{result.errors.map((e, i) => <tr key={i} className="border-t border-black/5"><td className="px-2 py-1">{e.row}</td><td className="px-2 py-1">{e.field}</td><td className="px-2 py-1">{e.message}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-[8px] border border-black/15 bg-white px-4 py-2 text-[14px] font-medium text-ink hover:bg-black/5">{result?.imported ? 'Close' : 'Cancel'}</button>
          {!result?.imported && (
            <>
              <button onClick={() => run(true)} disabled={!file || busy} className="rounded-[8px] border border-secondary bg-white px-4 py-2 text-[14px] font-medium text-secondary hover:bg-secondary/5 disabled:opacity-50">{busy ? 'Checking...' : 'Check file'}</button>
              <button onClick={() => run(false)} disabled={!canImport || busy} className="rounded-[8px] bg-primary px-4 py-2 text-[14px] font-medium text-white hover:bg-[#0c3e4a] disabled:opacity-50">Import</button>
            </>
          )}
        </div>
      </div>
    </Modal>
  )
}
