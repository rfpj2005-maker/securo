import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Phone, PhoneMissed, PhoneOff, TriangleAlert } from 'lucide-react'
import { pabx as pabxApi } from '@/lib/api'
import { useFeatureFlags } from '@/hooks/use-feature-flags'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const DIAS_OPTIONS = [7, 14, 30, 60] as const

function formatDuration(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${m}m ${s}s`
}

export default function PabxPage() {
  const { t } = useTranslation()
  const { pabxEnabled, isLoading: flagsLoading } = useFeatureFlags()
  const [dias, setDias] = useState<number>(7)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['pabx-resumo', dias],
    queryFn: () => pabxApi.resumo(dias),
    enabled: pabxEnabled,
  })

  const tooltipStyle = {
    background: 'var(--card)',
    color: 'var(--foreground)',
    border: '1px solid var(--border)',
    borderRadius: '0.75rem',
    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
    fontSize: '12px',
  }

  if (flagsLoading) {
    return (
      <div>
        <PageHeader section={t('pabx.section', 'Amparar')} title={t('pabx.title', 'PABX')} />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    )
  }

  if (!pabxEnabled) {
    return (
      <div>
        <PageHeader section={t('pabx.section', 'Amparar')} title={t('pabx.title', 'PABX')} />
        <p className="text-sm text-muted-foreground">
          {t('pabx.disabled', 'Este recurso não está habilitado nesta instalação.')}
        </p>
      </div>
    )
  }

  const notConfigured = isError && (error as { response?: { status?: number } })?.response?.status === 503

  return (
    <div>
      <PageHeader
        section={t('pabx.section', 'Amparar')}
        title={t('pabx.title', 'PABX')}
        action={
          <div className="flex items-center rounded-lg border border-border bg-card overflow-hidden">
            {DIAS_OPTIONS.map((opt) => (
              <button
                key={opt}
                onClick={() => setDias(opt)}
                className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
                  dias === opt
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
              >
                {t('pabx.diasOption', '{{count}}d', { count: opt })}
              </button>
            ))}
          </div>
        }
      />
      <p className="text-sm text-muted-foreground mb-5 max-w-2xl">
        {t('pabx.subtitle', 'Volume, duração e roteamento das ligações do PABX (Nuvem JTi).')}
      </p>

      {isLoading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      ) : notConfigured ? (
        <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
          <PhoneOff className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">{t('pabx.notConfigured', 'Integração com o PABX ainda não configurada.')}</p>
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
          <TriangleAlert className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">{t('pabx.error', 'Não foi possível carregar os dados do PABX.')}</p>
        </div>
      ) : data ? (
        <div className="space-y-5">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <KpiCard icon={Phone} label={t('pabx.totalChamadas', 'Total')} value={data.totais.total_chamadas} />
            <KpiCard icon={Phone} label={t('pabx.atendidas', 'Atendidas')} value={data.totais.atendidas} tone="emerald" />
            <KpiCard icon={PhoneMissed} label={t('pabx.naoAtendidas', 'Não atendidas')} value={data.totais.nao_atendidas} tone="amber" />
            <KpiCard icon={PhoneOff} label={t('pabx.falhas', 'Falhas')} value={data.totais.falhas} tone="rose" />
            <KpiCard icon={PhoneOff} label={t('pabx.ocupado', 'Ocupado')} value={data.totais.ocupado} tone="rose" />
            <KpiCard
              icon={Phone}
              label={t('pabx.duracaoMedia', 'Duração média')}
              value={formatDuration(data.totais.duracao_media_segundos)}
            />
          </div>

          {data.totais.soma_categorias_diverge && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
              <TriangleAlert className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>
                {t(
                  'pabx.categoriasDivergemHint',
                  'A soma de atendidas/não atendidas/falhas/ocupado não bate com o total — a operadora classifica algumas ligações em mais de uma categoria. O "Total" é o número correto de ligações.',
                )}
              </span>
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">{t('pabx.chamadasPorDia', 'Chamadas por dia')}</CardTitle>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.por_dia} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <XAxis
                    dataKey="dia"
                    tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                    axisLine={false}
                    tickLine={false}
                    width={32}
                    allowDecimals={false}
                  />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="total" fill="#6366F1" radius={[4, 4, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <RankedListCard title={t('pabx.topDids', 'Números mais discados')} rows={data.top_dids.map((d) => ({ label: d.did, total: d.total }))} />
            <RankedListCard title={t('pabx.topRamais', 'Ramais mais ativos')} rows={data.top_ramais.map((r) => ({ label: r.ramal, total: r.total }))} />
            <RankedListCard title={t('pabx.porTipoRota', 'Por tipo de rota')} rows={data.por_tipo_rota.map((r) => ({ label: r.rota, total: r.total }))} />
          </div>
        </div>
      ) : null}
    </div>
  )
}

const TONE_CLASSES: Record<string, string> = {
  emerald: 'text-emerald-600',
  amber: 'text-amber-600',
  rose: 'text-rose-500',
}

function KpiCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ElementType
  label: string
  value: number | string
  tone?: 'emerald' | 'amber' | 'rose'
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-1">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </div>
        <p className={`text-xl font-semibold tabular-nums ${tone ? TONE_CLASSES[tone] : ''}`}>{value}</p>
      </CardContent>
    </Card>
  )
}

function RankedListCard({ title, rows }: { title: string; rows: { label: string; total: number }[] }) {
  const { t } = useTranslation()
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {rows.length === 0 ? (
          <p className="text-xs text-muted-foreground">{t('pabx.semDados', 'Sem dados no período.')}</p>
        ) : (
          rows.map((row) => (
            <div key={row.label} className="flex items-center justify-between text-sm">
              <span className="truncate text-foreground/90">{row.label}</span>
              <span className="text-muted-foreground tabular-nums shrink-0 ml-2">{row.total}</span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}
