import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { RefreshCw, Watch as WatchIcon } from 'lucide-react'
import { auth } from '@/lib/api'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface WatchPairingDialogProps {
  open: boolean
  onClose: () => void
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

/** Shows a short-lived pairing code the Wear OS watch app redeems for
 *  its own access token (see backend app/api/watch_pairing.py — this
 *  dialog only ever calls `start`, never `redeem`, which is device-side
 *  only). Auto-generates a code on open and again whenever the previous
 *  one expires, so the dialog is never showing a dead code. */
export function WatchPairingDialog({ open, onClose }: WatchPairingDialogProps) {
  const { t } = useTranslation()
  const [code, setCode] = useState<string | null>(null)
  const [secondsLeft, setSecondsLeft] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const generate = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await auth.watchPairStart()
      setCode(data.code)
      setSecondsLeft(data.expires_in)
    } catch {
      setCode(null)
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) void generate()
    else {
      setCode(null)
      setSecondsLeft(0)
    }
  }, [open, generate])

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (!open || !code) return
    intervalRef.current = setInterval(() => {
      setSecondsLeft((s) => (s <= 1 ? 0 : s - 1))
    }, 1000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [open, code])

  const expired = code !== null && secondsLeft <= 0

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <WatchIcon className="h-4 w-4" />
            {t('auth.watchPairTitle')}
          </DialogTitle>
          <DialogDescription>{t('auth.watchPairDescription')}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-3 py-4">
          {code && !expired ? (
            <>
              <div className="text-4xl font-mono font-semibold tracking-[0.3em] tabular-nums">
                {code}
              </div>
              <p className="text-xs text-muted-foreground">
                {t('auth.watchPairExpiresIn', { time: formatCountdown(secondsLeft) })}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              {error
                ? t('auth.watchPairError')
                : expired
                  ? t('auth.watchPairExpired')
                  : t('common.loading')}
            </p>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => void generate()}
            disabled={loading}
            className="rounded-lg"
          >
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            {t('auth.watchPairRegenerate')}
          </Button>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} className="rounded-lg">
            {t('common.close')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
