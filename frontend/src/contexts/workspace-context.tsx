import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/contexts/auth-context'
import { auth as authApi, workspaces as workspacesApi, WORKSPACE_STORAGE_KEY } from '@/lib/api'
import type { ModuleId } from '@/lib/modules'
import type { FeatureId } from '@/lib/features'
import type { Workspace, WorkspaceRole } from '@/types'

interface WorkspaceContextType {
  current: Workspace | null
  workspaces: Workspace[]
  isLoading: boolean
  /** Switch the active workspace. Persists to localStorage and invalidates queries. */
  switchWorkspace: (id: string) => Promise<void>
  /** Re-fetch the list of workspaces the user can access. */
  refresh: () => Promise<void>
  /** Role of the current user inside the active workspace, or null if no active workspace. */
  role: WorkspaceRole | null
  /** True for owner OR manager (the manager has effective owner rights). */
  canManage: boolean
  /** True for owner, manager, OR editor — anyone allowed to mutate financial data. */
  canWrite: boolean
  /** Modules the active workspace shows, as resolved by the server. */
  enabledModules: ModuleId[]
  /**
   * The single question the UI asks about modules. False while the
   * workspace list is still loading, so nothing renders on a guess.
   */
  hasModule: (id: ModuleId) => boolean
  /** Securo's own destinations (tasks/calendar/meetings/cameras) this
   *  member can see, as resolved by the server. */
  enabledFeatures: FeatureId[]
  /** The single question the UI asks about Securo's own destinations. */
  hasFeature: (id: FeatureId) => boolean
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user, token, isLoading: authLoading, updateUser } = useAuth()
  const [list, setList] = useState<Workspace[]>([])
  const [currentId, setCurrentId] = useState<string | null>(() => localStorage.getItem(WORKSPACE_STORAGE_KEY))
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  const loadWorkspaces = useCallback(async () => {
    setIsLoading(true)
    try {
      const fetched = await workspacesApi.list()
      setList(fetched)
      // Reconcile the stored selection against what's actually accessible.
      // If the stored ID is stale (workspace archived, user removed, etc.)
      // fall back to the user's pinned default (preferences.default_workspace_id
      // — set automatically on every switchWorkspace call, see below) so a
      // fresh device/browser lands where they last chose everywhere else,
      // not just wherever this one happened to remember. Only when that's
      // also unset/stale do we fall back to the first (oldest) workspace.
      const storedId = localStorage.getItem(WORKSPACE_STORAGE_KEY)
      const found = fetched.find((w) => w.id === storedId)
      if (found) {
        setCurrentId(found.id)
      } else if (fetched.length > 0) {
        const preferredId = user?.preferences?.default_workspace_id
        const preferred = fetched.find((w) => w.id === preferredId)
        const fallbackId = (preferred ?? fetched[0]).id
        localStorage.setItem(WORKSPACE_STORAGE_KEY, fallbackId)
        setCurrentId(fallbackId)
      } else {
        localStorage.removeItem(WORKSPACE_STORAGE_KEY)
        setCurrentId(null)
      }
    } catch {
      // 401s are handled by the global interceptor; other failures we
      // just surface as no-data — the user can retry from the UI.
      setList([])
    } finally {
      setIsLoading(false)
    }
  }, [user])

  useEffect(() => {
    // Stay in the loading state until auth has settled. Reporting "done,
    // no workspaces" while the token is still being restored is a lie
    // that lasts one render — long enough for anything gated on
    // `hasModule` to decide the module is off and redirect away.
    if (authLoading) return
    if (!user || !token) {
      setList([])
      setCurrentId(null)
      setIsLoading(false)
      return
    }
    void loadWorkspaces()
  }, [authLoading, user, token, loadWorkspaces])

  const switchWorkspace = useCallback(
    async (id: string) => {
      if (id === currentId) return
      // Persist FIRST so the axios interceptor sends the new
      // workspace_id on every refetch fired below.
      localStorage.setItem(WORKSPACE_STORAGE_KEY, id)
      setCurrentId(id)
      // Every cached query was scoped to the previous workspace.
      // `resetQueries` flushes cached data AND refetches active
      // observers in one call — `clear()` alone removed data without
      // triggering refetches (mounted components kept their previous
      // render until a manual reload).
      await queryClient.resetQueries()
      // Also persist server-side (not just localStorage) so this becomes
      // the workspace a fresh login/new device lands on too — see
      // backend workspace_service.get_default_workspace. Best-effort: a
      // failure here shouldn't block the switch the user is already
      // looking at, it just means the next fresh device falls back to
      // the old default until they switch again from here.
      if (user) {
        const nextPreferences = { ...user.preferences, default_workspace_id: id }
        authApi
          .updateMe({ preferences: nextPreferences })
          .then((updated) => updateUser(updated))
          .catch(() => {})
      }
    },
    [currentId, queryClient, user, updateUser],
  )

  const current = useMemo(
    () => list.find((w) => w.id === currentId) ?? null,
    [list, currentId],
  )

  const role = current?.role ?? null
  const canManage = role === 'owner' || role === 'manager'
  const canWrite = role === 'owner' || role === 'manager' || role === 'editor'

  const enabledModules = useMemo(
    () => (current?.enabled_modules ?? []) as ModuleId[],
    [current],
  )
  const hasModule = useCallback(
    (id: ModuleId) => enabledModules.includes(id),
    [enabledModules],
  )

  const enabledFeatures = useMemo(
    () => (current?.enabled_features ?? []) as FeatureId[],
    [current],
  )
  const hasFeature = useCallback(
    (id: FeatureId) => enabledFeatures.includes(id),
    [enabledFeatures],
  )

  return (
    <WorkspaceContext.Provider
      value={{
        current,
        workspaces: list,
        isLoading,
        switchWorkspace,
        refresh: loadWorkspaces,
        role,
        canManage,
        canWrite,
        enabledModules,
        hasModule,
        enabledFeatures,
        hasFeature,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider')
  }
  return ctx
}
