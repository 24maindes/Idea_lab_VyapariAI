// The advisor chat: messages, suggestions, language switch, microphone, read-aloud, sources and clear.
import { useCallback, useEffect, useRef, useState } from 'react'
import { Mic, MicOff, Send, Volume2, VolumeX, Trash2, ChevronDown, ChevronUp, Sparkles, AlertCircle, RefreshCw, WifiOff } from 'lucide-react'
import { clearHistory, getHistory, sendChat } from '../../api/advisor'
import { LANGS, STRINGS } from '../../advisor/translations'
import useSpeechRecognition from '../../hooks/useSpeechRecognition'
import useSpeechSynthesis from '../../hooks/useSpeechSynthesis'
import { useAuth } from '../../context/AuthContext'
import ConfirmModal from '../ui/ConfirmModal'

const LANG_KEY = 'vyapariAdvisorLang'

function Sources({ sources, label }) {
  const [open, setOpen] = useState(false)
  if (!sources?.length) return null
  return (
    <div className="mt-2">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex items-center gap-1 text-[11px] font-medium text-secondary hover:underline">
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />} {label} ({sources.length})
      </button>
      {open && (
        <ul className="mt-1 space-y-0.5 rounded-[8px] bg-bg p-2 text-[11px] text-ink/70">
          {sources.map((s, i) => (
            <li key={i}><span className="text-ink/50">{s.label}:</span> <span className="font-medium text-ink">{s.value}</span></li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function ChatPanel({ compact = false, productId = null, initialQuestion = '', suggestions: suggestionsOverride }) {
  const { shop } = useAuth()
  const [lang, setLang] = useState(() => localStorage.getItem(LANG_KEY) || shop?.language || 'en')
  const t = STRINGS[lang]
  const speechLang = LANGS.find((l) => l.code === lang).speech

  const [messages, setMessages] = useState([])        // { role, content, sources?, usedFallback?, failed?, question? }
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [confirmClear, setConfirmClear] = useState(false)
  const [voiceNote, setVoiceNote] = useState('')
  const endRef = useRef(null)
  const inputRef = useRef(null)
  const tts = useSpeechSynthesis()

  useEffect(() => { localStorage.setItem(LANG_KEY, lang) }, [lang])

  // load the saved conversation once
  useEffect(() => {
    let alive = true
    getHistory(30)
      .then((h) => alive && setMessages(h.map((m) => ({ role: m.role, content: m.content }))))
      .catch(() => {})
      .finally(() => alive && setLoadingHistory(false))
    return () => { alive = false }
  }, [])

  useEffect(() => { endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' }) }, [messages, sending])

  const send = useCallback(
    async (text) => {
      const question = (text ?? '').trim()
      if (!question || sending) return
      setInput('')
      setVoiceNote('')
      tts.stop()
      setMessages((m) => [...m.filter((x) => !x.failed), { role: 'user', content: question }])
      setSending(true)
      try {
        const r = await sendChat({ message: question, language: lang, ...(productId ? { productId } : {}) })
        setMessages((m) => [...m, { role: 'assistant', content: r.answer, sources: r.sources, usedFallback: r.usedFallback }])
      } catch (e) {
        setMessages((m) => [...m, { role: 'assistant', failed: true, question, content: e.status === 0 ? t.offline : e.message || t.error }])
      } finally {
        setSending(false)
      }
    },
    [lang, productId, sending, t.error, t.offline, tts]
  )

  // a question passed from outside (the "Ask AI" buttons) is sent once
  const sentInitial = useRef('')
  useEffect(() => {
    if (initialQuestion && !loadingHistory && sentInitial.current !== initialQuestion) {
      sentInitial.current = initialQuestion
      send(initialQuestion)
    }
  }, [initialQuestion, loadingHistory, send])

  const mic = useSpeechRecognition({ lang: speechLang, onFinal: (text) => send(text) })
  useEffect(() => {
    const map = { unsupported: t.voiceUnsupported, denied: t.voiceDenied, none: t.voiceNone, error: t.voiceError }
    setVoiceNote(map[mic.error] || '')
  }, [mic.error, t])

  const toggleMic = () => {
    if (mic.listening) mic.stop()
    else { tts.stop(); mic.start() }
  }

  const clear = async () => {
    try { await clearHistory(); setMessages([]) } finally { setConfirmClear(false) }
  }

  const suggestions = suggestionsOverride || t.suggestions
  const showSuggestions = !loadingHistory && messages.length === 0

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* header */}
      <div className="flex items-center justify-between gap-2 border-b border-black/5 px-4 py-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-1.5 truncate text-[15px] font-semibold text-ink"><Sparkles size={15} className="text-accent" />{t.title}</h2>
          {!compact && <p className="mt-0.5 text-[12px] text-ink/55">{t.help}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <div className="inline-flex rounded-[8px] border border-black/10 p-0.5" role="group" aria-label="Language">
            {LANGS.map((l) => (
              <button key={l.code} onClick={() => setLang(l.code)} aria-pressed={lang === l.code} title={l.name}
                className={`rounded-[6px] px-2 py-1 text-[12px] font-semibold ${lang === l.code ? 'bg-primary text-white' : 'text-ink/60 hover:bg-black/5'}`}>{l.label}</button>
            ))}
          </div>
          <button onClick={() => setConfirmClear(true)} disabled={messages.length === 0} title={t.clear} aria-label={t.clear}
            className="rounded-[8px] p-1.5 text-ink/50 hover:bg-black/5 hover:text-accent disabled:opacity-30"><Trash2 size={16} /></button>
        </div>
      </div>

      {/* messages */}
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {loadingHistory && <div className="h-10 animate-pulse rounded-[10px] bg-black/5" />}
        {showSuggestions && (
          <div>
            <p className="mb-2 text-[13px] text-ink/60">{t.empty}</p>
            <p className="mb-1.5 text-[11px] uppercase tracking-wide text-ink/40">{t.askAbout}</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button key={s} onClick={() => send(s)} className="rounded-full border border-secondary/30 bg-secondary/5 px-3 py-1.5 text-[12px] text-secondary hover:bg-secondary/10">{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] whitespace-pre-wrap rounded-[14px] rounded-br-[4px] bg-primary px-3.5 py-2 text-[13px] text-white">{m.content}</div>
            </div>
          ) : (
            <div key={i} className="flex justify-start">
              <div className={`max-w-[92%] rounded-[14px] rounded-bl-[4px] border px-3.5 py-2.5 text-[13px] ${m.failed ? 'border-accent/30 bg-accent/5' : 'border-black/5 bg-white shadow-sm'}`}>
                {m.failed && <p className="mb-1 flex items-center gap-1 font-medium text-accent">{m.content === t.offline ? <WifiOff size={13} /> : <AlertCircle size={13} />}{t.error}</p>}
                <p className="whitespace-pre-wrap text-ink">{m.content}</p>
                {m.failed ? (
                  <button onClick={() => send(m.question)} className="mt-2 flex items-center gap-1 rounded-[8px] border border-black/10 px-2.5 py-1 text-[12px] font-medium"><RefreshCw size={12} />{t.retry}</button>
                ) : (
                  <>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2">
                      {m.usedFallback && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800">{t.basic}</span>}
                      {tts.supported && (
                        <button onClick={() => (tts.speaking ? tts.stop() : tts.speak(m.content, speechLang))}
                          disabled={!tts.hasVoiceFor(speechLang)} title={tts.hasVoiceFor(speechLang) ? t.speak : t.noVoice} aria-label={t.speak}
                          className="rounded-full p-1 text-ink/45 hover:bg-black/5 hover:text-primary disabled:opacity-30">
                          {tts.speaking ? <VolumeX size={14} /> : <Volume2 size={14} />}
                        </button>
                      )}
                    </div>
                    <Sources sources={m.sources} label={t.sources} />
                  </>
                )}
              </div>
            </div>
          )
        )}

        {sending && (
          <div className="flex justify-start">
            <div className="flex items-center gap-1.5 rounded-[14px] rounded-bl-[4px] border border-black/5 bg-white px-3.5 py-3 shadow-sm" role="status" aria-label={t.thinking}>
              {[0, 1, 2].map((d) => <span key={d} className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink/40" style={{ animationDelay: `${d * 0.15}s` }} />)}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* input */}
      <div className="border-t border-black/5 p-3">
        {voiceNote && <p className="mb-2 text-[12px] text-accent">{voiceNote}</p>}
        <form onSubmit={(e) => { e.preventDefault(); send(input) }} className="flex items-end gap-2">
          <div className="relative min-w-0 flex-1">
            <input ref={inputRef} value={mic.listening ? mic.interim : input} onChange={(e) => setInput(e.target.value)} readOnly={mic.listening}
              placeholder={mic.listening ? t.listening : t.placeholder} maxLength={1000} aria-label={t.placeholder}
              className={`w-full rounded-[10px] border bg-white px-3 py-2.5 text-[14px] text-ink focus:outline-none focus:ring-2 focus:ring-secondary/30 ${mic.listening ? 'border-accent' : 'border-black/15'}`} />
          </div>
          {mic.supported && (
            <button type="button" onClick={toggleMic} aria-pressed={mic.listening} title={mic.listening ? t.stopMic : t.mic} aria-label={mic.listening ? t.stopMic : t.mic}
              className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] border ${mic.listening ? 'border-accent bg-accent text-white' : 'border-black/15 bg-white text-ink/70 hover:bg-black/5'}`}>
              {mic.listening && <span className="absolute inset-0 animate-ping rounded-[10px] bg-accent/40" />}
              {mic.listening ? <MicOff size={17} className="relative" /> : <Mic size={17} />}
            </button>
          )}
          <button type="submit" disabled={sending || !input.trim()} aria-label={t.send} title={t.send}
            className="flex h-10 shrink-0 items-center gap-1.5 rounded-[10px] bg-primary px-3.5 text-[13px] font-medium text-white hover:bg-[#0c3e4a] disabled:opacity-50"><Send size={15} /><span className="hidden sm:inline">{t.send}</span></button>
        </form>
        {!mic.supported && <p className="mt-1.5 text-[11px] text-ink/40">{t.voiceUnsupported}</p>}
      </div>

      <ConfirmModal open={confirmClear} title={t.clearTitle} message={t.clearBody} confirmLabel={t.confirm} onConfirm={clear} onCancel={() => setConfirmClear(false)} />
    </div>
  )
}
