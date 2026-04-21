from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.shared.database import Laudo, StatusRevisao
from tests.regras_rotas_criticas_support import _criar_laudo, _login_app_inspetor

WAVE_1_ROUTE_MATRIX: tuple[tuple[str, str], ...] = (
    ("nr10_implantacao_loto", "nr10"),
    ("nr10_inspecao_instalacoes_eletricas", "nr10"),
    ("nr10_inspecao_spda", "nr10"),
    ("nr10_prontuario_instalacoes_eletricas", "nr10"),
    ("nr12_apreciacao_risco_maquina", "nr12maquinas"),
    ("nr12_inspecao_maquina_equipamento", "nr12maquinas"),
    ("nr13_inspecao_caldeira", "nr13"),
    ("nr13_inspecao_vaso_pressao", "nr13"),
    ("nr20_inspecao_instalacoes_inflamaveis", "nr20"),
    ("nr20_prontuario_instalacoes_inflamaveis", "nr20"),
    ("nr33_avaliacao_espaco_confinado", "nr33"),
    ("nr33_permissao_entrada_trabalho", "nr33"),
    ("nr35_inspecao_linha_de_vida", "nr35"),
    ("nr35_inspecao_ponto_ancoragem", "nr35"),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _family_schemas_dir() -> Path:
    return _repo_root() / "docs" / "family_schemas"


def _load_fixture(name: str) -> dict:
    return json.loads((_family_schemas_dir() / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("family_key", "route_tipo_template"), WAVE_1_ROUTE_MATRIX)
def test_wave1_fixture_emits_pdf_via_catalog_runtime(
    ambiente_critico,
    family_key: str,
    route_tipo_template: str,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    schema = _load_fixture(f"{family_key}.json")
    output_example = _load_fixture(f"{family_key}.laudo_output_exemplo.json")
    template_seed = _load_fixture(f"{family_key}.template_master_seed.json")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template=route_tipo_template,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = family_key
        laudo.catalog_family_label = str(schema.get("nome_exibicao") or family_key)
        laudo.catalog_variant_key = "wave1_fixture"
        laudo.catalog_variant_label = "Wave 1 fixture"
        laudo.setor_industrial = str(schema.get("macro_categoria") or "geral")
        laudo.primeira_mensagem = str(output_example.get("resumo_executivo") or family_key)[:80]
        laudo.parecer_ia = str(output_example.get("resumo_executivo") or "")
        laudo.dados_formulario = deepcopy(output_example)
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": str(output_example.get("resumo_executivo") or f"Smoke {family_key}"),
            "inspetor": "Gabriel Santos",
            "empresa": "Empresa Fixture Wave 1",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": route_tipo_template,
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert (
        f"{template_seed['template_code']}_v{int(template_seed.get('versao') or template_seed.get('schema_version') or 1)}"
        in str(resposta.headers.get("content-disposition", "")).lower()
    )
