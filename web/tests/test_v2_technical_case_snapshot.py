from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.shared.database import NivelAcesso, StatusRevisao
from app.v2.acl.technical_case_snapshot import (
    build_technical_case_snapshot_for_user,
)


def _build_user(*, nivel_acesso: int = NivelAcesso.REVISOR.value) -> SimpleNamespace:
    return SimpleNamespace(
        id=51,
        empresa_id=33,
        nivel_acesso=nivel_acesso,
    )


def test_snapshot_canonico_rico_deriva_ids_estado_e_versao_documental() -> None:
    agora = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    laudo = SimpleNamespace(
        id=88,
        empresa_id=33,
        usuario_id=17,
        revisado_por=51,
        status_revisao=StatusRevisao.AGUARDANDO.value,
        reabertura_pendente_em=None,
        reaberto_em=None,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho IA",
        nome_arquivo_pdf=None,
        criado_em=agora,
        atualizado_em=agora,
        revisoes=[
            SimpleNamespace(id=1, numero_versao=1),
            SimpleNamespace(id=2, numero_versao=2),
        ],
    )

    snapshot = build_technical_case_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "status_card": "aguardando",
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
        laudo=laudo,
        source_channel="review_api",
    )

    dumped = snapshot.model_dump(mode="json")
    assert dumped["case_ref"]["case_id"] == "case:legacy-laudo:33:88"
    assert dumped["main_thread_id"] == "thread:legacy-laudo:33:88"
    assert dumped["active_document_version_id"] == "document-version:legacy-laudo:33:88:2"
    assert dumped["latest_document_version_number"] == 2
    assert dumped["case_state"] == "review_in_progress"
    assert dumped["current_review_state"] == "in_review"
    assert dumped["current_document_state"] == "awaiting_approval"
    assert dumped["current_engineer_approval_state"] == "awaiting_engineer"
    assert dumped["case_origin"] == "review_web"
    assert dumped["visibility_scope"] == "tenant_technical_full"
    assert dumped["sensitivity_level"] == "documentary_working"
    assert dumped["legacy_refs"]["legacy_document_ref"] == "laudo_revisoes:laudo_id:88"


def test_snapshot_canonico_rico_marca_documento_emitido_e_flag_de_divergencia() -> None:
    agora = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    laudo = SimpleNamespace(
        id=91,
        empresa_id=33,
        usuario_id=17,
        revisado_por=51,
        status_revisao=StatusRevisao.APROVADO.value,
        reabertura_pendente_em=None,
        reaberto_em=None,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho IA",
        nome_arquivo_pdf="laudo_91.pdf",
        criado_em=agora,
        atualizado_em=agora,
        revisoes=[],
    )

    snapshot = build_technical_case_snapshot_for_user(
        usuario=_build_user(nivel_acesso=NivelAcesso.ADMIN_CLIENTE.value),
        legacy_payload={
            "estado": "aprovado",
            "laudo_id": 91,
            "status_card": "aprovado",
            "permite_reabrir": False,
            "laudo_card": {"id": 91, "status_revisao": StatusRevisao.APROVADO.value},
        },
        laudo=laudo,
        source_channel="admin_cliente_bridge",
    )

    dumped = snapshot.model_dump(mode="json")
    assert dumped["case_state"] == "issued"
    assert dumped["current_review_state"] == "approved"
    assert dumped["current_document_state"] == "issued"
    assert dumped["current_engineer_approval_state"] == "approved"
    assert dumped["case_origin"] == "admin_cliente_web"
    assert dumped["visibility_scope"] == "tenant_admin_summary"
    assert dumped["sensitivity_level"] == "administrative"
    assert "legacy_document_issued_without_revision_history" in dumped["divergence_flags"]
    assert dumped["legacy_refs"]["legacy_pdf_file_name"] == "laudo_91.pdf"


def test_snapshot_canonico_rico_explicita_reabertura_legada() -> None:
    agora = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    laudo = SimpleNamespace(
        id=99,
        empresa_id=33,
        usuario_id=17,
        revisado_por=51,
        status_revisao=StatusRevisao.RASCUNHO.value,
        reabertura_pendente_em=None,
        reaberto_em=agora,
        dados_formulario={"campo": "valor"},
        parecer_ia="",
        nome_arquivo_pdf=None,
        criado_em=agora,
        atualizado_em=agora,
        revisoes=[],
    )

    snapshot = build_technical_case_snapshot_for_user(
        usuario=_build_user(nivel_acesso=NivelAcesso.INSPETOR.value),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 99,
            "status_card": "aberto",
            "permite_reabrir": False,
            "laudo_card": {"id": 99, "status_revisao": StatusRevisao.RASCUNHO.value},
        },
        laudo=laudo,
        source_channel="web_app",
    )

    dumped = snapshot.model_dump(mode="json")
    assert dumped["case_state"] == "reopened"
    assert dumped["current_document_state"] == "reopened"
    assert "legacy_reopen_cycle_not_explicit" in dumped["divergence_flags"]


def test_snapshot_canonico_rico_prioriza_reabertura_mesmo_com_pdf_emitido_anterior() -> None:
    agora = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    laudo = SimpleNamespace(
        id=109,
        empresa_id=33,
        usuario_id=17,
        revisado_por=51,
        status_revisao=StatusRevisao.RASCUNHO.value,
        reabertura_pendente_em=None,
        reaberto_em=agora,
        dados_formulario={"campo": "valor"},
        parecer_ia="Documento reaberto",
        nome_arquivo_pdf="laudo_109_v1.pdf",
        criado_em=agora,
        atualizado_em=agora,
        revisoes=[],
    )

    snapshot = build_technical_case_snapshot_for_user(
        usuario=_build_user(nivel_acesso=NivelAcesso.INSPETOR.value),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 109,
            "status_card": "aberto",
            "permite_reabrir": False,
            "laudo_card": {"id": 109, "status_revisao": StatusRevisao.RASCUNHO.value},
        },
        laudo=laudo,
        source_channel="web_app",
    )

    dumped = snapshot.model_dump(mode="json")
    assert dumped["case_state"] == "reopened"
    assert dumped["current_document_state"] == "reopened"
    assert dumped["legacy_refs"]["legacy_pdf_file_name"] == "laudo_109_v1.pdf"
