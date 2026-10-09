import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { vehicles as vehiclesApi, type VehiclePayload } from '@/lib/api'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/page-header'
import { VehicleFormDialog } from '@/components/vehicle-form-dialog'
import { VehicleImportDialog } from '@/components/vehicle-import-dialog'
import { useWorkspace } from '@/contexts/workspace-context'
import { useAuth } from '@/contexts/auth-context'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import { formatCurrency } from '@/lib/format'
import { AlertTriangle, BellRing, CarFront, ClipboardCheck, FileUp, Fuel, Gauge } from 'lucide-react'
import type { Vehicle } from '@/types'

export default function VehiclesPage() {
  const { t } = useTranslation()
  const { canWrite } = useWorkspace()
  const { user } = useAuth()
  const { mask } = usePrivacyMode()
  const locale = useDisplayLocale()
  const currency = user?.preferences?.currency_display ?? 'USD'
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [showInactive, setShowInactive] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  const { data: allVehicles, isLoading } = useQuery({
    queryKey: ['vehicles'],
    queryFn: () => vehiclesApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: (data: VehiclePayload) => vehiclesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vehicles'] })
      setDialogOpen(false)
      toast.success(t('vehicles.created'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const list = (allVehicles ?? []).filter((v) => showInactive || v.is_active)
  const hasInactive = (allVehicles ?? []).some((v) => !v.is_active)
  const number = (value: number | string, digits = 0) =>
    Number(value).toLocaleString(locale, { maximumFractionDigits: digits, minimumFractionDigits: digits })

  return (
    <div>
      <PageHeader
        section={t('vehicles.section')}
        title={t('vehicles.title')}
        action={
          canWrite ? (
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => setImportOpen(true)}>
                <FileUp size={16} className="mr-1.5" />
                {t('vehicles.import.button')}
              </Button>
              <Button onClick={() => setDialogOpen(true)}>+ {t('vehicles.add')}</Button>
            </div>
          ) : undefined
        }
      />

      {hasInactive && (
        <label className="flex items-center gap-2 mb-4 text-sm text-muted-foreground cursor-pointer w-fit">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
            className="h-4 w-4 rounded border-border accent-primary"
          />
          {t('vehicles.showInactive')}
        </label>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-44 w-full rounded-xl" />
          ))}
        </div>
      ) : list.length === 0 ? (
        <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center text-muted-foreground">
          <CarFront size={32} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">{t('vehicles.empty')}</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {list.map((vehicle) => (
            <VehicleCard
              key={vehicle.id}
              vehicle={vehicle}
              money={(v) => mask(formatCurrency(Number(v), currency, locale))}
              number={number}
            />
          ))}
        </div>
      )}

      <VehicleImportDialog open={importOpen} onOpenChange={setImportOpen} />

      <VehicleFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        vehicle={null}
        pending={createMutation.isPending}
        onSubmit={(data) => createMutation.mutate(data)}
      />
    </div>
  )
}

function VehicleCard({
  vehicle,
  money,
  number,
}: {
  vehicle: Vehicle
  money: (value: string) => string
  number: (value: number | string, digits?: number) => string
}) {
  const { t } = useTranslation()
  const { stats } = vehicle
  const subtitle = [vehicle.brand, vehicle.model, vehicle.year].filter(Boolean).join(' · ')

  return (
    <Link
      to={`/vehicles/${vehicle.id}`}
      className={`block bg-card rounded-xl border border-border shadow-sm p-5 hover:border-primary/40 hover:shadow-md transition-all ${vehicle.is_active ? '' : 'opacity-60'}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-base font-semibold text-foreground truncate">{vehicle.name}</p>
          {subtitle && <p className="text-xs text-muted-foreground truncate">{subtitle}</p>}
        </div>
        {vehicle.plate && (
          <span className="shrink-0 font-mono text-xs font-semibold tracking-wider border border-border rounded px-2 py-0.5 bg-muted">
            {vehicle.plate}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <div>
          <p className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Gauge size={12} /> {t('vehicles.odometer')}
          </p>
          <p className="text-sm font-medium tabular-nums">{t('vehicles.km', { value: number(stats.current_odometer) })}</p>
        </div>
        <div>
          <p className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Fuel size={12} /> {t('vehicles.avgConsumption')}
          </p>
          <p className="text-sm font-medium tabular-nums">
            {stats.avg_consumption ? t('vehicles.kmPerLiter', { value: number(stats.avg_consumption, 1) }) : t('vehicles.noData')}
          </p>
        </div>
        <div>
          <p className="text-[11px] text-muted-foreground">{t('vehicles.totalCost')}</p>
          <p className="text-sm font-medium tabular-nums">{money(stats.total_cost)}</p>
        </div>
        <div>
          <p className="text-[11px] text-muted-foreground">{t('vehicles.costPerKm')}</p>
          <p className="text-sm font-medium tabular-nums">
            {stats.cost_per_km ? money(stats.cost_per_km) : t('vehicles.noData')}
          </p>
        </div>
      </div>

      {(stats.overdue_reminders > 0 || stats.pending_reminders > 0 || stats.last_inspection_has_issue) && (
        <div className="flex flex-wrap gap-2 mt-4">
          {stats.overdue_reminders > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-rose-600 bg-rose-500/10 px-2 py-0.5 rounded-full">
              <AlertTriangle size={12} />
              {t('vehicles.overdueCount', { count: stats.overdue_reminders })}
            </span>
          )}
          {stats.last_inspection_has_issue && (
            <span className="flex items-center gap-1 text-xs font-medium text-amber-700 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
              <ClipboardCheck size={12} />
              {t('vehicles.inspections.lastHasIssue')}
            </span>
          )}
          {stats.pending_reminders - stats.overdue_reminders > 0 && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              <BellRing size={12} />
              {t('vehicles.pendingCount', { count: stats.pending_reminders - stats.overdue_reminders })}
            </span>
          )}
        </div>
      )}
    </Link>
  )
}
