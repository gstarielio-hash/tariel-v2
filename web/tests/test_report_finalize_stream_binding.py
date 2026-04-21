from __future__ import annotations

import app.domains.chat.report_finalize_stream_shadow as finalize_stream_shadow

from app.shared.database import Laudo, StatusRevisao
from app.shared.tenant_report_catalog import build_catalog_selection_token
from tests.regras_rotas_criticas_support import _criar_laudo, _login_app_inspetor


def test_chat_stream_finalizacao_preserva_binding_governado_do_caso(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    selection_token = build_catalog_selection_token(
        "nr13_inspecao_caldeira",
        "premium_campo",
    )

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr13",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_selection_token = selection_token
        laudo.catalog_family_key = "nr13_inspecao_caldeira"
        laudo.catalog_family_label = "NR13 · Caldeira"
        laudo.catalog_variant_key = "premium_campo"
        laudo.catalog_variant_label = "Premium campo"
        laudo.primeira_mensagem = "Inspecao inicial em caldeira flamotubular CR-08."
        laudo.parecer_ia = "Foi observada deformacao leve no isolamento termico, sem vazamento aparente."
        laudo.report_pack_draft_json = {"quality_gates": {"missing_evidence": []}}
        laudo.reaberto_em = laudo.criado_em
        laudo.motivo_rejeicao = "Complementar isolamento termico."
        banco.commit()

    class ClienteIAStub:
        async def gerar_json_estruturado(self, **kwargs):  # noqa: ANN003
            return {
                "local_inspecao": "Casa de caldeiras - linha A",
                "nome_equipamento": "Caldeira flamotubular CR-08",
                "conclusao": {
                    "status": "conforme_com_restricoes",
                    "justificativa": "Equipamento apto mediante recomposicao do isolamento termico.",
                },
            }

    monkeypatch.setattr(
        finalize_stream_shadow,
        "obter_cliente_ia_ativo",
        lambda: ClienteIAStub(),
    )
    monkeypatch.setattr(
        finalize_stream_shadow,
        "garantir_gate_qualidade_laudo",
        lambda *args, **kwargs: None,
    )

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO padrao",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    assert "text/event-stream" in (resposta.headers.get("content-type", "").lower())

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert laudo.tipo_template == "nr13"
        assert laudo.catalog_selection_token == selection_token
        assert laudo.reaberto_em is None
        assert laudo.motivo_rejeicao is None
        assert laudo.encerrado_pelo_inspetor_em is not None
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr13_inspecao_caldeira"
