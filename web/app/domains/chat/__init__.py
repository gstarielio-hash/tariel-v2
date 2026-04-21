"""Domínio Chat/Inspetor.

`router.py` monta o roteador principal com os submódulos:
`auth`, `laudo`, `chat`, `mesa` e `pendencias`.
`routes.py` é apenas uma camada de compatibilidade legada
(exports mínimos para testes e integrações antigas).

Este pacote usa exports lazily loaded para evitar ciclos de import quando
submódulos utilitários, como `normalization`, são importados cedo no boot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "roteador_inspetor",
    "auth",
    "laudo",
    "chat",
    "mesa",
    "pendencias",
]

if TYPE_CHECKING:
    from app.domains.chat.router import (
        auth,
        chat,
        laudo,
        mesa,
        pendencias,
        roteador_inspetor,
    )


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from app.domains.chat.router import (
        auth,
        chat,
        laudo,
        mesa,
        pendencias,
        roteador_inspetor,
    )

    exports = {
        "roteador_inspetor": roteador_inspetor,
        "auth": auth,
        "laudo": laudo,
        "chat": chat,
        "mesa": mesa,
        "pendencias": pendencias,
    }
    return exports[name]
