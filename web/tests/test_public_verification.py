from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.paths import WEB_ROOT
from app.shared.database import (
    ApprovedCaseSnapshot,
    EmissaoOficialLaudo,
    Laudo,
    SignatarioGovernadoLaudo,
    StatusLaudo,
    StatusRevisao,
    Usuario,
)
from app.shared.public_verification import build_public_verification_payload


def test_verificacao_publica_por_hash_retorna_payload_json(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="nr13_inspecao_caldeira",
            catalog_selection_token="catalog:nr13_inspecao_caldeira:premium_campo",
            catalog_family_key="nr13_inspecao_caldeira",
            catalog_family_label="NR13 Inspecao Caldeira",
            catalog_variant_key="premium_campo",
            catalog_variant_label="Premium campo",
            pdf_template_snapshot_json={
                "template_ref": {
                    "codigo_template": "nr13_publico_v1",
                    "versao": 1,
                    "modo_editor": "rico",
                }
            },
            status_conformidade=StatusLaudo.CONFORME.value,
            status_revisao=StatusRevisao.APROVADO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        banco.add(
            ApprovedCaseSnapshot(
                laudo_id=laudo.id,
                empresa_id=usuario.empresa_id,
                family_key="nr13_inspecao_caldeira",
                approval_version=1,
                document_outcome="approved",
                laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
            )
        )
        banco.commit()
        codigo_hash = str(laudo.codigo_hash)

    resposta = client.get(
        f"/app/public/laudo/verificar/{codigo_hash}",
        params={"format": "json"},
    )

    assert resposta.status_code == 200
    payload = resposta.json()
    assert payload["verified"] is True
    assert payload["codigo_hash"] == codigo_hash
    assert payload["family_key"] == "nr13_inspecao_caldeira"
    assert payload["document_outcome"] == "approved"
    assert payload["selection_token"] == "catalog:nr13_inspecao_caldeira:premium_campo"
    assert payload["variant_label"] == "Premium campo"
    assert payload["template_code"] == "nr13_publico_v1"
    assert payload["catalog_binding_trace"]["family_key"] == "nr13_inspecao_caldeira"
    assert payload["catalog_binding_trace"]["variant_key"] == "premium_campo"
    assert payload["case_lifecycle_status"] == "aprovado"
    assert payload["active_owner_role"] == "none"
    assert payload["status_visual_label"] == "Aprovado / Responsavel: conclusao"
    assert payload["verification_url"].endswith(f"/app/public/laudo/verificar/{codigo_hash}")
    assert payload["qr_image_data_uri"].startswith("data:image/png;base64,")


def test_verificacao_publica_por_hash_retorna_html_sem_autenticacao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_conformidade=StatusLaudo.PENDENTE.value,
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.commit()
        codigo_hash = str(laudo.codigo_hash)

    resposta = client.get(f"/app/public/laudo/verificar/{codigo_hash}")

    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
    assert "documento verificado" in resposta.text.lower()
    assert codigo_hash in resposta.text
    assert "qr code" in resposta.text.lower()


def test_verificacao_publica_expoe_emissao_oficial_ativa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    caminho_pdf_emitido_atual: Path | None = None
    payload_pdf_emitido_atual = b"laudo-publico-atual-divergente"

    try:
        with SessionLocal() as banco:
            usuario = banco.get(Usuario, ids["inspetor_a"])
            assert usuario is not None
            primary_pdf_sha256 = hashlib.sha256(b"laudo-publico-emitido").hexdigest()

            laudo = Laudo(
                empresa_id=usuario.empresa_id,
                usuario_id=usuario.id,
                setor_industrial="NR Teste",
                tipo_template="runtime_drift",
                catalog_selection_token="catalog:runtime_drift:variante_atual",
                catalog_family_key="runtime_drift",
                catalog_family_label="Runtime Drift",
                catalog_variant_key="variante_atual",
                catalog_variant_label="Variante atual",
                status_conformidade=StatusLaudo.CONFORME.value,
                status_revisao=StatusRevisao.APROVADO.value,
                codigo_hash=uuid.uuid4().hex,
                nome_arquivo_pdf="laudo_emitido.pdf",
            )
            banco.add(laudo)
            banco.flush()

            snapshot = ApprovedCaseSnapshot(
                laudo_id=laudo.id,
                empresa_id=usuario.empresa_id,
                family_key="nr13_inspecao_caldeira",
                approval_version=3,
                document_outcome="approved",
                laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
            )
            banco.add(snapshot)
            banco.flush()

            signatario = SignatarioGovernadoLaudo(
                tenant_id=usuario.empresa_id,
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

            banco.add(
                EmissaoOficialLaudo(
                    laudo_id=int(laudo.id),
                    tenant_id=usuario.empresa_id,
                    approval_snapshot_id=int(snapshot.id),
                    signatory_id=int(signatario.id),
                    issued_by_user_id=ids["revisor_a"],
                    issue_number="TAR-20260410-000321",
                    issue_state="issued",
                    issued_at=datetime.now(timezone.utc),
                    verification_hash=laudo.codigo_hash,
                    public_verification_url=f"/app/public/laudo/verificar/{laudo.codigo_hash}",
                    package_sha256="c" * 64,
                    package_fingerprint_sha256="d" * 64,
                    package_filename="TAR-20260410-000321.zip",
                    package_storage_path="/tmp/TAR-20260410-000321.zip",
                    package_size_bytes=512,
                    manifest_json={"bundle_kind": "tariel_official_issue_package"},
                    issue_context_json={
                        "approval_version": 3,
                        "catalog_binding_trace": {
                            "selection_token": "catalog:nr13_inspecao_caldeira:premium_emitido",
                            "runtime_template_code": "nr13_inspecao_caldeira",
                            "family_key": "nr13_inspecao_caldeira",
                            "family_label": "NR13 Inspecao Caldeira",
                            "variant_key": "premium_emitido",
                            "variant_label": "Premium emitido",
                            "template_ref": {
                                "codigo_template": "nr13_emitido_v6",
                                "versao": 6,
                                "modo_editor": "rico",
                            },
                        },
                        "signatory_snapshot": {
                            "nome": "Eng. Tariel",
                            "funcao": "Responsável técnico",
                            "registro_profissional": "CREA 1234",
                        },
                        "reissue_of_issue_number": "TAR-20260409-000210",
                        "reissue_reason_codes": ["primary_pdf_diverged"],
                        "reissue_reason_summary": "Reemissão motivada por divergência do PDF principal.",
                        "primary_pdf_artifact": {
                            "archive_path": "documentos/laudo_emitido.pdf",
                            "storage_version": "v0006",
                            "storage_version_number": 6,
                            "sha256": primary_pdf_sha256,
                        },
                    },
                )
            )
            banco.commit()
            codigo_hash = str(laudo.codigo_hash)
            caminho_pdf_emitido_atual = (
                WEB_ROOT
                / "storage"
                / "laudos_emitidos"
                / f"empresa_{usuario.empresa_id}"
                / f"laudo_{int(laudo.id)}"
                / "v0007"
                / "laudo_emitido.pdf"
            )
            caminho_pdf_emitido_atual.parent.mkdir(parents=True, exist_ok=True)
            caminho_pdf_emitido_atual.write_bytes(payload_pdf_emitido_atual)

        resposta_json = client.get(
            f"/app/public/laudo/verificar/{codigo_hash}",
            params={"format": "json"},
        )

        assert resposta_json.status_code == 200
        payload = resposta_json.json()
        assert payload["official_issue_number"] == "TAR-20260410-000321"
        assert payload["official_issue_state"] == "issued"
        assert payload["case_lifecycle_status"] == "emitido"
        assert payload["active_owner_role"] == "none"
        assert payload["status_visual_label"] == "Emitido / Responsavel: conclusao"
        assert payload["official_issue_signatory_name"] == "Eng. Tariel"
        assert payload["official_issue_signatory_registration"] == "CREA 1234"
        assert payload["official_issue_package_sha256"] == "c" * 64
        assert payload["official_issue_primary_pdf_sha256"] == primary_pdf_sha256
        assert payload["official_issue_reissue_of_issue_number"] == "TAR-20260409-000210"
        assert payload["official_issue_reissue_reason_codes"] == ["primary_pdf_diverged"]
        assert payload["official_issue_reissue_reason_summary"] == "Reemissão motivada por divergência do PDF principal."
        assert payload["official_issue_lineage_summary"] == (
            "Esta emissão substitui TAR-20260409-000210. Reemissão motivada por divergência do PDF principal."
        )
        assert payload["official_issue_current_pdf_sha256"] == hashlib.sha256(payload_pdf_emitido_atual).hexdigest()
        assert payload["official_issue_current_pdf_storage_version"] == "v0007"
        assert payload["official_issue_primary_pdf_diverged"] is True
        assert payload["official_issue_primary_pdf_comparison_status"] == "diverged"
        assert payload["official_issue_document_integrity_summary"] == "Documento atual diverge do emitido. Atual: v0007."
        assert payload["family_key"] == "nr13_inspecao_caldeira"
        assert payload["family_label"] == "NR13 Inspecao Caldeira"
        assert payload["variant_key"] == "premium_emitido"
        assert payload["variant_label"] == "Premium emitido"
        assert payload["selection_token"] == "catalog:nr13_inspecao_caldeira:premium_emitido"
        assert payload["template_code"] == "nr13_emitido_v6"
        assert payload["catalog_binding_trace"]["template_ref"]["codigo_template"] == "nr13_emitido_v6"

        resposta_html = client.get(f"/app/public/laudo/verificar/{codigo_hash}")

        assert resposta_html.status_code == 200
        assert "TAR-20260410-000321" in resposta_html.text
        assert "CREA 1234" in resposta_html.text
        assert ("c" * 64) in resposta_html.text
        assert primary_pdf_sha256 in resposta_html.text
        assert "TAR-20260409-000210" in resposta_html.text
        assert "Linhagem da emissão" in resposta_html.text
        assert "Reemissão motivada por divergência do PDF principal." in resposta_html.text
        assert "Documento atual diverge do emitido. Atual: v0007." in resposta_html.text
        assert "nr13_emitido_v6" in resposta_html.text
        assert "catalog:nr13_inspecao_caldeira:premium_emitido" in resposta_html.text
    finally:
        if caminho_pdf_emitido_atual is not None and caminho_pdf_emitido_atual.exists():
            caminho_pdf_emitido_atual.unlink()


def test_build_public_verification_payload_sem_banco_expoe_status_visual_canonico(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_conformidade=StatusLaudo.CONFORME.value,
            status_revisao=StatusRevisao.APROVADO.value,
            codigo_hash=uuid.uuid4().hex,
            nome_arquivo_pdf="laudo_emitido.pdf",
        )
        banco.add(laudo)
        banco.commit()
        banco.refresh(laudo)

        payload = build_public_verification_payload(laudo=laudo)

    assert payload["case_lifecycle_status"] == "emitido"
    assert payload["active_owner_role"] == "none"
    assert payload["status_visual_label"] == "Emitido / Responsavel: conclusao"
