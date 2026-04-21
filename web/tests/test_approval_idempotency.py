from __future__ import annotations

from datetime import datetime, timezone

from app.shared.database import ApprovedCaseSnapshot, Laudo, StatusRevisao
from tests.regras_rotas_criticas_support import (
    SENHA_PADRAO,
    _login_app_inspetor,
    _login_revisor,
)
from tests.test_semantic_report_pack_nr35_autonomy import _criar_laudo_nr35_guiado


def _login_mobile_inspetor(client) -> dict[str, str]:
    resposta = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta.status_code == 200
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_finalizar_relatorio_mobile_autonomous_replay_e_idempotente(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=True)

    primeira = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )
    assert primeira.status_code == 200
    corpo_primeira = primeira.json()
    assert corpo_primeira["success"] is True
    assert corpo_primeira["review_mode_final"] == "mobile_autonomous"
    assert corpo_primeira["idempotent_replay"] is False

    segunda = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )
    assert segunda.status_code == 200
    corpo_segunda = segunda.json()
    assert corpo_segunda["success"] is True
    assert corpo_segunda["review_mode_final"] == "mobile_autonomous"
    assert corpo_segunda["idempotent_replay"] is True

    with SessionLocal() as banco:
        snapshots = (
            banco.query(ApprovedCaseSnapshot)
            .filter(ApprovedCaseSnapshot.laudo_id == laudo_id)
            .all()
        )
        assert len(snapshots) == 1
        assert snapshots[0].document_outcome == "approved_mobile_autonomous"


def test_mobile_review_command_aprovar_no_mobile_replay_e_idempotente(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers = _login_mobile_inspetor(client)
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=True)

    primeira = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={"command": "aprovar_no_mobile"},
    )
    assert primeira.status_code == 200
    corpo_primeira = primeira.json()
    assert corpo_primeira["ok"] is True
    assert corpo_primeira["command"] == "aprovar_no_mobile"
    assert corpo_primeira["review_mode_final"] == "mobile_autonomous"
    assert corpo_primeira["idempotent_replay"] is False

    segunda = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={"command": "aprovar_no_mobile"},
    )
    assert segunda.status_code == 200
    corpo_segunda = segunda.json()
    assert corpo_segunda["ok"] is True
    assert corpo_segunda["command"] == "aprovar_no_mobile"
    assert corpo_segunda["review_mode_final"] == "mobile_autonomous"
    assert corpo_segunda["idempotent_replay"] is True

    with SessionLocal() as banco:
        snapshots = (
            banco.query(ApprovedCaseSnapshot)
            .filter(ApprovedCaseSnapshot.laudo_id == laudo_id)
            .all()
        )
        assert len(snapshots) == 1
        assert snapshots[0].document_outcome == "approved_mobile_review"


def test_revisor_aprovar_via_api_replay_e_idempotente(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers_mobile = _login_mobile_inspetor(client)
    csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=True)

    envio_mesa = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers_mobile,
        json={"command": "enviar_para_mesa"},
    )
    assert envio_mesa.status_code == 200

    primeira = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        headers={"X-CSRF-Token": csrf_revisor},
        data={"acao": "aprovar", "motivo": "", "csrf_token": csrf_revisor},
    )
    assert primeira.status_code == 200
    corpo_primeira = primeira.json()
    assert corpo_primeira["success"] is True
    assert corpo_primeira["status_revisao"] == StatusRevisao.APROVADO.value
    assert corpo_primeira["case_status"] == "approved"
    assert corpo_primeira["case_lifecycle_status"] == "aprovado"
    assert corpo_primeira["active_owner_role"] == "none"
    assert corpo_primeira["status_visual_label"] == "Aprovado / Responsavel: conclusao"
    assert corpo_primeira["idempotent_replay"] is False

    segunda = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        headers={"X-CSRF-Token": csrf_revisor},
        data={"acao": "aprovar", "motivo": "", "csrf_token": csrf_revisor},
    )
    assert segunda.status_code == 200
    corpo_segunda = segunda.json()
    assert corpo_segunda["success"] is True
    assert corpo_segunda["status_revisao"] == StatusRevisao.APROVADO.value
    assert corpo_segunda["case_lifecycle_status"] == "aprovado"
    assert corpo_segunda["active_owner_role"] == "none"
    assert corpo_segunda["status_visual_label"] == "Aprovado / Responsavel: conclusao"
    assert corpo_segunda["idempotent_replay"] is True

    with SessionLocal() as banco:
        snapshots = (
            banco.query(ApprovedCaseSnapshot)
            .filter(ApprovedCaseSnapshot.laudo_id == laudo_id)
            .all()
        )
        assert len(snapshots) == 1
        assert snapshots[0].document_outcome == "approved_by_mesa"


def test_revisor_aprovar_nao_trata_como_replay_caso_reaberto_com_status_legado_aprovado(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers_mobile = _login_mobile_inspetor(client)
    csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=True)

    envio_mesa = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers_mobile,
        json={"command": "enviar_para_mesa"},
    )
    assert envio_mesa.status_code == 200

    primeira = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        headers={"X-CSRF-Token": csrf_revisor},
        data={"acao": "aprovar", "motivo": "", "csrf_token": csrf_revisor},
    )
    assert primeira.status_code == 200
    assert primeira.json()["idempotent_replay"] is False

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.reaberto_em = datetime.now(timezone.utc)
        banco.commit()

    segunda = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        headers={"X-CSRF-Token": csrf_revisor},
        data={"acao": "aprovar", "motivo": "", "csrf_token": csrf_revisor},
    )
    assert segunda.status_code == 400

    with SessionLocal() as banco:
        snapshots = (
            banco.query(ApprovedCaseSnapshot)
            .filter(ApprovedCaseSnapshot.laudo_id == laudo_id)
            .all()
        )
        assert len(snapshots) == 1
