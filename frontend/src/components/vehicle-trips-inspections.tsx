import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { vehicles as vehiclesApi } from '@/lib/api'
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table'
import { useDateLocale, useDisplayLocale } from '@/hooks/use-display-locale'
import { AlertTriangle, ArrowRight, CheckCircle2, Trash2 } from 'lucide-react'
import type { VehicleInspection } from '@/types'

const selectClass =
  'border border-border rounded-md px-3 py-2 text-sm bg-card focus:outline-none focus-visible:ring-ring/30 focus-visible:ring-[2px]'

function useFormatters() {
  const locale = useDisplayLocale()
  const dateLocale = useDateLocale()
  return {
    number: (value: number) => value.toLocaleString(locale),
    dateTime: (value: string) =>
      new Date(value).toLocaleString(dateLocale, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
  }
}

function DeleteButton({ onClick, disabled }: { onClick: () => void; disabled: boolean }) {
  const { t } = useTranslation()
  return (
    <button
      className="p-1.5 rounded-md text-muted-foreground hover:text-rose-500 hover:bg-rose-50 transition-colors"
      onClick={() => {
        if (window.confirm(t('vehicles.deleteRowConfirm'))) onClick()
      }}
      disabled={disabled}
      title={t('common.delete')}
    >
      <Trash2 size={13} />
    </button>
  )
}

export function VehicleTripsTab({ vehicleId, canWrite }: { vehicleId: string; canWrite: boolean }) {
  const { t } = useTranslation()
  const { number, dateTime } = useFormatters()
  const queryClient = useQueryClient()
  const [driver, setDriver] = useState('')

  const { data: trips } = useQuery({
    queryKey: ['vehicles', vehicleId, 'trips'],
    queryFn: () => vehiclesApi.trips.list(vehicleId),
  })

  const deleteTrip = useMutation({
    mutationFn: (tripId: string) => vehiclesApi.trips.delete(vehicleId, tripId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['vehicles'] }),
    onError: () => toast.error(t('common.error')),
  })

  const drivers = useMemo(
    () => Array.from(new Set((trips ?? []).map((trip) => trip.driver).filter(Boolean) as string[])).sort(),
    [trips],
  )
  const visible = (trips ?? []).filter((trip) => !driver || trip.driver === driver)
  // km by purpose for the filtered set — "Trabalho" vs "Uso Pessoal" is the
  // question a fleet manager asks first.
  const byPurpose = useMemo(() => {
    const totals = new Map<string, number>()
    for (const trip of visible) {
      const key = trip.purpose || t('vehicles.trips.noPurpose')
      totals.set(key, (totals.get(key) ?? 0) + trip.distance)
    }
    return Array.from(totals.entries()).sort((a, b) => b[1] - a[1])
  }, [visible, t])

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {drivers.length > 0 && (
          <select className={selectClass} value={driver} onChange={(e) => setDriver(e.target.value)}>
            <option value="">{t('vehicles.trips.allDrivers')}</option>
            {drivers.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        )}
        {byPurpose.map(([purpose, km]) => (
          <span key={purpose} className="text-xs bg-muted text-muted-foreground px-2 py-1 rounded-full tabular-nums">
            {purpose}: {t('vehicles.km', { value: number(km) })}
          </span>
        ))}
      </div>
      <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
        <Table>
          <TableBody>
            {visible.map((trip) => (
              <TableRow key={trip.id} className="border-b border-border last:border-0">
                <TableCell className="py-2.5 pl-4 whitespace-normal">
                  <span className="text-sm font-medium flex flex-wrap items-center gap-1.5">
                    {trip.origin || '—'} <ArrowRight size={12} className="text-muted-foreground" /> {trip.destination || '—'}
                  </span>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 text-xs text-muted-foreground">
                    <span>{dateTime(trip.started_at)}</span>
                    {trip.driver && <span>{trip.driver}</span>}
                    {trip.purpose && <span>{trip.purpose}</span>}
                    <span>
                      {number(trip.start_odometer)} → {number(trip.end_odometer)}
                    </span>
                  </div>
                  {trip.notes && <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{trip.notes}</p>}
                </TableCell>
                <TableCell className="py-2.5 text-right text-sm font-semibold tabular-nums whitespace-nowrap">
                  {t('vehicles.km', { value: number(trip.distance) })}
                </TableCell>
                {canWrite && (
                  <TableCell className="py-2.5 pr-4 w-[44px]">
                    <DeleteButton onClick={() => deleteTrip.mutate(trip.id)} disabled={deleteTrip.isPending} />
                  </TableCell>
                )}
              </TableRow>
            ))}
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-12 text-muted-foreground">
                  {t('vehicles.trips.empty')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

function Check({ label, value }: { label: string; value: boolean | null }) {
  if (value === null) return null
  return (
    <span className={value ? 'text-muted-foreground' : 'text-rose-600 font-medium'}>
      {label}: {value ? '✓' : '✗'}
    </span>
  )
}

export function VehicleInspectionsTab({ vehicleId, canWrite }: { vehicleId: string; canWrite: boolean }) {
  const { t } = useTranslation()
  const { number, dateTime } = useFormatters()
  const queryClient = useQueryClient()
  const [onlyIssues, setOnlyIssues] = useState(false)

  const { data: inspections } = useQuery({
    queryKey: ['vehicles', vehicleId, 'inspections'],
    queryFn: () => vehiclesApi.inspections.list(vehicleId),
  })

  const deleteInspection = useMutation({
    mutationFn: (inspectionId: string) => vehiclesApi.inspections.delete(vehicleId, inspectionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['vehicles'] }),
    onError: () => toast.error(t('common.error')),
  })

  const visible = (inspections ?? []).filter((i: VehicleInspection) => !onlyIssues || i.has_issue)

  return (
    <div>
      <label className="flex items-center gap-2 mb-3 text-sm text-muted-foreground cursor-pointer w-fit">
        <input
          type="checkbox"
          checked={onlyIssues}
          onChange={(e) => setOnlyIssues(e.target.checked)}
          className="h-4 w-4 rounded border-border accent-primary"
        />
        {t('vehicles.inspections.onlyIssues')}
      </label>
      <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
        <Table>
          <TableBody>
            {visible.map((inspection) => (
              <TableRow key={inspection.id} className="border-b border-border last:border-0">
                <TableCell className="py-2.5 pl-4 pr-0 w-[40px] align-top">
                  {inspection.has_issue ? (
                    <AlertTriangle size={16} className="text-rose-500 mt-0.5" />
                  ) : (
                    <CheckCircle2 size={16} className="text-emerald-600 mt-0.5" />
                  )}
                </TableCell>
                <TableCell className="py-2.5 whitespace-normal">
                  <span className="text-sm font-medium block">
                    {dateTime(inspection.inspected_at)}
                    {inspection.driver && <span className="text-muted-foreground font-normal"> · {inspection.driver}</span>}
                  </span>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 text-xs">
                    {inspection.odometer != null && (
                      <span className="text-muted-foreground">{t('vehicles.km', { value: number(inspection.odometer) })}</span>
                    )}
                    <Check label={t('vehicles.inspections.documents')} value={inspection.documents_ok} />
                    <Check label={t('vehicles.inspections.tires')} value={inspection.tires_ok} />
                    <Check label={t('vehicles.inspections.coolant')} value={inspection.coolant_checked} />
                  </div>
                  {inspection.failing_items && (
                    <p className="text-xs text-rose-600 mt-1">
                      {t('vehicles.inspections.failing')}: {inspection.failing_items}
                    </p>
                  )}
                  {inspection.other_problem && <p className="text-xs text-foreground mt-1">{inspection.other_problem}</p>}
                  {inspection.notes && <p className="text-xs text-muted-foreground mt-1">{inspection.notes}</p>}
                </TableCell>
                {canWrite && (
                  <TableCell className="py-2.5 pr-4 w-[44px] align-top">
                    <DeleteButton onClick={() => deleteInspection.mutate(inspection.id)} disabled={deleteInspection.isPending} />
                  </TableCell>
                )}
              </TableRow>
            ))}
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-12 text-muted-foreground">
                  {t('vehicles.inspections.empty')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
