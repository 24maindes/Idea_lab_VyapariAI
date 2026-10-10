// Read answers aloud with the browser's speech synthesis.
//   const { speak, stop, speaking, hasVoiceFor } = useSpeechSynthesis()
//   speak(text, 'hi-IN')
import { useCallback, useEffect, useState } from 'react'

const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined

export default function useSpeechSynthesis() {
  const [voices, setVoices] = useState([])
  const [speaking, setSpeaking] = useState(false)

  useEffect(() => {
    if (!synth) return undefined
    const load = () => setVoices(synth.getVoices())         // voices load late in Chrome, so listen for the event
    load()
    synth.addEventListener?.('voiceschanged', load)
    return () => {
      synth.removeEventListener?.('voiceschanged', load)
      synth.cancel()
    }
  }, [])

  const voiceFor = useCallback(
    (lang) => {
      const base = lang.split('-')[0].toLowerCase()
      return voices.find((v) => v.lang.toLowerCase() === lang.toLowerCase()) || voices.find((v) => v.lang.toLowerCase().startsWith(base)) || null
    },
    [voices]
  )

  const stop = useCallback(() => {
    synth?.cancel()
    setSpeaking(false)
  }, [])

  const speak = useCallback(
    (text, lang) => {
      if (!synth || !text) return false
      synth.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.lang = lang
      const v = voiceFor(lang)
      if (v) u.voice = v
      u.onend = () => setSpeaking(false)
      u.onerror = () => setSpeaking(false)
      setSpeaking(true)
      synth.speak(u)
      return true
    },
    [voiceFor]
  )

  return { supported: Boolean(synth), speak, stop, speaking, hasVoiceFor: (lang) => Boolean(voiceFor(lang)) }
}
