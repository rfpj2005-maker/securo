import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FeatureRoute } from '@/components/feature-route'
import { useWorkspace } from '@/contexts/workspace-context'
import { agents as agentsApi } from '@/lib/api'

/** `/agents/:id` serves both Siprov (a workspace-shared agent, resolved
 *  by name per workspace — see agents.getSiprov / app-layout.tsx's nav
 *  link) and each user's own custom agents. Only Siprov is subject to
 *  per-member restriction; any other id passes through untouched so a
 *  sócio's own agents are never affected by hiding Siprov from them. */
export function SiprovAwareRoute({ children }: { children: React.ReactNode }) {
  const { id } = useParams()
  const { current, isLoading: workspaceLoading } = useWorkspace()
  const { data: siprovAgent, isLoading: siprovLoading } = useQuery({
    queryKey: ['siprov-agent', current?.id],
    queryFn: () => agentsApi.getSiprov(),
    enabled: !!current,
    retry: false,
    staleTime: 1000 * 60,
  })
  // Wait for both to resolve before deciding — otherwise a fresh page
  // load would momentarily see `id !== siprovAgent?.id` (data not in yet)
  // and treat a real Siprov agent as an ordinary one, skipping the
  // feature check entirely instead of just delaying it.
  if (workspaceLoading || siprovLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }
  if (id && id === siprovAgent?.id) {
    return <FeatureRoute feature="siprov">{children}</FeatureRoute>
  }
  return <>{children}</>
}
