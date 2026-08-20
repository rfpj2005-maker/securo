import { useEffect, useRef, useState } from 'react'
import { cameras as camerasApi } from '@/lib/api'

/** Polls a camera's live JPEG snapshot as an object URL, re-fetching every
 * `intervalMs`. Uses a setTimeout chain (not setInterval) so a slow
 * request never overlaps the next one, and always revokes the previous
 * blob URL before replacing it so tab memory doesn't grow unbounded. */
export function useCameraSnapshot(location: string, cameraId: number, intervalMs: number, enabled: boolean) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const urlRef = useRef<string | null>(null)

  useEffect(() => {
    if (!enabled) {
      setUrl(null)
      return
    }
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>

    const fetchOnce = async () => {
      try {
        const next = await camerasApi.snapshotUrl(location, cameraId)
        if (cancelled) {
          URL.revokeObjectURL(next)
          return
        }
        if (urlRef.current) URL.revokeObjectURL(urlRef.current)
        urlRef.current = next
        setUrl(next)
        setError(false)
      } catch {
        if (!cancelled) setError(true)
      } finally {
        if (!cancelled) timer = setTimeout(fetchOnce, intervalMs)
      }
    }
    fetchOnce()

    return () => {
      cancelled = true
      clearTimeout(timer)
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current)
        urlRef.current = null
      }
    }
  }, [location, cameraId, intervalMs, enabled])

  return { url, error }
}
