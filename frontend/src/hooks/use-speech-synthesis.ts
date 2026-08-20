import { useCallback, useEffect, useRef, useState } from 'react'

/** Voices load asynchronously on most browsers (empty on first call until
 * the 'voiceschanged' event fires) — this waits for that instead of racing
 * it, but resolves immediately if the list is already populated. */
function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  const existing = window.speechSynthesis.getVoices()
  if (existing.length > 0) return Promise.resolve(existing)
  return new Promise((resolve) => {
    const handler = () => {
      window.speechSynthesis.removeEventListener('voiceschanged', handler)
      resolve(window.speechSynthesis.getVoices())
    }
    window.speechSynthesis.addEventListener('voiceschanged', handler)
    // Some browsers never fire the event if there's genuinely nothing to
    // report — don't hang the caller forever.
    setTimeout(() => resolve(window.speechSynthesis.getVoices()), 1500)
  })
}

/** Picks the most natural-sounding voice available for `lang`. Android
 * Chrome's default pick is often a flat local/offline voice even when a
 * much better cloud "Google" voice (e.g. "Google português do Brasil") is
 * installed on the same device — this ranks candidates instead of trusting
 * the browser's default. */
function pickBestVoice(voices: SpeechSynthesisVoice[], lang: string): SpeechSynthesisVoice | undefined {
  const base = lang.split('-')[0].toLowerCase()
  const matches = voices.filter((v) => v.lang.toLowerCase() === lang.toLowerCase())
  const sameLanguage = matches.length > 0 ? matches : voices.filter((v) => v.lang.toLowerCase().startsWith(base))
  if (sameLanguage.length === 0) return undefined

  const score = (v: SpeechSynthesisVoice) => {
    const name = v.name.toLowerCase()
    let s = 0
    // Cloud "Google" voices (Android Chrome) and platform-neural voices
    // (Natural/Enhanced on iOS/Edge) sound far less robotic than the
    // offline espeak-style default.
    if (name.includes('google')) s += 3
    if (name.includes('natural') || name.includes('neural') || name.includes('enhanced') || name.includes('premium')) s += 3
    if (!v.localService) s += 1 // network voices are usually the higher-quality tier
    if (v.lang.toLowerCase() === lang.toLowerCase()) s += 1 // exact regional match over a same-language fallback
    return s
  }
  return [...sameLanguage].sort((a, b) => score(b) - score(a))[0]
}

/** Browser-native text-to-speech (Web Speech API). Requires a secure
 * context; `supported` silently reports false elsewhere, same convention
 * as use-speech-recognition. */
export function useSpeechSynthesis(lang = 'pt-BR') {
  const [supported] = useState(() => typeof window !== 'undefined' && 'speechSynthesis' in window)
  const [speaking, setSpeaking] = useState(false)
  const voiceRef = useRef<SpeechSynthesisVoice | undefined>(undefined)
  // Guards against a stale utterance's onend firing after a newer speak()
  // call (or after stop()) already moved state on — e.g. voice mode was
  // toggled off mid-sentence.
  const currentIdRef = useRef(0)

  useEffect(() => {
    if (!supported) return
    let cancelled = false
    loadVoices().then((voices) => {
      if (!cancelled) voiceRef.current = pickBestVoice(voices, lang)
    })
    return () => {
      cancelled = true
    }
  }, [lang, supported])

  const speak = useCallback(
    (text: string, onDone?: () => void) => {
      if (!supported || !text.trim()) {
        onDone?.()
        return
      }
      window.speechSynthesis.cancel()
      const id = ++currentIdRef.current
      const utter = new SpeechSynthesisUtterance(text)
      utter.lang = lang
      if (voiceRef.current) utter.voice = voiceRef.current
      const finish = () => {
        if (currentIdRef.current !== id) return
        setSpeaking(false)
        onDone?.()
      }
      utter.onend = finish
      utter.onerror = finish
      setSpeaking(true)
      window.speechSynthesis.speak(utter)
    },
    [lang, supported],
  )

  const stop = useCallback(() => {
    currentIdRef.current++ // invalidate any in-flight onend/onerror
    if (supported) window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [supported])

  useEffect(() => {
    return () => {
      if (supported) window.speechSynthesis.cancel()
    }
  }, [supported])

  return { supported, speaking, speak, stop }
}
