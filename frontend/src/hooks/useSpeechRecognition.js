// Voice input with the browser's Web Speech API (works in Chrome and Edge, not in Firefox).
//   const { supported, listening, interim, error, start, stop } = useSpeechRecognition({ lang: 'hi-IN', onFinal })
// While you speak, `interim` holds the live text. When you stop, onFinal(fullText) is called once.
import { useCallback, useEffect, useRef, useState } from 'react'

const Recognition = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined

export default function useSpeechRecognition({ lang = 'en-IN', onFinal } = {}) {
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [error, setError] = useState('')           // '' | 'unsupported' | 'denied' | 'none' | 'error'
  const recRef = useRef(null)
  const textRef = useRef('')
  const onFinalRef = useRef(onFinal)
  useEffect(() => {
    onFinalRef.current = onFinal
  }, [onFinal])

  const supported = Boolean(Recognition)

  const stop = useCallback(() => {
    recRef.current?.stop()                           // triggers onend, which delivers the final text
  }, [])

  const start = useCallback(() => {
    if (!Recognition) {
      setError('unsupported')
      return
    }
    setError('')
    textRef.current = ''
    setInterim('')
    const rec = new Recognition()
    rec.lang = lang
    rec.continuous = false
    rec.interimResults = true
    rec.onresult = (e) => {
      let text = ''
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript
      textRef.current = text
      setInterim(text)
    }
    rec.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') setError('denied')
      else if (e.error === 'no-speech') setError('none')
      else if (e.error !== 'aborted') setError('error')
    }
    rec.onend = () => {
      setListening(false)
      const text = textRef.current.trim()
      setInterim('')
      if (text) onFinalRef.current?.(text)
    }
    recRef.current = rec
    try {
      rec.start()
      setListening(true)
    } catch {
      setError('error')                              // e.g. start() called twice
      setListening(false)
    }
  }, [lang])

  useEffect(() => () => recRef.current?.abort(), [])  // stop when the component disappears

  return { supported, listening, interim, error, start, stop }
}
