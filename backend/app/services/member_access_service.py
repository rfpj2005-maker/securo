"""Which of Securo's own destinations does a given workspace member get?

Tasks, Calendar, Meetings, Cameras, Siprov (the agents chat) and
Inadimplência are Securo-specific additions, not part of the upstream
module system (see `module_service.py`'s "not a feature-flag framework"
— that catalog mirrors the open-source project on purpose and stays
closed). They're gated two ways:

  1. By workspace kind: Cameras, Siprov and Inadimplência are
     Amparar-business infrastructure (physical store security footage;
     a chat over Amparar's own business data; the Em Atraso/Inadimplente/
     Negativado collections queues from the separate "Painel Amparar"
     app, embedded read-only via iframe) — not something a personal
     workspace has any use for, and not something a personal user should
     be able to see just by having *an* account on this install.
     `personal` workspaces never get them, regardless of member
     overrides.
  2. By per-member override, same as the module catalog
     (`WorkspaceMemberHiddenModule`) — an owner can hide any feature
     from a specific sócio within a business workspace.

Tasks/Calendar/Meetings stay available everywhere — they're generically
useful to any user, personal or business.

`siprov` only gates the fixed, workspace-shared agent's own nav link and
detail page (see `SIPROV_AGENT_ID` in the frontend's `lib/features.ts`)
— it does not touch `AGENTS_ENABLED` (the instance-wide switch for the
agents feature as a whole) or a member's access to agents they own
themselves.

`inadimplencia` doesn't touch Securo's own data at all — the page it
gates is just an iframe onto Painel Amparar itself (`rastreador-
conferencia/`, a separate app with its own separate login) — including
its "Carnê" module (associados whose pre-issued batch of boletos is
running out and need a new one generated in Siprov), which lives only
inside Painel Amparar's own nav, not as a separate Securo feature
(2026-09-14: reverted a same-shaped Securo mirror for it — Painel
Amparar's own tabs are the single place to navigate its modules).

`pa_carne`, `pa_cobranca`, `pa_dashboard`, `pa_rastreadores` (2026-09-16,
last one added same day after the owner noticed Rastreadores was the one
Painel Amparar module with no lock at all), and `pa_cancelados` (2026-09-17,
new "vehicles that got cancelled this month" tab) are a different thing from
`inadimplencia` above, despite overlapping names: they gate nothing in
the Securo web app itself (no page, no route) — they exist purely so
this same per-member catalog can drive real enforcement on **Painel
Amparar's own backend** (`rastreador-conferencia/server/bussola-auth.js`'s
`requireFeature`, since 2026-09-16 SSO — Painel Amparar has no login of
its own anymore, it trusts this same catalog) and the **native Android
app**'s unified menu. The web `workspace-settings.tsx` "hide modules"
dialog picks these up for free since it already iterates the whole
`FEATURE_IDS` catalog — that's the mechanism the owner uses to
grant/revoke them per person, same as every other id here.
"""
from collections.abc import Iterable

FEATURE_IDS: tuple[str, ...] = (
    "tasks",
    "calendar",
    "meetings",
    "cameras",
    "siprov",
    "inadimplencia",
    "pa_carne",
    "pa_cobranca",
    "pa_dashboard",
    "pa_rastreadores",
    "pa_cancelados",
)

# Company infrastructure — never shown outside a business workspace, no
# matter what a per-member override says. See module docstring.
BUSINESS_ONLY_FEATURES: frozenset[str] = frozenset(
    {"cameras", "siprov", "inadimplencia", "pa_carne", "pa_cobranca", "pa_dashboard", "pa_rastreadores", "pa_cancelados"}
)


def resolve_features_for_member(kind: str, hidden: Iterable[str] = ()) -> list[str]:
    """Feature list for one member of a workspace of the given `kind`
    ("personal"/"business"): every feature id available to that kind,
    minus their explicit hides."""
    hidden_set = set(hidden)
    available = FEATURE_IDS if kind == "business" else tuple(
        f for f in FEATURE_IDS if f not in BUSINESS_ONLY_FEATURES
    )
    return sorted(f for f in available if f not in hidden_set)
