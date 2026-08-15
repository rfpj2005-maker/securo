import { useCallback, useEffect, useRef, useState } from 'react'

export type RecordSource = 'mic' | 'tab_audio'

function pickMimeType(): string {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  for (const c of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(c)) return c
  }
  return ''
}

/** Records mic audio (in-person) or shared tab/system audio (online calls),
 * optionally mixed with the mic via Web Audio so both sides of an online
 * call get captured. Returns the finished recording as a Blob on stop(). */
export function useMeetingRecorder() {
  const [recording, setRecording] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamsRef = useRef<MediaStream[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const stopResolveRef = useRef<((blob: Blob | null) => void) | null>(null)

  const supported =
    typeof window !== 'undefined' &&
    typeof MediaRecorder !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia

  const cleanup = useCallback(() => {
    streamsRef.current.forEach((s) => s.getTracks().forEach((t) => t.stop()))
    streamsRef.current = []
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {})
      audioCtxRef.current = null
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const start = useCallback(async (source: RecordSource, includeMic = false) => {
    setError(null)
    chunksRef.current = []
    let finalStream: MediaStream

    if (source === 'mic') {
      const mic = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamsRef.current.push(mic)
      finalStream = mic
    } else {
      const display = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })
      streamsRef.current.push(display)
      const audioTracks = display.getAudioTracks()
      if (audioTracks.length === 0) {
        cleanup()
        throw new Error('no_tab_audio')
      }
      if (includeMic) {
        const mic = await navigator.mediaDevices.getUserMedia({ audio: true })
        streamsRef.current.push(mic)
        const ctx = new AudioContext()
        audioCtxRef.current = ctx
        const dest = ctx.createMediaStreamDestination()
        ctx.createMediaStreamSource(new MediaStream(audioTracks)).connect(dest)
        ctx.createMediaStreamSource(mic).connect(dest)
        finalStream = dest.stream
      } else {
        finalStream = new MediaStream(audioTracks)
      }
    }

    const mimeType = pickMimeType()
    const recorder = mimeType ? new MediaRecorder(finalStream, { mimeType }) : new MediaRecorder(finalStream)
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
      cleanup()
      stopResolveRef.current?.(blob)
      stopResolveRef.current = null
    }
    recorderRef.current = recorder
    recorder.start(1000)
    setRecording(true)
    setElapsedSeconds(0)
    timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000)
  }, [cleanup])

  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current
      if (!recorder || recorder.state === 'inactive') {
        resolve(null)
        return
      }
      stopResolveRef.current = resolve
      recorder.stop()
      setRecording(false)
    })
  }, [])

  useEffect(() => cleanup, [cleanup])

  return { supported, recording, elapsedSeconds, error, setError, start, stop }
}
