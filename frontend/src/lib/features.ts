/**
 * Mirror of the backend's `member_access_service.FEATURE_IDS`.
 *
 * Securo's own destinations (not part of the upstream module system —
 * see `modules.ts`). Always-on for the workspace itself; an owner can
 * hide one per member via the same override the module catalog uses.
 *
 * `pa_carne`/`pa_cobranca`/`pa_dashboard`/`pa_rastreadores` (2026-09-16)
 * and `pa_cancelados` (2026-09-17) are the exception: they gate nothing
 * in this web app (no route reads
 * them) — they exist so Painel Amparar's own backend can enforce them
 * for real (SSO since 2026-09-16 — it trusts this same catalog instead
 * of its own login) and so the native Android app's unified menu has
 * something to check against. This array's consumer in
 * `workspace-settings.tsx` (which just enumerates the whole catalog)
 * picks them up automatically as toggleable per-member permissions
 * without a dedicated screen of its own. See the backend docstring for
 * the full reasoning.
 */
export const FEATURE_IDS = [
  'tasks',
  'calendar',
  'meetings',
  'cameras',
  'siprov',
  'inadimplencia',
  'pa_carne',
  'pa_cobranca',
  'pa_dashboard',
  'pa_rastreadores',
  'pa_cancelados',
] as const

export type FeatureId = (typeof FEATURE_IDS)[number]

/**
 * The "Siprov" nav link's target isn't a fixed agent id — it's resolved
 * per-workspace by name via `agents.getSiprov()` (backend: `agent_service.
 * get_siprov_agent`), since which agent that is depends on which
 * workspace you're viewing (see app-layout.tsx and siprov-aware-route.tsx).
 * `SiprovAwareRoute` compares the URL's agent id against that resolved id
 * and re-checks `hasFeature('siprov')` only for it — every other agent id
 * passes through unaffected, so a sócio's own custom agents aren't part
 * of this restriction.
 */
