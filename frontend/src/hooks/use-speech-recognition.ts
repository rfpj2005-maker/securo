import { useCallback, useEffect, useRef, useState } from 'react'

// Minimal shape of the Web Speech API the browser gives us — TypeScript's
// DOM lib doesn't ship types for this experimental API.
interface SpeechRecognitionResultLike {
  isFinal: boolean
  [index: number]: { transcript: string }
}

interface SpeechRecognitionEventLike extends Event {
  results: ArrayLike<SpeechRecognitionResultLike>
}

interface SpeechRecognitionLike extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  start: () => void
  stop: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: Event) => void) | null
  onend: (() => void) | null
}

interface SpeechWindow extends Window {
  SpeechRecognition?: new () => SpeechRecognitionLike
  webkitSpeechRecognition?: new () => SpeechRecognitionLike
}

function getSpeechRecognition(): (new () => SpeechRecognitionLike) | null {
  const w = window as SpeechWindow
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

/** Browser-native speech-to-text (Chrome/Edge). Requires a secure context
 * (HTTPS or localhost) — silently reports `supported: false` elsewhere. */
export function useSpeechRecognition(lang = 'pt-BR') {
  const [supported] = useState(() => !!getSpeechRecognition())
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)

  useEffect(() => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    recognition.lang = lang
    recognition.continuous = false
    recognition.interimResults = true
    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      let text = ''
      for (let i = 0; i < event.results.length; i++) {
        text += event.results[i][0].transcript
      }
      setTranscript(text)
    }
    recognition.onerror = () => setListening(false)
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    return () => recognition.stop()
  }, [lang])

  const start = useCallback(() => {
    if (!recognitionRef.current) return
    setTranscript('')
    setListening(true)
    recognitionRef.current.start()
  }, [])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
  }, [])

  const resetTranscript = useCallback(() => setTranscript(''), [])

  return { supported, listening, transcript, setTranscript, start, stop, resetTranscript }
}
