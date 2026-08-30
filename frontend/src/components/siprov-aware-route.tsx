import { useParams } from 'react-router-dom'
import { FeatureRoute } from '@/components/feature-route'
import { SIPROV_AGENT_ID } from '@/lib/features'

/** `/agents/:id` serves both Siprov (a fixed, workspace-shared agent
 *  every member can already reach by URL — see SIPROV_AGENT_ID) and each
 *  user's own custom agents. Only Siprov is subject to per-member
 *  restriction; any other id passes through untouched so a sócio's own
 *  agents are never affected by hiding Siprov from them. */
export function SiprovAwareRoute({ children }: { children: React.ReactNode }) {
  const { id } = useParams()
  if (id === SIPROV_AGENT_ID) {
    return <FeatureRoute feature="siprov">{children}</FeatureRoute>
  }
  return <>{children}</>
}
