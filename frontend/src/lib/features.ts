/**
 * Mirror of the backend's `member_access_service.FEATURE_IDS`.
 *
 * Securo's own destinations (not part of the upstream module system —
 * see `modules.ts`). Always-on for the workspace itself; an owner can
 * hide one per member via the same override the module catalog uses.
 */
export const FEATURE_IDS = ['tasks', 'calendar', 'meetings', 'cameras', 'siprov'] as const

export type FeatureId = (typeof FEATURE_IDS)[number]

/**
 * The fixed, workspace-shared agent behind the "Siprov" nav link. Every
 * member of a workspace can already reach `/agents/{this id}` directly
 * (agents are looked up by workspace, not by owner — see
 * `agent_service.get_agent`), so hiding the nav link alone isn't enough;
 * `SiprovAwareRoute` in App.tsx re-checks `hasFeature('siprov')` for this
 * one id and lets every other agent id through unaffected — a sócio's own
 * custom agents aren't part of this restriction.
 */
export const SIPROV_AGENT_ID = '4ce30a80-01b0-4b89-aa35-1e4f6f493e92'
