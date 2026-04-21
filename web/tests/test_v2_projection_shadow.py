from __future__ import annotations

import asyncio
import uuid

from starlette.requests import Request

from app.domains.chat.laudo_service import obter_status_relatorio_resposta
from app.shared.database import Laudo, StatusRevisao, Usuario


def _build_request(session_data: dict[str, object] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/laudo/status",
            "headers": [],
            "query_string": b"",
            "session": session_data or {},
            "state": {},
        }
    )


def test_shadow_mode_do_status_relatorio_nao_altera_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        monkeypatch.delenv("TARIEL_V2_ENVELOPES", raising=False)
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        payload_base, status_base = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_request({"estado_relatorio": "sem_relatorio"}),
                usuario=usuario,
                banco=banco,
            )
        )

        monkeypatch.setenv("TARIEL_V2_ENVELOPES", "1")
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        payload_shadow, status_shadow = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_request({"estado_relatorio": "sem_relatorio"}),
                usuario=usuario,
                banco=banco,
            )
        )

    assert status_base == 200
    assert status_shadow == 200
    assert payload_shadow == payload_base


def test_acl_do_case_core_no_status_relatorio_mantem_payload_e_expoe_snapshot(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_ENVELOPES", raising=False)
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        payload_base, status_base = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_acl = _build_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_ENVELOPES", "1")
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        payload_acl, status_acl = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_acl,
                usuario=usuario,
                banco=banco,
            )
        )

    assert status_base == 200
    assert status_acl == 200
    assert payload_acl == payload_base
    assert request_acl.state.v2_case_core_snapshot["case_ref"]["case_id"] == (
        f"case:legacy-laudo:{usuario.empresa_id}:{laudo.id}"
    )
    assert request_acl.state.v2_shadow_projection_result["projection"]["payload"]["state"] == "needs_reviewer"
