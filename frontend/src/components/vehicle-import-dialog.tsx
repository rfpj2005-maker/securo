import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { vehicles as vehiclesApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { AlertTriangle, FileUp } from 'lucide-react'
import type { VehicleImportResult } from '@/types'

/**
 * Two steps: pick the Drivvo export → preview what would be imported
 * (dry run) → confirm. Re-importing the same export only adds what's new.
 */
export function VehicleImportDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<VehicleImportResult | null>(null)
  const [lastOpen, setLastOpen] = useState(false)

  if (open !== lastOpen) {
    setLastOpen(open)
    if (open) {
      setFile(null)
      setPreview(null)
    }
  }

  const previewMutation = useMutation({
    mutationFn: (f: File) => vehiclesApi.importDrivvo(f, true),
    onSuccess: setPreview,
    onError: () => toast.error(t('vehicles.import.invalidFile')),
  })

  const importMutation = useMutation({
    mutationFn: (f: File) => vehiclesApi.importDrivvo(f, false),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['vehicles'] })
      onOpenChange(false)
      const total = result.records.created + result.trips.created + result.inspections.created
      toast.success(t('vehicles.import.done', { count: total }))
    },
    onError: () => toast.error(t('common.error')),
  })

  const nothingNew =
    preview &&
    preview.vehicles_created.length === 0 &&
    preview.records.created + preview.trips.created + preview.inspections.created === 0

  const rows: { label: string; created: number; skipped: number }[] = preview
    ? [
        { label: t('vehicles.import.records'), ...preview.records },
        { label: t('vehicles.import.trips'), ...preview.trips },
        { label: t('vehicles.import.inspections'), ...preview.inspections },
      ]
    : []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('vehicles.import.title')}</DialogTitle>
        </DialogHeader>

        {!preview ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">{t('vehicles.import.instructions')}</p>
            <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-border rounded-xl px-4 py-8 text-sm text-muted-foreground cursor-pointer hover:bg-muted/50 transition-colors">
              <FileUp size={22} />
              <span className="font-medium text-foreground">{file ? file.name : t('vehicles.import.chooseFile')}</span>
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        ) : (
          <div className="space-y-4 text-sm">
            {preview.vehicles_created.length > 0 && (
              <div>
                <p className="font-medium mb-1">{t('vehicles.import.vehiclesCreated')}</p>
                <p className="text-muted-foreground">{preview.vehicles_created.join(', ')}</p>
              </div>
            )}
            {preview.vehicles_matched.length > 0 && (
              <div>
                <p className="font-medium mb-1">{t('vehicles.import.vehiclesMatched')}</p>
                <p className="text-muted-foreground">{preview.vehicles_matched.join(', ')}</p>
              </div>
            )}
            <div className="rounded-lg border border-border divide-y divide-border">
              {rows.map((row) => (
                <div key={row.label} className="flex items-center justify-between px-3 py-2">
                  <span>{row.label}</span>
                  <span className="tabular-nums">
                    <span className="font-semibold">{t('vehicles.import.new', { count: row.created })}</span>
                    {row.skipped > 0 && (
                      <span className="text-muted-foreground"> · {t('vehicles.import.alreadyHere', { count: row.skipped })}</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
            {nothingNew && <p className="text-muted-foreground">{t('vehicles.import.nothingNew')}</p>}
            {preview.warnings.length > 0 && (
              <div className="rounded-lg bg-amber-500/10 px-3 py-2">
                <p className="flex items-center gap-1.5 font-medium text-amber-700 dark:text-amber-400 mb-1">
                  <AlertTriangle size={14} /> {t('vehicles.import.warnings', { count: preview.warnings.length })}
                </p>
                <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-0.5">
                  {preview.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => (preview ? setPreview(null) : onOpenChange(false))}>
            {preview ? t('common.back') : t('common.cancel')}
          </Button>
          {!preview ? (
            <Button disabled={!file || previewMutation.isPending} onClick={() => file && previewMutation.mutate(file)}>
              {previewMutation.isPending ? t('common.loading') : t('vehicles.import.preview')}
            </Button>
          ) : (
            <Button disabled={!!nothingNew || importMutation.isPending} onClick={() => file && importMutation.mutate(file)}>
              {importMutation.isPending ? t('common.saving') : t('vehicles.import.confirm')}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
