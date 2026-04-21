from __future__ import annotations

from types import SimpleNamespace

from app.domains.chat.catalog_document_contract import (
    build_document_contract_payload,
    build_document_control_payload,
    build_document_delivery_package_payload,
    build_runtime_brand_assets,
    build_tenant_branding_payload,
    resolve_master_template_id_for_family,
)
from app.domains.chat.catalog_pdf_templates import (
    ResolvedPdfTemplateRef,
    materialize_runtime_document_editor_json,
)
from nucleo.template_editor_word import MODO_EDITOR_RICO


def test_resolve_master_template_id_for_representative_families() -> None:
    assert resolve_master_template_id_for_family("nr35_inspecao_linha_de_vida") == "inspection_conformity"
    assert resolve_master_template_id_for_family("nr12_apreciacao_risco_maquina") == "risk_analysis"
    assert resolve_master_template_id_for_family("nr13_inspecao_vaso_pressao") == "integrity_specialized"
    assert resolve_master_template_id_for_family("nr33_permissao_entrada_trabalho") == "controlled_permit"
    assert resolve_master_template_id_for_family("nr10_prontuario_instalacoes_eletricas") == "technical_dossier"
    assert resolve_master_template_id_for_family("nr01_gro_pgr") == "program_plan"


def test_build_tenant_branding_payload_accepts_overrides_and_company_defaults() -> None:
    empresa = SimpleNamespace(
        nome_fantasia="Cliente Base",
        cnpj="12.345.678/0001-90",
        cidade_estado="Curitiba/PR",
        nome_responsavel="Maria Cliente",
        observacoes=None,
    )
    payload = build_tenant_branding_payload(
        empresa_entity=empresa,
        empresa_nome="Cliente Base",
        source_payload={
            "tenant_branding": {
                "legal_name": "Cliente Base S/A",
                "confidentiality_notice": "Documento confidencial do cliente.",
                "logo_asset": {
                    "path": "/tmp/logo_cliente.png",
                    "mime_type": "image/png",
                },
            }
        },
    )

    assert payload["display_name"] == "Cliente Base"
    assert payload["legal_name"] == "Cliente Base S/A"
    assert payload["cnpj"] == "12.345.678/0001-90"
    assert payload["location_label"] == "Curitiba/PR"
    assert payload["contact_name"] == "Maria Cliente"
    assert payload["confidentiality_notice"] == "Documento confidencial do cliente."
    assert payload["logo_asset"]["id"] == "tenant_logo"


def test_build_document_contract_and_control_payloads_expose_master_model() -> None:
    contract = build_document_contract_payload(
        family_key="nr33_permissao_entrada_trabalho",
        family_label="NR33 · Permissao de Entrada e Trabalho",
        template_code="nr33_permissao_entrada_trabalho",
    )
    control = build_document_control_payload(
        family_key="nr33_permissao_entrada_trabalho",
        family_label="NR33 · Permissao de Entrada e Trabalho",
        template_code="nr33_permissao_entrada_trabalho",
        version=3,
        laudo=SimpleNamespace(id=77),
        source_payload={"document_control": {"document_code": "PET-NR33-00077"}},
        issue_date="09/04/2026",
        master_template_id=contract["id"],
        master_template_label=contract["label"],
    )

    assert contract["id"] == "controlled_permit"
    assert "riscos_e_controles" in contract["section_order"]
    assert control["document_code"] == "PET-NR33-00077"
    assert control["revision"] == "v3"
    assert control["master_template_id"] == "controlled_permit"

    delivery = build_document_delivery_package_payload(
        document_contract=contract,
        document_control=control,
        render_mode="client_pdf_filled",
    )

    assert delivery["package_kind"] == "tariel_pdf_delivery_bundle"
    assert delivery["delivery_path"] == "document_view_model_to_editor_to_render"
    assert delivery["public_payload_mode"] == "human_validated_pdf"
    assert "pdf_final" in delivery["artifacts"]


def test_build_runtime_brand_assets_replaces_existing_logo_slot() -> None:
    assets = build_runtime_brand_assets(
        template_assets_json=[
            {
                "id": "tenant_logo",
                "path": "/tmp/old_logo.png",
                "mime_type": "image/png",
                "filename": "old.png",
            }
        ],
        payload={
            "tenant_branding": {
                "logo_asset": {
                    "id": "tenant_logo",
                    "path": "/tmp/new_logo.png",
                    "mime_type": "image/png",
                    "filename": "new.png",
                }
            }
        },
    )

    assert len(assets) == 1
    assert assets[0]["path"] == "/tmp/new_logo.png"


def test_materialize_runtime_document_editor_json_injeta_bloco_visual_do_cliente() -> None:
    template_ref = ResolvedPdfTemplateRef(
        source_kind="catalog_canonical_seed",
        family_key="nr35_inspecao_linha_de_vida",
        template_id=None,
        codigo_template="nr35_inspecao_linha_de_vida",
        versao=1,
        modo_editor=MODO_EDITOR_RICO,
        arquivo_pdf_base="",
        documento_editor_json={
            "version": 1,
            "doc": {
                "type": "doc",
                "content": [
                    {
                        "type": "heading",
                        "attrs": {"level": 1},
                        "content": [{"type": "text", "text": "Titulo do documento"}],
                    }
                ],
            },
        },
        estilo_json={},
        assets_json=[],
    )

    document = materialize_runtime_document_editor_json(
        template_ref=template_ref,
        payload={
            "tenant_branding": {
                "display_name": "Cliente XPTO",
                "cnpj": "12.345.678/0001-90",
                "confidentiality_notice": "Uso restrito.",
                "logo_asset_id": "tenant_logo",
            }
        },
    )

    content = document["doc"]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["attrs"]["asset_id"] == "tenant_logo"
    assert content[1]["type"] == "paragraph"
    assert "Cliente XPTO" in str(content[1]["content"])
    assert content[2]["type"] == "horizontalRule"
