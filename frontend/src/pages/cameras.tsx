import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { cameras as camerasApi } from '@/lib/api'
import { useCameraSnapshot } from '@/hooks/use-camera-snapshot'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Video, WifiOff, Circle, Camera as CameraIcon, Search, ServerCrash, Volume2, VolumeX, Maximize2, Minimize2 } from 'lucide-react'
import type { Camera, CameraLocationError, CameraRecording } from '@/types'

const LOCATION_LABELS: Record<string, string> = {
  matriz: 'Matriz',
  belvedere: 'Belvedere',
  varginha: 'Varginha',
  centro: 'Centro',
}

const RECORDINGS_PAGE_SIZE = 30

function isLocationError(c: Camera | CameraLocationError): c is CameraLocationError {
  return 'error' in c
}

export default function CamerasPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<Camera | null>(null)

  const { data: rawList, isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: () => camerasApi.list(),
    refetchInterval: 30000,
  })

  // A location whose recording server couldn't be reached at all (store's
  // local machine powered off, tunnel down, ...) sends one error
  // placeholder instead of its usual camera entries — split those out so
  // they get an explanatory banner instead of rendering as a blank tile.
  const realCameras = useMemo(
    () => (rawList ?? []).filter((c): c is Camera => !isLocationError(c)),
    [rawList],
  )
  const unreachableLocations = useMemo(
    () => (rawList ?? []).filter(isLocationError),
    [rawList],
  )

  const byLocation = useMemo(() => {
    const map = new Map<string, Camera[]>()
    for (const cam of realCameras) {
      const list = map.get(cam.location) ?? []
      list.push(cam)
      map.set(cam.location, list)
    }
    return map
  }, [realCameras])

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
      ) : (rawList ?? []).length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
          <CameraIcon className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">{t('cameras.empty', 'Nenhuma câmera configurada.')}</p>
        </div>
      ) : (
        <>
          {Array.from(byLocation.entries()).map(([location, cams]) => (
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
          ))}
          {unreachableLocations.map((loc) => (
            <div key={loc.location} className="mb-6">
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {LOCATION_LABELS[loc.location] ?? loc.location}
              </h2>
              <div className="flex items-center gap-2 rounded-xl border border-dashed border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                <ServerCrash className="h-4 w-4 shrink-0" />
                {t('cameras.locationUnreachable', 'Servidor local dessa unidade está fora do ar no momento.')}
              </div>
            </div>
          ))}
        </>
      )}

      {!isLoading && realCameras.length > 0 && <RecordingSearch camerasList={realCameras} />}

      <CameraDetailDialog camera={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function CameraTile({ camera, onClick }: { camera: Camera; onClick: () => void }) {
  const { url } = useCameraSnapshot(camera.location, camera.id, 10000, camera.online)
  const statusColor = !camera.online ? 'fill-rose-400 text-rose-400' : camera.connected ? 'fill-emerald-400 text-emerald-400' : 'fill-amber-400 text-amber-400'
  const label = camera.display_name ?? camera.name

  return (
    <button
      type="button"
      onClick={onClick}
      className="relative aspect-video rounded-xl overflow-hidden border border-border bg-muted text-left"
    >
      {url ? (
        <img src={url} alt={label} className="w-full h-full object-cover" />
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
          <span className="text-xs font-medium text-white truncate">{label}</span>
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
  const [audioOn, setAudioOn] = useState(false)
  const [audioUnavailable, setAudioUnavailable] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const audioElRef = useRef<HTMLAudioElement | null>(null)

  // Selecting a different camera swaps `camera` without the dialog ever
  // closing (see CamerasPage's tile onClick) — give the new one a fresh
  // chance at audio instead of carrying over the previous camera's
  // "no microphone" state.
  useEffect(() => {
    setAudioUnavailable(false)
  }, [camera?.location, camera?.id])

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
    setAudioOn(false)
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
      setAudioOn(false)
      setAudioUnavailable(false)
      setExpanded(false)
      setRecLimit(RECORDINGS_PAGE_SIZE)
      onClose()
    }
  }

  // Live audio, in ~10s chunks (see backend camera_service.AUDIO_CHUNK_SECONDS)
  // fetched back-to-back — reuses the same authenticated-blob pattern as
  // snapshots/recordings instead of needing a streaming-auth mechanism
  // just for this. Not every camera has a microphone; a 404 here just
  // disables the toggle rather than showing an error.
  useEffect(() => {
    if (!audioOn || !camera || playing) return
    let cancelled = false
    let objectUrl: string | null = null

    async function loop() {
      while (!cancelled) {
        try {
          const blob = await camerasApi.audioBlob(camera!.location, camera!.name)
          if (cancelled) return
          if (objectUrl) URL.revokeObjectURL(objectUrl)
          objectUrl = URL.createObjectURL(blob)
          const el = audioElRef.current
          if (el) {
            el.src = objectUrl
            await el.play().catch(() => {})
          }
        } catch {
          if (!cancelled) {
            setAudioUnavailable(true)
            setAudioOn(false)
          }
          return
        }
      }
    }
    void loop()

    return () => {
      cancelled = true
      const el = audioElRef.current
      if (el) {
        el.pause()
        el.src = ''
      }
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [audioOn, camera, playing])

  return (
    <Dialog open={!!camera} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        {camera && (
          <>
            <DialogHeader>
              <DialogTitle>{camera.display_name ?? camera.name}</DialogTitle>
            </DialogHeader>

            {playing ? (
              <div className="space-y-2">
                <div className="relative h-56 sm:h-72 rounded-lg overflow-hidden bg-black flex items-center justify-center isolate">
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
              <div
                className={`relative rounded-lg overflow-hidden bg-muted flex items-center justify-center isolate transition-[height] ${
                  expanded ? 'h-[70vh]' : 'h-56 sm:h-72'
                }`}
              >
                {url ? (
                  <img src={url} alt={camera.display_name ?? camera.name} className="w-full h-full object-cover" />
                ) : (
                  <Skeleton className="w-full h-full rounded-none" />
                )}
                <audio ref={audioElRef} className="hidden" />
                <div className="absolute top-2 right-2 flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setAudioOn((v) => !v)}
                    disabled={audioUnavailable}
                    title={
                      audioUnavailable
                        ? t('cameras.audioUnavailable', 'Esta câmera não tem microfone.')
                        : audioOn
                          ? t('cameras.muteAudio', 'Desativar som')
                          : t('cameras.liveAudio', 'Ouvir som ao vivo')
                    }
                    className="rounded-full bg-black/60 p-1.5 text-white hover:bg-black/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {audioOn ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => setExpanded((v) => !v)}
                    title={expanded ? t('cameras.collapse', 'Recolher') : t('cameras.expand', 'Ampliar')}
                    className="rounded-full bg-black/60 p-1.5 text-white hover:bg-black/80 transition-colors"
                  >
                    {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            )}

            <div className={`relative mt-4 bg-background ${expanded ? 'hidden' : ''}`}>
              <h3 className="text-sm font-semibold mb-2">{t('cameras.recordings', 'Gravações')}</h3>
              {recLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : !recordings || recordings.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('cameras.noRecordings', 'Nenhuma gravação encontrada.')}</p>
              ) : (
                <>
                  <div className="space-y-4">
                    {groupRecordingsByDay(recordings.slice(0, recLimit), t).map((group) => (
                      <div key={group.key}>
                        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                          {group.label}
                        </div>
                        <div className="divide-y divide-border border border-border rounded-lg overflow-hidden bg-card">
                          {group.items.map((rec) => (
                            <button
                              key={rec.filename}
                              type="button"
                              onClick={() => openRecording(rec)}
                              className="w-full flex items-center gap-3 px-3 py-2 bg-card hover:bg-muted/50 transition-colors text-left"
                            >
                              <Video className="h-4 w-4 text-muted-foreground shrink-0" />
                              <span className="text-sm flex-1 min-w-0 truncate">
                                {formatTimeOfDay(getRecordingDate(rec.filename, rec.modified))}
                              </span>
                              <span className="text-xs text-muted-foreground tabular-nums shrink-0">{formatSize(rec.size)}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  {recordings.length > recLimit && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3 w-full"
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

function RecordingSearch({ camerasList }: { camerasList: Camera[] }) {
  const { t } = useTranslation()
  const [cameraKey, setCameraKey] = useState('')
  const [date, setDate] = useState('')
  const [timeFrom, setTimeFrom] = useState('')
  const [timeTo, setTimeTo] = useState('')
  const [results, setResults] = useState<CameraRecording[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [playing, setPlaying] = useState<CameraRecording | null>(null)

  const byLocation = useMemo(() => {
    const map = new Map<string, Camera[]>()
    for (const cam of camerasList) {
      const list = map.get(cam.location) ?? []
      list.push(cam)
      map.set(cam.location, list)
    }
    return map
  }, [camerasList])

  const [selLocation, selName] = cameraKey ? cameraKey.split('::') : ['', '']

  const handleSearch = async () => {
    if (!cameraKey) return
    setSearching(true)
    setResults(null)
    try {
      const items = await camerasApi.search(selLocation, selName, {
        date: date || undefined,
        time_from: timeFrom || undefined,
        time_to: timeTo || undefined,
      })
      setResults(items)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-4 mb-5">
      <div className="flex items-center gap-2 mb-3">
        <Search className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">{t('cameras.searchTitle', 'Buscar gravação')}</h2>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="col-span-2 sm:col-span-1 space-y-1.5">
          <Label className="text-xs">{t('cameras.searchCamera', 'Câmera')}</Label>
          <select
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-card focus:outline-none focus-visible:ring-ring/30 focus-visible:ring-[2px]"
            value={cameraKey}
            onChange={(e) => setCameraKey(e.target.value)}
          >
            <option value="">{t('cameras.searchCameraPlaceholder', 'Escolha uma câmera')}</option>
            {Array.from(byLocation.entries()).map(([location, cams]) => (
              <optgroup key={location} label={LOCATION_LABELS[location] ?? location}>
                {cams.map((cam) => (
                  <option key={cam.id} value={`${cam.location}::${cam.name}`}>
                    {cam.display_name ?? cam.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">{t('cameras.searchDate', 'Dia')}</Label>
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">{t('cameras.searchTimeFrom', 'A partir de')}</Label>
          <Input type="time" value={timeFrom} onChange={(e) => setTimeFrom(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">{t('cameras.searchTimeTo', 'Até')}</Label>
          <Input type="time" value={timeTo} onChange={(e) => setTimeTo(e.target.value)} />
        </div>
      </div>
      <Button size="sm" className="mt-3" onClick={handleSearch} disabled={!cameraKey || searching}>
        <Search className="h-3.5 w-3.5 mr-1.5" />
        {searching ? t('cameras.searching', 'Buscando…') : t('cameras.search', 'Buscar')}
      </Button>

      {results !== null && (
        <div className="mt-4">
          {results.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t('cameras.noRecordings', 'Nenhuma gravação encontrada.')}</p>
          ) : (
            <div className="space-y-4">
              {groupRecordingsByDay(results, t).map((group) => (
                <div key={group.key}>
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                    {group.label}
                  </div>
                  <div className="divide-y divide-border border border-border rounded-lg overflow-hidden bg-card">
                    {group.items.map((rec) => (
                      <button
                        key={rec.filename}
                        type="button"
                        onClick={() => setPlaying(rec)}
                        className="w-full flex items-center gap-3 px-3 py-2 bg-card hover:bg-muted/50 transition-colors text-left"
                      >
                        <Video className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="text-sm flex-1 min-w-0 truncate">
                          {formatTimeOfDay(getRecordingDate(rec.filename, rec.modified))}
                        </span>
                        <span className="text-xs text-muted-foreground tabular-nums shrink-0">{formatSize(rec.size)}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <SearchResultPlayerDialog
        location={selLocation}
        cameraName={selName}
        recording={playing}
        onClose={() => setPlaying(null)}
      />
    </div>
  )
}

function SearchResultPlayerDialog({
  location,
  cameraName,
  recording,
  onClose,
}: {
  location: string
  cameraName: string
  recording: CameraRecording | null
  onClose: () => void
}) {
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!recording) {
      setVideoUrl(null)
      return
    }
    let cancelled = false
    setLoading(true)
    camerasApi.recordingUrl(location, cameraName, recording.filename).then((u) => {
      if (cancelled) {
        URL.revokeObjectURL(u)
        return
      }
      setVideoUrl(u)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [recording, location, cameraName])

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      if (videoUrl) URL.revokeObjectURL(videoUrl)
      setVideoUrl(null)
      onClose()
    }
  }

  return (
    <Dialog open={!!recording} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        {recording && (
          <>
            <DialogHeader>
              <DialogTitle>
                {cameraName} — {formatTimeOfDay(getRecordingDate(recording.filename, recording.modified))}
              </DialogTitle>
            </DialogHeader>
            <div className="relative h-56 sm:h-72 rounded-lg overflow-hidden bg-black flex items-center justify-center isolate">
              {loading || !videoUrl ? (
                <Skeleton className="w-full h-full rounded-none" />
              ) : (
                <video src={videoUrl} controls autoPlay aria-label={cameraName} className="w-full h-full" />
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

// Filenames embed the actual recording start (e.g.
// "1_2026-08-20_16-36-05_411.mp4"), already in local time — several
// seconds earlier than `modified`, which is when the server finished
// writing the file to disk. Prefer the real event time; fall back to
// `modified` only if a filename doesn't match the expected pattern.
const RECORDING_FILENAME_TIMESTAMP = /_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})_/

function getRecordingDate(filename: string, modified: string): Date {
  const match = filename.match(RECORDING_FILENAME_TIMESTAMP)
  if (match) {
    const [, date, hh, mm, ss] = match
    return new Date(`${date}T${hh}:${mm}:${ss}`)
  }
  return new Date(modified)
}

function formatTimeOfDay(date: Date): string {
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

interface RecordingDayGroup {
  key: string
  label: string
  items: CameraRecording[]
}

/** Groups an already-sorted (newest-first) recordings slice by calendar
 * day, labeling today/yesterday specially. Grouping only the visible
 * slice (not the full list) keeps this cheap even with hundreds of clips. */
function groupRecordingsByDay(
  recordings: CameraRecording[],
  t: (key: string, fallback: string) => string,
): RecordingDayGroup[] {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const todayKey = today.toDateString()
  const yesterdayKey = yesterday.toDateString()

  const groups: RecordingDayGroup[] = []
  const byKey = new Map<string, RecordingDayGroup>()
  for (const rec of recordings) {
    const date = getRecordingDate(rec.filename, rec.modified)
    const key = date.toDateString()
    let group = byKey.get(key)
    if (!group) {
      const label =
        key === todayKey
          ? t('cameras.today', 'Hoje')
          : key === yesterdayKey
            ? t('cameras.yesterday', 'Ontem')
            : date.toLocaleDateString(undefined, { day: '2-digit', month: 'long', year: 'numeric' })
      group = { key, label, items: [] }
      byKey.set(key, group)
      groups.push(group)
    }
    group.items.push(rec)
  }
  return groups
}
