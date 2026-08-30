"""Which of Securo's own destinations does a given workspace member get?

Tasks, Calendar, Meetings, Cameras and Siprov (the agents chat) are
Securo-specific additions, not part of the upstream module system (see
`module_service.py`'s "not a feature-flag framework" — that catalog
mirrors the open-source project on purpose and stays closed). They're
gated two ways:

  1. By workspace kind: Cameras and Siprov are Amparar-business
     infrastructure (physical store security footage; a chat over
     Amparar's own business data) — not something a personal workspace
     has any use for, and not something a personal user should be able
     to see just by having *an* account on this install. `personal`
     workspaces never get them, regardless of member overrides.
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
"""
from collections.abc import Iterable

FEATURE_IDS: tuple[str, ...] = ("tasks", "calendar", "meetings", "cameras", "siprov")

# Company infrastructure — never shown outside a business workspace, no
# matter what a per-member override says. See module docstring.
BUSINESS_ONLY_FEATURES: frozenset[str] = frozenset({"cameras", "siprov"})


def resolve_features_for_member(kind: str, hidden: Iterable[str] = ()) -> list[str]:
    """Feature list for one member of a workspace of the given `kind`
    ("personal"/"business"): every feature id available to that kind,
    minus their explicit hides."""
    hidden_set = set(hidden)
    available = FEATURE_IDS if kind == "business" else tuple(
        f for f in FEATURE_IDS if f not in BUSINESS_ONLY_FEATURES
    )
    return sorted(f for f in available if f not in hidden_set)
