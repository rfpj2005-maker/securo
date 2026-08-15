import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { meetings as meetingsApi } from '@/lib/api'
import { toast } from 'sonner'
import { useDateLocale } from '@/hooks/use-display-locale'
import { resolveDateFnsLocale } from '@/lib/date-fns-locale'
import { useMeetingRecorder, type RecordSource } from '@/hooks/use-meeting-recorder'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { PageHeader } from '@/components/page-header'
import {
  Mic,
  Square,
  Plus,
  Trash2,
  RotateCw,
  Video,
  Users,
  FileAudio,
  ListChecks,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { MeetingListItem, MeetingType, MeetingStatus } from '@/types'

const IN_PROGRESS: MeetingStatus[] = ['pending', 'transcribing', 'summarizing']

function formatDuration(seconds: number | null): string {
  if (!seconds) return '--:--'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function MeetingsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const dateLocale = useDateLocale()
  const [newOpen, setNewOpen] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)
  const [meetingToDelete, setMeetingToDelete] = useState<string | null>(null)

  const { data: list, isLoading } = useQuery({
    queryKey: ['meetings'],
    queryFn: () => meetingsApi.list(),
    refetchInterval: (query) => {
      const data = query.state.data as MeetingListItem[] | undefined
      return data?.some((m) => IN_PROGRESS.includes(m.status)) ? 4000 : false
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => meetingsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] })
      toast.success(t('meetings.deleted'))
      setMeetingToDelete(null)
    },
    onError: () => toast.error(t('common.error')),
  })

  const statusBadge = (status: MeetingStatus) => {
    switch (status) {
      case 'completed':
        return <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"><CheckCircle2 size={11} />{t('meetings.statusCompleted')}</Badge>
      case 'failed':
        return <Badge variant="destructive"><AlertCircle size={11} />{t('meetings.statusFailed')}</Badge>
      case 'transcribing':
        return <Badge variant="secondary"><Loader2 size={11} className="animate-spin" />{t('meetings.statusTranscribing')}</Badge>
      case 'summarizing':
        return <Badge variant="secondary"><Loader2 size={11} className="animate-spin" />{t('meetings.statusSummarizing')}</Badge>
      default:
        return <Badge variant="secondary"><Loader2 size={11} className="animate-spin" />{t('meetings.statusPending')}</Badge>
    }
  }

  return (
    <div>
      <PageHeader
        section={t('nav.meetings')}
        title={t('meetings.title')}
        action={
          <Button onClick={() => setNewOpen(true)}>
            <Plus size={16} className="mr-1" />
            {t('meetings.new')}
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !list || list.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <FileAudio size={40} className="text-muted-foreground/40 mb-3" />
          <p className="text-sm text-muted-foreground mb-4">{t('meetings.empty')}</p>
          <Button onClick={() => setNewOpen(true)}>
            <Plus size={16} className="mr-1" />
            {t('meetings.new')}
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          {list.map((m) => (
            <button
              key={m.id}
              onClick={() => setOpenId(m.id)}
              className="w-full text-left flex items-start gap-3 rounded-lg border border-border bg-card p-4 hover:border-primary/40 transition-colors"
            >
              <div className="mt-0.5 shrink-0 text-muted-foreground">
                {m.meeting_type === 'online' ? <Video size={18} /> : <Users size={18} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm text-foreground truncate">{m.title}</span>
                  {statusBadge(m.status)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {formatDistanceToNow(parseISO(m.recorded_at), { addSuffix: true, locale: resolveDateFnsLocale(dateLocale) })}
                  {' · '}
                  {formatDuration(m.duration_seconds)}
                </p>
                {m.summary && <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{m.summary}</p>}
                {m.status === 'failed' && m.error && <p className="text-xs text-destructive mt-2">{m.error}</p>}
              </div>
              <div
                role="button"
                tabIndex={0}
                onClick={(e) => { e.stopPropagation(); setMeetingToDelete(m.id) }}
                className="shrink-0 p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
              >
                <Trash2 size={14} />
              </div>
            </button>
          ))}
        </div>
      )}

      <NewMeetingDialog open={newOpen} onOpenChange={setNewOpen} onCreated={(id) => setOpenId(id)} />
      <MeetingDetailDialog id={openId} onOpenChange={(open) => !open && setOpenId(null)} />

      <Dialog open={!!meetingToDelete} onOpenChange={(open) => !open && setMeetingToDelete(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('meetings.deleteTitle')}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">{t('meetings.deleteConfirm')}</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMeetingToDelete(null)}>{t('common.cancel')}</Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => meetingToDelete && deleteMutation.mutate(meetingToDelete)}
            >
              <Trash2 size={14} className="mr-1" />
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function NewMeetingDialog({ open, onOpenChange, onCreated }: { open: boolean; onOpenChange: (open: boolean) => void; onCreated: (id: string) => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const recorder = useMeetingRecorder()
  const [title, setTitle] = useState('')
  const [meetingType, setMeetingType] = useState<MeetingType>('in_person')
  const [includeMic, setIncludeMic] = useState(true)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  const reset = () => {
    setTitle('')
    setMeetingType('in_person')
    setIncludeMic(true)
    setRecordedBlob(null)
    setUploadedFile(null)
  }

  const uploadMutation = useMutation({
    mutationFn: () =>
      meetingsApi.upload({
        title: title.trim() || t('meetings.untitled'),
        meeting_type: meetingType,
        file: (uploadedFile ?? recordedBlob) as File | Blob,
        filename: uploadedFile?.name,
      }),
    onSuccess: (meeting) => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] })
      toast.success(t('meetings.uploadStarted'))
      onOpenChange(false)
      reset()
      onCreated(meeting.id)
    },
    onError: () => toast.error(t('common.error')),
  })

  const source: RecordSource = meetingType === 'online' ? 'tab_audio' : 'mic'

  const handleToggleRecord = async () => {
    if (recorder.recording) {
      const blob = await recorder.stop()
      if (blob) setRecordedBlob(blob)
      return
    }
    setUploadedFile(null)
    setRecordedBlob(null)
    try {
      await recorder.start(source, includeMic)
    } catch {
      recorder.setError(source === 'tab_audio' ? 'no_tab_audio' : 'mic_denied')
    }
  }

  const pendingAudio = uploadedFile ?? recordedBlob
  const minutes = Math.floor(recorder.elapsedSeconds / 60)
  const seconds = recorder.elapsedSeconds % 60

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!recorder.recording) { onOpenChange(v); if (!v) reset() } }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('meetings.new')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t('meetings.titleLabel')}</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t('meetings.titlePlaceholder')} disabled={recorder.recording} />
          </div>

          <div className="space-y-2">
            <Label>{t('meetings.type')}</Label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={recorder.recording}
                onClick={() => setMeetingType('in_person')}
                className={cn('flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                  meetingType === 'in_person' ? 'border-primary bg-primary/[0.08] text-primary' : 'border-border text-muted-foreground hover:bg-accent')}
              >
                <Users size={15} />
                {t('meetings.typeInPerson')}
              </button>
              <button
                type="button"
                disabled={recorder.recording}
                onClick={() => setMeetingType('online')}
                className={cn('flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                  meetingType === 'online' ? 'border-primary bg-primary/[0.08] text-primary' : 'border-border text-muted-foreground hover:bg-accent')}
              >
                <Video size={15} />
                {t('meetings.typeOnline')}
              </button>
            </div>
          </div>

          {meetingType === 'online' && (
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input type="checkbox" checked={includeMic} onChange={(e) => setIncludeMic(e.target.checked)} disabled={recorder.recording} />
              {t('meetings.includeMic')}
            </label>
          )}

          {!recorder.supported ? (
            <p className="text-sm text-muted-foreground">{t('meetings.recorderUnsupported')}</p>
          ) : (
            <div className="flex flex-col items-center py-4">
              <button
                onClick={handleToggleRecord}
                className={cn('flex items-center justify-center rounded-full h-20 w-20 transition-all shrink-0',
                  recorder.recording
                    ? 'bg-destructive text-white animate-pulse shadow-lg shadow-destructive/30'
                    : 'bg-primary text-primary-foreground shadow-lg shadow-primary/30 hover:bg-primary/90')}
                aria-label={recorder.recording ? t('meetings.stopRecording') : t('meetings.startRecording')}
              >
                {recorder.recording ? <Square size={26} /> : <Mic size={30} />}
              </button>
              <p className="text-sm text-muted-foreground mt-3 tabular-nums">
                {recorder.recording
                  ? `${minutes}:${String(seconds).padStart(2, '0')}`
                  : pendingAudio
                    ? t('meetings.recordingReady')
                    : t('meetings.tapToRecord')}
              </p>
              {recorder.error && (
                <p className="text-xs text-destructive mt-2 text-center max-w-xs">
                  {recorder.error === 'no_tab_audio' ? t('meetings.errorNoTabAudio') : t('meetings.errorMicDenied')}
                </p>
              )}
            </div>
          )}

          <div className="relative">
            <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-border" /></div>
            <div className="relative flex justify-center text-xs uppercase"><span className="bg-card px-2 text-muted-foreground">{t('common.or')}</span></div>
          </div>

          <div className="space-y-2">
            <Label>{t('meetings.uploadFile')}</Label>
            <input
              type="file"
              accept="audio/*,video/*"
              disabled={recorder.recording}
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) {
                  setUploadedFile(f)
                  setRecordedBlob(null)
                }
              }}
              className="w-full text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-secondary-foreground hover:file:bg-secondary/80"
            />
            {uploadedFile && <p className="text-xs text-muted-foreground">{uploadedFile.name}</p>}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={recorder.recording}>
            {t('common.cancel')}
          </Button>
          <Button
            disabled={!pendingAudio || recorder.recording || uploadMutation.isPending}
            onClick={() => uploadMutation.mutate()}
          >
            {uploadMutation.isPending && <Loader2 size={14} className="mr-1 animate-spin" />}
            {t('meetings.saveAndTranscribe')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function MeetingDetailDialog({ id, onOpenChange }: { id: string | null; onOpenChange: (open: boolean) => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [showTranscript, setShowTranscript] = useState(false)

  const { data: meeting, isLoading } = useQuery({
    queryKey: ['meeting', id],
    queryFn: () => meetingsApi.get(id as string),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data
      return data && IN_PROGRESS.includes(data.status) ? 3000 : false
    },
  })

  const retryMutation = useMutation({
    mutationFn: () => meetingsApi.retry(id as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', id] })
      queryClient.invalidateQueries({ queryKey: ['meetings'] })
      toast.success(t('meetings.retryStarted'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const inProgress = meeting ? IN_PROGRESS.includes(meeting.status) : false

  return (
    <Dialog open={!!id} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        {isLoading || !meeting ? (
          <div className="space-y-3 py-4">
            <Skeleton className="h-6 w-1/2" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {meeting.meeting_type === 'online' ? <Video size={18} /> : <Users size={18} />}
                {meeting.title}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-5">
              {inProgress && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground bg-secondary/50 rounded-lg px-3 py-2">
                  <Loader2 size={15} className="animate-spin" />
                  {meeting.status === 'transcribing' ? t('meetings.statusTranscribing') : t('meetings.statusSummarizing')}
                </div>
              )}

              {meeting.status === 'failed' && (
                <div className="flex items-start gap-2 text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <p>{meeting.error || t('meetings.genericFailure')}</p>
                    <Button size="sm" variant="outline" className="mt-2" disabled={retryMutation.isPending} onClick={() => retryMutation.mutate()}>
                      <RotateCw size={13} className="mr-1" />
                      {t('meetings.retry')}
                    </Button>
                  </div>
                </div>
              )}

              {meeting.status === 'completed' && meeting.error && (
                <div className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-400 bg-amber-500/10 rounded-lg px-3 py-2">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" />
                  <p>{meeting.error}</p>
                </div>
              )}

              {meeting.summary && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-1.5">{t('meetings.summary')}</h3>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{meeting.summary}</p>
                </div>
              )}

              {meeting.created_tasks.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-1.5 flex items-center gap-1.5">
                    <ListChecks size={15} />
                    {t('meetings.tasksCreated', { count: meeting.created_tasks.length })}
                  </h3>
                  <ul className="space-y-1">
                    {meeting.created_tasks.map((task) => (
                      <li key={task.id} className="text-sm text-muted-foreground flex items-center gap-2">
                        <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', task.status === 'completed' ? 'bg-emerald-500' : 'bg-muted-foreground/40')} />
                        {task.title}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {meeting.transcript && (
                <div>
                  <button
                    onClick={() => setShowTranscript((v) => !v)}
                    className="text-sm font-semibold text-foreground mb-1.5 hover:text-primary transition-colors"
                  >
                    {showTranscript ? t('meetings.hideTranscript') : t('meetings.showTranscript')}
                  </button>
                  {showTranscript && (
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap bg-secondary/30 rounded-lg p-3 max-h-64 overflow-y-auto">
                      {meeting.transcript}
                    </p>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
