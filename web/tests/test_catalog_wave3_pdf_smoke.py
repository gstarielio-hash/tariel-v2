from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.shared.database import Laudo, StatusRevisao
from tests.catalog_wave3_cases import WAVE_3_FAMILIES
from tests.regras_rotas_criticas_support import _criar_laudo, _login_app_inspetor

WAVE_3_ROUTE_MATRIX: tuple[tuple[str, str], ...] = tuple((family_key, "padrao") for family_key in WAVE_3_FAMILIES)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _family_schemas_dir() -> Path:
    return _repo_root() / "docs" / "family_schemas"


def _load_fixture(name: str) -> dict:
    return json.loads((_family_schemas_dir() / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("family_key", "route_tipo_template"), WAVE_3_ROUTE_MATRIX)
def test_wave3_fixture_emits_pdf_via_catalog_runtime(
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
        laudo.catalog_variant_key = "wave3_fixture"
        laudo.catalog_variant_label = "Wave 3 fixture"
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
            "empresa": "Empresa Fixture Wave 3",
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
