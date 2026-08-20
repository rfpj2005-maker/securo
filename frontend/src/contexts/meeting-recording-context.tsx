import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import type { MeetingType } from '@/types'

export type RecordSource = 'mic' | 'tab_audio'

export type RecordingMeta = {
  title: string
  meetingType: MeetingType
  includeMic: boolean
}

type MeetingRecordingValue = {
  supported: boolean
  recording: boolean
  elapsedSeconds: number
  error: string | null
  setError: (e: string | null) => void
  // The finished recording, once stop() has run — survives navigation so
  // whichever page/dialog the user is on when they hit stop can pick it up.
  pendingBlob: Blob | null
  meta: RecordingMeta
  setMeta: (patch: Partial<RecordingMeta>) => void
  start: (source: RecordSource, includeMic: boolean) => Promise<void>
  stop: () => Promise<void>
  clearPending: () => void
  resetAll: () => void
}

const MeetingRecordingContext = createContext<MeetingRecordingValue | null>(null)

function pickMimeType(): string {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  for (const c of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(c)) return c
  }
  return ''
}

const DEFAULT_META: RecordingMeta = { title: '', meetingType: 'in_person', includeMic: true }

/** Recording lives here, not in the Meetings page, specifically so it
 * survives navigating to another part of the app — a component-scoped
 * MediaRecorder gets torn down (and the in-progress audio lost) the moment
 * its owning page unmounts, which is exactly what "switched screens and the
 * recording just vanished" was: React Router unmounting MeetingsPage killed
 * the stream before stop() ever produced a Blob. Mounted once in AppLayout,
 * outside <Outlet />, so it's the same lifetime as the app shell. */
export function MeetingRecordingProvider({ children }: { children: ReactNode }) {
  const [recording, setRecording] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [pendingBlob, setPendingBlob] = useState<Blob | null>(null)
  const [meta, setMetaState] = useState<RecordingMeta>(DEFAULT_META)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamsRef = useRef<MediaStream[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const stopResolveRef = useRef<(() => void) | null>(null)

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

  const setMeta = useCallback((patch: Partial<RecordingMeta>) => {
    setMetaState((prev) => ({ ...prev, ...patch }))
  }, [])

  const start = useCallback(async (source: RecordSource, includeMic: boolean) => {
    setError(null)
    chunksRef.current = []
    setPendingBlob(null)
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
      setPendingBlob(blob)
      stopResolveRef.current?.()
      stopResolveRef.current = null
    }
    recorderRef.current = recorder
    recorder.start(1000)
    setRecording(true)
    setElapsedSeconds(0)
    timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000)
  }, [cleanup])

  const stop = useCallback((): Promise<void> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current
      if (!recorder || recorder.state === 'inactive') {
        resolve()
        return
      }
      stopResolveRef.current = resolve
      recorder.stop()
      setRecording(false)
    })
  }, [])

  // Discards a finished-but-unsaved blob, e.g. right before starting a new
  // take — deliberately leaves `meta` (title/type) alone, since the user may
  // have already typed a title for the recording they're about to make.
  const clearPending = useCallback(() => {
    setPendingBlob(null)
  }, [])

  // Full reset after an upload succeeds, or when the user cancels out of
  // the dialog — clears the blob AND the title/type they'd entered.
  const resetAll = useCallback(() => {
    setPendingBlob(null)
    setMetaState(DEFAULT_META)
  }, [])

  // Only tears down on a full app unmount (tab close/reload) — not on route
  // changes, since this provider sits above <Outlet /> in AppLayout.
  useEffect(() => cleanup, [cleanup])

  // Best-effort warning if the tab closes mid-recording — the audio itself
  // can't survive that, unlike an in-app navigation.
  useEffect(() => {
    if (!recording) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [recording])

  const value: MeetingRecordingValue = {
    supported,
    recording,
    elapsedSeconds,
    error,
    setError,
    pendingBlob,
    meta,
    setMeta,
    start,
    stop,
    clearPending,
    resetAll,
  }

  return <MeetingRecordingContext.Provider value={value}>{children}</MeetingRecordingContext.Provider>
}

export function useMeetingRecording(): MeetingRecordingValue {
  const ctx = useContext(MeetingRecordingContext)
  if (!ctx) {
    throw new Error('useMeetingRecording must be used within a MeetingRecordingProvider')
  }
  return ctx
}
