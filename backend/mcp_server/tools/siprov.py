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


_MAX_NOME_PAGES = 20  # 20 * 1000 = 20k associados, comfortably above the real total


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
    if nome:
        # Siprov's `nome` query param doesn't filter server-side — it always
        # returns the same first page (1000 itens, alphabetical) regardless
        # of the search string. The real API paginates via `pagina`
        # (confirmed against /openapi.json), so the only way to actually find
        # someone by name is to walk every page ourselves and filter
        # client-side. Capped at _MAX_NOME_PAGES as a safety net against an
        # unexpected `proximaPagina: true` loop.
        all_itens: list[dict[str, Any]] = []
        pagina = 1
        while pagina <= _MAX_NOME_PAGES:
            page_result = await _siprov_get("/ext/associado", {"nome": nome, "pagina": pagina})
            if not isinstance(page_result, dict):
                break
            page_itens = page_result.get("itens")
            if isinstance(page_itens, list):
                all_itens.extend(item for item in page_itens if isinstance(item, dict))
            if not page_result.get("proximaPagina"):
                break
            pagina += 1
        filtered = [item for item in all_itens if _matches_nome(item, nome)]
        return {"quantidade": len(filtered), "itens": filtered}
    return await _siprov_get("/ext/associado", {"cpf": cpf, "placa": placa})


@tool(
    name="siprov_eventos",
    description=(
        "Search eventos (sinistros/acionamentos de proteção veicular — claim/incident records) "
        "in Siprov. To find a specific person's events, resolve them with siprov_buscar_associado "
        "first and pass their cod_pessoa (or cpf_cnpj) here — there is no free-text name filter on "
        "this endpoint. Otherwise filter by protocolo or by date range. Returns protocolo, "
        "tipoEvento, situacao, dataAbertura, dataEvento per evento."
    ),
    parameters={
        "type": "object",
        "properties": {
            "cpf_cnpj": {"type": "string", "description": "CPF/CNPJ of the person involved"},
            "cod_pessoa": {"type": "integer", "description": "Siprov internal person code, from siprov_buscar_associado"},
            "protocolo": {"type": "string"},
            "data_abertura_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_abertura_final": {"type": "string", "description": "dd/MM/yyyy"},
            "data_evento_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_evento_final": {"type": "string", "description": "dd/MM/yyyy"},
        },
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_eventos(
    *,
    session: AsyncSession,
    ctx: CallContext,
    cpf_cnpj: str | None = None,
    cod_pessoa: int | None = None,
    protocolo: str | None = None,
    data_abertura_inicial: str | None = None,
    data_abertura_final: str | None = None,
    data_evento_inicial: str | None = None,
    data_evento_final: str | None = None,
) -> Any:
    return await _siprov_get(
        "/ext/evento",
        {
            "cpfCnpj": cpf_cnpj,
            "codPessoa": cod_pessoa,
            "protocolo": protocolo,
            "dataAberturaInicial": data_abertura_inicial,
            "dataAberturaFinal": data_abertura_final,
            "dataEventoInicial": data_evento_inicial,
            "dataEventoFinal": data_evento_final,
        },
    )


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


_BOLETO_SITUACOES = ["Aberto", "Pendente", "Liquidado", "Cancelado", "Protestado", "Rejeitado", "Agrupado", "Negociado"]
# Siprov caps each page at 100 itens (offset pagination via `inicio`). This
# cap bounds how many pages we'll auto-walk per call — 100 * 50 = 5000
# boletos, comfortably above any realistic single query.
_MAX_BOLETO_PAGES = 50
# Returning thousands of raw records would blow up the LLM's context for no
# reason when it usually just wants a count/sum — sum server-side (exact,
# no LLM arithmetic) and cap the raw list actually returned.
_BOLETO_ITEMS_CAP = 50


@tool(
    name="siprov_boletos",
    description=(
        "List/total boletos (payment slips) due in a date range. Handles Siprov's 100-item-per-page "
        "limit internally — walks every page and returns the TRUE total count and a precomputed "
        "`valor_total` (sum of `valor` across every matching boleto, not just the ones shown), so "
        "you never need to paginate manually or sum amounts yourself. The raw `itens` list is capped "
        "at 50 for context size — `itens_omitidos` tells you how many more exist beyond that; use "
        "`quantidade`/`valor_total` for counts and totals, not len(itens).\n\n"
        "IMPORTANT: when `situacao` is omitted, Siprov does NOT return every boleto — it silently "
        "returns only 'active' ones (Aberto/Pendente/Protestado-style), EXCLUDING 'Liquidado' (paid) "
        "and 'Cancelado'. To answer 'how many were paid' or 'give me the full picture', pass situacao "
        "explicitly — e.g. 'Liquidado' alone for paid ones, or ['Aberto', 'Liquidado'] for both in one "
        "call."
    ),
    parameters={
        "type": "object",
        "properties": {
            "data_vencimento_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_vencimento_final": {"type": "string", "description": "dd/MM/yyyy"},
            "situacao": {
                "anyOf": [
                    {"type": "string", "enum": _BOLETO_SITUACOES},
                    {"type": "array", "items": {"type": "string", "enum": _BOLETO_SITUACOES}},
                ],
                "description": (
                    "One or more statuses to filter by. Omitting this returns Siprov's 'active-only' "
                    "default, NOT all boletos — see the tool description."
                ),
            },
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
    situacao: str | list[str] | None = None,
) -> Any:
    base_params = {
        "dataVencimentoInicial": data_vencimento_inicial,
        "dataVencimentoFinal": data_vencimento_final,
        # The API expects the param repeated for multiple values — httpx
        # does that automatically for a list, so normalize a single string
        # into a one-item list rather than special-casing it.
        "situacao": [situacao] if isinstance(situacao, str) else situacao,
    }

    all_items: list[dict[str, Any]] = []
    total: Optional[int] = None
    inicio = 0
    for _ in range(_MAX_BOLETO_PAGES):
        page = await _siprov_get("/ext/financeiro/titulo/boleto", {**base_params, "inicio": inicio})
        items = page.get("itens") or []
        total = page.get("quantidade", total)
        all_items.extend(items)
        if not items or len(all_items) >= (total or 0):
            break
        inicio += len(items)

    valor_total = round(sum(float(it.get("valor") or 0) for it in all_items), 2)
    return {
        "quantidade": total if total is not None else len(all_items),
        "valor_total": valor_total,
        "itens": all_items[:_BOLETO_ITEMS_CAP],
        "itens_omitidos": max(0, len(all_items) - _BOLETO_ITEMS_CAP),
    }


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
