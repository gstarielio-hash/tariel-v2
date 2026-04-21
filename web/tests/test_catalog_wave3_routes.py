from __future__ import annotations

from copy import deepcopy

import pytest

from app.shared.database import Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from tests.catalog_wave3_cases import WAVE_3_CASES
from tests.regras_rotas_criticas_support import _criar_laudo, _login_app_inspetor


@pytest.mark.parametrize("case", WAVE_3_CASES, ids=[case["family_key"] for case in WAVE_3_CASES])
def test_api_gerar_pdf_materializa_wave3_catalogado(ambiente_critico, case: dict) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = case["family_key"]
        laudo.catalog_family_label = case["family_label"]
        laudo.catalog_variant_key = f"wave3_{case['family_key']}"
        laudo.catalog_variant_label = "Wave 3 runtime"
        laudo.setor_industrial = case["macro_categoria"]
        laudo.primeira_mensagem = case["first_message"][:80]
        laudo.parecer_ia = case["parecer_ia"]
        laudo.dados_formulario = deepcopy(case["source_payload"])
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": case["diagnostico"],
            "inspetor": "Gabriel Santos",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert f"{case['family_key']}_v1" in str(resposta.headers.get("content-disposition", "")).lower()


@pytest.mark.parametrize("case", WAVE_3_CASES, ids=[case["family_key"] for case in WAVE_3_CASES])
def test_inspetor_finalizacao_catalogada_persiste_wave3_canonico(ambiente_critico, case: dict) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = case["family_key"]
        laudo.catalog_family_label = case["family_label"]
        laudo.catalog_variant_key = f"wave3_{case['family_key']}"
        laudo.catalog_variant_label = "Wave 3 runtime"
        laudo.setor_industrial = case["macro_categoria"]
        laudo.primeira_mensagem = case["first_message"][:80]
        laudo.parecer_ia = case["parecer_ia"]
        laudo.dados_formulario = deepcopy(case["source_payload"])
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo=case["first_message"],
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo=case["attention_description"],
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
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo=case["parecer_ia"],
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == case["family_key"]
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == case["object_title"]
        assert laudo.dados_formulario["escopo_servico"]["tipo_entrega"] == case["expected_delivery_type"]
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == case["expected_execution_mode"]
        assert case["expected_doc_marker"] in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert case["expected_param_marker"] in str(laudo.dados_formulario["execucao_servico"]["parametros_relevantes"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is case["expected_attention"]
        assert laudo.dados_formulario["conclusao"]["status"] == case["expected_status"]
