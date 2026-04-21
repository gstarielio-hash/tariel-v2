from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.domains.chat.catalog_pdf_templates import ResolvedPdfTemplateRef, build_catalog_pdf_payload
from app.shared.database import StatusRevisao
from nucleo.template_editor_word import MODO_EDITOR_RICO
from tests.catalog_wave3_cases import WAVE_3_CASES


@pytest.mark.parametrize("case", WAVE_3_CASES, ids=[case["family_key"] for case in WAVE_3_CASES])
def test_build_catalog_pdf_payload_materializa_wave3_family(case: dict) -> None:
    source_payload = deepcopy(case["source_payload"])
    laudo = SimpleNamespace(
        id=999,
        catalog_family_key=case["family_key"],
        catalog_family_label=case["family_label"],
        catalog_variant_label="wave_3_runtime",
        status_revisao=StatusRevisao.RASCUNHO.value,
        setor_industrial=case["macro_categoria"],
        parecer_ia=case["parecer_ia"],
        primeira_mensagem=case["first_message"],
        motivo_rejeicao=None,
        dados_formulario=source_payload,
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=ResolvedPdfTemplateRef(
            source_kind="catalog_canonical_seed",
            family_key=case["family_key"],
            template_id=None,
            codigo_template=case["family_key"],
            versao=1,
            modo_editor=MODO_EDITOR_RICO,
            arquivo_pdf_base="",
            documento_editor_json={},
            estilo_json={},
            assets_json=[],
        ),
        source_payload=source_payload,
        diagnostico=case["diagnostico"],
        inspetor="Gabriel Santos",
        empresa="Empresa Fixture Wave 3",
        data="09/04/2026",
    )

    assert payload["family_key"] == case["family_key"]
    assert payload["identificacao"]["objeto_principal"] == case["object_title"]
    assert payload["escopo_servico"]["tipo_entrega"] == case["expected_delivery_type"]
    assert payload["escopo_servico"]["modo_execucao"] == case["expected_execution_mode"]
    assert case["expected_doc_marker"] in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert case["expected_param_marker"] in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is case["expected_attention"]
    assert payload["conclusao"]["status"] == case["expected_status"]
