from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domains.chat.catalog_pdf_templates import ResolvedPdfTemplateRef, build_catalog_pdf_payload
from app.shared.database import StatusRevisao
from nucleo.template_editor_word import MODO_EDITOR_RICO

WAVE_1_FAMILIES: tuple[str, ...] = (
    "nr10_implantacao_loto",
    "nr10_inspecao_instalacoes_eletricas",
    "nr10_inspecao_spda",
    "nr10_prontuario_instalacoes_eletricas",
    "nr12_apreciacao_risco_maquina",
    "nr12_inspecao_maquina_equipamento",
    "nr13_inspecao_caldeira",
    "nr13_inspecao_vaso_pressao",
    "nr20_inspecao_instalacoes_inflamaveis",
    "nr20_prontuario_instalacoes_inflamaveis",
    "nr33_avaliacao_espaco_confinado",
    "nr33_permissao_entrada_trabalho",
    "nr35_inspecao_linha_de_vida",
    "nr35_inspecao_ponto_ancoragem",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _family_schemas_dir() -> Path:
    return _repo_root() / "docs" / "family_schemas"


def _load_fixture(name: str) -> dict:
    return json.loads((_family_schemas_dir() / name).read_text(encoding="utf-8"))


def _template_ref(*, family_key: str, template_code: str, version: int) -> ResolvedPdfTemplateRef:
    return ResolvedPdfTemplateRef(
        source_kind="catalog_canonical_seed",
        family_key=family_key,
        template_id=None,
        codigo_template=template_code,
        versao=version,
        modo_editor=MODO_EDITOR_RICO,
        arquivo_pdf_base="",
        documento_editor_json={},
        estilo_json={},
        assets_json=[],
    )


def _iter_leaf_values(payload: dict, prefix: str = ""):
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            yield from _iter_leaf_values(value, path)
            continue
        yield path, value


def _value_by_path(payload: dict, path: str):
    current = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            raise AssertionError(f"path inesperado sem dict intermediario: {path}")
        current = current[segment]
    return current


@pytest.mark.parametrize("family_key", WAVE_1_FAMILIES)
def test_wave1_family_artifacts_exist_and_are_coherent(family_key: str) -> None:
    schema = _load_fixture(f"{family_key}.json")
    output_seed = _load_fixture(f"{family_key}.laudo_output_seed.json")
    output_example = _load_fixture(f"{family_key}.laudo_output_exemplo.json")
    template_seed = _load_fixture(f"{family_key}.template_master_seed.json")

    assert schema["family_key"] == family_key
    assert output_seed["family_key"] == family_key
    assert output_example["family_key"] == family_key
    assert template_seed["family_key"] == family_key
    assert output_seed["template_code"] == template_seed["template_code"]
    assert output_example["template_code"] == template_seed["template_code"]
    assert output_seed["schema_type"] == "laudo_output"
    assert output_example["schema_type"] == "laudo_output"


@pytest.mark.parametrize("family_key", WAVE_1_FAMILIES)
def test_wave1_build_catalog_pdf_payload_preserva_fixture_canonico(family_key: str) -> None:
    output_example = _load_fixture(f"{family_key}.laudo_output_exemplo.json")
    template_seed = _load_fixture(f"{family_key}.template_master_seed.json")

    laudo = SimpleNamespace(
        id=999,
        catalog_family_key=family_key,
        catalog_family_label=family_key.replace("_", " "),
        catalog_variant_label="fixture_wave_1",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="fixture",
        parecer_ia="Fixture canonico da onda 1",
        primeira_mensagem=f"Fixture {family_key}",
        motivo_rejeicao=None,
        dados_formulario=output_example,
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key=family_key,
            template_code=str(template_seed["template_code"]),
            version=int(template_seed.get("versao") or template_seed.get("schema_version") or 1),
        ),
        source_payload=output_example,
        diagnostico="Fixture wave 1",
        inspetor="Gabriel Santos",
        empresa="Empresa Fixture",
        data="09/04/2026",
    )

    assert payload["schema_type"] == "laudo_output"
    assert payload["family_key"] == family_key
    assert payload["template_code"] == output_example["template_code"]

    for path, expected in _iter_leaf_values(output_example):
        assert _value_by_path(payload, path) == expected, path
