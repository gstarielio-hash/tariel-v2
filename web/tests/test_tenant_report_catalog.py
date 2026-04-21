from __future__ import annotations

import pytest

import app.domains.admin.services as admin_services
from app.shared.tenant_report_catalog import (
    build_admin_tenant_catalog_snapshot,
    build_catalog_selection_token,
    build_tenant_template_option_snapshot,
    resolve_tenant_template_request,
)


def test_tenant_catalog_requires_explicit_variant_for_ambiguous_runtime(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_exibicao="NR13 · Vaso de Pressao",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_oferta="NR13 Premium · Vaso de Pressao",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text=(
                "premium_campo | Premium campo | nr13_premium | Operacao critica\n"
                "premium_documental | Premium documental | nr13_documental | Prontuario reforcado"
            ),
            criado_por_id=ids["admin_a"],
        )

        tokens = [
            build_catalog_selection_token("nr13_inspecao_vaso_pressao", "premium_campo"),
            build_catalog_selection_token("nr13_inspecao_vaso_pressao", "premium_documental"),
        ]
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=tokens,
            admin_id=ids["admin_a"],
        )

        with pytest.raises(PermissionError) as exc:
            resolve_tenant_template_request(
                banco,
                empresa_id=ids["empresa_a"],
                requested_value="nr13",
            )

        assert "variante comercial" in str(exc.value)

        resolvido = resolve_tenant_template_request(
            banco,
            empresa_id=ids["empresa_a"],
            requested_value=tokens[1],
        )

        assert resolvido["governed_mode"] is True
        assert resolvido["runtime_template_code"] == "nr13"
        assert resolvido["family_key"] == "nr13_inspecao_vaso_pressao"
        assert resolvido["variant_key"] == "premium_documental"
        assert resolvido["selection_token"] == tokens[1]
        assert resolvido["compatibility_mode"] is False


def test_tenant_catalog_snapshot_exposes_variant_matrix_by_family(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_oferta="NR35 Premium · Linha de Vida",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text=(
                "premium_campo | Premium campo | nr35_linha_vida | Campo\n"
                "premium_parada | Premium parada | nr35_linha_vida | Parada programada"
            ),
            criado_por_id=ids["admin_a"],
        )

        selecionada = build_catalog_selection_token("nr35_inspecao_linha_de_vida", "premium_campo")
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[selecionada],
            admin_id=ids["admin_a"],
        )

        admin_snapshot = build_admin_tenant_catalog_snapshot(banco, empresa_id=ids["empresa_a"])
        tenant_snapshot = build_tenant_template_option_snapshot(banco, empresa_id=ids["empresa_a"])

        assert admin_snapshot["governed_mode"] is True
        assert admin_snapshot["available_variant_count"] >= 2
        assert admin_snapshot["operational_variant_count"] >= 2

        familia_nr35 = next(
            item for item in admin_snapshot["families"] if item["family_key"] == "nr35_inspecao_linha_de_vida"
        )
        variantes = {item["variant_key"]: item for item in familia_nr35["variantes"]}

        assert set(variantes) >= {"premium_campo", "premium_parada"}
        assert variantes["premium_campo"]["is_active"] is True
        assert variantes["premium_campo"]["is_operational"] is True
        assert variantes["premium_campo"]["runtime_template_code"] == "nr35_linha_vida"
        assert variantes["premium_parada"]["is_active"] is False
        assert variantes["premium_parada"]["is_operational"] is True

        assert tenant_snapshot["governed_mode"] is True
        assert tenant_snapshot["activation_count"] == 1
        assert tenant_snapshot["runtime_codes"] == ["nr35_linha_vida"]
        assert tenant_snapshot["options"][0]["selection_token"] == selecionada
        assert tenant_snapshot["options"][0]["variant_key"] == "premium_campo"


def test_tenant_catalog_governed_empty_blocks_legacy_fallback(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Premium · Caldeira",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Campo crítico",
            criado_por_id=ids["admin_a"],
        )

        token = build_catalog_selection_token("nr13_inspecao_caldeira", "premium_campo")
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            allowed_variants=[token],
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[token],
            admin_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="paused",
            allowed_variants=[token],
            criado_por_id=ids["admin_a"],
        )

        tenant_snapshot = build_tenant_template_option_snapshot(banco, empresa_id=ids["empresa_a"])

        assert tenant_snapshot["governed_mode"] is True
        assert tenant_snapshot["catalog_state"] == "managed_empty"
        assert tenant_snapshot["options"] == []
        assert tenant_snapshot["permissions"]["managed_by_admin_ceo"] is True

        with pytest.raises(PermissionError) as exc:
            resolve_tenant_template_request(
                banco,
                empresa_id=ids["empresa_a"],
                requested_value="nr13",
            )

        assert "Admin-CEO" in str(exc.value)


def test_revogar_catalogo_de_um_tenant_nao_afeta_outros_tenants(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_oferta="NR35 Premium · Linha de Vida",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr35_linha_vida | Campo crítico",
            criado_por_id=ids["admin_a"],
        )

        token = build_catalog_selection_token("nr35_inspecao_linha_de_vida", "premium_campo")
        for tenant_id in (ids["empresa_a"], ids["empresa_b"]):
            admin_services.upsert_tenant_family_release(
                banco,
                tenant_id=tenant_id,
                family_key="nr35_inspecao_linha_de_vida",
                release_status="active",
                allowed_variants=[token],
                criado_por_id=ids["admin_a"],
            )
            admin_services.sincronizar_portfolio_catalogo_empresa(
                banco,
                empresa_id=tenant_id,
                selection_tokens=[token],
                admin_id=ids["admin_a"],
            )

        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr35_inspecao_linha_de_vida",
            release_status="paused",
            allowed_variants=[token],
            criado_por_id=ids["admin_a"],
        )

        snapshot_a = build_tenant_template_option_snapshot(banco, empresa_id=ids["empresa_a"])
        snapshot_b = build_tenant_template_option_snapshot(banco, empresa_id=ids["empresa_b"])
        resolvido_b = resolve_tenant_template_request(
            banco,
            empresa_id=ids["empresa_b"],
            requested_value=token,
        )

        assert snapshot_a["governed_mode"] is True
        assert snapshot_a["catalog_state"] == "managed_empty"
        assert snapshot_a["options"] == []

        assert snapshot_b["governed_mode"] is True
        assert snapshot_b["catalog_state"] == "managed_active"
        assert snapshot_b["options"][0]["selection_token"] == token
        assert resolvido_b["selection_token"] == token
        assert resolvido_b["family_key"] == "nr35_inspecao_linha_de_vida"


def test_tenant_catalog_sintetiza_modelo_principal_para_oferta_ativa_legada(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        oferta = admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Premium · Caldeira",
            pacote_comercial="Premium",
            lifecycle_status="active",
            template_default_code="nr13_prime",
            variantes_comerciais_text="",
            criado_por_id=ids["admin_a"],
        )
        oferta.ativo_comercial = False
        oferta.variantes_json = None
        banco.flush()

        admin_snapshot = build_admin_tenant_catalog_snapshot(banco, empresa_id=ids["empresa_a"])
        familia = next(
            item for item in admin_snapshot["families"] if item["family_key"] == "nr13_inspecao_caldeira"
        )
        variantes = familia["variantes"]

        assert len(variantes) == 1
        assert variantes[0]["variant_key"] == "nr13_prime"
        assert variantes[0]["template_code"] == "nr13_prime"
        assert variantes[0]["is_operational"] is True
        assert variantes[0]["is_selectable_for_tenant"] is True

        token = build_catalog_selection_token("nr13_inspecao_caldeira", "nr13_prime")
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            allowed_variants=[token],
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[token],
            admin_id=ids["admin_a"],
        )

        resolvido = resolve_tenant_template_request(
            banco,
            empresa_id=ids["empresa_a"],
            requested_value=token,
        )

        assert resolvido["governed_mode"] is True
        assert resolvido["selection_token"] == token
        assert resolvido["family_key"] == "nr13_inspecao_caldeira"
        assert resolvido["variant_key"] == "nr13_prime"
        assert resolvido["runtime_template_code"] == "nr13"
