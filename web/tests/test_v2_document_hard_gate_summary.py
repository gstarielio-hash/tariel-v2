from __future__ import annotations

import asyncio
import json

from starlette.requests import Request

from app.domains.admin.routes import api_document_hard_gate_summary
from app.domains.chat.laudo import api_finalizar_relatorio
from app.shared.database import Laudo, MensagemLaudo, NivelAcesso, StatusRevisao, TipoMensagem, Usuario
from app.v2.document import clear_document_hard_gate_metrics_for_tests
from tests.regras_rotas_criticas_support import _criar_laudo


def _build_finalize_request(laudo_id: int) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": f"/app/api/laudo/{laudo_id}/finalizar",
            "headers": [(b"x-csrf-token", b"csrf-hard-gate")],
            "query_string": b"",
            "session": {
                "csrf_token_inspetor": "csrf-hard-gate",
                "laudo_ativo_id": int(laudo_id),
                "estado_relatorio": "relatorio_ativo",
            },
            "state": {},
            "client": ("testclient", 50004),
        }
    )


def _build_admin_request(remote_host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/admin/api/document-hard-gate/summary",
            "headers": [],
            "query_string": b"",
            "state": {},
            "client": (remote_host, 50005),
        }
    )


def test_admin_summary_do_hard_gate_permanece_local_only_e_expoe_contadores(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()

    assert client.get("/admin/api/document-hard-gate/summary").status_code == 401

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspeção inicial do hard gate."
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Mensagem operacional com evidência mínima.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar suportado por IA.",
                ),
            ]
        )
        banco.commit()

        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", raising=False)
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize")

        asyncio.run(
            api_finalizar_relatorio(
                laudo_id=laudo_id,
                request=_build_finalize_request(laudo_id),
                usuario=usuario,
                banco=banco,
            )
        )

    resposta_remote = asyncio.run(
        api_document_hard_gate_summary(
            request=_build_admin_request("10.10.10.10"),
            usuario=Usuario(
                id=ids["admin_a"],
                empresa_id=ids["empresa_a"],
                nivel_acesso=NivelAcesso.DIRETORIA.value,
                email="admin@empresa-a.test",
            ),
        )
    )
    assert resposta_remote.status_code == 403

    resposta = asyncio.run(
        api_document_hard_gate_summary(
            request=_build_admin_request("testclient"),
            usuario=Usuario(
                id=ids["admin_a"],
                empresa_id=ids["empresa_a"],
                nivel_acesso=NivelAcesso.DIRETORIA.value,
                email="admin@empresa-a.test",
            ),
        )
    )

    assert resposta.status_code == 200
    payload = json.loads(resposta.body)
    assert payload["contract_name"] == "DocumentHardGateSummaryV1"
    assert payload["feature_flags"]["hard_gate_enabled"] is True
    assert payload["feature_flags"]["operation_allowlist"] == ["report_finalize"]
    assert payload["totals"]["evaluations"] >= 1
    assert any(
        item["operation_kind"] == "report_finalize" and item["evaluations"] >= 1
        for item in payload["by_operation_kind"]
    )
