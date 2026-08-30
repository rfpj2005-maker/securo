"""Tools that query the Nuvem JTi API (Amparar's cloud PABX) directly, so
an agent can answer questions about call volume/duration/routing without
the user leaving Securo.

Auth: a dedicated API user provisioned by Nuvem JTi support (usuario+token
headers, no expiry/refresh flow — unlike Siprov's bearer token). See
app/services/pabx_service.py, shared with the /api/pabx dashboard route.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import pabx_service
from app.services.workspace_service import is_business_member
from mcp_server.auth import CallContext
from mcp_server.registry import tool


def _parse_br_date(value: str) -> date:
    dd, mm, yyyy = value.split("/")
    return date(int(yyyy), int(mm), int(dd))


async def _require_business_member(session: AsyncSession, ctx: CallContext) -> None:
    """PABX call data is Amparar company infrastructure, not workspace
    data — mirrors the same gate api/pabx.py enforces over HTTP
    (current_business_user)."""
    if not await is_business_member(session, ctx.user_id):
        raise PermissionError("PABX data is only available to business workspace members.")


@tool(
    name="pabx_resumo_chamadas",
    description=(
        "Aggregate call volume/duration/routing summary for Amparar's PABX (Nuvem JTi) over "
        "the last N days. Use this for questions like 'quantas ligações essa semana', 'qual "
        "ramal mais ativo', 'duração média das chamadas' — it does the counting/grouping "
        "server-side so you don't need to page through raw CDR yourself. Returns: total_chamadas "
        "(ground-truth count from the raw call log), atendidas/nao_atendidas/falhas/ocupado (the "
        "operadora's own status classification — NOTE these four numbers can sum to MORE than "
        "total_chamadas, a known overlap in the operadora's categories; don't 'fix' the math, "
        "just report both as given), duracao_media_segundos, calls per day, top DIDs (inbound "
        "numbers) and top ramais (extensions) by volume, and a breakdown by call-routing pattern."
    ),
    parameters={
        "type": "object",
        "properties": {
            "dias": {
                "type": "integer",
                "description": "How many days back from today to include (today counts as day 1). Default 7.",
                "minimum": 1,
                "maximum": 60,
            },
        },
        "additionalProperties": False,
    },
    tags=["read", "pabx"],
)
async def pabx_resumo_chamadas(*, session: AsyncSession, ctx: CallContext, dias: int = 7) -> Any:
    await _require_business_member(session, ctx)
    return await pabx_service.resumo_chamadas(dias=dias)


@tool(
    name="pabx_historico_chamadas",
    description=(
        "List individual calls from Amparar's PABX (Nuvem JTi) in a date range, with filters. "
        "Use this when you need actual call records (e.g. to find a specific call, list calls "
        "from/to a number or ramal, or check recording links) rather than aggregate counts — for "
        "totals/trends use pabx_resumo_chamadas instead, it's cheaper and does the math for you. "
        "Capped at 100 results per call; narrow the date range or add filters if you hit the cap."
    ),
    parameters={
        "type": "object",
        "properties": {
            "data_inicial": {"type": "string", "description": "dd/MM/yyyy. Required."},
            "data_final": {"type": "string", "description": "dd/MM/yyyy. Required. Max 2 months after data_inicial."},
            "filtro_status_chamada": {
                "type": "string",
                "enum": ["atendido", "nao_atendido", "falha", "ocupado"],
                "description": "Optional status filter (the operadora's own classification — see the overlap caveat on pabx_resumo_chamadas).",
            },
            "ramal_origem": {"type": "string", "description": "Optional: filter by originating ramal, e.g. 'amparar-1005'."},
            "ramal_destino": {"type": "string", "description": "Optional: filter by receiving ramal."},
            "did": {"type": "string", "description": "Optional: filter by DID (inbound number)."},
            "quantidade": {"type": "integer", "description": "Max results, capped at 100. Default 50.", "minimum": 1, "maximum": 100},
        },
        "required": ["data_inicial", "data_final"],
        "additionalProperties": False,
    },
    tags=["read", "pabx"],
)
async def pabx_historico_chamadas(
    *,
    session: AsyncSession,
    ctx: CallContext,
    data_inicial: str,
    data_final: str,
    filtro_status_chamada: str | None = None,
    ramal_origem: str | None = None,
    ramal_destino: str | None = None,
    did: str | None = None,
    quantidade: int = 50,
) -> Any:
    await _require_business_member(session, ctx)
    r = await pabx_service.historico_chamadas(
        data_inicial=_parse_br_date(data_inicial),
        data_final=_parse_br_date(data_final),
        filtro_status_chamada=filtro_status_chamada,
        ramal_origem=ramal_origem,
        ramal_destino=ramal_destino,
        did=did,
        quantidade=min(quantidade, 100),
    )
    return {
        "quantidade_total": r.get("qtd_total_resultados", 0),
        "quantidade_retornada": r.get("qtd_resultados_retornados", 0),
        "chamadas": r.get("dados", []),
    }
