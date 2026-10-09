import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  vehicles as vehiclesApi,
  type VehiclePayload,
  type VehicleRecordPayload,
  type VehicleReminderPayload,
} from '@/lib/api'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table'
import { VehicleFormDialog } from '@/components/vehicle-form-dialog'
import { VehicleInspectionsTab, VehicleTripsTab } from '@/components/vehicle-trips-inspections'
import { useWorkspace } from '@/contexts/workspace-context'
import { useAuth } from '@/contexts/auth-context'
import { useDateLocale, useDisplayLocale } from '@/hooks/use-display-locale'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import { formatCurrency } from '@/lib/format'
import { localDateString } from '@/lib/date-utils'
import { AlertTriangle, ArrowLeft, Fuel, Pencil, Receipt, Trash2, Wrench } from 'lucide-react'
import type { VehicleRecord, VehicleRecordKind, VehicleReminder } from '@/types'

const RECORD_KINDS: VehicleRecordKind[] = ['fuel', 'maintenance', 'expense']
const KIND_ICONS: Record<VehicleRecordKind, React.ElementType> = { fuel: Fuel, maintenance: Wrench, expense: Receipt }
const REMINDER_SUGGESTIONS = ['ipva', 'licensing', 'insurance', 'oilChange', 'inspection']

const selectClass =
  'border border-border rounded-md px-3 py-2 text-sm bg-card focus:outline-none focus-visible:ring-ring/30 focus-visible:ring-[2px]'

export default function VehicleDetailPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { canWrite } = useWorkspace()
  const { user } = useAuth()
  const { mask } = usePrivacyMode()
  const locale = useDisplayLocale()
  const dateLocale = useDateLocale()
  const currency = user?.preferences?.currency_display ?? 'USD'
  const queryClient = useQueryClient()

  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [recordDialog, setRecordDialog] = useState<{ open: boolean; record: VehicleRecord | null }>({ open: false, record: null })
  const [reminderDialog, setReminderDialog] = useState<{ open: boolean; reminder: VehicleReminder | null }>({ open: false, reminder: null })
  const [kindFilter, setKindFilter] = useState<'' | VehicleRecordKind>('')

  const { data: vehicle, isLoading, isError } = useQuery({
    queryKey: ['vehicles', id],
    queryFn: () => vehiclesApi.get(id),
  })
  const { data: records } = useQuery({
    queryKey: ['vehicles', id, 'records'],
    queryFn: () => vehiclesApi.records.list(id),
  })
  const { data: reminders } = useQuery({
    queryKey: ['vehicles', id, 'reminders'],
    queryFn: () => vehiclesApi.reminders.list(id),
  })

  // Records and reminders feed the vehicle's stats (odometer, costs,
  // overdue counts), so every write refreshes the whole vehicle subtree.
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['vehicles'] })

  const money = (value: string | number) => mask(formatCurrency(Number(value), currency, locale))
  const number = (value: number | string, digits = 0) =>
    Number(value).toLocaleString(locale, { maximumFractionDigits: digits, minimumFractionDigits: digits })
  const formatDate = (value: string) => new Date(value + 'T00:00:00').toLocaleDateString(dateLocale)

  const updateVehicle = useMutation({
    mutationFn: (data: VehiclePayload) => vehiclesApi.update(id, data),
    onSuccess: () => {
      refresh()
      setEditOpen(false)
      toast.success(t('vehicles.updated'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const deleteVehicle = useMutation({
    mutationFn: () => vehiclesApi.delete(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ['vehicles', id] })
      queryClient.invalidateQueries({ queryKey: ['vehicles'] })
      toast.success(t('vehicles.deleted'))
      navigate('/vehicles')
    },
    onError: () => toast.error(t('common.error')),
  })

  const saveRecord = useMutation({
    mutationFn: ({ recordId, data }: { recordId?: string; data: VehicleRecordPayload }) =>
      recordId ? vehiclesApi.records.update(id, recordId, data) : vehiclesApi.records.create(id, data),
    onSuccess: (_, { recordId }) => {
      refresh()
      setRecordDialog({ open: false, record: null })
      toast.success(t(recordId ? 'vehicles.records.updated' : 'vehicles.records.created'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const deleteRecord = useMutation({
    mutationFn: (recordId: string) => vehiclesApi.records.delete(id, recordId),
    onSuccess: () => {
      refresh()
      setRecordDialog({ open: false, record: null })
      toast.success(t('vehicles.records.deleted'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const saveReminder = useMutation({
    mutationFn: ({ reminderId, data }: { reminderId?: string; data: VehicleReminderPayload }) =>
      reminderId ? vehiclesApi.reminders.update(id, reminderId, data) : vehiclesApi.reminders.create(id, data),
    onSuccess: (_, { reminderId, data }) => {
      refresh()
      setReminderDialog({ open: false, reminder: null })
      // Ticking the checkbox is feedback enough; only toast on form saves.
      if (Object.keys(data).length > 1 || data.is_done === undefined) {
        toast.success(t(reminderId ? 'vehicles.reminders.updated' : 'vehicles.reminders.created'))
      }
    },
    onError: () => toast.error(t('common.error')),
  })

  const deleteReminder = useMutation({
    mutationFn: (reminderId: string) => vehiclesApi.reminders.delete(id, reminderId),
    onSuccess: () => {
      refresh()
      setReminderDialog({ open: false, reminder: null })
      toast.success(t('vehicles.reminders.deleted'))
    },
    onError: () => toast.error(t('common.error')),
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (isError || !vehicle) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <p className="mb-4">{t('common.error')}</p>
        <Link to="/vehicles" className="text-primary text-sm">{t('vehicles.back')}</Link>
      </div>
    )
  }

  const { stats } = vehicle
  const subtitle = [vehicle.brand, vehicle.model, vehicle.year, vehicle.color].filter(Boolean).join(' · ')
  const visibleRecords = (records ?? []).filter((r) => !kindFilter || r.kind === kindFilter)
  const statTiles: { label: string; value: string; hint?: string }[] = [
    { label: t('vehicles.odometer'), value: t('vehicles.km', { value: number(stats.current_odometer) }), hint: t('vehicles.distance') + ': ' + t('vehicles.km', { value: number(stats.distance) }) },
    {
      label: t('vehicles.avgConsumption'),
      value: stats.avg_consumption ? t('vehicles.kmPerLiter', { value: number(stats.avg_consumption, 1) }) : t('vehicles.noData'),
      hint: t('vehicles.totalLiters') + ': ' + number(stats.total_liters, 1) + ' L',
    },
    {
      label: t('vehicles.totalCost'),
      value: money(stats.total_cost),
      hint: `${t('vehicles.fuelCost')} ${money(stats.fuel_cost)} · ${t('vehicles.maintenanceCost')} ${money(stats.maintenance_cost)} · ${t('vehicles.otherCost')} ${money(stats.other_cost)}`,
    },
    { label: t('vehicles.costPerKm'), value: stats.cost_per_km ? money(stats.cost_per_km) : t('vehicles.noData') },
  ]

  return (
    <div>
      <Link to="/vehicles" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-3">
        <ArrowLeft size={12} /> {t('vehicles.back')}
      </Link>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-6">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">{vehicle.name}</h1>
            {vehicle.plate && (
              <span className="font-mono text-xs font-semibold tracking-wider border border-border rounded px-2 py-0.5 bg-muted">
                {vehicle.plate}
              </span>
            )}
            {!vehicle.is_active && (
              <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">{t('vehicles.inactive')}</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {[subtitle, t(`vehicles.fuel.${vehicle.fuel_type}`)].filter(Boolean).join(' · ')}
          </p>
        </div>
        {canWrite && (
          <Button variant="outline" onClick={() => setEditOpen(true)}>
            <Pencil size={14} className="mr-1.5" />
            {t('common.edit')}
          </Button>
        )}
      </div>

      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4 mb-6">
        {statTiles.map((tile) => (
          <div key={tile.label} className="bg-card rounded-xl border border-border shadow-sm p-4">
            <p className="text-[11px] text-muted-foreground">{tile.label}</p>
            <p className="text-lg font-semibold tabular-nums mt-0.5">{tile.value}</p>
            {tile.hint && <p className="text-[11px] text-muted-foreground mt-1 leading-snug">{tile.hint}</p>}
          </div>
        ))}
      </div>

      {vehicle.notes && (
        <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg px-4 py-3 mb-6 whitespace-pre-wrap">{vehicle.notes}</p>
      )}

      <Tabs defaultValue="records">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <TabsList>
            <TabsTrigger value="records">{t('vehicles.tabRecords')}</TabsTrigger>
            <TabsTrigger value="trips">{t('vehicles.tabTrips')}</TabsTrigger>
            <TabsTrigger value="inspections">
              {t('vehicles.tabInspections')}
              {stats.last_inspection_has_issue && <AlertTriangle size={12} className="ml-1 text-rose-500" />}
            </TabsTrigger>
            <TabsTrigger value="reminders">
              {t('vehicles.tabReminders')}
              {stats.overdue_reminders > 0 && (
                <span className="ml-1 text-[10px] font-semibold text-white bg-rose-500 rounded-full px-1.5">{stats.overdue_reminders}</span>
              )}
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="records">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <select className={selectClass} value={kindFilter} onChange={(e) => setKindFilter(e.target.value as '' | VehicleRecordKind)}>
              <option value="">{t('vehicles.records.allKinds')}</option>
              {RECORD_KINDS.map((k) => (
                <option key={k} value={k}>{t(`vehicles.records.kinds.${k}`)}</option>
              ))}
            </select>
            {canWrite && (
              <Button onClick={() => setRecordDialog({ open: true, record: null })}>+ {t('vehicles.records.add')}</Button>
            )}
          </div>
          <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
            <Table>
              <TableBody>
                {visibleRecords.map((record) => {
                  const Icon = KIND_ICONS[record.kind]
                  const pricePerLiter =
                    record.liters && Number(record.liters) > 0 ? Number(record.amount) / Number(record.liters) : null
                  return (
                    <TableRow
                      key={record.id}
                      className={`border-b border-border last:border-0 ${canWrite ? 'cursor-pointer' : ''}`}
                      onClick={() => canWrite && setRecordDialog({ open: true, record })}
                    >
                      <TableCell className="py-2.5 pl-4 pr-0 w-[40px]">
                        <Icon size={16} className="text-muted-foreground" />
                      </TableCell>
                      <TableCell className="py-2.5 whitespace-normal">
                        <span className="text-sm font-medium block">
                          {record.description || t(`vehicles.records.kinds.${record.kind}`)}
                        </span>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 text-xs text-muted-foreground">
                          <span>{formatDate(record.date)}</span>
                          {record.odometer != null && <span>{t('vehicles.km', { value: number(record.odometer) })}</span>}
                          {record.driver && <span>{record.driver}</span>}
                          {record.place && <span>{record.place}</span>}
                          {record.liters && (
                            <span>
                              {number(record.liters, 2)} L
                              {pricePerLiter != null && ` · ${t('vehicles.records.pricePerLiter', { value: money(pricePerLiter) })}`}
                              {!record.full_tank && ` · ${t('vehicles.records.partial')}`}
                            </span>
                          )}
                          {record.consumption && (
                            <span className="text-emerald-600 font-medium">
                              {t('vehicles.kmPerLiter', { value: number(record.consumption, 1) })}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5 pr-4 sm:pr-5 text-right text-sm font-semibold tabular-nums whitespace-nowrap">
                        {money(record.amount)}
                      </TableCell>
                    </TableRow>
                  )
                })}
                {visibleRecords.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-12 text-muted-foreground">
                      {t('vehicles.records.empty')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="trips">
          <VehicleTripsTab vehicleId={id} canWrite={canWrite} />
        </TabsContent>

        <TabsContent value="inspections">
          <VehicleInspectionsTab vehicleId={id} canWrite={canWrite} />
        </TabsContent>

        <TabsContent value="reminders">
          {canWrite && (
            <div className="flex justify-end mb-3">
              <Button onClick={() => setReminderDialog({ open: true, reminder: null })}>+ {t('vehicles.reminders.add')}</Button>
            </div>
          )}
          <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
            <Table>
              <TableBody>
                {(reminders ?? []).map((reminder) => {
                  const kmLeft = reminder.due_odometer != null ? reminder.due_odometer - stats.current_odometer : null
                  return (
                    <TableRow key={reminder.id} className="border-b border-border last:border-0">
                      <TableCell className="py-2.5 pl-4 pr-0 w-[40px]">
                        <input
                          type="checkbox"
                          checked={reminder.is_done}
                          disabled={!canWrite}
                          onChange={() => saveReminder.mutate({ reminderId: reminder.id, data: { is_done: !reminder.is_done } })}
                          className="h-4 w-4 rounded border-border accent-primary cursor-pointer"
                        />
                      </TableCell>
                      <TableCell className="py-2.5 whitespace-normal">
                        <span className={`text-sm font-medium block ${reminder.is_done ? 'line-through text-muted-foreground' : ''}`}>
                          {reminder.title}
                        </span>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 text-xs text-muted-foreground">
                          {reminder.is_overdue && (
                            <span className="flex items-center gap-1 font-medium text-rose-600">
                              <AlertTriangle size={11} /> {t('vehicles.reminders.overdue')}
                            </span>
                          )}
                          {reminder.due_date && <span>{formatDate(reminder.due_date)}</span>}
                          {reminder.due_odometer != null && (
                            <span>
                              {t('vehicles.km', { value: number(reminder.due_odometer) })}
                              {!reminder.is_done && kmLeft != null && kmLeft > 0 && ` · ${t('vehicles.reminders.dueIn', { value: number(kmLeft) })}`}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      {canWrite && (
                        <TableCell className="py-2.5 pr-4 sm:pr-5 w-[48px]">
                          <button
                            className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors"
                            onClick={() => setReminderDialog({ open: true, reminder })}
                            title={t('common.edit')}
                          >
                            <Pencil size={13} />
                          </button>
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}
                {(reminders ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-12 text-muted-foreground">
                      {t('vehicles.reminders.empty')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      <VehicleFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        vehicle={vehicle}
        pending={updateVehicle.isPending}
        onSubmit={(data) => updateVehicle.mutate(data)}
        onDelete={() => {
          setEditOpen(false)
          setDeleteOpen(true)
        }}
      />

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('vehicles.deleteTitle')}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">{t('vehicles.deleteConfirm')}</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>{t('common.cancel')}</Button>
            <Button variant="destructive" disabled={deleteVehicle.isPending} onClick={() => deleteVehicle.mutate()}>
              <Trash2 size={14} className="mr-1" />
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <RecordDialog
        open={recordDialog.open}
        record={recordDialog.record}
        currentOdometer={stats.current_odometer}
        pending={saveRecord.isPending || deleteRecord.isPending}
        onOpenChange={(open) => setRecordDialog((s) => ({ ...s, open }))}
        onSubmit={(data) => saveRecord.mutate({ recordId: recordDialog.record?.id, data })}
        onDelete={recordDialog.record ? () => deleteRecord.mutate(recordDialog.record!.id) : undefined}
      />

      <ReminderDialog
        open={reminderDialog.open}
        reminder={reminderDialog.reminder}
        pending={saveReminder.isPending || deleteReminder.isPending}
        onOpenChange={(open) => setReminderDialog((s) => ({ ...s, open }))}
        onSubmit={(data) => saveReminder.mutate({ reminderId: reminderDialog.reminder?.id, data })}
        onDelete={reminderDialog.reminder ? () => deleteReminder.mutate(reminderDialog.reminder!.id) : undefined}
      />
    </div>
  )
}

function RecordDialog({
  open,
  record,
  currentOdometer,
  pending,
  onOpenChange,
  onSubmit,
  onDelete,
}: {
  open: boolean
  record: VehicleRecord | null
  currentOdometer: number
  pending: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: VehicleRecordPayload) => void
  onDelete?: () => void
}) {
  const { t } = useTranslation()
  const [kind, setKind] = useState<VehicleRecordKind>('fuel')
  const [date, setDate] = useState(localDateString())
  const [odometer, setOdometer] = useState('')
  const [amount, setAmount] = useState('')
  const [liters, setLiters] = useState('')
  const [fullTank, setFullTank] = useState(true)
  const [description, setDescription] = useState('')
  const [driver, setDriver] = useState('')
  const [place, setPlace] = useState('')
  const [lastOpen, setLastOpen] = useState(false)

  // Reset on the closed→open transition (render-time, no effect needed).
  if (open !== lastOpen) {
    setLastOpen(open)
    if (open) {
      setKind(record?.kind ?? 'fuel')
      setDate(record?.date ?? localDateString())
      setOdometer(record?.odometer != null ? String(record.odometer) : '')
      setAmount(record ? String(Number(record.amount)) : '')
      setLiters(record?.liters ? String(Number(record.liters)) : '')
      setFullTank(record?.full_tank ?? true)
      setDescription(record?.description ?? '')
      setDriver(record?.driver ?? '')
      setPlace(record?.place ?? '')
    }
  }

  const isFuel = kind === 'fuel'
  const handleSave = () => {
    onSubmit({
      kind,
      date,
      odometer: odometer ? Number(odometer) : null,
      amount: amount || '0',
      liters: isFuel && liters ? liters : null,
      full_tank: isFuel ? fullTank : false,
      description: description.trim() || null,
      driver: driver.trim() || null,
      place: place.trim() || null,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{record ? t('vehicles.records.edit') : t('vehicles.records.add')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2">
            {RECORD_KINDS.map((k) => {
              const Icon = KIND_ICONS[k]
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => setKind(k)}
                  className={`flex flex-col items-center gap-1 rounded-lg border px-2 py-2.5 text-xs font-medium transition-colors ${
                    kind === k ? 'border-primary bg-primary/[0.08] text-primary' : 'border-border text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <Icon size={16} />
                  {t(`vehicles.records.kinds.${k}`)}
                </button>
              )
            })}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>{t('vehicles.records.date')}</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{t('vehicles.odometer')}</Label>
              <Input
                type="number"
                min={0}
                value={odometer}
                placeholder={String(currentOdometer)}
                onChange={(e) => setOdometer(e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>{t('vehicles.records.amount')}</Label>
              <Input type="number" min={0} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            {isFuel && (
              <div className="space-y-2">
                <Label>{t('vehicles.records.liters')}</Label>
                <Input type="number" min={0} step="0.001" value={liters} onChange={(e) => setLiters(e.target.value)} />
              </div>
            )}
          </div>
          {isFuel && (
            <div className="space-y-1">
              <label className="flex items-center gap-2 text-sm cursor-pointer w-fit">
                <input
                  type="checkbox"
                  checked={fullTank}
                  onChange={(e) => setFullTank(e.target.checked)}
                  className="h-4 w-4 rounded border-border accent-primary"
                />
                {t('vehicles.records.fullTank')}
              </label>
              <p className="text-xs text-muted-foreground">{t('vehicles.records.fullTankHint')}</p>
            </div>
          )}
          <div className="space-y-2">
            <Label>{t('vehicles.records.description')}</Label>
            <Input
              value={description}
              maxLength={255}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('vehicles.records.descriptionPlaceholder')}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>{t('vehicles.records.driver')}</Label>
              <Input value={driver} maxLength={100} onChange={(e) => setDriver(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{isFuel ? t('vehicles.records.station') : t('vehicles.records.place')}</Label>
              <Input value={place} maxLength={150} onChange={(e) => setPlace(e.target.value)} />
            </div>
          </div>
        </div>
        <DialogFooter className={onDelete ? 'flex justify-between sm:justify-between' : ''}>
          {onDelete && (
            <Button variant="destructive" onClick={onDelete} disabled={pending}>
              <Trash2 size={14} className="mr-1" />
              {t('common.delete')}
            </Button>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
            <Button onClick={handleSave} disabled={!date || pending}>{t('common.save')}</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ReminderDialog({
  open,
  reminder,
  pending,
  onOpenChange,
  onSubmit,
  onDelete,
}: {
  open: boolean
  reminder: VehicleReminder | null
  pending: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: VehicleReminderPayload) => void
  onDelete?: () => void
}) {
  const { t } = useTranslation()
  const [title, setTitle] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [dueOdometer, setDueOdometer] = useState('')
  const [lastOpen, setLastOpen] = useState(false)

  if (open !== lastOpen) {
    setLastOpen(open)
    if (open) {
      setTitle(reminder?.title ?? '')
      setDueDate(reminder?.due_date ?? '')
      setDueOdometer(reminder?.due_odometer != null ? String(reminder.due_odometer) : '')
    }
  }

  const handleSave = () => {
    onSubmit({
      title: title.trim(),
      due_date: dueDate || null,
      due_odometer: dueOdometer ? Number(dueOdometer) : null,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{reminder ? t('vehicles.reminders.edit') : t('vehicles.reminders.add')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t('vehicles.reminders.title')}</Label>
            <Input value={title} maxLength={255} onChange={(e) => setTitle(e.target.value)} placeholder={t('vehicles.reminders.titlePlaceholder')} />
            {!reminder && (
              <div className="flex flex-wrap gap-1.5">
                {REMINDER_SUGGESTIONS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setTitle(t(`vehicles.reminders.suggestions.${key}`))}
                    className="text-xs border border-border rounded-full px-2.5 py-0.5 text-muted-foreground hover:bg-muted"
                  >
                    {t(`vehicles.reminders.suggestions.${key}`)}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>{t('vehicles.reminders.dueDate')}</Label>
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{t('vehicles.reminders.dueOdometer')}</Label>
              <Input type="number" min={0} value={dueOdometer} onChange={(e) => setDueOdometer(e.target.value)} />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">{t('vehicles.reminders.dueHint')}</p>
        </div>
        <DialogFooter className={onDelete ? 'flex justify-between sm:justify-between' : ''}>
          {onDelete && (
            <Button variant="destructive" onClick={onDelete} disabled={pending}>
              <Trash2 size={14} className="mr-1" />
              {t('common.delete')}
            </Button>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
            <Button onClick={handleSave} disabled={!title.trim() || pending}>{t('common.save')}</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
