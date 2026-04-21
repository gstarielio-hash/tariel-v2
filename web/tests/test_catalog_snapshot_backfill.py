from __future__ import annotations

import uuid

import app.domains.admin.services as admin_services
from app.domains.chat.catalog_snapshot_backfill import backfill_laudo_catalog_snapshots
from app.shared.database import Laudo, StatusRevisao
from tests.regras_rotas_criticas_support import _login_app_inspetor


def _publicar_familia_governada(SessionLocal, *, admin_id: int, empresa_id: int) -> str:
    selection_token = "catalog:nr13_inspecao_caldeira:premium_campo"
    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=admin_id,
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Premium · Caldeira",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Campo crítico",
            criado_por_id=admin_id,
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=empresa_id,
            selection_tokens=[selection_token],
            admin_id=admin_id,
        )
        banco.commit()
    return selection_token


def test_backfill_congela_snapshot_antigo_com_metadado_explicito(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    selection_token = _publicar_familia_governada(
        SessionLocal,
        admin_id=ids["admin_a"],
        empresa_id=ids["empresa_a"],
    )

    with SessionLocal() as banco:
        laudo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="geral",
            tipo_template=selection_token,
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            catalog_selection_token=selection_token,
            catalog_family_key="nr13_inspecao_caldeira",
            catalog_family_label="NR13 · Caldeira",
            catalog_variant_key="premium_campo",
            catalog_variant_label="Premium campo",
        )
        banco.add(laudo)
        banco.commit()
        banco.refresh(laudo)
        laudo_id = int(laudo.id)

        summary = backfill_laudo_catalog_snapshots(
            banco,
            empresa_id=ids["empresa_a"],
            capture_actor="pytest:test_backfill_congela_snapshot_antigo_com_metadado_explicito",
        )
        banco.commit()
        banco.refresh(laudo)

        assert summary["eligible"] == 1
        assert summary["updated"] == 1
        assert summary["updated_ids"] == [laudo_id]
        assert isinstance(laudo.catalog_snapshot_json, dict)
        assert isinstance(laudo.pdf_template_snapshot_json, dict)
        assert laudo.catalog_snapshot_json["capture_reason"] == "backfill_current_state"
        assert laudo.catalog_snapshot_json["backfill"] is True
        assert laudo.catalog_snapshot_json["selection_token"] == selection_token
        assert laudo.pdf_template_snapshot_json["capture_reason"] == "backfill_current_state"
        assert laudo.pdf_template_snapshot_json["backfill"] is True
        assert laudo.pdf_template_snapshot_json["capture_actor"] == (
            "pytest:test_backfill_congela_snapshot_antigo_com_metadado_explicito"
        )


def test_backfill_dry_run_nao_persiste_e_ignora_laudo_sem_catalogo(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    selection_token = _publicar_familia_governada(
        SessionLocal,
        admin_id=ids["admin_a"],
        empresa_id=ids["empresa_a"],
    )

    with SessionLocal() as banco:
        laudo_catalogado = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="geral",
            tipo_template=selection_token,
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            catalog_selection_token=selection_token,
        )
        laudo_sem_catalogo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="geral",
            tipo_template="padrao",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
        )
        banco.add_all([laudo_catalogado, laudo_sem_catalogo])
        banco.commit()
        banco.refresh(laudo_catalogado)
        banco.refresh(laudo_sem_catalogo)

        summary = backfill_laudo_catalog_snapshots(
            banco,
            empresa_id=ids["empresa_a"],
            dry_run=True,
        )
        banco.rollback()

        assert summary["dry_run"] is True
        assert summary["eligible"] == 1
        assert summary["updated"] == 0
        assert summary["eligible_ids"] == [int(laudo_catalogado.id)]
        assert summary["skipped_without_catalog_identity"] == 1

    with SessionLocal() as banco:
        laudo_catalogado = banco.get(Laudo, int(laudo_catalogado.id))
        assert laudo_catalogado is not None
        assert laudo_catalogado.catalog_snapshot_json is None
        assert laudo_catalogado.pdf_template_snapshot_json is None
        assert laudo_catalogado.catalog_family_key is None


def test_backfill_preserva_emissao_pdf_mesmo_apos_revogacao_do_catalogo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    selection_token = _publicar_familia_governada(
        SessionLocal,
        admin_id=ids["admin_a"],
        empresa_id=ids["empresa_a"],
    )

    with SessionLocal() as banco:
        laudo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="geral",
            tipo_template=selection_token,
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            primeira_mensagem="Laudo antigo sem snapshot",
            parecer_ia="Backfill deve manter a emissao apos a revogacao.",
            dados_formulario={"resumo_executivo": "Snapshot retroativo auditavel."},
            catalog_selection_token=selection_token,
            catalog_family_key="nr13_inspecao_caldeira",
            catalog_family_label="NR13 · Caldeira",
            catalog_variant_key="premium_campo",
            catalog_variant_label="Premium campo",
        )
        banco.add(laudo)
        banco.commit()
        banco.refresh(laudo)
        laudo_id = int(laudo.id)

        summary = backfill_laudo_catalog_snapshots(banco, laudo_ids=[laudo_id])
        assert summary["updated"] == 1
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[],
            admin_id=ids["admin_a"],
        )
        banco.commit()

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_pdf = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Emissao retroativa com snapshot",
            "inspetor": "Gabriel Santos",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "12/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr13",
        },
    )

    assert resposta_pdf.status_code == 200
    assert "application/pdf" in (resposta_pdf.headers.get("content-type", "").lower())
    assert resposta_pdf.content.startswith(b"%PDF")
