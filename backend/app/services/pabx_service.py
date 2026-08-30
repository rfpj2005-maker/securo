"""Queries and aggregates call data from Nuvem JTi's API (Amparar's cloud
PABX), so both the `/api/pabx` dashboard and the `pabx_*` agent tools share
one implementation.

Auth: a dedicated API user (usuario+token sent as headers, no refresh flow
— unlike Siprov's bearer token, this one doesn't expire). Company-wide, not
workspace-scoped — see the config.py comment next to `nuvemjti_api_usuario`.

Known data-quality quirk (confirmed live 2026-08-24): the four status
categories the operadora exposes (atendido/não_atendido/falha/ocupado) sum
to MORE than the actual number of CDR records for the same period — they
appear to overlap. `total_chamadas` in the summary below is therefore taken
from the raw CDR count (ground truth), and the four category counts are
surfaced separately, labeled as the operadora's own approximate
classification. Don't quietly "fix" this by making them add up — that would
hide a real discrepancy worth asking Nuvem JTi support about.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

import httpx

from app.core.config import get_settings

_ENDPOINT = "/listar_historico_chamada"
_STATUS_KEYS = ("atendido", "nao_atendido", "falha", "ocupado")
_DID_RE = re.compile(r"DID:\s*(\d+)")
_RAMAL_RE = re.compile(r"^amparar-\d+")
_PAGE_SIZE = 1000
_MAX_PAGES = 20  # 20 * 1000 = 20k CDRs, comfortably above any realistic window


class NuvemJtiNotConfigured(RuntimeError):
    pass


def _base_url() -> str:
    settings = get_settings()
    if not settings.nuvemjti_api_usuario or not settings.nuvemjti_api_token.get_secret_value():
        raise NuvemJtiNotConfigured(
            "Nuvem JTi API credentials are not configured "
            "(NUVEMJTI_API_USUARIO / NUVEMJTI_API_TOKEN)."
        )
    return "https://plataforma.nuvemjti.com.br/pabx/api"


def _auth_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "usuario": settings.nuvemjti_api_usuario,
        "token": settings.nuvemjti_api_token.get_secret_value(),
    }


async def _get(client: httpx.AsyncClient, params: dict[str, Any]) -> dict[str, Any]:
    resp = await client.get(
        f"{_base_url()}{_ENDPOINT}",
        headers=_auth_headers(),
        params={k: v for k, v in params.items() if v is not None},
    )
    resp.raise_for_status()
    return resp.json()


def _fmt_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


async def historico_chamadas(
    *,
    data_inicial: date,
    data_final: date,
    hora_inicial: str = "00:00",
    hora_final: str = "23:59",
    filtro_status_chamada: Optional[str] = None,
    ramal_origem: Optional[str] = None,
    ramal_destino: Optional[str] = None,
    did: Optional[str] = None,
    quantidade: int = 100,
) -> dict[str, Any]:
    """Thin wrapper around GET /listar_historico_chamada for a single page
    (used by the agent tool — the agent asks for what it needs and can
    request more with pos_registro_inicial itself if it wants to page)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _get(
            client,
            {
                "data_inicial": _fmt_br(data_inicial),
                "hora_inicial": hora_inicial,
                "data_final": _fmt_br(data_final),
                "hora_final": hora_final,
                "filtro_status_chamada": filtro_status_chamada,
                "ramal_origem": ramal_origem,
                "ramal_destino": ramal_destino,
                "did": did,
                "quantidade": min(quantidade, _PAGE_SIZE),
            },
        )


def _duracao_para_segundos(duracao_real: str) -> int:
    if not duracao_real:
        return 0
    hms = duracao_real.split(",")[0]
    parts = hms.split(":")
    if len(parts) != 3:
        return 0
    h, m, s = (int(p) for p in parts)
    return h * 3600 + m * 60 + s


async def resumo_chamadas(*, dias: int = 7) -> dict[str, Any]:
    """Aggregate call volume/duration/routing for the last `dias` days
    (today inclusive). This is the same aggregation the standalone
    monitoramento/fetch.js script does for the local dashboard — kept here
    in Python so both the Securo dashboard page and the agent tool
    (pabx_resumo_chamadas) share one implementation."""
    hoje = date.today()
    inicio = hoje - timedelta(days=dias - 1)
    data_inicial_str = _fmt_br(inicio)
    data_final_str = _fmt_br(hoje)

    async with httpx.AsyncClient(timeout=30.0) as client:
        contagens: dict[str, int] = {}
        for status in _STATUS_KEYS:
            r = await _get(
                client,
                {
                    "data_inicial": data_inicial_str,
                    "hora_inicial": "00:00",
                    "data_final": data_final_str,
                    "hora_final": "23:59",
                    "filtro_status_chamada": status,
                    "quantidade": 1,
                },
            )
            contagens[status] = r.get("qtd_total_resultados", 0) or 0

        chamadas: list[dict[str, Any]] = []
        pos = 0
        for _ in range(_MAX_PAGES):
            r = await _get(
                client,
                {
                    "data_inicial": data_inicial_str,
                    "hora_inicial": "00:00",
                    "data_final": data_final_str,
                    "hora_final": "23:59",
                    "quantidade": _PAGE_SIZE,
                    "pos_registro_inicial": pos,
                },
            )
            dados = r.get("dados") or []
            chamadas.extend(dados)
            if len(dados) < _PAGE_SIZE:
                break
            pos += _PAGE_SIZE

    por_dia: dict[str, int] = {}
    por_did: dict[str, int] = {}
    por_ramal: dict[str, int] = {}
    por_tipo_rota: dict[str, int] = {}
    soma_duracao = 0
    qtd_com_duracao = 0

    for c in chamadas:
        data_hora = c.get("data") or ""
        data_parte = data_hora.split(" ")[0] if data_hora else ""
        if data_parte and len(data_parte.split("/")) == 3:
            dd, mm, yyyy = data_parte.split("/")
            dia_iso = f"{yyyy}-{mm}-{dd}"
            por_dia[dia_iso] = por_dia.get(dia_iso, 0) + 1

        origem = c.get("origem") or ""
        m = _DID_RE.search(origem)
        if m:
            por_did[m.group(1)] = por_did.get(m.group(1), 0) + 1
        if _RAMAL_RE.match(origem):
            por_ramal[origem] = por_ramal.get(origem, 0) + 1

        rota = c.get("recursos") or "Desconhecido"
        por_tipo_rota[rota] = por_tipo_rota.get(rota, 0) + 1

        seg = _duracao_para_segundos(c.get("duracao_real") or "")
        if seg > 0:
            soma_duracao += seg
            qtd_com_duracao += 1

    por_dia_lista = []
    for i in range(dias):
        d = inicio + timedelta(days=i)
        iso = d.isoformat()
        por_dia_lista.append({"dia": iso, "total": por_dia.get(iso, 0)})

    soma_categorias = sum(contagens.values())

    return {
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "periodo": {"inicio": data_inicial_str, "fim": data_final_str, "dias": dias},
        "totais": {
            "total_chamadas": len(chamadas),
            "atendidas": contagens["atendido"],
            "nao_atendidas": contagens["nao_atendido"],
            "falhas": contagens["falha"],
            "ocupado": contagens["ocupado"],
            "soma_categorias_diverge": soma_categorias != len(chamadas),
            "duracao_media_segundos": round(soma_duracao / qtd_com_duracao) if qtd_com_duracao else 0,
        },
        "por_dia": por_dia_lista,
        "top_dids": [
            {"did": k, "total": v}
            for k, v in sorted(por_did.items(), key=lambda kv: kv[1], reverse=True)[:10]
        ],
        "top_ramais": [
            {"ramal": k, "total": v}
            for k, v in sorted(por_ramal.items(), key=lambda kv: kv[1], reverse=True)[:10]
        ],
        "por_tipo_rota": [
            {"rota": k, "total": v}
            for k, v in sorted(por_tipo_rota.items(), key=lambda kv: kv[1], reverse=True)
        ],
    }
