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
import json
import os
import time
from datetime import date
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.workspace_service import is_business_member
from mcp_server.auth import CallContext
from mcp_server.registry import tool

_BASE_URL = "https://acesso.siprov.com.br/siprov-api"


async def _require_business_member(session: AsyncSession, ctx: CallContext) -> None:
    """Siprov is Amparar's own business system (associados, financeiro) —
    mirrors the same reasoning as cameras/PABX. A personal-only user
    could otherwise enable these tools on their own agent and query real
    associado/financial data that has nothing to do with them."""
    if not await is_business_member(session, ctx.user_id):
        raise PermissionError("Siprov tools are only available to business workspace members.")


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


async def _siprov_post(path: str, json_body: dict[str, Any]) -> Any:
    """POST against the Siprov API with a cached bearer token, retrying once
    on 401. Used for the report-generation endpoints (see
    _siprov_generate_report) — everything else in this file is read-only."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await _get_token(client)
        resp = await client.post(
            f"{_BASE_URL}{path}", headers={"authorization": f"Bearer {token}"}, json=json_body
        )
        if resp.status_code == 401:
            token = await _get_token(client, force=True)
            resp = await client.post(
                f"{_BASE_URL}{path}", headers={"authorization": f"Bearer {token}"}, json=json_body
            )
        resp.raise_for_status()
        return resp.json()


_REPORT_POLL_INTERVAL_SECONDS = 2
_REPORT_POLL_MAX_ATTEMPTS = 30  # 60s ceiling — a 69-row adesão report finished in ~4-6s live


async def _siprov_generate_report(base_path: str, body: dict[str, Any]) -> Any:
    """Siprov's report endpoints (adesão, financeiro) are async, not a plain
    GET — confirmed live against the real API (a bare GET on `base_path`,
    which is what this file used to do, hits "Recuperar Parâmetros de
    Adesão" — the report's PARAMETER schema, not any data, which is why it
    always looked empty). The real flow:

        1. POST base_path with the filter body -> {codRelatorio, ...}
        2. OPTIONS base_path/{codRelatorio} -> {situacao: PENDENTE|PROCESSANDO|FINALIZADO|CANCELADO, ...}
           poll this until it's done generating.
        3. GET base_path/{codRelatorio} -> the actual rows (when formato=JSON).

    Siprov returns `situacao` upper-cased ("FINALIZADO") even though its
    own OpenAPI spec documents the enum as Title-case ("Finalizado") — the
    comparisons below are case-insensitive so a spelling drift either way
    doesn't quietly break this again.
    """
    started = await _siprov_post(base_path, {k: v for k, v in body.items() if v is not None})
    cod_relatorio = started.get("codRelatorio")
    if cod_relatorio is None:
        raise RuntimeError(f"Siprov did not return codRelatorio when generating a report: {started}")

    detail_path = f"{base_path}/{cod_relatorio}"
    situacao = str(started.get("situacao") or "").upper()

    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await _get_token(client)
        for _ in range(_REPORT_POLL_MAX_ATTEMPTS):
            if situacao in ("FINALIZADO", "CANCELADO"):
                break
            await asyncio.sleep(_REPORT_POLL_INTERVAL_SECONDS)
            resp = await client.request(
                "OPTIONS", f"{_BASE_URL}{detail_path}", headers={"authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            situacao = str(resp.json().get("situacao") or "").upper()

    if situacao != "FINALIZADO":
        raise RuntimeError(
            f"Siprov report {cod_relatorio} didn't finish generating in time (situacao={situacao})"
        )
    return await _siprov_get(detail_path)


# Report responses can run to hundreds of rows — same reasoning as
# siprov_boletos: dumping everything into the LLM's context is wasteful
# when it usually wants a count, not every row. Siprov's report-download
# endpoint (unlike the live-listing ones) is NOT paginated — one call
# already returns every row (confirmed live: 644 items in one response),
# so this cap is purely about what we hand back to the model, not a real
# fetch limit. That means grouping below runs over the TRUE full set,
# not just the capped sample.
_REPORT_ITEMS_CAP = 50


def _dedupe_cancelamento_rows(items: list[dict]) -> list[dict]:
    """Layout 4008 (cancelamentos) emits one row per financial component
    of the same cancellation — itens_titular_valor_total varies between
    rows, everything else identifying the event is identical. Confirmed
    live against real data: 1,277 raw rows collapsed to 538 real
    cancellation events (2-5 duplicate rows per event). Uncorrected, every
    count/aggregate off this report (including por_grupo) overcounts by
    roughly 2-2.5x — this was caught live when the model had to eyeball
    and disclaim it manually; fixing it here means it never has to again.
    """
    seen: dict[tuple, dict] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        key = (
            it.get("veiculo_placa_veiculo"),
            it.get("beneficio_data_cancelamento"),
            it.get("beneficio_nome_consultor"),
            it.get("beneficio_data_ativacao"),
        )
        if key not in seen:
            seen[key] = it
    return list(seen.values())


def _tenure_stats(items: list[dict]) -> Optional[dict[str, Any]]:
    """Days between ativação and cancelamento, over every deduped row that
    has both dates — average and median. Cheap now that the report is
    deduped and the full set (not just the capped sample) is in memory;
    answers a question ('quanto tempo até cancelar?') the model
    previously had to decline for lack of the complete dataset."""
    days: list[int] = []
    for it in items:
        start, end = it.get("beneficio_data_ativacao"), it.get("beneficio_data_cancelamento")
        if not start or not end:
            continue
        try:
            delta = (date.fromisoformat(end) - date.fromisoformat(start)).days
        except ValueError:
            continue
        if delta >= 0:
            days.append(delta)
    if not days:
        return None
    days.sort()
    mid = len(days) // 2
    median = days[mid] if len(days) % 2 else (days[mid - 1] + days[mid]) / 2
    return {
        "media_dias": round(sum(days) / len(days), 1),
        "mediana_dias": median,
        "amostra": len(days),
    }


def _cap_report_items(items: Any, *, group_by: Optional[str] = None) -> dict[str, Any]:
    """`group_by`, when given a field name present on the rows (e.g.
    'beneficio_nome_consultor'), adds a `por_grupo` breakdown — counted
    over every row Siprov returned, not just the capped `itens` sample —
    so a question like 'quantos cancelamentos por consultora' doesn't
    require walking the report in monthly windows and summing by hand."""
    if not isinstance(items, list):
        return {"quantidade": 0, "itens": [], "itens_omitidos": 0}
    result: dict[str, Any] = {
        "quantidade": len(items),
        "itens": items[:_REPORT_ITEMS_CAP],
        "itens_omitidos": max(0, len(items) - _REPORT_ITEMS_CAP),
    }
    if group_by:
        counts: dict[str, int] = {}
        for it in items:
            if not isinstance(it, dict):
                continue
            key = it.get(group_by)
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
        if counts:
            result["por_grupo"] = [
                {"valor": k, "quantidade": v}
                for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
            ]
    return result


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
    await _require_business_member(session, ctx)
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
    name="siprov_beneficio",
    description=(
        "Look up an associado's benefício (the actual plan/contract) — separate from "
        "siprov_buscar_associado, which only returns personal/vehicle registration data. "
        "This is where the responsible consultor (nomeConsultor), the monthly plan value "
        "(valorMensalidade), plan name, and situação live. Use this to answer 'who is the "
        "consultant for X' or 'how much does X pay per month' — siprov_buscar_associado "
        "cannot answer those. Requires cpf, cnpj, or placa (resolve from "
        "siprov_buscar_associado if you only have a name)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "cpf": {"type": "string"},
            "cnpj": {"type": "string"},
            "placa": {"type": "string"},
        },
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_beneficio(
    *, session: AsyncSession, ctx: CallContext, cpf: str | None = None, cnpj: str | None = None, placa: str | None = None
) -> Any:
    await _require_business_member(session, ctx)
    if not cpf and not cnpj and not placa:
        raise ValueError("Provide at least one of: cpf, cnpj, placa")
    return await _siprov_get("/ext/beneficio", {"cpf": cpf, "cnpj": cnpj, "placa": placa})


@tool(
    name="siprov_eventos",
    description=(
        "Search eventos (sinistros/acionamentos de proteção veicular — claim/incident records) "
        "in Siprov. To find a specific person's events, resolve them with siprov_buscar_associado "
        "first and pass their cod_pessoa (or cpf_cnpj) here — there is no free-text name filter on "
        "this endpoint. Otherwise filter by protocolo or by date range. Returns protocolo, "
        "tipoEvento, situacao, dataAbertura, dataEvento, codEvento per evento — NOT a cost/value "
        "field (events themselves have no valor). For the cost of a specific event, take its "
        "codEvento and call siprov_evento_orcamentos."
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
    await _require_business_member(session, ctx)
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
    name="siprov_evento_orcamentos",
    description=(
        "Get the orçamentos (cost quotes) for one evento — this is where an evento's cost "
        "actually lives (events themselves have no valor field). Get cod_evento from "
        "siprov_eventos first. An evento can have multiple orçamentos (different fornecedores, "
        "or a revised quote) — `situacao` on each tells you which is approved/pending/rejected; "
        "don't assume the first one is the real cost, check situacao."
    ),
    parameters={
        "type": "object",
        "properties": {
            "cod_evento": {"type": "integer", "description": "From siprov_eventos' codEvento field"},
        },
        "required": ["cod_evento"],
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_evento_orcamentos(*, session: AsyncSession, ctx: CallContext, cod_evento: int) -> Any:
    await _require_business_member(session, ctx)
    return await _siprov_get(f"/ext/evento/{cod_evento}/orcamentos")


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
    await _require_business_member(session, ctx)
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
        "List/total boletos (payment slips) due in a date range, optionally for one specific "
        "associado (pass cpf_cnpj — e.g. 'is this person up to date on their payments'). Handles "
        "Siprov's 100-item-per-page limit internally — walks every page and returns the TRUE total "
        "count and a precomputed `valor_total` (sum of `valor` across every matching boleto, not "
        "just the ones shown), so you never need to paginate manually or sum amounts yourself. The "
        "raw `itens` list is capped at 50 for context size — `itens_omitidos` tells you how many "
        "more exist beyond that; use `quantidade`/`valor_total` for counts and totals, not "
        "len(itens).\n\n"
        "IMPORTANT: when `situacao` is omitted, Siprov does NOT return every boleto — it silently "
        "returns only 'active' ones (Aberto/Pendente/Protestado-style), EXCLUDING 'Liquidado' (paid) "
        "and 'Cancelado'. To answer 'how many were paid' or 'is this person current', pass situacao "
        "explicitly — e.g. ['Aberto', 'Pendente', 'Liquidado', 'Cancelado', 'Protestado', 'Negociado'] "
        "to see the whole picture for one person's payment history."
    ),
    parameters={
        "type": "object",
        "properties": {
            "data_vencimento_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_vencimento_final": {"type": "string", "description": "dd/MM/yyyy"},
            "cpf_cnpj": {
                "type": "string",
                "description": "Restrict to one associado's boletos — from siprov_buscar_associado.",
            },
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
    cpf_cnpj: str | None = None,
    situacao: str | list[str] | None = None,
) -> Any:
    await _require_business_member(session, ctx)
    base_params = {
        "dataVencimentoInicial": data_vencimento_inicial,
        "dataVencimentoFinal": data_vencimento_final,
        "cpfCnpj": cpf_cnpj,
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
        "Generate and pull Siprov's adesão report — bulk data by cancellation or "
        "enrollment date, not a single associado. Use this for 'how many cancelled "
        "in August', 'list of cancellations this month', portfolio growth, etc. "
        "Slower than the other siprov_* tools (Siprov generates the report "
        "asynchronously, this polls until it's ready — usually a few seconds). "
        "cod_layout defaults to 4008 ('LISTA DE CANCELADOS'), the only layout "
        "confirmed working — it returns cancellations, not new enrollments. If a "
        "user needs a different report shape (new adesões, etc.), a different "
        "cod_layout would need to be found in Siprov's own report configuration "
        "first; don't guess a value that hasn't been confirmed.\n\n"
        "For layout 4008, two things are already handled server-side so you "
        "don't need to catch or disclaim them yourself: (1) Siprov emits 2-5 "
        "rows per real cancellation (one per financial component of the same "
        "event) — already deduplicated to one row per real vehicle/event before "
        "you see it, so `quantidade`/`itens`/`por_grupo` are true counts, not "
        "inflated line counts. (2) the response includes `tempo_ate_cancelamento` "
        "({media_dias, mediana_dias, amostra}) — days between ativação and "
        "cancelamento, computed over the full deduped set. Two dimensions the "
        "report genuinely does NOT have, so don't imply you can get them from "
        "this tool: city/location, and the vehicle's own market value (only "
        "`beneficio_valor_mensalidade`, the plan price, is present).\n\n"
        "IMPORTANT: omitting BOTH date_cancelamento_* and data_adesao_* does not "
        "mean 'no filter, show recent activity' — it returns Siprov's ENTIRE "
        "historical dataset for this layout (thousands of rows), mixing every "
        "benefício status (Ativo, Cancelado, Substituído, Negativado, "
        "Inadimplente...), not just cancellations. For any date-scoped question "
        "('this month', 'in August', etc.) always pass "
        "data_cancelamento_inicial/data_cancelamento_final — that's what actually "
        "narrows the result. `quantidade` in the response is the true total "
        "count (computed from Siprov's own report metadata) — trust it over "
        "counting `itens`, which is capped at 50 for context size; "
        "`itens_omitidos` says how many more exist beyond that. That cap is "
        "ONLY about what's shown to you — Siprov's report download is not "
        "paginated, one call already returns every row.\n\n"
        "The response also includes `por_grupo`: a count of rows per "
        "consultor (field beneficio_nome_consultor), sorted highest first, "
        "e.g. {valor: 'FULANO', quantidade: 12}. Use this directly for any "
        "per-consultora question (cancellations by consultant, a rate/index "
        "study, etc.) instead of walking the date range in monthly windows "
        "and summing itens by hand — it's already the true total per "
        "consultor for whatever period you queried."
    ),
    parameters={
        "type": "object",
        "properties": {
            "cod_layout": {"type": "integer", "description": "Siprov report layout id. Default 4008 = cancellations."},
            "data_cancelamento_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_cancelamento_final": {"type": "string", "description": "dd/MM/yyyy"},
            "data_adesao_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_adesao_final": {"type": "string", "description": "dd/MM/yyyy"},
        },
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_relatorio_adesao(
    *,
    session: AsyncSession,
    ctx: CallContext,
    cod_layout: int = 4008,
    data_cancelamento_inicial: str | None = None,
    data_cancelamento_final: str | None = None,
    data_adesao_inicial: str | None = None,
    data_adesao_final: str | None = None,
) -> Any:
    await _require_business_member(session, ctx)
    # Enforced, not just documented: a prose warning in the description is
    # easy for a smaller/local model to skip. Omitting every date filter
    # doesn't mean "no filter, show me something reasonable" — it means
    # Siprov's entire historical dataset for this layout (thousands of
    # rows, every benefício status mixed together), which is never what a
    # date-scoped question ("cancelled in August") actually wants. Reject
    # it outright so the agent gets an explicit, actionable error instead
    # of silently the wrong (much bigger, unfiltered) answer.
    if not any(
        (data_cancelamento_inicial, data_cancelamento_final, data_adesao_inicial, data_adesao_final)
    ):
        raise ValueError(
            "At least one date filter is required (data_cancelamento_inicial/"
            "data_cancelamento_final for cancellations, or data_adesao_inicial/"
            "data_adesao_final for enrollments). Without one, this would return "
            "Siprov's entire historical dataset for this layout — thousands of "
            "rows mixing every benefício status (Ativo, Cancelado, Substituído, "
            "Negativado, Inadimplente...), not a date-scoped answer. Pick a "
            "range that actually covers what was asked."
        )
    items = await _siprov_generate_report(
        "/ext/relatorio/adesao",
        {
            "codLayout": cod_layout,
            "formato": "JSON",
            "dataCancelamentoInicial": data_cancelamento_inicial,
            "dataCancelamentoFinal": data_cancelamento_final,
            "dataAdesaoInicial": data_adesao_inicial,
            "dataAdesaoFinal": data_adesao_final,
        },
    )
    result_extra: dict[str, Any] = {}
    if cod_layout == 4008 and isinstance(items, list):
        items = _dedupe_cancelamento_rows(items)
        tenure = _tenure_stats(items)
        if tenure:
            result_extra["tempo_ate_cancelamento"] = tenure
    result = _cap_report_items(items, group_by="beneficio_nome_consultor")
    result.update(result_extra)
    return result


@tool(
    name="siprov_relatorio_financeiro",
    description=(
        "Generate and pull Siprov's financial report (faturamento, recebimentos, etc.) — "
        "bulk data by date range, not a single título (see siprov_titulos_financeiros/"
        "siprov_boletos for that). cod_layout must be a report layout id configured in "
        "Siprov — there is no confirmed default for this one, unlike siprov_relatorio_adesao. "
        "If you don't have a cod_layout, ask the user or check Siprov's report configuration "
        "rather than guessing. Slower than the other siprov_* tools (Siprov generates the "
        "report asynchronously, this polls until it's ready)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "cod_layout": {"type": "integer", "description": "Siprov report layout id — no confirmed default"},
            "tipo_lancamento": {"type": "string", "enum": ["Débito", "Crédito", "Rateio"]},
            "data_vencimento_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_vencimento_final": {"type": "string", "description": "dd/MM/yyyy"},
            "data_liquidacao_inicial": {"type": "string", "description": "dd/MM/yyyy"},
            "data_liquidacao_final": {"type": "string", "description": "dd/MM/yyyy"},
            "situacao_titulo": {
                "type": "array",
                "items": {"type": "string", "enum": _BOLETO_SITUACOES},
            },
        },
        "required": ["cod_layout", "tipo_lancamento"],
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_relatorio_financeiro(
    *,
    session: AsyncSession,
    ctx: CallContext,
    cod_layout: int,
    tipo_lancamento: str,
    data_vencimento_inicial: str | None = None,
    data_vencimento_final: str | None = None,
    data_liquidacao_inicial: str | None = None,
    data_liquidacao_final: str | None = None,
    situacao_titulo: list[str] | None = None,
) -> Any:
    await _require_business_member(session, ctx)
    items = await _siprov_generate_report(
        "/ext/relatorio/financeiro",
        {
            "codLayout": cod_layout,
            "formato": "JSON",
            "tipoLancamento": tipo_lancamento,
            "dataVencimentoInicial": data_vencimento_inicial,
            "dataVencimentoFinal": data_vencimento_final,
            "dataLiquidacaoInicial": data_liquidacao_inicial,
            "dataLiquidacaoFinal": data_liquidacao_final,
            "situacaoTitulo": situacao_titulo,
        },
    )
    return _cap_report_items(items)


# Local cache of the full associado portfolio, refreshed straight from the
# live Siprov API every 6h by a Celery beat task (app.tasks.siprov_tasks —
# see backend/app/worker.py), independent of both this MCP server process
# and of any user's personal files. This used to read a CSV mirrored from
# the workspace admin's personal Obsidian vault; that vault moved off this
# server entirely on 2026-09-03/04 (to a local+Obsidian-Sync setup on his
# own machine, specifically so personal data stays out of the shared
# Amparar server) which orphaned that approach. Sourcing the cache from
# the API directly instead of a personal vault also means this is regular
# shared business data now, not something that needs restricting to one
# person — same _require_business_member as every other Siprov tool here.
_CARTEIRA_CACHE_PATH = "/app/data/siprov_cache/carteira.json"
_CARTEIRA_ITEMS_CAP = 100
_CARTEIRA_GROUP_FIELDS = {"cidade": "cidade", "uf": "uf", "situacao": "situacao"}


def _load_carteira_cache() -> Optional[dict[str, Any]]:
    if not os.path.isfile(_CARTEIRA_CACHE_PATH):
        return None
    with open(_CARTEIRA_CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalize_digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def _carteira_group_value(item: dict, field: str) -> str:
    """cidade/uf live under item['endereco'] in the raw /ext/associado shape;
    situacao is top-level. Centralized here so the filter and the grouping
    below can't drift out of sync on where a field actually lives."""
    if field in ("cidade", "uf"):
        return ((item.get("endereco") or {}).get(field) or "").strip()
    return (item.get(field) or "").strip()


@tool(
    name="siprov_carteira_cache",
    description=(
        "Search the FULL associado portfolio from a local cache (refreshed straight "
        "from the live Siprov API every 6h) instead of a live call — use this for two "
        "situations the other siprov_* tools can't handle well:\n"
        "1. Bulk/aggregate questions across the whole portfolio in one call — 'quantos "
        "associados em Contagem', 'cancelados por cidade', 'associados ativos em MG' — "
        "pass agrupar_por ('cidade', 'uf', or 'situacao') to get real counts per value "
        "over the FULL cache (not just the capped sample shown in itens).\n"
        "2. A fallback when siprov_buscar_associado / siprov_beneficio are down (this "
        "reads a local file, no live API call at all).\n\n"
        "Trade-off: data is as of the last refresh (up to ~6h old), not real-time — for "
        "one associado's current exact status, prefer siprov_buscar_associado. Fields "
        "are the raw Siprov shape: codPessoa, nomePessoa, cpfCnpj, sexo, idade, "
        "endereco (nested: logradouro, numero, bairro, cidade, uf, cep), "
        "telefoneCelular, email, placa, chassi, sequencial, tipoBeneficio, situacao, "
        "dataCadastro, dataAdesao, dataAtivacao, numeroCartaoDesconto, planos (list). "
        "No `consultor` field here — for that, use siprov_beneficio per person."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nome": {"type": "string", "description": "Substring match on nomePessoa, case-insensitive"},
            "cpf": {"type": "string", "description": "Digits only or formatted, either works"},
            "cidade": {"type": "string", "description": "Exact match, case-insensitive"},
            "uf": {"type": "string"},
            "situacao": {"type": "string", "description": "e.g. Ativo, Cancelado, Substituido"},
            "placa": {"type": "string"},
            "agrupar_por": {
                "type": "string",
                "enum": list(_CARTEIRA_GROUP_FIELDS.keys()),
                "description": "Adds a `por_grupo` count breakdown over the full filtered set, e.g. 'cidade' for cancellations-by-city.",
            },
        },
        "additionalProperties": False,
    },
    tags=["read", "siprov"],
)
async def siprov_carteira_cache(
    *,
    session: AsyncSession,
    ctx: CallContext,
    nome: str | None = None,
    cpf: str | None = None,
    cidade: str | None = None,
    uf: str | None = None,
    situacao: str | None = None,
    placa: str | None = None,
    agrupar_por: str | None = None,
) -> Any:
    await _require_business_member(session, ctx)
    cache = _load_carteira_cache()
    if cache is None:
        raise RuntimeError(
            "Cache local da carteira ainda não existe — a tarefa periódica "
            "(app.tasks.siprov_tasks.sync_siprov_carteira) pode não ter rodado ainda. "
            "Use siprov_buscar_associado (API ao vivo) como alternativa."
        )
    rows = cache.get("itens") or []

    cpf_digits = _normalize_digits(cpf) if cpf else None

    def matches(r: dict) -> bool:
        if nome and nome.lower() not in (r.get("nomePessoa") or "").lower():
            return False
        if cpf_digits and cpf_digits not in _normalize_digits(r.get("cpfCnpj") or ""):
            return False
        if cidade and cidade.lower() != _carteira_group_value(r, "cidade").lower():
            return False
        if uf and uf.lower() != _carteira_group_value(r, "uf").lower():
            return False
        if situacao and situacao.lower() != (r.get("situacao") or "").lower():
            return False
        if placa and placa.lower() != (r.get("placa") or "").lower():
            return False
        return True

    filtered = [r for r in rows if matches(r)]
    result: dict[str, Any] = {
        "cache_generated_at": cache.get("generated_at"),
        "quantidade": len(filtered),
        "itens": filtered[:_CARTEIRA_ITEMS_CAP],
        "itens_omitidos": max(0, len(filtered) - _CARTEIRA_ITEMS_CAP),
    }
    if agrupar_por:
        counts: dict[str, int] = {}
        for r in filtered:
            key = _carteira_group_value(r, agrupar_por)
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
        result["por_grupo"] = [
            {"valor": k, "quantidade": v}
            for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        ]
    return result
