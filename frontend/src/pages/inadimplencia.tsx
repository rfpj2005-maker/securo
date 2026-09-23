import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/page-header'
import { ExternalLink } from 'lucide-react'

// Read-only embed of Painel Amparar as a whole — a separate app, but
// (2026-09-16) no longer a separate login: it trusts the same Bússola
// JWT this page already has, passed via URL fragment
// (#dashboard&sso=<token>) since the iframe is a different origin and
// can't read this page's localStorage directly. Painel Amparar's own
// boot() picks the token up, stores it in ITS localStorage, and strips
// it from the visible URL — so it lands straight on the Dashboard with
// no login prompt. Its own top nav has all of its modules (Dashboard,
// Rastreadores, Cobrança, Carnê, ...), so this stays a single generic
// entry point rather than one Securo nav item per module. Whoever
// doesn't have Dashboard access (per Bússola's `pa_dashboard` feature,
// same catalog as everything else here) just sees Painel Amparar's
// normal default view instead. See member_access_service.py's
// `inadimplencia` feature (kept as the underlying id/route for
// continuity) and rastreador-conferencia/README.md for the source of
// truth.
const PAINEL_AMPARAR_BASE = 'https://servidor-ampara.tail887dc2.ts.net:8444'

export default function InadimplenciaPage() {
  const { t } = useTranslation()

  const painelAmpararUrl = useMemo(() => {
    const token = localStorage.getItem('token')
    const sso = token ? `&sso=${encodeURIComponent(token)}` : ''
    return `${PAINEL_AMPARAR_BASE}/#dashboard${sso}`
  }, [])
  // "Abrir em outra aba" intentionally does NOT carry the token in a
  // visible link (a new tab's address bar would show it) — that tab logs
  // in on its own, same as visiting Painel Amparar directly always has.
  const openInNewTabUrl = `${PAINEL_AMPARAR_BASE}/#dashboard`

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)]">
      <PageHeader
        section={t('inadimplencia.section', 'Amparar')}
        title={t('inadimplencia.title', 'Painel Amparar')}
      />
      <p className="text-sm text-muted-foreground mb-3 max-w-2xl flex items-center gap-1.5">
        {t(
          'inadimplencia.subtitle',
          'Rastreadores, cobrança, carnê e mais — mesma conta Bússola, sem login separado.',
        )}
        <a
          href={openInNewTabUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-primary hover:underline shrink-0"
        >
          {t('inadimplencia.openInNewTab', 'Abrir em outra aba')}
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </p>
      <iframe
        src={painelAmpararUrl}
        title="Painel Amparar"
        className="w-full flex-1 rounded-xl border border-border bg-white"
      />
    </div>
  )
}
