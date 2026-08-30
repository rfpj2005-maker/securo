import { Navigate } from 'react-router-dom'
import { useWorkspace } from '@/contexts/workspace-context'
import type { FeatureId } from '@/lib/features'

/** Wraps one of Securo's own destinations (tasks/calendar/meetings/
 *  cameras) so navigating straight to the URL when this member has been
 *  restricted from it lands on home instead of rendering it. Hiding the
 *  nav link alone leaves the page reachable. Mirrors ModuleRoute, but
 *  against `hasFeature` — a separate id space, see lib/features.ts. */
export function FeatureRoute({
  feature,
  children,
}: {
  feature: FeatureId
  children: React.ReactNode
}) {
  const { hasFeature, isLoading } = useWorkspace()
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }
  if (!hasFeature(feature)) return <Navigate to="/" replace />
  return <>{children}</>
}
