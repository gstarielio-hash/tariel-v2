from __future__ import annotations

from datetime import datetime, timezone
import uuid

import app.shared.official_issue_package as official_issue_package
from app.shared.database import EmissaoOficialLaudo, Laudo, StatusRevisao, Usuario
from tests.regras_rotas_criticas_support import SENHA_PADRAO, _login_app_inspetor


def _login_mobile_inspetor(client, email: str) -> dict[str, str]:
    resposta = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": email,
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def test_portal_app_ssr_expone_preferencia_padrao_de_modo_de_entrada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    resposta_settings = client.put(
        "/app/api/mobile/account/settings",
        headers=headers,
        json={
            "experiencia_ia": {
                "entry_mode_preference": "evidence_first",
                "remember_last_case_mode": False,
            }
        },
    )
    assert resposta_settings.status_code == 200

    _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_portal = client.get("/app/")

    assert resposta_portal.status_code == 200
    assert 'data-entry-mode-preference-default="evidence_first"' in resposta_portal.text
    assert 'data-entry-mode-remember-last-case-mode="false"' in resposta_portal.text
    assert 'name="entry-mode-preference"' in resposta_portal.text
    assert 'id="workspace-entry-mode-note"' in resposta_portal.text


def test_portal_app_ssr_expone_ultimo_modo_efetivo_quando_usuario_pede_memoria(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    resposta_settings = client.put(
        "/app/api/mobile/account/settings",
        headers=headers,
        json={
            "experiencia_ia": {
                "entry_mode_preference": "auto_recommended",
                "remember_last_case_mode": True,
            }
        },
    )
    assert resposta_settings.status_code == 200

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="chat_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
        )
        banco.add(laudo)
        banco.commit()

    _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_portal = client.get("/app/")

    assert resposta_portal.status_code == 200
    assert 'data-entry-mode-preference-default="auto_recommended"' in resposta_portal.text
    assert 'data-entry-mode-remember-last-case-mode="true"' in resposta_portal.text
    assert 'data-entry-mode-last-case-mode="evidence_first"' in resposta_portal.text


def test_portal_app_ssr_expone_modo_de_entrada_nos_cards_de_laudo(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="linha de vida",
            primeira_mensagem="Inspeção iniciada com evidências do caso.",
            tipo_template="nr35",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="auto_recommended",
            entry_mode_effective="evidence_first",
            entry_mode_reason="family_required_mode",
        )
        banco.add(laudo)
        banco.commit()

    _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_portal = client.get("/app/")

    assert resposta_portal.status_code == 200
    assert 'data-entry-mode-effective="evidence_first"' in resposta_portal.text
    assert 'data-entry-mode-reason="family_required_mode"' in resposta_portal.text


def test_portal_app_ssr_expone_governanca_de_reemissao_no_ponto_de_entrada(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    monkeypatch.setattr(official_issue_package, "WEB_ROOT", tmp_path)

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="linha de vida",
            primeira_mensagem="Portal com drift oficial",
            tipo_template="nr35",
            status_revisao=StatusRevisao.APROVADO.value,
            codigo_hash=uuid.uuid4().hex,
            nome_arquivo_pdf="nr35_emitido.pdf",
        )
        banco.add(laudo)
        banco.flush()

        frozen_path = tmp_path / "frozen" / "nr35_emitido.pdf"
        frozen_path.parent.mkdir(parents=True, exist_ok=True)
        frozen_path.write_bytes(b"pdf-frozen-web")

        current_path = (
            tmp_path
            / "storage"
            / "laudos_emitidos"
            / f"empresa_{usuario.empresa_id}"
            / f"laudo_{laudo.id}"
            / "v0004"
            / "nr35_emitido.pdf"
        )
        current_path.parent.mkdir(parents=True, exist_ok=True)
        current_path.write_bytes(b"pdf-current-web")

        emissao = EmissaoOficialLaudo(
            laudo_id=laudo.id,
            tenant_id=usuario.empresa_id,
            issue_number="EO-NR35-WEB-1",
            issue_state="issued",
            issued_at=datetime.now(timezone.utc),
            package_sha256="e" * 64,
            package_fingerprint_sha256="f" * 64,
            issue_context_json={
                "primary_pdf_artifact": {
                    "storage_path": str(frozen_path),
                    "storage_file_name": "nr35_emitido.pdf",
                    "storage_version": "v0003",
                    "storage_version_number": 3,
                    "source": "issue_context",
                }
            },
        )
        banco.add(emissao)
        banco.commit()

    _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_portal = client.get("/app/")

    assert resposta_portal.status_code == 200
    assert 'id="portal-governance-summary"' in resposta_portal.text
    assert "1 caso com reemissão recomendada" in resposta_portal.text
    assert 'id="workspace-assistant-governance"' in resposta_portal.text
    assert "PDF oficial divergente detectado no ponto de entrada do inspetor." in resposta_portal.text
    assert 'data-official-issue-diverged="true"' in resposta_portal.text
    assert 'data-official-issue-label="Reemissão recomendada"' in resposta_portal.text
    assert 'data-official-issue-detail="PDF emitido divergente · Emitido v0003 · Atual v0004"' in resposta_portal.text
    assert 'data-open-thread-tab="mesa"' in resposta_portal.text
    assert "Abrir pela Mesa" in resposta_portal.text
