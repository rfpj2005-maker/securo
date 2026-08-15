import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  startOfDay,
  endOfDay,
  addDays,
  subDays,
  addWeeks,
  subWeeks,
  addMonths,
  subMonths,
  isSameMonth,
  isToday,
  format,
  parseISO,
  type Locale,
} from 'date-fns'
import { googleCalendar as gcalApi } from '@/lib/api'
import { toast } from 'sonner'
import { useDateLocale } from '@/hooks/use-display-locale'
import { resolveDateFnsLocale } from '@/lib/date-fns-locale'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { PageHeader } from '@/components/page-header'
import { ChevronLeft, ChevronRight, Plus, Trash2, CalendarDays, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { CalendarEvent } from '@/types'

type ViewMode = 'day' | '3day' | 'week' | 'month'
const GRID_COLS_BY_MODE: Record<ViewMode, number> = { day: 1, '3day': 3, week: 7, month: 7 }

function toDateTimeLocalInput(iso: string, allDay: boolean): string {
  const d = parseISO(iso)
  if (allDay) return format(d, 'yyyy-MM-dd')
  return format(d, "yyyy-MM-dd'T'HH:mm")
}

function navigate(date: Date, mode: ViewMode, direction: 1 | -1): Date {
  if (mode === 'day') return direction === 1 ? addDays(date, 1) : subDays(date, 1)
  if (mode === '3day') return direction === 1 ? addDays(date, 3) : subDays(date, 3)
  if (mode === 'week') return direction === 1 ? addWeeks(date, 1) : subWeeks(date, 1)
  return direction === 1 ? addMonths(date, 1) : subMonths(date, 1)
}

// Deterministic per-calendar color so events from different Google
// calendars (e.g. a business calendar vs. a personal one) are visually
// distinguishable when merged into one view.
const CALENDAR_DOT_COLORS = ['bg-primary', 'bg-emerald-500', 'bg-amber-500', 'bg-violet-500', 'bg-rose-500', 'bg-sky-500']
function calendarDotColor(calendarId: string): string {
  let hash = 0
  for (let i = 0; i < calendarId.length; i++) hash = (hash * 31 + calendarId.charCodeAt(i)) | 0
  return CALENDAR_DOT_COLORS[Math.abs(hash) % CALENDAR_DOT_COLORS.length]
}

function formatViewLabel(date: Date, mode: ViewMode, locale: Locale): string {
  if (mode === 'day') return format(date, 'PPPP', { locale })
  if (mode === '3day') {
    const end = addDays(date, 2)
    return isSameMonth(date, end)
      ? `${format(date, 'd')}–${format(end, 'd LLLL yyyy', { locale })}`
      : `${format(date, 'd LLL', { locale })} – ${format(end, 'd LLL yyyy', { locale })}`
  }
  if (mode === 'week') {
    const start = startOfWeek(date, { locale })
    const end = endOfWeek(date, { locale })
    return isSameMonth(start, end)
      ? `${format(start, 'd')}–${format(end, 'd LLLL yyyy', { locale })}`
      : `${format(start, 'd LLL', { locale })} – ${format(end, 'd LLL yyyy', { locale })}`
  }
  return format(date, 'LLLL yyyy', { locale })
}

export default function CalendarPage() {
  const { t } = useTranslation()
  const dateLocale = useDateLocale()
  const dfLocale = resolveDateFnsLocale(dateLocale)
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const [viewMode, setViewMode] = useState<ViewMode>('week')
  const [viewDate, setViewDate] = useState(new Date())
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null)
  const [formSummary, setFormSummary] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formLocation, setFormLocation] = useState('')
  const [formAllDay, setFormAllDay] = useState(false)
  const [formStart, setFormStart] = useState('')
  const [formEnd, setFormEnd] = useState('')

  useEffect(() => {
    if (searchParams.get('google_calendar_connected')) {
      toast.success(t('calendar.connected'))
      setSearchParams({}, { replace: true })
    } else if (searchParams.get('google_calendar_error')) {
      toast.error(t('calendar.connectError'))
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['google-calendar', 'status'],
    queryFn: () => gcalApi.status(),
  })

  const { data: calendars } = useQuery({
    queryKey: ['google-calendar', 'calendars'],
    queryFn: () => gcalApi.calendars(),
    enabled: !!status?.connected,
  })

  const rangeStart = useMemo(() => {
    if (viewMode === 'day' || viewMode === '3day') return startOfDay(viewDate)
    if (viewMode === 'week') return startOfWeek(viewDate, { locale: dfLocale })
    return startOfWeek(startOfMonth(viewDate), { locale: dfLocale })
  }, [viewMode, viewDate, dfLocale])

  const rangeEnd = useMemo(() => {
    if (viewMode === 'day') return endOfDay(viewDate)
    if (viewMode === '3day') return endOfDay(addDays(viewDate, 2))
    if (viewMode === 'week') return endOfWeek(viewDate, { locale: dfLocale })
    return endOfWeek(endOfMonth(viewDate), { locale: dfLocale })
  }, [viewMode, viewDate, dfLocale])

  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['google-calendar', 'events', rangeStart.toISOString(), rangeEnd.toISOString()],
    queryFn: () => gcalApi.events(rangeStart.toISOString(), rangeEnd.toISOString()),
    enabled: !!status?.connected,
  })

  const connectMutation = useMutation({
    mutationFn: () => gcalApi.connect(),
    onSuccess: (data) => {
      window.location.href = data.authorize_url
    },
    onError: () => toast.error(t('calendar.connectError')),
  })

  const disconnectMutation = useMutation({
    mutationFn: () => gcalApi.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['google-calendar'] })
      toast.success(t('calendar.disconnected'))
    },
  })

  const selectCalendarMutation = useMutation({
    mutationFn: (calendarId: string) => gcalApi.selectCalendar(calendarId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['google-calendar'] }),
  })

  const createMutation = useMutation({
    mutationFn: (data: { summary: string; description?: string; location?: string; start: string; end: string; all_day: boolean }) =>
      gcalApi.createEvent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['google-calendar', 'events'] })
      setDialogOpen(false)
      toast.success(t('calendar.eventCreated'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, calendarId, ...data }: { id: string; calendarId: string; summary: string; description?: string; location?: string; start: string; end: string; all_day: boolean }) =>
      gcalApi.updateEvent(id, calendarId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['google-calendar', 'events'] })
      setDialogOpen(false)
      toast.success(t('calendar.eventUpdated'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const deleteMutation = useMutation({
    mutationFn: ({ id, calendarId }: { id: string; calendarId: string }) => gcalApi.deleteEvent(id, calendarId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['google-calendar', 'events'] })
      setDialogOpen(false)
      toast.success(t('calendar.eventDeleted'))
    },
    onError: () => toast.error(t('common.error')),
  })

  // Flat list of visible days — a CSS grid with the right column count wraps
  // it into rows automatically, so day/week/month all share one renderer.
  const visibleDays = useMemo(() => {
    const out: Date[] = []
    let day = rangeStart
    while (day <= rangeEnd) {
      out.push(day)
      day = addDays(day, 1)
    }
    return out
  }, [rangeStart, rangeEnd])

  const gridCols = GRID_COLS_BY_MODE[viewMode]

  const weekdayLabels = useMemo(() => {
    if (viewMode === 'day') return []
    const labels: string[] = []
    for (let i = 0; i < gridCols; i++) labels.push(format(addDays(rangeStart, i), 'EEEEEE', { locale: dfLocale }))
    return labels
  }, [rangeStart, dfLocale, viewMode, gridCols])

  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>()
    for (const ev of events ?? []) {
      const key = ev.start.slice(0, 10)
      const list = map.get(key) ?? []
      list.push(ev)
      map.set(key, list)
    }
    return map
  }, [events])

  const openCreate = (day?: Date) => {
    setEditingEvent(null)
    setFormSummary('')
    setFormDescription('')
    setFormLocation('')
    setFormAllDay(false)
    const base = day ?? new Date()
    const start = new Date(base)
    start.setHours(9, 0, 0, 0)
    const end = new Date(base)
    end.setHours(10, 0, 0, 0)
    setFormStart(format(start, "yyyy-MM-dd'T'HH:mm"))
    setFormEnd(format(end, "yyyy-MM-dd'T'HH:mm"))
    setDialogOpen(true)
  }

  const openEdit = (ev: CalendarEvent) => {
    setEditingEvent(ev)
    setFormSummary(ev.summary)
    setFormDescription(ev.description ?? '')
    setFormLocation(ev.location ?? '')
    setFormAllDay(ev.all_day)
    setFormStart(toDateTimeLocalInput(ev.start, ev.all_day))
    setFormEnd(toDateTimeLocalInput(ev.end, ev.all_day))
    setDialogOpen(true)
  }

  const handleSave = () => {
    const start = formAllDay ? `${formStart}T00:00:00` : formStart
    const end = formAllDay ? `${formEnd}T00:00:00` : formEnd
    const payload = {
      summary: formSummary,
      description: formDescription || undefined,
      location: formLocation || undefined,
      start,
      end,
      all_day: formAllDay,
    }
    if (editingEvent) {
      updateMutation.mutate({ id: editingEvent.id, calendarId: editingEvent.calendar_id, ...payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  if (statusLoading) {
    return (
      <div>
        <PageHeader section={t('calendar.section')} title={t('calendar.title')} />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!status?.connected) {
    return (
      <div>
        <PageHeader section={t('calendar.section')} title={t('calendar.title')} />
        <div className="bg-card rounded-xl border border-border shadow-sm p-10 flex flex-col items-center text-center gap-3">
          <CalendarDays size={32} className="text-muted-foreground" />
          <p className="text-sm text-muted-foreground max-w-md">{t('calendar.notConnectedDesc')}</p>
          <Button onClick={() => connectMutation.mutate()} disabled={connectMutation.isPending}>
            {t('calendar.connect')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        section={t('calendar.section')}
        title={t('calendar.title')}
        action={
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            {calendars && calendars.length > 1 && (
              <select
                className="flex-1 sm:flex-none min-w-0 border border-border rounded-md px-2 py-1.5 text-sm bg-card"
                value={status.selected_calendar_id ?? 'primary'}
                onChange={(e) => selectCalendarMutation.mutate(e.target.value)}
                title={t('calendar.newEventCalendarHint')}
                aria-label={t('calendar.newEventCalendarHint')}
              >
                {calendars.map((c) => (
                  <option key={c.id} value={c.id}>{c.summary}</option>
                ))}
              </select>
            )}
            <Button variant="outline" className="shrink-0" onClick={() => openCreate()}>
              <Plus size={16} className="mr-1.5" />
              {t('calendar.addEvent')}
            </Button>
          </div>
        }
      />

      {status.google_email && (
        <div className="flex items-center justify-between mb-3 text-xs text-muted-foreground">
          <span>{t('calendar.connectedAs', { email: status.google_email })}</span>
          <button
            onClick={() => disconnectMutation.mutate()}
            className="text-rose-500 hover:underline"
          >
            {t('calendar.disconnect')}
          </button>
        </div>
      )}

      <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border gap-3 flex-wrap">
          <div className="flex items-center gap-1">
            <button onClick={() => setViewDate((d) => navigate(d, viewMode, -1))} className="p-1.5 rounded-md hover:bg-muted">
              <ChevronLeft size={16} />
            </button>
            <span className="text-sm font-semibold capitalize min-w-0">{formatViewLabel(viewDate, viewMode, dfLocale)}</span>
            <button onClick={() => setViewDate((d) => navigate(d, viewMode, 1))} className="p-1.5 rounded-md hover:bg-muted">
              <ChevronRight size={16} />
            </button>
          </div>
          <div className="flex items-center rounded-lg border border-border p-0.5 bg-muted/40">
            {(['day', '3day', 'week', 'month'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-colors',
                  viewMode === mode ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {t(`calendar.view${mode.charAt(0).toUpperCase()}${mode.slice(1)}`)}
              </button>
            ))}
          </div>
        </div>

        {eventsLoading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : (
          <>
            {weekdayLabels.length > 0 && (
              <div className="grid border-b border-border" style={{ gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))` }}>
                {weekdayLabels.map((label, i) => (
                  <div key={i} className="text-center text-[11px] font-medium text-muted-foreground py-2 uppercase">
                    {label}
                  </div>
                ))}
              </div>
            )}
            <div className="grid" style={{ gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))` }}>
              {visibleDays.map((day, idx) => {
                const key = format(day, 'yyyy-MM-dd')
                const dayEvents = eventsByDay.get(key) ?? []
                const inMonth = viewMode !== 'month' || isSameMonth(day, viewDate)
                const maxVisible = viewMode === 'month' ? 3 : viewMode === 'week' ? 8 : 50
                return (
                  <div
                    key={idx}
                    className={cn(
                      'border-b border-r border-border p-1.5 cursor-pointer hover:bg-muted/30 transition-colors',
                      viewMode === 'month' ? 'min-h-[92px]' : viewMode === 'week' ? 'min-h-[220px]' : 'min-h-[420px]',
                      idx % gridCols === gridCols - 1 && 'border-r-0',
                    )}
                    onClick={() => openCreate(day)}
                  >
                    <span
                      className={cn(
                        'inline-flex items-center justify-center h-5 w-5 rounded-full text-[11px]',
                        !inMonth && 'text-muted-foreground/40',
                        isToday(day) && 'bg-primary text-primary-foreground font-semibold',
                        inMonth && !isToday(day) && 'text-foreground',
                      )}
                    >
                      {day.getDate()}
                    </span>
                    <div className="mt-1 space-y-0.5">
                      {dayEvents.slice(0, maxVisible).map((ev) => (
                        <button
                          key={ev.id}
                          onClick={(e) => { e.stopPropagation(); openEdit(ev) }}
                          className={cn(
                            'flex w-full gap-1 text-left text-[11px] px-1.5 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20 transition-colors',
                            viewMode === 'month' ? 'items-center truncate' : 'items-start',
                          )}
                          title={ev.calendar_summary ? `${ev.summary} · ${ev.calendar_summary}` : ev.summary}
                        >
                          <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', viewMode !== 'month' && 'mt-1', calendarDotColor(ev.calendar_id))} />
                          <span className={viewMode === 'month' ? 'truncate' : 'line-clamp-2 break-words'}>{ev.summary}</span>
                        </button>
                      ))}
                      {dayEvents.length > maxVisible && (
                        <span className="text-[10px] text-muted-foreground px-1.5">
                          {t('calendar.moreEvents', { count: dayEvents.length - maxVisible })}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingEvent ? t('calendar.editEvent') : t('calendar.addEvent')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t('calendar.eventTitle')}</Label>
              <Input value={formSummary} onChange={(e) => setFormSummary(e.target.value)} required />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="all-day"
                checked={formAllDay}
                onChange={(e) => setFormAllDay(e.target.checked)}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              <Label htmlFor="all-day" className="cursor-pointer">{t('calendar.allDay')}</Label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{t('calendar.start')}</Label>
                <Input
                  type={formAllDay ? 'date' : 'datetime-local'}
                  value={formStart}
                  onChange={(e) => setFormStart(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>{t('calendar.end')}</Label>
                <Input
                  type={formAllDay ? 'date' : 'datetime-local'}
                  value={formEnd}
                  onChange={(e) => setFormEnd(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>{t('calendar.location')}</Label>
              <Input value={formLocation} onChange={(e) => setFormLocation(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{t('calendar.description')}</Label>
              <textarea
                className="w-full border border-border rounded-md px-3 py-2 text-sm bg-card resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                rows={2}
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
              />
            </div>
            {editingEvent?.html_link && (
              <a
                href={editingEvent.html_link}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                {t('calendar.openInGoogle')} <ExternalLink size={12} />
              </a>
            )}
          </div>
          <DialogFooter className={editingEvent ? 'flex justify-between sm:justify-between' : ''}>
            {editingEvent && (
              <Button
                variant="destructive"
                onClick={() => deleteMutation.mutate({ id: editingEvent.id, calendarId: editingEvent.calendar_id })}
                disabled={deleteMutation.isPending}
              >
                <Trash2 size={14} className="mr-1" />
                {t('common.delete')}
              </Button>
            )}
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleSave}
                disabled={!formSummary.trim() || !formStart || !formEnd || createMutation.isPending || updateMutation.isPending}
              >
                {t('common.save')}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
