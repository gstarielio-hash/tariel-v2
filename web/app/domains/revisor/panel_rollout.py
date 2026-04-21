from __future__ import annotations

import os
from fastapi import Request

PRIMARY_SURFACE_ENV = "TARIEL_REVIEW_DESK_PRIMARY_SURFACE"
CANONICAL_UI_ENV = "REVIEW_UI_CANONICAL"
SURFACE_QUERY_PARAM = "surface"

_SSR_SURFACE_VALUES = {"ssr", "legacy"}


def _normalize_surface(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in _SSR_SURFACE_VALUES:
        return "ssr"
    return None


def _platform_setting_override_value(key: str) -> str | None:
    try:
        from app.shared.database import ConfiguracaoPlataforma, SessaoLocal

        with SessaoLocal() as banco:
            configuracao = banco.get(ConfiguracaoPlataforma, key)
            if configuracao is None:
                return None
            normalized = str(configuracao.valor_json or "").strip().lower()
            return normalized or None
    except Exception:
        return None


def get_review_panel_primary_surface() -> str:
    # Superfície oficial fixa no SSR legado.
    # Qualquer configuração fora de SSR é ignorada para evitar nova bifurcação de UI.
    _ = _normalize_surface(_platform_setting_override_value("review_ui_canonical"))
    _ = _normalize_surface(os.getenv(CANONICAL_UI_ENV))
    _ = _normalize_surface(os.getenv(PRIMARY_SURFACE_ENV))
    return "ssr"


def get_review_panel_next_base_url() -> str | None:
    # Mantido apenas por compatibilidade de import/chamadas indiretas.
    return None


def resolve_review_panel_surface(request: Request) -> str:
    _ = _normalize_surface(request.query_params.get(SURFACE_QUERY_PARAM))
    return "ssr"


def is_review_panel_explicit_ssr_fallback(request: Request) -> bool:
    return _normalize_surface(request.query_params.get(SURFACE_QUERY_PARAM)) == "ssr"


def resolve_review_panel_redirect_url(request: Request) -> str | None:
    _ = resolve_review_panel_surface(request)
    return None


__all__ = [
    "CANONICAL_UI_ENV",
    "PRIMARY_SURFACE_ENV",
    "SURFACE_QUERY_PARAM",
    "get_review_panel_next_base_url",
    "get_review_panel_primary_surface",
    "is_review_panel_explicit_ssr_fallback",
    "resolve_review_panel_surface",
    "resolve_review_panel_redirect_url",
]
