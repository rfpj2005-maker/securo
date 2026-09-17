import { useState, useCallback, useEffect, useMemo } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/auth-context'
import { useMeetingRecording } from '@/contexts/meeting-recording-context'
import { useWorkspace } from '@/contexts/workspace-context'
import { type FeatureId } from '@/lib/features'
import { CollectionSelector } from '@/components/collection-selector'
import { auth as authApi, backup as backupApi, admin as adminApi, agents as agentsApi } from '@/lib/api'
import { resolveSupportedLang, changeLanguageExplicitly } from '@/lib/i18n'
import { toast } from 'sonner'
import { OnboardingTour } from '@/components/onboarding-tour'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuPortal,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { APP_VERSION } from '@/lib/build-info'
import { ShellLogo } from '@/components/shell-logo'
import { UpdateAvailableBanner } from '@/components/update-available-banner'
import { UpdateAvailableDialog } from '@/components/update-available-dialog'
import { WorkspaceSwitcher } from '@/components/workspace-switcher'
import { navItems, visibleNavItems, type NavItem } from '@/lib/nav-items'
import {
  Menu,
  ChevronRight,
  Eye,
  EyeOff,
  ListChecks,
  Car,
  Sun,
  Moon,
  Languages,
  KeyRound,
  Check,
  HardDriveDownload,
  Shield,
  ShieldCheck,
  Fingerprint,
  CalendarDays,
  Mic,
  Camera,
  Phone,
  UserX,
} from 'lucide-react'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import { ChangePasswordDialog } from '@/components/change-password-dialog'
import { TwoFactorSetup } from '@/components/two-factor-setup'
import { PasskeyManagementDialog } from '@/components/passkey-management-dialog'
import { CommandPalette } from '@/components/command-palette'
import { useCommandPaletteHotkey } from '@/hooks/use-command-palette-hotkey'
import { GlobalChatPanel } from '@/components/global-chat-panel'
import { useFeatureFlags } from '@/hooks/use-feature-flags'
import { Bot, Search, Sparkles } from 'lucide-react'
import { setThemeBasedOnSystem } from '@/lib/theme-utils'

// Securo's own always-on destinations — not part of the workspace module
// system (which only gates the upstream finance modules). Appended after
// the module-gated list below, filtered per member by `hasFeature` (see
// lib/features.ts / member_access_service.py) rather than `hasModule`.
const CUSTOM_NAV_ITEMS: { key: string; path: string; icon: React.ElementType; feature: FeatureId }[] = [
  { key: 'tasks', path: '/tasks', icon: ListChecks, feature: 'tasks' },
  { key: 'calendar', path: '/calendar', icon: CalendarDays, feature: 'calendar' },
  { key: 'meetings', path: '/meetings', icon: Mic, feature: 'meetings' },
  { key: 'cameras', path: '/cameras', icon: Camera, feature: 'cameras' },
  { key: 'inadimplencia', path: '/inadimplencia', icon: UserX, feature: 'inadimplencia' },
]

/** Placeholder rows shown while the workspace's module list is in flight. */
function NavSkeleton() {
  return (
    <div className="flex flex-col gap-0.5" aria-hidden>
      {[3, 2, 7].map((count, section) => (
        <div key={section} className={cn('flex flex-col gap-0.5', section > 0 && 'pt-3')}>
          <div className="px-3 pt-1 pb-1">
            <div className="h-2 w-16 rounded bg-sidebar-accent/60 animate-pulse" />
          </div>
          {Array.from({ length: count }).map((_, row) => (
            <div key={row} className="flex items-center gap-3 px-3 py-2">
              <div className="h-4 w-4 rounded bg-sidebar-accent/60 animate-pulse" />
              <div className="h-3 flex-1 max-w-[7rem] rounded bg-sidebar-accent/40 animate-pulse" />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

export function AppLayout() {
  const { t } = useTranslation()
  const { user, logout, updateUser } = useAuth()
  const { theme, setTheme, resolvedTheme } = useTheme()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [financesExpanded, setFinancesExpanded] = useState(false)
  const { privacyMode, togglePrivacyMode } = usePrivacyMode()
  const [changePasswordOpen, setChangePasswordOpen] = useState(false)
  const [twoFactorOpen, setTwoFactorOpen] = useState(false)
  const [passkeysOpen, setPasskeysOpen] = useState(false)
  const [backingUp, setBackingUp] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false)
  useCommandPaletteHotkey(setPaletteOpen)
  const { agentsEnabled, pabxEnabled } = useFeatureFlags()
  const { current, hasModule, hasFeature, isLoading: workspaceLoading, canWrite } = useWorkspace()
  const meetingRecording = useMeetingRecording()
  // The chat is offered only to members who can write. Sending a message
  // reaches a tool set that persists — `propose_create_transaction` and its
  // siblings — so the backend refuses it for a read-only role. Showing the
  // panel anyway would put a raw `403: {"detail":"Read-only role"}` in front
  // of the user, which is what happened before this guard.
  //
  // This costs a viewer the ability to *ask* questions, which is a real use
  // case. Restoring it means making the agent's tools role-aware so a
  // read-only session only exposes the reading ones; then this becomes
  // `agentsEnabled` again.
  const chatAvailable = agentsEnabled && canWrite

  // The current workspace's Siprov agent (by name, resolved server-side —
  // see agents.getSiprov). Not every workspace has one, so a 404 here is
  // normal and just means the nav item shouldn't show, not an error.
  const { data: siprovAgent } = useQuery({
    queryKey: ['siprov-agent', current?.id],
    queryFn: () => agentsApi.getSiprov(),
    enabled: agentsEnabled && !!current,
    retry: false,
    staleTime: 1000 * 60,
  })

  // ⌘J / Ctrl+J toggles the global slide-over chat from anywhere.
  // Distinct from ⌘K (command palette) so users can have both open.
  // Gated on agentsEnabled so the hotkey is a no-op when the feature is
  // off — keeps ⌘J free for browsers/other tools.
  useEffect(() => {
    adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
    
    if (!chatAvailable) return
    const handler = (e: KeyboardEvent) => {
      const isMod = e.metaKey || e.ctrlKey
      if (isMod && (e.key === 'j' || e.key === 'J')) {
        e.preventDefault()
        setChatOpen((prev) => !prev)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [chatAvailable, resolvedTheme])
  // The "Agents" management page used to live in the sidebar, but it's
  // a configuration surface (KB upload, providers, default selection),
  // not a daily destination. Moved to the user menu (Change password,
  // 2FA, Backups, AI agents).
  const finalNavItems: NavItem[] = useMemo(
    () => visibleNavItems(navItems, hasModule),
    [hasModule],
  )
  const isMac =
    typeof navigator !== 'undefined' &&
    /Mac|iPhone|iPad|iPod/.test(navigator.platform)

  const showTour =
    user &&
    !user.preferences?.onboarding_completed &&
    !localStorage.getItem('onboarding_completed')

  const handleTourComplete = useCallback(async () => {
    localStorage.setItem('onboarding_completed', 'true')
    try {
      const prefs = {
        ...(user?.preferences || {}),
        onboarding_completed: true,
      }
      const updated = await authApi.updateMe({ preferences: prefs })
      updateUser(updated)
    } catch {
      // localStorage fallback is already set
    }
  }, [user, updateUser])

  const userInitial = user?.email?.charAt(0).toUpperCase() ?? '?'
  const resolvedThemeLocal = theme === 'system' ? undefined : theme
  const isDark = resolvedThemeLocal
    ? resolvedThemeLocal === 'dark'
    : typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-color-scheme: dark)').matches
  const toggleTheme = () => setTheme(isDark ? 'light' : 'dark')

  const versionA11yLabel = t('app.versionAriaLabel', { version: APP_VERSION })

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile header */}
      <header className="sticky top-0 z-40 flex h-14 items-center gap-3 bg-sidebar border-b border-sidebar-border px-4 lg:hidden">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="text-sidebar-muted hover:text-sidebar-foreground transition-colors"
          aria-label="Toggle menu"
        >
          <Menu size={20} />
        </button>
        <Link
          to="/"
          className="flex items-center gap-2 -mx-1 px-1 py-1 rounded-md hover:bg-sidebar-accent transition-colors"
          aria-label={t('app.name')}
          title={t('nav.dashboard')}
        >
          <ShellLogo size={22} className="text-primary shrink-0" />
          <span className="font-bold text-sidebar-foreground">
            {t('app.name')}
          </span>
        </Link>
        <div className="ml-auto flex items-center gap-2">
          {meetingRecording.recording && <RecordingPill seconds={meetingRecording.elapsedSeconds} />}
          <button
            onClick={() => setPaletteOpen(true)}
            className="text-sidebar-muted hover:text-sidebar-foreground transition-colors p-1"
            title={t('cmdk.triggerAria')}
            aria-label={t('cmdk.triggerAria')}
          >
            <Search size={18} />
          </button>
          <button
            onClick={togglePrivacyMode}
            className="text-sidebar-muted hover:text-sidebar-foreground transition-colors p-1"
            title={privacyMode ? t('privacy.show') : t('privacy.hide')}
          >
            {privacyMode ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
          <button
            onClick={toggleTheme}
            className="text-sidebar-muted hover:text-sidebar-foreground transition-colors p-1"
            title={isDark ? t('settings.themeLight') : t('settings.themeDark')}
            aria-label={
              isDark ? t('settings.themeLight') : t('settings.themeDark')
            }
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          {/* AI chat — opens the global slide-over (also reachable via
              ⌘J). Sits next to the theme toggle so the icon is always
              within thumb reach on mobile too. */}
          {chatAvailable && (
            <button
              onClick={() => setChatOpen(true)}
              className="text-sidebar-muted hover:text-sidebar-foreground transition-colors p-1"
              title={`${t('agents.globalChat.title', 'Chat')} (${isMac ? '⌘J' : 'Ctrl+J'})`}
              aria-label={t('agents.globalChat.openHint', 'Open chat (⌘J)')}
            >
              <Bot size={18} />
            </button>
          )}
          <UserMenu
            userInitial={userInitial}
            logout={logout}
            onChangePassword={() => setChangePasswordOpen(true)}
            onTwoFactor={() => setTwoFactorOpen(true)}
            onPasskeys={() => setPasskeysOpen(true)}
            agentsEnabled={agentsEnabled}
            backingUp={backingUp}
            onBackup={async () => {
              setBackingUp(true)
              try {
                await backupApi.download()
                toast.success(t('backup.success'))
              } catch {
                toast.error(t('backup.error'))
              } finally {
                setBackingUp(false)
              }
            }}
            dark
            isAdmin={user?.is_superuser}
          />
        </div>
      </header>

      <div className="flex">
        {/* Sidebar overlay for mobile */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside
          className={cn(
            'fixed inset-y-0 left-0 z-50 w-60 bg-sidebar border-r border-sidebar-border flex flex-col transform transition-transform lg:translate-x-0 shrink-0',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          {/* Logo — clickable link to the dashboard. Replaces the
              dedicated 'Painel' nav item so the sidebar stays focused
              on the main destinations. */}
          <div className="flex h-16 min-h-16 items-center justify-between px-5 border-b border-sidebar-border shrink-0">
            <Link
              to="/"
              className="flex items-center gap-2.5 -mx-1 px-1 py-1 rounded-md hover:bg-sidebar-accent transition-colors"
              onClick={() => setSidebarOpen(false)}
              aria-label={t('app.name')}
              title={t('nav.dashboard')}
            >
              <ShellLogo size={24} className="text-primary shrink-0" />
              <span className="font-bold text-lg text-sidebar-foreground tracking-tight">
                {t('app.name')}
              </span>
            </Link>
            <div className="flex items-center gap-0.5">
              {meetingRecording.recording && <RecordingPill seconds={meetingRecording.elapsedSeconds} />}
              <button
                onClick={togglePrivacyMode}
                className="text-sidebar-muted hover:text-sidebar-foreground transition-colors p-1 rounded-md hover:bg-sidebar-accent"
                title={privacyMode ? t('privacy.show') : t('privacy.hide')}
                aria-label={privacyMode ? t('privacy.show') : t('privacy.hide')}
              >
                {privacyMode ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
              {/* AI chat — same trigger as the mobile bar, ⌘J also
                  works. Lives in the sidebar header so the entry point
                  is visible even on first load (no floating button). */}
              {chatAvailable && (
                <button
                  onClick={() => setChatOpen(true)}
                  className="text-sidebar-muted hover:text-sidebar-foreground transition-colors p-1 rounded-md hover:bg-sidebar-accent"
                  title={`${t('agents.globalChat.title', 'Chat')} (${isMac ? '⌘J' : 'Ctrl+J'})`}
                  aria-label={t('agents.globalChat.openHint', 'Open chat (⌘J)')}
                >
                  <Bot size={16} />
                </button>
              )}
              <button
                onClick={toggleTheme}
                className="text-sidebar-muted hover:text-sidebar-foreground transition-colors p-1 rounded-md hover:bg-sidebar-accent"
                title={
                  isDark ? t('settings.themeLight') : t('settings.themeDark')
                }
                aria-label={
                  isDark ? t('settings.themeLight') : t('settings.themeDark')
                }
              >
                {isDark ? <Sun size={16} /> : <Moon size={16} />}
              </button>
            </div>
          </div>

          {/* Command palette trigger */}
          <div className="px-3 pt-3">
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className={cn(
                'group flex w-full items-center gap-2 rounded-lg border border-sidebar-border/80 bg-sidebar-accent/40 px-3 py-2',
                'text-[12.5px] text-sidebar-muted transition-all',
                'hover:bg-sidebar-accent hover:text-sidebar-foreground hover:border-sidebar-border',
              )}
              aria-label={t('cmdk.triggerAria')}
            >
              <Search size={13} className="shrink-0" />
              <span className="flex-1 text-left">{t('cmdk.triggerLabel')}</span>
              <kbd className="hidden lg:inline-flex h-[17px] items-center rounded border border-sidebar-border bg-sidebar px-1 font-mono text-[9.5px] font-semibold text-sidebar-muted/80">
                {isMac ? '⌘' : 'Ctrl'}&nbsp;K
              </kbd>
            </button>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto">
          {/* Nav */}
          <nav className="flex flex-col gap-0.5 px-3 pt-1 pb-3" data-tour="sidebar">
            {/* Which modules this workspace shows is resolved server-side,
                so until the workspace list lands there is no honest answer
                — a placeholder beats both an empty sidebar and a guess. */}
            {workspaceLoading && <NavSkeleton />}
            {!workspaceLoading && finalNavItems.map((item, idx) => {
              if (item.type === 'separator') {
                // The first separator sits right below the search bar
                // — without trimming the top padding it leaves a wide
                // gap that makes the section header feel disconnected
                // from the search trigger.
                const isFirstSep = idx === 0
                return (
                  <div key={`sep-${idx}`} className={cn(isFirstSep ? 'pt-1 pb-1 px-3' : 'pt-3 pb-1 px-3')}>
                    <span className="text-[10px] uppercase tracking-[0.12em] font-semibold text-sidebar-muted/50">
                      {t(item.labelKey)}
                    </span>
                  </div>
                )
              }

              if (item.type === 'group') {
                const GroupIcon = item.icon
                const groupActive =
                  location.pathname === '/' ||
                  item.items.some((c) => location.pathname.startsWith(c.path))
                return (
                  <div key={item.key}>
                    <div
                      className={cn(
                        'flex w-full items-center gap-1 text-[13px] font-medium transition-all rounded-lg pr-1',
                        groupActive && !financesExpanded
                          ? 'bg-primary/[0.08] text-primary'
                          : 'text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground',
                      )}
                    >
                      <Link
                        to="/"
                        data-tour={`nav-${item.key}`}
                        onClick={() => setSidebarOpen(false)}
                        className="flex flex-1 items-center gap-3 px-3 py-2 min-w-0"
                      >
                        <GroupIcon
                          size={17}
                          className={cn(
                            'shrink-0',
                            groupActive && !financesExpanded ? 'text-primary' : 'text-sidebar-muted',
                          )}
                        />
                        <span className="flex-1 text-left">{t(`nav.${item.key}`)}</span>
                      </Link>
                      <button
                        type="button"
                        onClick={() => setFinancesExpanded((v) => !v)}
                        aria-label={financesExpanded ? t('common.collapse') : t('common.expand')}
                        className="shrink-0 p-1.5 rounded-md hover:bg-sidebar-accent"
                      >
                        <ChevronRight
                          size={13}
                          className={cn(
                            'shrink-0 text-sidebar-muted transition-transform',
                            financesExpanded && 'rotate-90',
                          )}
                        />
                      </button>
                    </div>
                    {financesExpanded && (
                      <div className="mt-0.5 space-y-0.5">
                        {item.items.map((child) => {
                          const childActive = location.pathname.startsWith(child.path)
                          const ChildIcon = child.icon
                          return (
                            <Link
                              key={child.key}
                              to={child.path}
                              data-tour={`nav-${child.key}`}
                              onClick={() => setSidebarOpen(false)}
                              className={cn(
                                'flex items-center gap-3 text-[13px] font-medium transition-all rounded-lg pl-8 pr-3 py-1.5',
                                childActive
                                  ? 'bg-primary/[0.08] text-primary border-l-[3px] border-primary pl-[29px]'
                                  : 'text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground',
                              )}
                            >
                              <ChildIcon
                                size={15}
                                className={cn(
                                  'shrink-0',
                                  childActive ? 'text-primary' : 'text-sidebar-muted',
                                )}
                              />
                              <span>{t(`nav.${child.key}`)}</span>
                            </Link>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              }

              const isActive =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path)
              const Icon = item.icon
              return (
                <Link
                  key={item.key}
                  to={item.path}
                  data-tour={`nav-${item.key}`}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-3 text-[13px] font-medium transition-all rounded-lg px-3 py-2',
                    isActive
                      ? 'bg-primary/[0.08] text-primary border-l-[3px] border-primary pl-[9px]'
                      : 'text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground',
                  )}
                >
                  <Icon
                    size={17}
                    className={cn(
                      'shrink-0',
                      isActive ? 'text-primary' : 'text-sidebar-muted',
                    )}
                  />
                  <span>{t(`nav.${item.key}`)}</span>
                </Link>
              )
            })}
            {!workspaceLoading && [
              ...CUSTOM_NAV_ITEMS.filter((item) => hasFeature(item.feature)),
              // The Siprov agent chat is a daily destination when agents
              // are on, so it gets its own direct link alongside Tasks/
              // Calendar/Meetings rather than living only in the chat panel.
              // Only shows once we know this workspace actually has one
              // (siprovAgent) — see the agents.getSiprov query above.
              ...(agentsEnabled && hasFeature('siprov') && siprovAgent
                ? [{ key: 'siprov', path: `/agents/${siprovAgent.id}`, icon: Car }]
                : []),
              ...(pabxEnabled ? [{ key: 'pabx', path: '/pabx', icon: Phone }] : []),
            ].map((item) => {
              const isActive = location.pathname.startsWith(item.path)
              const Icon = item.icon
              return (
                <Link
                  key={item.key}
                  to={item.path}
                  data-tour={`nav-${item.key}`}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-3 text-[13px] font-medium transition-all rounded-lg px-3 py-2',
                    isActive
                      ? 'bg-primary/[0.08] text-primary border-l-[3px] border-primary pl-[9px]'
                      : 'text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground',
                  )}
                >
                  <Icon
                    size={17}
                    className={cn(
                      'shrink-0',
                      isActive ? 'text-primary' : 'text-sidebar-muted',
                    )}
                  />
                  <span>{t(`nav.${item.key}`)}</span>
                </Link>
              )
            })}
          </nav>
          </div>

          <UpdateAvailableBanner onOpen={() => setUpdateDialogOpen(true)} />

          {/* Merged account + workspace menu — one trigger at the
              bottom of the sidebar shows the active workspace as the
              primary identity, the user email + role as the secondary
              line, and combines workspace switching with all the
              account actions that used to live in a separate dropdown. */}
          <div className="px-3 pt-1">
            <WorkspaceSwitcher
              backingUp={backingUp}
              onChangePassword={() => setChangePasswordOpen(true)}
              onTwoFactor={() => setTwoFactorOpen(true)}
              onPasskeys={() => setPasskeysOpen(true)}
              onBackup={async () => {
                setBackingUp(true)
                try {
                  await backupApi.download()
                  toast.success(t('backup.success'))
                } catch {
                  toast.error(t('backup.error'))
                } finally {
                  setBackingUp(false)
                }
              }}
              onUpdateAvailable={() => setUpdateDialogOpen(true)}
              agentsEnabled={agentsEnabled}
            />
          </div>

          <div className="px-3 pb-3 pt-1">
            <div
              className="text-[11px] leading-4 text-sidebar-muted/70 text-center"
              role="note"
            >
              <span className="sr-only">{versionA11yLabel}</span>
              <span aria-hidden="true" className="block break-all line-clamp-2">
                {t('app.versionLabel', { version: APP_VERSION })}
              </span>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-h-screen overflow-x-hidden lg:ml-60">
          <div className="p-6 max-w-7xl mx-auto">
            {/* Active-collection filter (issue #105): sticky bar above the
                content so the scope is visible right where the data is. */}
            <CollectionSelector variant="header" />
            <Outlet />
          </div>
        </main>
      </div>

      {showTour && <OnboardingTour onComplete={handleTourComplete} />}
      <ChangePasswordDialog
        open={changePasswordOpen}
        onClose={() => setChangePasswordOpen(false)}
      />
      <TwoFactorSetup
        open={twoFactorOpen}
        onClose={() => setTwoFactorOpen(false)}
      />
      <PasskeyManagementDialog
        open={passkeysOpen}
        onClose={() => setPasskeysOpen(false)}
      />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      {/* Slide-over global chat — opened from the sidebar pill or via
          ⌘J. The previous floating bottom-right button was removed
          since the entry point now lives in the sidebar next to ⌘K. */}
      {chatAvailable && <GlobalChatPanel open={chatOpen} onOpenChange={setChatOpen} />}
      <UpdateAvailableDialog
        open={updateDialogOpen}
        onClose={() => setUpdateDialogOpen(false)}
      />
    </div>
  )
}

/** Shown in the header on every page, not just /meetings — recording lives
 * in a context above <Outlet /> so it keeps going while the user is
 * elsewhere in the app; this is the reminder that it's still on, and a way
 * back to it (and to the finished-recording save prompt once stopped). */
function RecordingPill({ seconds }: { seconds: number }) {
  const { t } = useTranslation()
  const mm = Math.floor(seconds / 60)
  const ss = seconds % 60
  return (
    <Link
      to="/meetings"
      className="flex items-center gap-1.5 rounded-full bg-destructive/10 text-destructive px-2.5 py-1 text-xs font-semibold tabular-nums hover:bg-destructive/20 transition-colors"
      title={t('meetings.recordingInBackground', 'Recording in background — tap to open')}
    >
      <Mic size={12} className="animate-pulse" />
      {mm}:{String(ss).padStart(2, '0')}
    </Link>
  )
}

function UserMenu({
  userInitial,
  logout,
  onChangePassword,
  onTwoFactor,
  onPasskeys,
  onBackup,
  backingUp,
  dark,
  isAdmin,
  agentsEnabled,
}: {
  userInitial: string
  logout: () => void
  onChangePassword: () => void
  onTwoFactor: () => void
  onPasskeys: () => void
  onBackup: () => void
  backingUp: boolean
  dark?: boolean
  isAdmin?: boolean
  agentsEnabled?: boolean
}) {
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const currentLang = resolveSupportedLang(i18n.resolvedLanguage ?? i18n.language)
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-8 w-8 rounded-full p-0" aria-label={t('common.userMenu')}>
          <Avatar className="h-8 w-8">
            <AvatarFallback
              className={
                dark
                  ? 'bg-primary/20 text-primary text-xs font-semibold'
                  : 'bg-primary/10 text-primary text-xs font-semibold'
              }
            >
              {userInitial}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {isAdmin && (
          <>
            <DropdownMenuItem
              onClick={() => nav('/admin')}
              className="flex items-center gap-2"
            >
              <Shield size={14} />
              {t('nav.groupAdmin')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuItem
          onClick={onChangePassword}
          className="flex items-center gap-2"
        >
          <KeyRound size={14} />
          {t('auth.changePassword')}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={onTwoFactor}
          className="flex items-center gap-2"
        >
          <ShieldCheck size={14} />
          {t('auth.twoFactorTitle')}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={onPasskeys}
          className="flex items-center gap-2"
        >
          <Fingerprint size={14} />
          {t('auth.passkeysTitle')}
        </DropdownMenuItem>
        <DropdownMenuItem
          disabled={backingUp}
          onClick={onBackup}
          className="flex items-center gap-2"
        >
          <HardDriveDownload size={14} />
          {backingUp ? t('backup.downloading') : t('backup.button')}
        </DropdownMenuItem>
        {agentsEnabled && (
          <DropdownMenuItem
            onClick={() => nav('/agents')}
            className="flex items-center gap-2"
          >
            <Sparkles size={14} />
            {t('nav.aiAgents')}
          </DropdownMenuItem>
        )}
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="flex items-center gap-2">
            <Languages size={14} />
            <span className="flex-1">{t('setup.language')}</span>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              {currentLang.split('-')[0]}
            </span>
          </DropdownMenuSubTrigger>
          <DropdownMenuPortal>
            <DropdownMenuSubContent className="w-40">
              <DropdownMenuLabel className="px-2 py-1 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
                {t('setup.language')}
              </DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('ru')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Русский</span>
                {currentLang === 'ru' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('de')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Deutsch</span>
                {currentLang === 'de' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('uk')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Українська</span>
                {currentLang === 'uk' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('pt-BR')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Português (BR)</span>
                {currentLang === 'pt-BR' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('pt-PT')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Português (PT)</span>
                {currentLang === 'pt-PT' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('en')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">English</span>
                {currentLang === 'en' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('es')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Español</span>
                {currentLang === 'es' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('pl')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Polski</span>
                {currentLang === 'pl' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('it')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Italiano</span>
                {currentLang === 'it' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => changeLanguageExplicitly('fr')}
                className="flex items-center gap-2"
              >
                <span className="flex-1">Français</span>
                {currentLang === 'fr' && (
                  <Check size={13} className="text-primary" />
                )}
              </DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuPortal>
        </DropdownMenuSub>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={logout}
          className="text-rose-600 focus:text-rose-600"
        >
          {t('auth.logout')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
