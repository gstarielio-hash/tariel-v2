"""Helpers para tratar preferências internas de IA do app mobile.

Esse contexto pode influenciar a resposta da IA, mas nunca deve aparecer
como texto visível do caso técnico.
"""

from __future__ import annotations

import re
from typing import Iterable

PREFERENCIAS_IA_MOBILE_INICIO = "[preferencias_ia_mobile]"
PREFERENCIAS_IA_MOBILE_FIM = "[/preferencias_ia_mobile]"
_PREFERENCIAS_IA_MOBILE_RE = re.compile(
    r"\[preferencias_ia_mobile\][\s\S]*?\[/preferencias_ia_mobile\]",
    flags=re.IGNORECASE,
)


def _normalizar_espacos_visiveis(texto: str) -> str:
    texto_limpo = str(texto or "").replace("\r\n", "\n").replace("\r", "\n")
    texto_limpo = re.sub(r"[ \t]+\n", "\n", texto_limpo)
    texto_limpo = re.sub(r"\n{3,}", "\n\n", texto_limpo)
    texto_limpo = re.sub(r"[ \t]{2,}", " ", texto_limpo)
    return texto_limpo.strip()


def extrair_preferencias_ia_mobile_embutidas(texto: str) -> tuple[str, str]:
    bruto = str(texto or "")
    blocos: list[str] = []

    def _substituir(match: re.Match[str]) -> str:
        bloco = str(match.group(0) or "").strip()
        if bloco:
            blocos.append(bloco)
        return " "

    texto_limpo = _normalizar_espacos_visiveis(
        _PREFERENCIAS_IA_MOBILE_RE.sub(_substituir, bruto)
    )
    preferencias = "\n\n".join(blocos).strip()
    return texto_limpo, preferencias


def limpar_texto_visivel_chat(
    texto: str,
    *,
    fallback_hidden_only: str = "",
) -> str:
    texto_limpo, preferencias_embutidas = extrair_preferencias_ia_mobile_embutidas(texto)
    if texto_limpo:
        return texto_limpo
    if preferencias_embutidas and str(fallback_hidden_only or "").strip():
        return str(fallback_hidden_only).strip()
    return texto_limpo


def normalizar_preferencias_ia_mobile_contexto(valor: str | None) -> str:
    contexto = str(valor or "").strip()
    if not contexto:
        return ""
    if (
        PREFERENCIAS_IA_MOBILE_INICIO.lower() in contexto.lower()
        and PREFERENCIAS_IA_MOBILE_FIM.lower() in contexto.lower()
    ):
        _texto_descartado, preferencias_embutidas = extrair_preferencias_ia_mobile_embutidas(
            contexto
        )
        return preferencias_embutidas or contexto
    return contexto


def combinar_preferencias_ia_mobile_contexto(*partes: str | None) -> str:
    vistos: set[str] = set()
    blocos: list[str] = []

    for parte in partes:
        contexto = normalizar_preferencias_ia_mobile_contexto(parte)
        if not contexto:
            continue
        chave = contexto.casefold()
        if chave in vistos:
            continue
        vistos.add(chave)
        blocos.append(contexto)

    return "\n\n".join(blocos).strip()


def anexar_preferencias_ia_mobile_na_mensagem(
    mensagem: str,
    *,
    preferencias_ia_mobile: str = "",
) -> str:
    mensagem_limpa = str(mensagem or "").strip()
    contexto = normalizar_preferencias_ia_mobile_contexto(preferencias_ia_mobile)
    if not contexto:
        return mensagem_limpa
    if not mensagem_limpa:
        return contexto
    return f"{contexto}\n\n{mensagem_limpa}"


def limpar_historico_visivel_chat(
    historico: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    itens: list[dict[str, object]] = []
    for item in historico:
        texto = limpar_texto_visivel_chat(
            str(item.get("texto") or ""),
            fallback_hidden_only=(
                "Evidência enviada"
                if str(item.get("papel") or "").strip().lower() == "usuario"
                else ""
            ),
        )
        if not texto:
            continue
        proximo = dict(item)
        proximo["texto"] = texto
        itens.append(proximo)
    return itens


__all__ = [
    "anexar_preferencias_ia_mobile_na_mensagem",
    "combinar_preferencias_ia_mobile_contexto",
    "extrair_preferencias_ia_mobile_embutidas",
    "limpar_historico_visivel_chat",
    "limpar_texto_visivel_chat",
    "normalizar_preferencias_ia_mobile_contexto",
]
