import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import type { Transaction } from '@/types'
import type { TransactionSavePayload } from '@/components/transaction-dialog'

export type TransactionUpdatePayload = TransactionSavePayload & {
  apply_to_transfer_pair?: boolean
  apply_to_all_with_description?: boolean
}

type PendingTransferCategoryUpdate = { id: string; data: TransactionUpdatePayload }
type PendingDescriptionCategoryUpdate = { id: string; data: TransactionUpdatePayload; description: string }

/** Every surface that lets someone edit an existing transaction's category
 *  (transactions.tsx, dashboard.tsx, account-detail.tsx) needs the same
 *  "just this one, or every transaction with this description?" prompt —
 *  and, for a transfer's paired leg, the equivalent transfer-pair prompt.
 *  Shared here so the three pages can't drift out of sync again (they did
 *  once already: only transactions.tsx had this check, so editing a
 *  category from the Dashboard or an account's transaction list saved
 *  silently with no scope choice at all). */
export function useTransactionCategoryPrompt(
  editingTx: Transaction | null,
  mutate: (payload: TransactionUpdatePayload & { id: string }) => void,
  isPending: boolean,
) {
  const { t } = useTranslation()
  const [pendingTransferCategoryUpdate, setPendingTransferCategoryUpdate] =
    useState<PendingTransferCategoryUpdate | null>(null)
  const [pendingDescriptionCategoryUpdate, setPendingDescriptionCategoryUpdate] =
    useState<PendingDescriptionCategoryUpdate | null>(null)

  const submitPendingTransferCategoryUpdate = (applyToTransferPair: boolean) => {
    if (!pendingTransferCategoryUpdate) return
    const { id, data } = pendingTransferCategoryUpdate
    mutate({ id, ...data, apply_to_transfer_pair: applyToTransferPair })
    setPendingTransferCategoryUpdate(null)
  }

  const submitPendingDescriptionCategoryUpdate = (applyToAllWithDescription: boolean) => {
    if (!pendingDescriptionCategoryUpdate) return
    const { id, data } = pendingDescriptionCategoryUpdate
    mutate({ id, ...data, apply_to_all_with_description: applyToAllWithDescription })
    setPendingDescriptionCategoryUpdate(null)
  }

  /** Drop-in replacement for a plain `updateMutation.mutate({ id, ...data })`
   *  save handler — intercepts a category-only change on an existing
   *  transaction and asks the scope question first. Everything else
   *  (no category change, or no transaction being edited at all) saves
   *  immediately, unchanged. */
  function handleSave(data: TransactionUpdatePayload) {
    if (!editingTx) return

    const isCategoryChange =
      Object.prototype.hasOwnProperty.call(data, 'category_id') &&
      data.category_id !== editingTx.category_id

    const isTransferCategoryChange = isCategoryChange && !!editingTx.transfer_pair_id

    if (isTransferCategoryChange) {
      setPendingTransferCategoryUpdate({ id: editingTx.id, data })
      return
    }

    if (isCategoryChange) {
      setPendingDescriptionCategoryUpdate({ id: editingTx.id, data, description: editingTx.description })
      return
    }

    mutate({ id: editingTx.id, ...data })
  }

  const dialogs = (
    <>
      <Dialog
        open={!!pendingTransferCategoryUpdate}
        onOpenChange={(open) => {
          if (!open) setPendingTransferCategoryUpdate(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('transactions.confirmTransferCategoryTitle')}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            {t('transactions.confirmTransferCategoryDesc')}
          </p>
          <DialogFooter className="flex-row flex-nowrap items-center justify-end gap-2 sm:space-x-0">
            <Button
              className="shrink-0"
              variant="outline"
              onClick={() => setPendingTransferCategoryUpdate(null)}
            >
              {t('common.cancel')}
            </Button>
            <Button
              className="min-w-0 flex-1 truncate"
              variant="outline"
              onClick={() => submitPendingTransferCategoryUpdate(false)}
              disabled={isPending}
            >
              {t('transactions.confirmTransferCategorySingle')}
            </Button>
            <Button
              className="min-w-0 flex-1 truncate"
              onClick={() => submitPendingTransferCategoryUpdate(true)}
              disabled={isPending}
            >
              {isPending ? t('common.loading') : t('transactions.confirmTransferCategoryBoth')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!pendingDescriptionCategoryUpdate}
        onOpenChange={(open) => {
          if (!open) setPendingDescriptionCategoryUpdate(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('transactions.confirmDescriptionCategoryTitle')}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            {t('transactions.confirmDescriptionCategoryDesc', {
              description: pendingDescriptionCategoryUpdate?.description ?? '',
            })}
          </p>
          <DialogFooter className="flex-row flex-nowrap items-center justify-end gap-2 sm:space-x-0">
            <Button
              className="shrink-0"
              variant="outline"
              onClick={() => setPendingDescriptionCategoryUpdate(null)}
            >
              {t('common.cancel')}
            </Button>
            <Button
              className="min-w-0 flex-1 truncate"
              variant="outline"
              onClick={() => submitPendingDescriptionCategoryUpdate(false)}
              disabled={isPending}
            >
              {t('transactions.confirmDescriptionCategorySingle')}
            </Button>
            <Button
              className="min-w-0 flex-1 truncate"
              onClick={() => submitPendingDescriptionCategoryUpdate(true)}
              disabled={isPending}
            >
              {isPending ? t('common.loading') : t('transactions.confirmDescriptionCategoryAll')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )

  return { handleSave, dialogs }
}
