import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, CheckCircle2, Edit2, Mail, Plug, Plus, Star, Trash2, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/page-header'
import { agents, gmail as gmailApi, emailConnection as emailApi } from '@/lib/api'
import type { LlmConnection } from '@/lib/api'
import { ConnectionFormDialog } from '@/components/agents/connection-form-dialog'
import { EmailConnectionDialog } from '@/components/agents/email-connection-dialog'
import { McpExternalPanel } from '@/components/agents/mcp-external-panel'
import { useWorkspace } from '@/contexts/workspace-context'

export default function AgentConnectionsPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const { canWrite } = useWorkspace()
  const [editing, setEditing] = useState<LlmConnection | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; detail: string }>>({})
  const [searchParams, setSearchParams] = useSearchParams()
  const [emailFormOpen, setEmailFormOpen] = useState(false)

  useEffect(() => {
    if (searchParams.get('gmail_connected')) {
      toast.success(t('agents.connections.gmail.connected', 'Gmail connected'))
      setSearchParams({}, { replace: true })
    } else if (searchParams.get('gmail_error')) {
      toast.error(t('agents.connections.gmail.connectError', 'Could not connect Gmail'))
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const { data: gmailStatus, isLoading: gmailLoading } = useQuery({
    queryKey: ['gmail', 'status'],
    queryFn: () => gmailApi.status(),
  })

  const gmailConnectMut = useMutation({
    mutationFn: () => gmailApi.connect(),
    onSuccess: (data) => {
      window.location.href = data.authorize_url
    },
    onError: () => toast.error(t('common.error')),
  })

  const gmailDisconnectMut = useMutation({
    mutationFn: () => gmailApi.disconnect(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gmail', 'status'] })
      toast.success(t('agents.connections.gmail.disconnected', 'Gmail disconnected'))
    },
  })

  const { data: emailStatus, isLoading: emailLoading } = useQuery({
    queryKey: ['email-connection', 'status'],
    queryFn: () => emailApi.status(),
  })

  const emailDisconnectMut = useMutation({
    mutationFn: () => emailApi.disconnect(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['email-connection', 'status'] })
      toast.success(t('agents.connections.email.disconnected', 'Email disconnected'))
    },
  })

  const { data: list, isLoading } = useQuery({
    queryKey: ['agent-connections'],
    queryFn: () => agents.connections.list(),
  })

  const removeMut = useMutation({
    mutationFn: (id: string) => agents.connections.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-connections'] })
      toast.success(t('agents.connections.deleted'))
    },
  })

  const testMut = useMutation({
    mutationFn: (id: string) => agents.connections.test(id),
    onSuccess: (res, id) => {
      setTestResults((r) => ({ ...r, [id]: { ok: res.ok, detail: res.detail } }))
    },
  })

  return (
    <div>
      <Link
        to="/agents"
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-2 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> {t('agents.title')}
      </Link>

      <PageHeader
        section={t('agents.title')}
        title={t('agents.connections.title')}
        action={
          canWrite ? (
            <Button size="sm" className="gap-1.5 h-8" onClick={() => setCreateOpen(true)}>
              <Plus size={13} /> {t('agents.connections.add')}
            </Button>
          ) : undefined
        }
      />

      <p className="text-sm text-muted-foreground mb-6 max-w-2xl">{t('agents.connections.subtitle')}</p>

      {isLoading ? (
        <div className="bg-card rounded-xl border border-border shadow-sm p-6 text-sm text-muted-foreground">
          {t('agents.loading')}
        </div>
      ) : (list?.length ?? 0) === 0 ? (
        <div className="bg-card rounded-xl border border-border shadow-sm p-10 text-center">
          <div className="h-12 w-12 mx-auto rounded-full bg-muted flex items-center justify-center mb-3">
            <Plug className="h-6 w-6 text-muted-foreground" />
          </div>
          <h2 className="text-base font-semibold">{t('agents.connections.empty.title')}</h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
            {t('agents.connections.empty.subtitle')}
          </p>
          {canWrite && (
            <Button size="sm" className="gap-1.5 h-8 mt-4" onClick={() => setCreateOpen(true)}>
              <Plus size={13} /> {t('agents.connections.add')}
            </Button>
          )}
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
          <div className="divide-y divide-border">
            {list?.map((c) => {
              const tested = testResults[c.id]
              return (
                <div
                  key={c.id}
                  className="flex items-start gap-3 px-4 sm:px-5 py-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="h-10 w-10 rounded-md bg-muted flex items-center justify-center shrink-0">
                    <Plug className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold truncate">{c.name}</span>
                      <Badge variant="secondary" className="text-[10px] uppercase tracking-wider px-1.5 py-0">
                        {c.kind}
                      </Badge>
                      {c.is_default && (
                        <Badge className="text-[10px] uppercase tracking-wider px-1.5 py-0 bg-amber-100 hover:bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200 inline-flex items-center gap-1">
                          <Star className="h-3 w-3" /> {t('agents.connections.default')}
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5 truncate">
                      {c.base_url || t('agents.connections.providerDefaultEndpoint')} ·{' '}
                      {c.default_model || t('agents.connections.noDefaultModel')}
                    </div>
                    {tested && (
                      <div
                        className={`mt-2 inline-flex items-center gap-1.5 text-xs ${
                          tested.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                        }`}
                      >
                        {tested.ok ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                        {tested.detail}
                      </div>
                    )}
                  </div>
                  {canWrite && (
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-8 text-xs"
                        onClick={() => testMut.mutate(c.id)}
                        disabled={testMut.isPending}
                      >
                        {t('agents.connections.test')}
                      </Button>
                      <button
                        type="button"
                        onClick={() => setEditing(c)}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors"
                        title={t('common.edit')}
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (confirm(t('agents.connections.deleteConfirm', { name: c.name }))) {
                            removeMut.mutate(c.id)
                          }
                        }}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                        title={t('common.delete')}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      <McpExternalPanel />

      {/* Gmail — a per-person connection, like Google Calendar: each user
          links their own inbox, and their agent's Ferramentas tab is where
          search_gmail/get_gmail_message get switched on for it. */}
      <div className="mt-8">
        <h2 className="text-sm font-semibold text-foreground mb-1">
          {t('agents.connections.gmail.title', 'Gmail')}
        </h2>
        <p className="text-sm text-muted-foreground mb-3 max-w-2xl">
          {t(
            'agents.connections.gmail.subtitle',
            'Connect your own Gmail so your agents can search and read it (read-only for now — drafting and sending come later).',
          )}
        </p>
        <div className="bg-card rounded-xl border border-border shadow-sm p-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-muted flex items-center justify-center shrink-0">
            <Mail className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            {gmailLoading ? (
              <span className="text-sm text-muted-foreground">{t('agents.loading')}</span>
            ) : gmailStatus?.connected ? (
              <>
                <p className="text-sm font-medium text-foreground truncate">{gmailStatus.gmail_email}</p>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 inline-flex items-center gap-1 mt-0.5">
                  <CheckCircle2 className="h-3.5 w-3.5" /> {t('agents.connections.gmail.connectedLabel', 'Connected')}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t('agents.connections.gmail.notConnected', 'Not connected')}</p>
            )}
          </div>
          {canWrite && (
            gmailStatus?.connected ? (
              <Button size="sm" variant="outline" onClick={() => gmailDisconnectMut.mutate()} disabled={gmailDisconnectMut.isPending}>
                {t('agents.connections.gmail.disconnect', 'Disconnect')}
              </Button>
            ) : (
              <Button size="sm" onClick={() => gmailConnectMut.mutate()} disabled={gmailConnectMut.isPending}>
                {t('agents.connections.gmail.connect', 'Connect Gmail')}
              </Button>
            )
          )}
        </div>
      </div>

      {/* Generic IMAP email (Hostinger, or any other traditional mailbox) —
          same per-person model as Gmail, but no OAuth: the user types their
          own IMAP host/username/password directly into this form. */}
      <div className="mt-8">
        <h2 className="text-sm font-semibold text-foreground mb-1">
          {t('agents.connections.email.title', 'Email')}
        </h2>
        <p className="text-sm text-muted-foreground mb-3 max-w-2xl">
          {t(
            'agents.connections.email.subtitle',
            'Connect a business or other traditional mailbox (e.g. Hostinger) via IMAP so your agents can search and read it.',
          )}
        </p>
        <div className="bg-card rounded-xl border border-border shadow-sm p-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-muted flex items-center justify-center shrink-0">
            <Mail className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            {emailLoading ? (
              <span className="text-sm text-muted-foreground">{t('agents.loading')}</span>
            ) : emailStatus?.connected ? (
              <>
                <p className="text-sm font-medium text-foreground truncate">{emailStatus.email_address}</p>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 inline-flex items-center gap-1 mt-0.5">
                  <CheckCircle2 className="h-3.5 w-3.5" /> {t('agents.connections.email.connectedLabel', 'Connected')}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t('agents.connections.email.notConnected', 'Not connected')}</p>
            )}
          </div>
          {canWrite && (
            emailStatus?.connected ? (
              <Button size="sm" variant="outline" onClick={() => emailDisconnectMut.mutate()} disabled={emailDisconnectMut.isPending}>
                {t('agents.connections.email.disconnect', 'Disconnect')}
              </Button>
            ) : (
              <Button size="sm" onClick={() => setEmailFormOpen(true)}>
                {t('agents.connections.email.connect', 'Connect email')}
              </Button>
            )
          )}
        </div>
      </div>

      <ConnectionFormDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ConnectionFormDialog
        open={!!editing}
        onOpenChange={(o) => !o && setEditing(null)}
        connection={editing}
      />
      <EmailConnectionDialog open={emailFormOpen} onOpenChange={setEmailFormOpen} />
    </div>
  )
}
