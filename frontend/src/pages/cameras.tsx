import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { cameras as camerasApi } from '@/lib/api'
import { useCameraSnapshot } from '@/hooks/use-camera-snapshot'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Video, WifiOff, Circle, Camera as CameraIcon } from 'lucide-react'
import type { Camera, CameraRecording } from '@/types'

const LOCATION_LABELS: Record<string, string> = {
  matriz: 'Matriz',
  belvedere: 'Belvedere',
  varginha: 'Varginha',
  centro: 'Centro',
}

const RECORDINGS_PAGE_SIZE = 30

export default function CamerasPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<Camera | null>(null)

  const { data: camerasList, isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: () => camerasApi.list(),
    refetchInterval: 30000,
  })

  const byLocation = useMemo(() => {
    const map = new Map<string, Camera[]>()
    for (const cam of camerasList ?? []) {
      const list = map.get(cam.location) ?? []
      list.push(cam)
      map.set(cam.location, list)
    }
    return map
  }, [camerasList])

  return (
    <div>
      <PageHeader section={t('cameras.section', 'Segurança')} title={t('cameras.title', 'Câmeras')} />
      <p className="text-sm text-muted-foreground mb-5 max-w-2xl">
        {t('cameras.subtitle', 'Câmeras de todas as unidades, com imagem ao vivo e gravações.')}
      </p>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video rounded-xl" />
          ))}
        </div>
      ) : (camerasList ?? []).length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
          <CameraIcon className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">{t('cameras.empty', 'Nenhuma câmera configurada.')}</p>
        </div>
      ) : (
        Array.from(byLocation.entries()).map(([location, cams]) => (
          <div key={location} className="mb-6">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              {LOCATION_LABELS[location] ?? location}
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {cams.map((cam) => (
                <CameraTile key={`${cam.location}-${cam.id}`} camera={cam} onClick={() => setSelected(cam)} />
              ))}
            </div>
          </div>
        ))
      )}

      <CameraDetailDialog camera={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function CameraTile({ camera, onClick }: { camera: Camera; onClick: () => void }) {
  const { url } = useCameraSnapshot(camera.location, camera.id, 10000, camera.online)
  const statusColor = !camera.online ? 'fill-rose-400 text-rose-400' : camera.connected ? 'fill-emerald-400 text-emerald-400' : 'fill-amber-400 text-amber-400'

  return (
    <button
      type="button"
      onClick={onClick}
      className="relative aspect-video rounded-xl overflow-hidden border border-border bg-muted text-left"
    >
      {url ? (
        <img src={url} alt={camera.name} className="w-full h-full object-cover" />
      ) : camera.online ? (
        <Skeleton className="w-full h-full rounded-none" />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-muted-foreground">
          <WifiOff className="h-6 w-6" />
        </div>
      )}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-2.5 py-1.5">
        <div className="flex items-center gap-1.5">
          <Circle className={`h-2 w-2 shrink-0 ${statusColor}`} />
          <span className="text-xs font-medium text-white truncate">{camera.name}</span>
        </div>
      </div>
    </button>
  )
}

function CameraDetailDialog({ camera, onClose }: { camera: Camera | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { url } = useCameraSnapshot(camera?.location ?? '', camera?.id ?? 0, 3000, !!camera)
  const [playing, setPlaying] = useState<CameraRecording | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [videoLoading, setVideoLoading] = useState(false)
  const [recLimit, setRecLimit] = useState(RECORDINGS_PAGE_SIZE)

  const { data: recordings, isLoading: recLoading } = useQuery({
    queryKey: ['camera-recordings', camera?.location, camera?.name],
    queryFn: () => camerasApi.recordings(camera!.location, camera!.name),
    enabled: !!camera,
  })

  const closePlayback = () => {
    if (videoUrl) URL.revokeObjectURL(videoUrl)
    setVideoUrl(null)
    setPlaying(null)
  }

  const openRecording = async (rec: CameraRecording) => {
    setPlaying(rec)
    setVideoLoading(true)
    try {
      const u = await camerasApi.recordingUrl(camera!.location, camera!.name, rec.filename)
      setVideoUrl(u)
    } finally {
      setVideoLoading(false)
    }
  }

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      closePlayback()
      setRecLimit(RECORDINGS_PAGE_SIZE)
      onClose()
    }
  }

  return (
    <Dialog open={!!camera} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        {camera && (
          <>
            <DialogHeader>
              <DialogTitle>{camera.name}</DialogTitle>
            </DialogHeader>

            {playing ? (
              <div className="space-y-2">
                <div className="relative aspect-video rounded-lg overflow-hidden bg-black flex items-center justify-center isolate">
                  {videoLoading || !videoUrl ? (
                    <Skeleton className="w-full h-full rounded-none" />
                  ) : (
                    <video src={videoUrl} controls autoPlay aria-label={t('cameras.recordings', 'Gravações')} className="w-full h-full" />
                  )}
                </div>
                <Button variant="outline" size="sm" onClick={closePlayback}>
                  {t('cameras.backToLive', 'Voltar pra câmera ao vivo')}
                </Button>
              </div>
            ) : (
              <div className="relative aspect-video rounded-lg overflow-hidden bg-muted flex items-center justify-center isolate">
                {url ? (
                  <img src={url} alt={camera.name} className="w-full h-full object-cover" />
                ) : (
                  <Skeleton className="w-full h-full rounded-none" />
                )}
              </div>
            )}

            <div className="relative mt-4 bg-background">
              <h3 className="text-sm font-semibold mb-2">{t('cameras.recordings', 'Gravações')}</h3>
              {recLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : !recordings || recordings.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('cameras.noRecordings', 'Nenhuma gravação encontrada.')}</p>
              ) : (
                <>
                  <div className="divide-y divide-border border border-border rounded-lg overflow-hidden bg-card">
                    {recordings.slice(0, recLimit).map((rec) => (
                      <button
                        key={rec.filename}
                        type="button"
                        onClick={() => openRecording(rec)}
                        className="w-full flex items-center gap-3 px-3 py-2 bg-card hover:bg-muted/50 transition-colors text-left"
                      >
                        <Video className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="text-sm flex-1 min-w-0 truncate">{formatRecordingDate(rec.modified)}</span>
                        <span className="text-xs text-muted-foreground tabular-nums shrink-0">{formatSize(rec.size)}</span>
                      </button>
                    ))}
                  </div>
                  {recordings.length > recLimit && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2 w-full"
                      onClick={() => setRecLimit((n) => n + RECORDINGS_PAGE_SIZE)}
                    >
                      {t('cameras.loadMore', 'Carregar mais')} ({recordings.length - recLimit})
                    </Button>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

function formatSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatRecordingDate(iso: string): string {
  return new Date(iso).toLocaleString()
}
