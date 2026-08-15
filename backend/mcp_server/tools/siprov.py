"""Tools that query the Siprov API (Amparar Benefícios' management system,
vendor Rumo Tecnologia) directly, so an agent can answer questions and pull
reports about the vehicle-protection association's business — associados,
títulos financeiros, boletos, adesão — without the user leaving Securo.

Auth: a dedicated "Tipo de Usuário = API" account in Siprov. The bearer
token is valid 12h and the auth endpoint rate-limits aggressively (429 on
back-to-back calls), so the token is cached in-process and only refreshed
once it's actually expired or rejected.
"""
from __future__ import annotations

import asyncio
import base64
import time
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from mcp_server.auth import CallContext
from mcp_server.registry import tool

_BASE_URL = "https://acesso.siprov.com.br/siprov-api"

# Module-level cache: {"token": str, "expires_at": float (unix seconds)}.
# One Siprov account for the whole instance, so a single shared cache is
# correct — this isn't per-workspace data.
_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}

# The agent runtime executes an assistant's tool calls concurrently
# (asyncio.gather). Without this lock, two tools that both miss the cache
# (e.g. right after a restart) each fire their own authentication request
# at the same instant — and Siprov's auth endpoint 429s the second one.
# The lock makes every concurrent caller share one in-flight authentication.
_auth_lock = asyncio.Lock()


class SiprovNotConfigured(RuntimeError):
    pass


async def _authenticate(client: httpx.AsyncClient) -> str:
    settings = get_settings()
    email = settings.siprov_api_email
    password = settings.siprov_api_password.get_secret_value()
    if not email or not password:
        raise SiprovNotConfigured(
            "Siprov API credentials are not configured (SIPROV_API_EMAIL / SIPROV_API_PASSWORD)."
        )
    basic = base64.b64encode(f"{email}:{password}".encode()).decode()
    headers = {"authorization": f"Basic {basic}", "accept": "application/json"}
    resp = await client.post(f"{_BASE_URL}/ext/autenticacao", headers=headers)
    if resp.status_code == 429:
        # Siprov's auth endpoint rate-limits aggressively on back-to-back
        # calls; a short backoff and single retry clears most transient hits.
        await asyncio.sleep(3)
        resp = await client.post(f"{_BASE_URL}/ext/autenticacao", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    token = data["authorizationToken"]
    # Cache for 11h (under the real 12h TTL) so we never call a stale token.
    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + 11 * 3600
    return token


async def _get_token(client: httpx.AsyncClient, *, force: bool = False) -> str:
    if not force and _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    async with _auth_lock:
        # Re-check after acquiring the lock: another coroutine may have
        # already refreshed the token while we were waiting on it.
        if not force and _token_cache["token"] and time.time() < _token_cache["expires_at"]:
            return _token_cache["token"]
        return await _authenticate(client)


async def _siprov_get(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    """GET against the Siprov API with a cached bearer token, retrying once
    on 401 in case the token was invalidated server-side before our TTL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await _get_token(client)
        resp = await client.get(
            f"{_BASE_URL}{path}",
            headers={"authorization": f"Bearer {token}"},
            params={k: v for k, v in (params or {}).items() if v is not None},
        )
        if resp.status_code == 401:
            token = await _get_token(client, force=True)
            resp = await client.get(
                f"{_BASE_URL}{path}",
                headers={"authorization": f"Bearer {token}"},
                params={k: v for k, v in (params or {}).items() if v is not None},
            )
        resp.raise_for_status()
        return resp.json()


_NOME_FIELD_CANDIDATES = ("nome", "nomeAssociado", "nomeCompleto", "nomePessoa")


def _matches_nome(item: dict[str, Any], needle: str) -> bool:
    needle = needle.strip().lower()
    for field in _NOME_FIELD_CANDIDATES:
        value = item.get(field)
        if isinstance(value, str) and needle in value.lower():
            return True
    return False


@tool(
    name="siprov_buscar_associado",
    description=(
        "Look up an Amparar Benefícios (Siprov) associado by name, CPF, or vehicle plate. "
        "Returns registration data: address, plan, vehicle, situação (status), benefício."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nome": {"type": "string", "description": "Associado's name (partial match, case-insensitive)"},
            "cpf": {"type": "string", "description": "Associado's CPF (digits only or formatted)"},
            "placa": {"type": "string", "description": "Vehicle plate"},
        },
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_buscar_associado(
    *, session: AsyncSession, ctx: CallContext, nome: str | None = None, cpf: str | None = None, placa: str | None = None
) -> Any:
    if not nome and not cpf and not placa:
        raise ValueError("Provide at least one of: nome, cpf, placa")
    result = await _siprov_get("/ext/associado", {"nome": nome, "cpf": cpf, "placa": placa})
    # Siprov's `nome` query param has been unreliable in testing — it can
    # return the full unfiltered list instead of matching. Filter client-side
    # as a safety net whenever a name was requested and the API returned a
    # paginated `itens` list, so the caller always gets a narrowed result.
    if nome and isinstance(result, dict) and isinstance(result.get("itens"), list):
        filtered = [item for item in result["itens"] if isinstance(item, dict) and _matches_nome(item, nome)]
        result = {**result, "itens": filtered, "quantidade": len(filtered)}
    return result


@tool(
    name="siprov_titulos_financeiros",
    description=(
        "List financial títulos (accounts receivable/payable) from Siprov. "
        "`tipo` is required: 'Crédito' (money owed to Amparar), 'Débito', or 'Rateio'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tipo": {"type": "string", "enum": ["Crédito", "Débito", "Rateio"]},
        },
        "required": ["tipo"],
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_titulos_financeiros(*, session: AsyncSession, ctx: CallContext, tipo: str) -> Any:
    return await _siprov_get("/ext/financeiro/titulo", {"tipo": tipo})


@tool(
    name="siprov_boletos",
    description=(
        "List boletos (payment slips) due in a date range, with situação filter "
        "(e.g. 'Aberto' for unpaid). Includes linha digitável and PDF/fatura links per boleto."
    ),
    parameters={
        "type": "object",
        "properties": {
            "data_vencimento_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_vencimento_final": {"type": "string", "description": "dd/MM/yyyy"},
            "situacao": {"type": "string", "description": "e.g. 'Aberto', 'Pago', 'Cancelado'"},
        },
        "required": ["data_vencimento_inicial", "data_vencimento_final"],
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_boletos(
    *,
    session: AsyncSession,
    ctx: CallContext,
    data_vencimento_inicial: str,
    data_vencimento_final: str,
    situacao: str | None = None,
) -> Any:
    return await _siprov_get(
        "/ext/financeiro/titulo/boleto",
        {
            "dataVencimentoInicial": data_vencimento_inicial,
            "dataVencimentoFinal": data_vencimento_final,
            "situacao": situacao,
        },
    )


@tool(
    name="siprov_relatorio_adesao",
    description=(
        "Pull the adesão (enrollment) report — useful for portfolio growth, new "
        "associados, and cancellations over time."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "siprov"],
)
async def siprov_relatorio_adesao(*, session: AsyncSession, ctx: CallContext) -> Any:
    return await _siprov_get("/ext/relatorio/adesao")


@tool(
    name="siprov_relatorio_financeiro",
    description="Pull Siprov's built-in financial report (faturamento, recebimentos, etc.).",
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "siprov"],
)
async def siprov_relatorio_financeiro(*, session: AsyncSession, ctx: CallContext) -> Any:
    return await _siprov_get("/ext/relatorio/financeiro")
