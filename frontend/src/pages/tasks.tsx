import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDateLocale } from '@/hooks/use-display-locale'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tasks as tasksApi, push as pushApi } from '@/lib/api'
import { isPushSupported, enablePushOnThisDevice, disablePushOnThisDevice } from '@/lib/push'
import { toast } from 'sonner'
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
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from '@/components/ui/table'
import { PageHeader } from '@/components/page-header'
import { Trash2, Pencil, Mic, Plus, ListChecks, Bell, BellOff, BellRing } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useWorkspace } from '@/contexts/workspace-context'
import type { Task } from '@/types'

const DEFAULT_CATEGORIES = ['marketing', 'management', 'commercial', 'administrative']
type SortBy = 'name' | 'category' | 'dueDate'

export default function TasksPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const dateLocale = useDateLocale()
  const { canWrite } = useWorkspace()
  const queryClient = useQueryClient()

  const knownLabels: Record<string, string> = {
    marketing: t('tasks.categoryMarketing'),
    management: t('tasks.categoryManagement'),
    commercial: t('tasks.categoryCommercial'),
    administrative: t('tasks.categoryAdministrative'),
    meetings: t('tasks.categoryMeetings'),
  }
  // Custom categories (anything the user typed that isn't one of the four
  // defaults) don't have a translation — show them back exactly as typed.
  const categoryLabel = (category: string) => knownLabels[category] ?? category

  const [filterCategory, setFilterCategory] = useState('')
  const [sortBy, setSortBy] = useState<SortBy>('dueDate')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null)
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('')

  const [formTitle, setFormTitle] = useState('')
  const [formCategory, setFormCategory] = useState('administrative')
  const [formDueDate, setFormDueDate] = useState('')
  const [formDueTime, setFormDueTime] = useState('')

  const { data: allTasks, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => tasksApi.list(),
  })

  // All categories in use, plus the four defaults, so the filter/datalist
  // always offer everything the user has already typed before.
  const availableCategories = useMemo(() => {
    const set = new Set(DEFAULT_CATEGORIES)
    for (const task of allTasks ?? []) set.add(task.category)
    return Array.from(set)
  }, [allTasks])

  const list = useMemo(() => {
    const filtered = (allTasks ?? []).filter((task) => !filterCategory || task.category === filterCategory)
    const sorted = [...filtered]
    if (sortBy === 'name') {
      sorted.sort((a, b) => a.title.localeCompare(b.title))
    } else if (sortBy === 'category') {
      sorted.sort((a, b) => categoryLabel(a.category).localeCompare(categoryLabel(b.category)) || a.title.localeCompare(b.title))
    } else {
      sorted.sort((a, b) => {
        if (!a.due_date && !b.due_date) return 0
        if (!a.due_date) return 1
        if (!b.due_date) return -1
        return a.due_date.localeCompare(b.due_date)
      })
    }
    return sorted
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allTasks, filterCategory, sortBy])

  // Looked up live from the query cache (not the snapshot captured when the
  // dialog opened) so subtask add/toggle/delete show up immediately.
  const liveEditingTask = editingTask ? (allTasks ?? []).find((t) => t.id === editingTask.id) ?? editingTask : null

  const createMutation = useMutation({
    mutationFn: (data: { title: string; category: string; due_date?: string | null; due_time?: string | null }) => tasksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setDialogOpen(false)
      toast.success(t('tasks.created'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: Partial<Task> & { id: string }) => tasksApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setDialogOpen(false)
      setEditingTask(null)
      toast.success(t('tasks.updated'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tasksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setDialogOpen(false)
      setDeleteDialogOpen(false)
      toast.success(t('tasks.deleted'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Task['status'] }) => tasksApi.update(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const addSubtaskMutation = useMutation({
    mutationFn: ({ taskId, title }: { taskId: string; title: string }) => tasksApi.subtasks.create(taskId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setNewSubtaskTitle('')
    },
    onError: () => toast.error(t('common.error')),
  })

  const toggleSubtaskMutation = useMutation({
    mutationFn: ({ taskId, subtaskId, is_done }: { taskId: string; subtaskId: string; is_done: boolean }) =>
      tasksApi.subtasks.update(taskId, subtaskId, { is_done }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const deleteSubtaskMutation = useMutation({
    mutationFn: ({ taskId, subtaskId }: { taskId: string; subtaskId: string }) => tasksApi.subtasks.delete(taskId, subtaskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const openCreate = () => {
    setEditingTask(null)
    setFormTitle('')
    setFormCategory('administrative')
    setFormDueDate('')
    setFormDueTime('')
    setNewSubtaskTitle('')
    setDialogOpen(true)
  }

  const openEdit = (task: Task) => {
    setEditingTask(task)
    setFormTitle(task.title)
    setFormCategory(task.category)
    setFormDueDate(task.due_date ?? '')
    setFormDueTime(task.due_time ? task.due_time.slice(0, 5) : '')
    setNewSubtaskTitle('')
    setDialogOpen(true)
  }

  const handleSave = () => {
    const category = formCategory.trim() || 'administrative'
    if (editingTask) {
      updateMutation.mutate({
        id: editingTask.id,
        title: formTitle,
        category,
        due_date: formDueDate || null,
        due_time: formDueDate ? formDueTime || null : null,
      })
    } else {
      createMutation.mutate({
        title: formTitle,
        category,
        due_date: formDueDate || null,
        due_time: formDueDate ? formDueTime || null : null,
      })
    }
  }

  const formatDueDate = (dueDate: string | null) =>
    dueDate ? new Date(dueDate + 'T00:00:00').toLocaleDateString(dateLocale) : t('tasks.noDueDate')

  return (
    <div>
      <PageHeader
        section={t('tasks.section')}
        title={t('tasks.title')}
        action={
          canWrite ? (
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => navigate('/tasks/voice')}>
                <Mic size={16} className="mr-1.5" />
                {t('tasks.voice')}
              </Button>
              <Button onClick={openCreate}>+ {t('tasks.add')}</Button>
            </div>
          ) : undefined
        }
      />

      {canWrite && <ReminderBanner />}

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <select
          className="border border-border rounded-md px-3 py-2 text-sm bg-card focus:outline-none focus-visible:ring-ring/30 focus-visible:ring-[2px]"
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
        >
          <option value="">{t('tasks.allCategories')}</option>
          {availableCategories.map((c) => (
            <option key={c} value={c}>{categoryLabel(c)}</option>
          ))}
        </select>
        <select
          className="border border-border rounded-md px-3 py-2 text-sm bg-card focus:outline-none focus-visible:ring-ring/30 focus-visible:ring-[2px]"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortBy)}
        >
          <option value="dueDate">{t('tasks.sortByDueDate')}</option>
          <option value="name">{t('tasks.sortByName')}</option>
          <option value="category">{t('tasks.sortByCategory')}</option>
        </select>
      </div>

      <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden mb-4">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : (
          <Table>
            <TableBody>
              {list.map((task) => {
                const doneCount = task.subtasks.filter((s) => s.is_done).length
                return (
                  <TableRow key={task.id} className="border-b border-border last:border-0">
                    <TableCell className="py-2.5 pl-4 pr-0 w-[40px]">
                      <input
                        type="checkbox"
                        checked={task.status === 'completed'}
                        disabled={!canWrite}
                        onChange={() =>
                          toggleStatusMutation.mutate({
                            id: task.id,
                            status: task.status === 'completed' ? 'pending' : 'completed',
                          })
                        }
                        className="h-4 w-4 rounded border-border accent-primary cursor-pointer"
                      />
                    </TableCell>
                    <TableCell className="py-2.5 whitespace-normal">
                      <span className={`text-sm font-semibold block ${task.status === 'completed' ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
                        {task.title}
                      </span>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">{categoryLabel(task.category)}</span>
                        <span className="text-xs text-muted-foreground">{formatDueDate(task.due_date)}</span>
                        {task.subtasks.length > 0 && (
                          <span className="flex items-center gap-1 text-xs text-muted-foreground">
                            <ListChecks size={12} />
                            {doneCount}/{task.subtasks.length}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    {canWrite && (
                      <TableCell className="py-2.5 pr-4 sm:pr-5 w-[76px]">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors"
                            onClick={() => openEdit(task)}
                            title={t('common.edit')}
                          >
                            <Pencil size={13} />
                          </button>
                          <button
                            className="p-1.5 rounded-md text-muted-foreground hover:text-rose-500 hover:bg-rose-50 transition-colors"
                            onClick={() => {
                              setTaskToDelete(task.id)
                              setDeleteDialogOpen(true)
                            }}
                            disabled={deleteMutation.isPending}
                            title={t('common.delete')}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                )
              })}
              {list.length === 0 && (
                <TableRow>
                  <TableCell colSpan={canWrite ? 3 : 2} className="text-center py-16 text-muted-foreground">
                    {t('tasks.empty')}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingTask ? t('tasks.edit') : t('tasks.add')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t('tasks.taskTitle')}</Label>
              <Input value={formTitle} onChange={(e) => setFormTitle(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>{t('tasks.category')}</Label>
              <Input
                list="task-categories"
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                placeholder={t('tasks.categoryPlaceholder')}
              />
              <datalist id="task-categories">
                {availableCategories.map((c) => (
                  <option key={c} value={c}>{categoryLabel(c)}</option>
                ))}
              </datalist>
              <p className="text-xs text-muted-foreground">{t('tasks.categoryHint')}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{t('tasks.dueDate')}</Label>
                <Input type="date" value={formDueDate} onChange={(e) => setFormDueDate(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>{t('tasks.dueTime', 'Hora do lembrete')}</Label>
                <Input
                  type="time"
                  value={formDueTime}
                  onChange={(e) => setFormDueTime(e.target.value)}
                  disabled={!formDueDate}
                  placeholder="08:00"
                />
              </div>
            </div>

            {/* Subtasks — only once the task exists, since they need a task_id */}
            <div className="space-y-2 pt-2 border-t border-border">
              <Label>{t('tasks.subtasks')}</Label>
              {!liveEditingTask ? (
                <p className="text-xs text-muted-foreground">{t('tasks.subtasksHint')}</p>
              ) : (
                <>
                  <div className="space-y-1">
                    {liveEditingTask.subtasks.map((sub) => (
                      <div key={sub.id} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={sub.is_done}
                          onChange={() =>
                            toggleSubtaskMutation.mutate({
                              taskId: liveEditingTask.id,
                              subtaskId: sub.id,
                              is_done: !sub.is_done,
                            })
                          }
                          className="h-4 w-4 rounded border-border accent-primary cursor-pointer shrink-0"
                        />
                        <span className={`text-sm flex-1 ${sub.is_done ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
                          {sub.title}
                        </span>
                        <button
                          className="p-1 rounded text-muted-foreground hover:text-rose-500 shrink-0"
                          onClick={() => deleteSubtaskMutation.mutate({ taskId: liveEditingTask.id, subtaskId: sub.id })}
                          title={t('common.delete')}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                    {liveEditingTask.subtasks.length === 0 && (
                      <p className="text-xs text-muted-foreground">{t('tasks.noSubtasks')}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      value={newSubtaskTitle}
                      onChange={(e) => setNewSubtaskTitle(e.target.value)}
                      placeholder={t('tasks.addSubtaskPlaceholder')}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && newSubtaskTitle.trim()) {
                          e.preventDefault()
                          addSubtaskMutation.mutate({ taskId: liveEditingTask.id, title: newSubtaskTitle.trim() })
                        }
                      }}
                    />
                    <Button
                      size="icon"
                      variant="outline"
                      disabled={!newSubtaskTitle.trim() || addSubtaskMutation.isPending}
                      onClick={() => addSubtaskMutation.mutate({ taskId: liveEditingTask.id, title: newSubtaskTitle.trim() })}
                    >
                      <Plus size={14} />
                    </Button>
                  </div>
                </>
              )}
            </div>
          </div>
          <DialogFooter className={editingTask ? 'flex justify-between sm:justify-between' : ''}>
            {editingTask && (
              <Button
                variant="destructive"
                onClick={() => deleteMutation.mutate(editingTask.id)}
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
                disabled={!formTitle.trim() || createMutation.isPending || updateMutation.isPending}
              >
                {t('common.save')}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('tasks.deleteTitle')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">{t('tasks.deleteConfirm')}</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (taskToDelete) deleteMutation.mutate(taskToDelete)
              }}
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

/** Enable/disable Web Push reminders for the current device. Hidden
 * entirely on browsers that don't support the Push API — the button would
 * just fail, so there's nothing useful to show. */
function ReminderBanner() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const supported = isPushSupported()

  const { data: status, isLoading } = useQuery({
    queryKey: ['push-status'],
    queryFn: () => pushApi.status(),
    enabled: supported,
    staleTime: 1000 * 30,
  })

  const enableMutation = useMutation({
    mutationFn: enablePushOnThisDevice,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['push-status'] })
      toast.success(t('tasks.reminders.enabled', 'Lembretes ativados neste aparelho'))
    },
    onError: (err: unknown) => toast.error(err instanceof Error ? err.message : t('common.error')),
  })

  const disableMutation = useMutation({
    mutationFn: disablePushOnThisDevice,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['push-status'] })
      toast.success(t('tasks.reminders.disabled', 'Lembretes desativados neste aparelho'))
    },
    onError: () => toast.error(t('common.error')),
  })

  const testMutation = useMutation({
    mutationFn: () => pushApi.test(),
    onSuccess: () => toast.success(t('tasks.reminders.testSent', 'Notificação de teste enviada')),
    onError: () => toast.error(t('tasks.reminders.testFailed', 'Não foi possível enviar — tente reativar')),
  })

  if (!supported || isLoading) return null

  const subscribed = !!status?.subscribed

  return (
    <div className="flex items-center gap-2 mb-4 px-3 py-2 rounded-lg border border-border bg-card text-sm">
      {subscribed ? (
        <BellRing className="h-4 w-4 text-primary shrink-0" />
      ) : (
        <Bell className="h-4 w-4 text-muted-foreground shrink-0" />
      )}
      <span className="flex-1 text-muted-foreground">
        {subscribed
          ? t('tasks.reminders.activeHint', 'Você recebe uma notificação quando uma tarefa vence.')
          : t('tasks.reminders.inactiveHint', 'Ative para ser avisado quando uma tarefa vencer.')}
      </span>
      {subscribed ? (
        <>
          <Button size="sm" variant="outline" onClick={() => testMutation.mutate()} disabled={testMutation.isPending}>
            {t('tasks.reminders.test', 'Testar')}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => disableMutation.mutate()} disabled={disableMutation.isPending}>
            <BellOff className="h-3.5 w-3.5 mr-1.5" />
            {t('tasks.reminders.disable', 'Desativar')}
          </Button>
        </>
      ) : (
        <Button size="sm" onClick={() => enableMutation.mutate()} disabled={enableMutation.isPending}>
          <Bell className="h-3.5 w-3.5 mr-1.5" />
          {t('tasks.reminders.enable', 'Ativar lembretes')}
        </Button>
      )}
    </div>
  )
}
