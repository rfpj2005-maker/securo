import { lazy, Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider } from '@/components/theme-provider'
import { AuthProvider } from '@/contexts/auth-context'
import { WorkspaceProvider } from '@/contexts/workspace-context'
import { CollectionFilterProvider } from '@/contexts/collection-filter-context'
import { MeetingRecordingProvider } from '@/contexts/meeting-recording-context'
import { ProtectedRoute } from '@/components/protected-route'
import { AdminRoute } from '@/components/admin-route'
import { AgentsRoute } from '@/components/agents-route'
import { ModuleRoute } from '@/components/module-route'
import { FeatureRoute } from '@/components/feature-route'
import { SiprovAwareRoute } from '@/components/siprov-aware-route'
import { AppLayout } from '@/components/app-layout'

const SetupPage = lazy(() => import('@/pages/setup'))
const LoginPage = lazy(() => import('@/pages/login'))
const ForgotPasswordPage = lazy(() => import('@/pages/forgot-password'))
const ResetPasswordPage = lazy(() => import('@/pages/reset-password'))
const RegisterPage = lazy(() => import('@/pages/register'))
const DashboardPage = lazy(() => import('@/pages/dashboard'))
const TransactionsPage = lazy(() => import('@/pages/transactions'))
const AccountsPage = lazy(() => import('@/pages/accounts'))
const AccountDetailPage = lazy(() => import('@/pages/account-detail'))
const ImportPage = lazy(() => import('@/pages/import'))
const RulesPage = lazy(() => import('@/pages/rules'))
const CategoriesPage = lazy(() => import('@/pages/categories'))
const CollectionsPage = lazy(() => import('@/pages/collections'))
const BudgetsPage = lazy(() => import('@/pages/budgets'))
const RecurringPage = lazy(() => import('@/pages/recurring'))
const GoalsPage = lazy(() => import('@/pages/goals'))
const AssetsPage = lazy(() => import('@/pages/assets'))
const ReportsPage = lazy(() => import('@/pages/reports'))
const PayeesPage = lazy(() => import('@/pages/payees'))
const TasksPage = lazy(() => import('@/pages/tasks'))
const VoiceTaskPage = lazy(() => import('@/pages/voice-task'))
const CalendarPage = lazy(() => import('@/pages/calendar'))
const MeetingsPage = lazy(() => import('@/pages/meetings'))
const CamerasPage = lazy(() => import('@/pages/cameras'))
const PabxPage = lazy(() => import('@/pages/pabx'))
const InadimplenciaPage = lazy(() => import('@/pages/inadimplencia'))
const GroupsPage = lazy(() => import('@/pages/groups'))
const GroupDetailPage = lazy(() => import('@/pages/group-detail'))
const AdminSettingsPage = lazy(() => import('@/pages/admin/settings'))
const AgentsListPage = lazy(() => import('@/pages/agents-list'))
const AgentDetailPage = lazy(() => import('@/pages/agent-detail'))
const AgentConnectionsPage = lazy(() => import('@/pages/agent-connections'))
const InvoicesPage = lazy(() => import('@/pages/invoices'))
const WorkspaceSettingsPage = lazy(() => import('@/pages/workspace-settings'))
const OAuthCallbackPage = lazy(() => import('@/pages/oauth-callback'))
const OIDCCallbackPage = lazy(() => import('@/pages/oidc-callback'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <WorkspaceProvider>
            <Suspense fallback={<LoadingFallback />}>
              <Routes>
                <Route path="/setup" element={<SetupPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/auth/oidc/callback" element={<OIDCCallbackPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route
                  element={
                    <ProtectedRoute>
                      <CollectionFilterProvider>
                        <MeetingRecordingProvider>
                          <AppLayout />
                        </MeetingRecordingProvider>
                      </CollectionFilterProvider>
                    </ProtectedRoute>
                  }
                >
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/transactions" element={<ModuleRoute module="transactions"><TransactionsPage /></ModuleRoute>} />
                  <Route path="/accounts" element={<ModuleRoute module="accounts"><AccountsPage /></ModuleRoute>} />
                  <Route path="/accounts/:id" element={<ModuleRoute module="accounts"><AccountDetailPage /></ModuleRoute>} />
                  <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
                  <Route path="/enable-banking" element={<OAuthCallbackPage />} />
                  <Route path="/import" element={<ModuleRoute module="import"><ImportPage /></ModuleRoute>} />
                  <Route path="/rules" element={<ModuleRoute module="rules"><RulesPage /></ModuleRoute>} />
                  <Route path="/categories" element={<ModuleRoute module="categories"><CategoriesPage /></ModuleRoute>} />
                  <Route path="/collections" element={<CollectionsPage />} />
                  <Route path="/budgets" element={<ModuleRoute module="budgets"><BudgetsPage /></ModuleRoute>} />
                  <Route path="/goals" element={<ModuleRoute module="goals"><GoalsPage /></ModuleRoute>} />
                  <Route path="/recurring" element={<ModuleRoute module="recurring"><RecurringPage /></ModuleRoute>} />
                  <Route path="/assets" element={<ModuleRoute module="assets"><AssetsPage /></ModuleRoute>} />
                  <Route path="/reports" element={<ModuleRoute module="reports"><ReportsPage /></ModuleRoute>} />
                  <Route path="/payees" element={<ModuleRoute module="payees"><PayeesPage /></ModuleRoute>} />
                  <Route path="/tasks" element={<FeatureRoute feature="tasks"><TasksPage /></FeatureRoute>} />
                  <Route path="/tasks/voice" element={<FeatureRoute feature="tasks"><VoiceTaskPage /></FeatureRoute>} />
                  <Route path="/calendar" element={<FeatureRoute feature="calendar"><CalendarPage /></FeatureRoute>} />
                  <Route path="/meetings" element={<FeatureRoute feature="meetings"><MeetingsPage /></FeatureRoute>} />
                  <Route path="/cameras" element={<FeatureRoute feature="cameras"><CamerasPage /></FeatureRoute>} />
                  <Route path="/inadimplencia" element={<FeatureRoute feature="inadimplencia"><InadimplenciaPage /></FeatureRoute>} />
                  <Route path="/pabx" element={<PabxPage />} />
                  <Route path="/groups" element={<ModuleRoute module="split_groups"><GroupsPage /></ModuleRoute>} />
                  <Route path="/groups/:id" element={<ModuleRoute module="split_groups"><GroupDetailPage /></ModuleRoute>} />
                  <Route path="/invoices" element={<ModuleRoute module="invoices"><InvoicesPage /></ModuleRoute>} />
                  <Route path="/workspace/settings" element={<WorkspaceSettingsPage />} />
                  <Route path="/admin" element={<AdminRoute><AdminSettingsPage /></AdminRoute>} />
                  <Route path="/agents" element={<AgentsRoute><AgentsListPage /></AgentsRoute>} />
                  <Route path="/agents/connections" element={<AgentsRoute><AgentConnectionsPage /></AgentsRoute>} />
                  <Route path="/agents/:id" element={<AgentsRoute><SiprovAwareRoute><AgentDetailPage /></SiprovAwareRoute></AgentsRoute>} />
                </Route>
              </Routes>
            </Suspense>
            <Toaster />
            </WorkspaceProvider>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
