from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.paths import WEB_ROOT
from app.shared.database import (
    AnexoMesa,
    ApprovedCaseSnapshot,
    EmissaoOficialLaudo,
    Laudo,
    MensagemLaudo,
    SignatarioGovernadoLaudo,
    StatusLaudo,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from app.shared.official_issue_package import build_official_issue_package
from app.shared.official_issue_transaction import emitir_oficialmente_transacional
from tests.regras_rotas_criticas_support import _pdf_base_bytes_teste


def test_build_official_issue_package_resume_anexos_e_signatarios(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR13",
            tipo_template="nr13",
            catalog_family_key="nr13_inspecao_caldeira",
            status_revisao=StatusRevisao.APROVADO.value,
            status_conformidade=StatusLaudo.CONFORME.value,
            codigo_hash=uuid.uuid4().hex,
            nome_arquivo_pdf="laudo_nr13.pdf",
            report_pack_draft_json={
                "quality_gates": {
                    "missing_evidence": [],
                }
            },
        )
        banco.add(laudo)
        banco.flush()

        mensagem = MensagemLaudo(
            laudo_id=int(laudo.id),
            remetente_id=ids["revisor_a"],
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="Documento complementar anexado",
        )
        banco.add(mensagem)
        banco.flush()

        banco.add(
            AnexoMesa(
                laudo_id=int(laudo.id),
                mensagem_id=int(mensagem.id),
                enviado_por_id=ids["revisor_a"],
                nome_original="art.pdf",
                nome_arquivo="art.pdf",
                mime_type="application/pdf",
                categoria="documento",
                tamanho_bytes=128,
                caminho_arquivo="/tmp/art.pdf",
            )
        )
        banco.add(
            SignatarioGovernadoLaudo(
                tenant_id=ids["empresa_a"],
                nome="Eng. Tariel",
                funcao="Responsável técnico",
                registro_profissional="CREA 1234",
                valid_until=datetime.now(timezone.utc) + timedelta(days=120),
                allowed_family_keys_json=["nr13_inspecao_caldeira"],
                ativo=True,
                criado_por_id=ids["admin_a"],
            )
        )
        banco.commit()

        anexo_pack, emissao_oficial = build_official_issue_package(
            banco,
            laudo=laudo,
        )

    assert anexo_pack["ready_for_issue"] is True
    assert anexo_pack["document_count"] >= 2
    assert emissao_oficial["ready_for_issue"] is True
    assert emissao_oficial["issue_status"] == "ready_for_issue"
    assert emissao_oficial["case_status"] == "approved"
    assert emissao_oficial["active_owner_role"] == "none"
    assert str(emissao_oficial["status_visual_label"]).endswith("Responsavel: conclusao")
    assert emissao_oficial["eligible_signatory_count"] == 1
    assert emissao_oficial["signature_status"] == "ready"
    assert anexo_pack["delivery_manifest"]["bundle_kind"] == "tariel_pdf_delivery_bundle"
    assert anexo_pack["delivery_manifest"]["ready_for_issue"] is True
    assert "documentos/laudo_nr13.pdf" in anexo_pack["delivery_manifest"]["present_archive_paths"]
    assert emissao_oficial["delivery_manifest"]["public_payload_mode"] == "human_validated_pdf"
    trail_keys = [item["event_key"] for item in emissao_oficial["audit_trail"]]
    assert trail_keys == [
        "review_approval",
        "primary_pdf",
        "public_verification",
        "annex_pack",
        "governed_signatory",
    ]
    assert anexo_pack["items"][0]["archive_path"].startswith("documentos/")
    assert anexo_pack["items"][1]["archive_path"] == "metadados/verificacao_publica.json"


def test_build_official_issue_package_bloqueia_sem_signatario_e_sem_pdf(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR10",
            tipo_template="nr10",
            catalog_family_key="nr10_inspecao_instalacoes_eletricas",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            status_conformidade=StatusLaudo.PENDENTE.value,
            codigo_hash=uuid.uuid4().hex,
            report_pack_draft_json={
                "quality_gates": {
                    "missing_evidence": [
                        {
                            "code": "documento_base_pendente",
                            "kind": "document",
                            "message": "Anexar documento-base controlado.",
                        }
                    ],
                }
            },
        )
        banco.add(laudo)
        banco.commit()

        anexo_pack, emissao_oficial = build_official_issue_package(
            banco,
            laudo=laudo,
        )

    assert anexo_pack["missing_required_count"] >= 2
    assert emissao_oficial["ready_for_issue"] is False
    blocker_codes = {item["code"] for item in emissao_oficial["blockers"]}
    assert "review_not_approved" in blocker_codes
    assert "missing_pdf" in blocker_codes
    assert "no_eligible_signatory" in blocker_codes
    assert anexo_pack["delivery_manifest"]["ready_for_issue"] is False
    assert "pdf_principal" in anexo_pack["delivery_manifest"]["missing_required_item_keys"]
    trail_statuses = {item["event_key"]: item["status"] for item in emissao_oficial["audit_trail"]}
    assert trail_statuses["review_approval"] == "blocked"
    assert trail_statuses["primary_pdf"] == "blocked"


def test_build_official_issue_package_expoe_emissao_ativa_e_reemissao_recomendada(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR13",
            tipo_template="nr13",
            catalog_family_key="nr13_inspecao_caldeira",
            status_revisao=StatusRevisao.APROVADO.value,
            status_conformidade=StatusLaudo.CONFORME.value,
            codigo_hash=uuid.uuid4().hex,
            nome_arquivo_pdf="laudo_nr13_emitido.pdf",
            report_pack_draft_json={"quality_gates": {"missing_evidence": []}},
        )
        banco.add(laudo)
        banco.flush()

        signatario = SignatarioGovernadoLaudo(
            tenant_id=ids["empresa_a"],
            nome="Eng. Tariel",
            funcao="Responsável técnico",
            registro_profissional="CREA 1234",
            valid_until=datetime.now(timezone.utc) + timedelta(days=120),
            allowed_family_keys_json=["nr13_inspecao_caldeira"],
            ativo=True,
            criado_por_id=ids["admin_a"],
        )
        banco.add(signatario)
        banco.flush()

        snapshot_v1 = ApprovedCaseSnapshot(
            laudo_id=int(laudo.id),
            empresa_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            approval_version=1,
            document_outcome="approved",
            laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
        )
        banco.add(snapshot_v1)
        banco.flush()

        banco.add(
            EmissaoOficialLaudo(
                laudo_id=int(laudo.id),
                tenant_id=ids["empresa_a"],
                approval_snapshot_id=int(snapshot_v1.id),
                signatory_id=int(signatario.id),
                issued_by_user_id=ids["revisor_a"],
                issue_number="TAR-20260410-0001",
                issue_state="issued",
                issued_at=datetime.now(timezone.utc),
                verification_hash=laudo.codigo_hash,
                public_verification_url=f"/app/public/laudo/verificar/{laudo.codigo_hash}",
                package_sha256="a" * 64,
                package_fingerprint_sha256="b" * 64,
                package_filename="TAR-20260410-0001.zip",
                package_storage_path="/tmp/TAR-20260410-0001.zip",
                package_size_bytes=256,
                manifest_json={"bundle_kind": "tariel_official_issue_package"},
                issue_context_json={
                    "approval_version": 1,
                    "signatory_snapshot": {
                        "nome": "Eng. Tariel",
                        "funcao": "Responsável técnico",
                        "registro_profissional": "CREA 1234",
                    },
                    "issued_by_snapshot": {
                        "nome": "Revisor A",
                    },
                },
            )
        )
        banco.commit()

        anexo_pack, emissao_oficial = build_official_issue_package(
            banco,
            laudo=laudo,
        )

        assert anexo_pack["ready_for_issue"] is True
        assert emissao_oficial["already_issued"] is True
        assert emissao_oficial["reissue_recommended"] is False
        assert emissao_oficial["issue_status"] == "issued_officially"
        assert emissao_oficial["current_issue"]["issue_number"] == "TAR-20260410-0001"
        assert emissao_oficial["audit_trail"][0]["event_key"] == "official_issue_record"

        snapshot_v2 = ApprovedCaseSnapshot(
            laudo_id=int(laudo.id),
            empresa_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            approval_version=2,
            document_outcome="approved",
            laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
        )
        banco.add(snapshot_v2)
        banco.commit()

        _anexo_pack_reemit, emissao_reemit = build_official_issue_package(
            banco,
            laudo=laudo,
        )

    assert emissao_reemit["already_issued"] is True
    assert emissao_reemit["reissue_recommended"] is True
    assert emissao_reemit["issue_status"] == "reissue_recommended"
    assert emissao_reemit["issue_action_label"] == "Reemitir oficialmente"


def test_build_official_issue_package_sinaliza_divergencia_do_pdf_atual(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    caminho_pdf_emitido_atual: Path | None = None
    payload_pdf_emitido_atual = b"pdf-atual-divergente"
    payload_pdf_emitido_congelado = b"pdf-congelado-oficial"

    try:
        with SessionLocal() as banco:
            laudo = Laudo(
                empresa_id=ids["empresa_a"],
                usuario_id=ids["inspetor_a"],
                setor_industrial="NR13",
                tipo_template="nr13",
                catalog_family_key="nr13_inspecao_caldeira",
                status_revisao=StatusRevisao.APROVADO.value,
                status_conformidade=StatusLaudo.CONFORME.value,
                codigo_hash=uuid.uuid4().hex,
                nome_arquivo_pdf="laudo_nr13_emitido.pdf",
                report_pack_draft_json={"quality_gates": {"missing_evidence": []}},
            )
            banco.add(laudo)
            banco.flush()

            signatario = SignatarioGovernadoLaudo(
                tenant_id=ids["empresa_a"],
                nome="Eng. Tariel",
                funcao="Responsável técnico",
                registro_profissional="CREA 1234",
                valid_until=datetime.now(timezone.utc) + timedelta(days=120),
                allowed_family_keys_json=["nr13_inspecao_caldeira"],
                ativo=True,
                criado_por_id=ids["admin_a"],
            )
            banco.add(signatario)
            banco.flush()

            snapshot_v1 = ApprovedCaseSnapshot(
                laudo_id=int(laudo.id),
                empresa_id=ids["empresa_a"],
                family_key="nr13_inspecao_caldeira",
                approval_version=1,
                document_outcome="approved",
                laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
            )
            banco.add(snapshot_v1)
            banco.flush()

            banco.add(
                EmissaoOficialLaudo(
                    laudo_id=int(laudo.id),
                    tenant_id=ids["empresa_a"],
                    approval_snapshot_id=int(snapshot_v1.id),
                    signatory_id=int(signatario.id),
                    issued_by_user_id=ids["revisor_a"],
                    issue_number="TAR-20260410-0002",
                    issue_state="issued",
                    issued_at=datetime.now(timezone.utc),
                    verification_hash=laudo.codigo_hash,
                    public_verification_url=f"/app/public/laudo/verificar/{laudo.codigo_hash}",
                    package_sha256="e" * 64,
                    package_fingerprint_sha256="f" * 64,
                    package_filename="TAR-20260410-0002.zip",
                    package_storage_path="/tmp/TAR-20260410-0002.zip",
                    package_size_bytes=256,
                    manifest_json={"bundle_kind": "tariel_official_issue_package"},
                    issue_context_json={
                        "approval_version": 1,
                        "signatory_snapshot": {
                            "nome": "Eng. Tariel",
                            "funcao": "Responsável técnico",
                            "registro_profissional": "CREA 1234",
                        },
                        "primary_pdf_artifact": {
                            "archive_path": "documentos/laudo_nr13_emitido.pdf",
                            "storage_version": "v0003",
                            "storage_version_number": 3,
                            "sha256": hashlib.sha256(payload_pdf_emitido_congelado).hexdigest(),
                        },
                    },
                )
            )
            banco.commit()

            caminho_pdf_emitido_atual = (
                WEB_ROOT
                / "storage"
                / "laudos_emitidos"
                / f"empresa_{ids['empresa_a']}"
                / f"laudo_{int(laudo.id)}"
                / "v0004"
                / "laudo_nr13_emitido.pdf"
            )
            caminho_pdf_emitido_atual.parent.mkdir(parents=True, exist_ok=True)
            caminho_pdf_emitido_atual.write_bytes(payload_pdf_emitido_atual)

            anexo_pack, emissao_oficial = build_official_issue_package(
                banco,
                laudo=laudo,
            )

        assert anexo_pack["ready_for_issue"] is True
        assert emissao_oficial["already_issued"] is True
        assert emissao_oficial["reissue_recommended"] is True
        assert emissao_oficial["issue_status"] == "reissue_recommended"
        assert emissao_oficial["current_issue"]["primary_pdf_diverged"] is True
        assert emissao_oficial["current_issue"]["primary_pdf_comparison_status"] == "diverged"
        assert emissao_oficial["current_issue"]["current_primary_pdf_storage_version"] == "v0004"
        assert emissao_oficial["current_issue"]["current_primary_pdf_sha256"] == hashlib.sha256(
            payload_pdf_emitido_atual
        ).hexdigest()
        assert any(
            item["event_key"] == "official_issue_document_integrity" and item["status"] == "attention"
            for item in emissao_oficial["audit_trail"]
        )
    finally:
        if caminho_pdf_emitido_atual is not None and caminho_pdf_emitido_atual.exists():
            caminho_pdf_emitido_atual.unlink()


def test_emitir_oficialmente_transacional_congela_bundle_e_reaproveita_registro(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    caminho_anexo = os.path.join(tempfile.gettempdir(), f"official_issue_{uuid.uuid4().hex[:8]}.pdf")
    caminho_pdf_emitido: Path | None = None
    payload_pdf_emitido = _pdf_base_bytes_teste()
    with open(caminho_anexo, "wb") as arquivo:
        arquivo.write(_pdf_base_bytes_teste())

    try:
        with SessionLocal() as banco:
            laudo = Laudo(
                empresa_id=ids["empresa_a"],
                usuario_id=ids["inspetor_a"],
                setor_industrial="NR13",
                tipo_template="nr13",
                catalog_selection_token="catalog:nr13_inspecao_caldeira:premium_campo",
                catalog_family_key="nr13_inspecao_caldeira",
                catalog_family_label="NR13 · Caldeira",
                catalog_variant_key="premium_campo",
                catalog_variant_label="Premium campo",
                catalog_snapshot_json={
                    "captured_at": "2026-04-15T12:00:00+00:00",
                    "capture_reason": "creation",
                    "selection_token": "catalog:nr13_inspecao_caldeira:premium_campo",
                    "family": {"key": "nr13_inspecao_caldeira", "label": "NR13 · Caldeira"},
                    "variant": {"key": "premium_campo", "label": "Premium campo"},
                    "offer": {"name": "Oferta Premium NR13"},
                    "tenant_release": {"status": "active"},
                },
                pdf_template_snapshot_json={
                    "template_ref": {
                        "source_kind": "tenant_template",
                        "template_id": 91,
                        "codigo_template": "nr13_premium_emit",
                        "versao": 4,
                        "modo_editor": "rico",
                        "arquivo_pdf_base": "/tmp/nr13_emit.pdf",
                        "assets_json": [{"kind": "logo"}],
                    }
                },
                status_revisao=StatusRevisao.APROVADO.value,
                status_conformidade=StatusLaudo.CONFORME.value,
                codigo_hash=uuid.uuid4().hex,
                nome_arquivo_pdf="laudo_nr13_emitido.pdf",
                report_pack_draft_json={"quality_gates": {"missing_evidence": []}},
            )
            banco.add(laudo)
            banco.flush()

            mensagem = MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Pacote final oficial pronto para congelamento.",
            )
            banco.add(mensagem)
            banco.flush()

            banco.add(
                AnexoMesa(
                    laudo_id=int(laudo.id),
                    mensagem_id=int(mensagem.id),
                    enviado_por_id=ids["revisor_a"],
                    nome_original="checklist_final.pdf",
                    nome_arquivo="checklist_final.pdf",
                    mime_type="application/pdf",
                    categoria="documento",
                    tamanho_bytes=os.path.getsize(caminho_anexo),
                    caminho_arquivo=caminho_anexo,
                )
            )
            snapshot_aprovado = ApprovedCaseSnapshot(
                laudo_id=int(laudo.id),
                empresa_id=ids["empresa_a"],
                family_key="nr13_inspecao_caldeira",
                approval_version=1,
                document_outcome="approved",
                laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
            )
            banco.add(snapshot_aprovado)
            signatario = SignatarioGovernadoLaudo(
                tenant_id=ids["empresa_a"],
                nome="Eng. Tariel",
                funcao="Responsável técnico",
                registro_profissional="CREA 1234",
                valid_until=datetime.now(timezone.utc) + timedelta(days=120),
                allowed_family_keys_json=["nr13_inspecao_caldeira"],
                ativo=True,
                criado_por_id=ids["admin_a"],
            )
            banco.add(signatario)
            banco.commit()

            laudo = banco.get(Laudo, int(laudo.id))
            actor_user = banco.get(Usuario, ids["revisor_a"])
            assert laudo is not None
            assert actor_user is not None
            caminho_pdf_emitido = (
                WEB_ROOT
                / "storage"
                / "laudos_emitidos"
                / f"empresa_{ids['empresa_a']}"
                / f"laudo_{int(laudo.id)}"
                / "v0003"
                / "laudo_nr13_emitido.pdf"
            )
            caminho_pdf_emitido.parent.mkdir(parents=True, exist_ok=True)
            caminho_pdf_emitido.write_bytes(payload_pdf_emitido)

            primeira = emitir_oficialmente_transacional(
                banco,
                laudo=laudo,
                actor_user=actor_user,
                signatory_id=int(signatario.id),
            )
            banco.commit()

            registro = primeira["record"]
            caminho_congelado = str(registro.package_storage_path or "")
            assert primeira["idempotent_replay"] is False
            assert os.path.isfile(caminho_congelado)
            assert primeira["record_payload"]["issue_number"].startswith("TAR-")
            assert primeira["record_payload"]["package_storage_ready"] is True
            with open(caminho_congelado, "rb") as arquivo_congelado:
                pacote_bytes = arquivo_congelado.read()
            assert hashlib.sha256(pacote_bytes).hexdigest() == registro.package_sha256
            with zipfile.ZipFile(io.BytesIO(pacote_bytes)) as arquivo_zip:
                manifest = json.loads(arquivo_zip.read("manifest.json").decode("utf-8"))
                catalog_binding_trace = manifest["catalog_binding_trace"]
                assert "governanca/catalog_binding_trace.json" in set(arquivo_zip.namelist())
                assert "governanca/catalog_snapshot.json" in set(arquivo_zip.namelist())
                assert "governanca/pdf_template_snapshot.json" in set(arquivo_zip.namelist())
                assert arquivo_zip.read("documentos/laudo_nr13_emitido.pdf") == payload_pdf_emitido
                assert catalog_binding_trace["selection_token"] == "catalog:nr13_inspecao_caldeira:premium_campo"
                assert catalog_binding_trace["family_key"] == "nr13_inspecao_caldeira"
                assert catalog_binding_trace["variant_key"] == "premium_campo"
                assert catalog_binding_trace["template_ref"]["codigo_template"] == "nr13_premium_emit"
                assert catalog_binding_trace["approval_version"] == 1
                assert catalog_binding_trace["approved_snapshot_id"] == int(snapshot_aprovado.id)
            assert registro.issue_context_json["primary_pdf_artifact"]["archive_path"] == "documentos/laudo_nr13_emitido.pdf"
            assert registro.issue_context_json["primary_pdf_artifact"]["storage_version"] == "v0003"
            assert registro.issue_context_json["primary_pdf_artifact"]["storage_version_number"] == 3
            assert registro.issue_context_json["primary_pdf_artifact"]["storage_path"] == str(caminho_pdf_emitido)
            assert registro.issue_context_json["primary_pdf_artifact"]["sha256"] == hashlib.sha256(payload_pdf_emitido).hexdigest()
            assert registro.issue_context_json["catalog_binding_trace"]["selection_token"] == (
                "catalog:nr13_inspecao_caldeira:premium_campo"
            )
            assert registro.issue_context_json["catalog_binding_trace"]["template_ref"]["codigo_template"] == (
                "nr13_premium_emit"
            )
            assert primeira["record_payload"]["primary_pdf_archive_path"] == "documentos/laudo_nr13_emitido.pdf"
            assert primeira["record_payload"]["primary_pdf_storage_ready"] is True
            assert primeira["record_payload"]["primary_pdf_storage_version"] == "v0003"
            assert primeira["record_payload"]["primary_pdf_storage_version_number"] == 3
            assert primeira["record_payload"]["primary_pdf_sha256"] == hashlib.sha256(payload_pdf_emitido).hexdigest()
            assert registro.manifest_json["catalog_binding_trace"]["tenant_release_status"] == "active"
            assert registro.manifest_json["case_status"] == "approved"
            assert registro.manifest_json["active_owner_role"] == "none"

            segunda = emitir_oficialmente_transacional(
                banco,
                laudo=laudo,
                actor_user=actor_user,
                signatory_id=int(signatario.id),
            )
            banco.commit()

            assert segunda["idempotent_replay"] is True
            assert segunda["record_payload"]["id"] == primeira["record_payload"]["id"]
            assert segunda["record_payload"]["issue_number"] == primeira["record_payload"]["issue_number"]
            assert segunda["record_payload"]["primary_pdf_storage_version"] == "v0003"
            assert segunda["record_payload"]["primary_pdf_sha256"] == hashlib.sha256(payload_pdf_emitido).hexdigest()
            assert segunda["download_storage_path"] == caminho_congelado

            laudo.reaberto_em = datetime.now(timezone.utc)
            banco.flush()

            _anexo_pack_reaberto, emissao_reaberta = build_official_issue_package(
                banco,
                laudo=laudo,
            )

            assert emissao_reaberta["ready_for_issue"] is False
            assert emissao_reaberta["already_issued"] is True
            assert emissao_reaberta["issue_status"] == "awaiting_approval"
            assert emissao_reaberta["case_lifecycle_status"] == "devolvido_para_correcao"
            assert emissao_reaberta["status_visual_label"] == "Devolvido para correcao / Responsavel: campo"
            assert emissao_reaberta["audit_trail"][0]["event_key"] == "official_issue_record"
            assert emissao_reaberta["audit_trail"][0]["status"] == "attention"
            assert {item["code"] for item in emissao_reaberta["blockers"]} >= {"review_not_approved"}

            with pytest.raises(ValueError, match="aprovação governada"):
                emitir_oficialmente_transacional(
                    banco,
                    laudo=laudo,
                    actor_user=actor_user,
                    signatory_id=int(signatario.id),
                )
    finally:
        if os.path.exists(caminho_anexo):
            os.remove(caminho_anexo)
        if caminho_pdf_emitido is not None and caminho_pdf_emitido.exists():
            caminho_pdf_emitido.unlink()
