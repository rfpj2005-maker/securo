import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import type { VehiclePayload } from '@/lib/api'
import type { Vehicle, VehicleFuelType } from '@/types'

const FUEL_TYPES: VehicleFuelType[] = ['flex', 'gasoline', 'ethanol', 'diesel', 'cng', 'electric', 'hybrid']

const selectClass =
  'w-full border border-border rounded-md px-3 py-2 text-sm bg-card focus:outline-none focus-visible:ring-ring/30 focus-visible:ring-[2px]'

export function VehicleFormDialog({
  open,
  onOpenChange,
  vehicle,
  pending,
  onSubmit,
  onDelete,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  vehicle: Vehicle | null
  pending: boolean
  onSubmit: (data: VehiclePayload) => void
  onDelete?: () => void
}) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [plate, setPlate] = useState('')
  const [brand, setBrand] = useState('')
  const [model, setModel] = useState('')
  const [year, setYear] = useState('')
  const [color, setColor] = useState('')
  const [fuelType, setFuelType] = useState<VehicleFuelType>('flex')
  const [initialOdometer, setInitialOdometer] = useState('')
  const [notes, setNotes] = useState('')
  const [isActive, setIsActive] = useState(true)

  const [lastOpen, setLastOpen] = useState(false)

  // Reset on the closed→open transition, from the vehicle being edited or
  // blank for a new one (render-time, no effect needed).
  if (open !== lastOpen) {
    setLastOpen(open)
    if (open) {
      setName(vehicle?.name ?? '')
      setPlate(vehicle?.plate ?? '')
      setBrand(vehicle?.brand ?? '')
      setModel(vehicle?.model ?? '')
      setYear(vehicle?.year ? String(vehicle.year) : '')
      setColor(vehicle?.color ?? '')
      setFuelType(vehicle?.fuel_type ?? 'flex')
      setInitialOdometer(vehicle ? String(vehicle.initial_odometer) : '')
      setNotes(vehicle?.notes ?? '')
      setIsActive(vehicle?.is_active ?? true)
    }
  }

  const handleSave = () => {
    onSubmit({
      name: name.trim(),
      plate: plate.trim() || null,
      brand: brand.trim() || null,
      model: model.trim() || null,
      year: year ? Number(year) : null,
      color: color.trim() || null,
      fuel_type: fuelType,
      initial_odometer: initialOdometer ? Number(initialOdometer) : 0,
      notes: notes.trim() || null,
      is_active: isActive,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{vehicle ? t('vehicles.edit') : t('vehicles.add')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-2 col-span-2">
              <Label>{t('vehicles.name')}</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('vehicles.namePlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label>{t('vehicles.plate')}</Label>
              <Input
                value={plate}
                onChange={(e) => setPlate(e.target.value.toUpperCase())}
                placeholder="ABC1D23"
                maxLength={20}
                className="font-mono uppercase"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>{t('vehicles.brand')}</Label>
              <Input value={brand} onChange={(e) => setBrand(e.target.value)} maxLength={50} />
            </div>
            <div className="space-y-2">
              <Label>{t('vehicles.model')}</Label>
              <Input value={model} onChange={(e) => setModel(e.target.value)} maxLength={80} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label>{t('vehicles.year')}</Label>
              <Input type="number" min={1900} max={2100} value={year} onChange={(e) => setYear(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{t('vehicles.color')}</Label>
              <Input value={color} onChange={(e) => setColor(e.target.value)} maxLength={30} />
            </div>
            <div className="space-y-2">
              <Label>{t('vehicles.fuelType')}</Label>
              <select className={selectClass} value={fuelType} onChange={(e) => setFuelType(e.target.value as VehicleFuelType)}>
                {FUEL_TYPES.map((f) => (
                  <option key={f} value={f}>{t(`vehicles.fuel.${f}`)}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>{t('vehicles.initialOdometer')}</Label>
            <Input type="number" min={0} value={initialOdometer} onChange={(e) => setInitialOdometer(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>{t('vehicles.notes')}</Label>
            <textarea
              className={`${selectClass} min-h-[72px]`}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          {vehicle && (
            <label className="flex items-center gap-2 text-sm cursor-pointer w-fit">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              {t('vehicles.active')}
            </label>
          )}
        </div>
        <DialogFooter className={onDelete ? 'flex justify-between sm:justify-between' : ''}>
          {onDelete && (
            <Button variant="destructive" onClick={onDelete}>
              {t('common.delete')}
            </Button>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={!name.trim() || pending}>
              {t('common.save')}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
