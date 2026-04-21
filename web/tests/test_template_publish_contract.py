from __future__ import annotations

from app.shared.database import RegistroAuditoriaEmpresa, TemplateLaudo
from tests.regras_rotas_criticas_support import (
    _login_revisor,
    _pdf_base_bytes_teste,
)


def test_publicar_template_expoe_mesmo_envelope_minimo_na_rota_classica(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_v1 = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template contrato v1",
            "codigo_template": "contrato_publish_pdf",
            "versao": "1",
            "ativo": "true",
        },
        files={
            "arquivo_base": ("contrato_v1.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_v1.status_code == 201
    id_v1 = int(resposta_v1.json()["id"])

    resposta_v2 = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template contrato v2",
            "codigo_template": "contrato_publish_pdf",
            "versao": "2",
        },
        files={
            "arquivo_base": ("contrato_v2.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_v2.status_code == 201
    id_v2 = int(resposta_v2.json()["id"])

    resposta_publicar = client.post(
        f"/revisao/api/templates-laudo/{id_v2}/publicar",
        headers={"X-CSRF-Token": csrf},
        data={"csrf_token": csrf},
    )

    assert resposta_publicar.status_code == 200
    assert resposta_publicar.json() == {
        "ok": True,
        "template_id": id_v2,
        "status": "publicado",
    }

    with SessionLocal() as banco:
        template_v1 = banco.get(TemplateLaudo, id_v1)
        template_v2 = banco.get(TemplateLaudo, id_v2)
        assert template_v1 is not None
        assert template_v2 is not None
        assert template_v1.ativo is False
        assert template_v2.ativo is True


def test_publicar_template_editor_rico_expoe_mesmo_envelope_minimo_e_auditoria(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_v1 = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Word contrato v1",
            "codigo_template": "contrato_publish_word",
            "versao": 1,
            "origem_modo": "a4",
            "ativo": True,
        },
    )
    assert resposta_v1.status_code == 201

    resposta_v2 = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Word contrato v2",
            "codigo_template": "contrato_publish_word",
            "versao": 2,
            "origem_modo": "a4",
        },
    )
    assert resposta_v2.status_code == 201
    id_v2 = int(resposta_v2.json()["id"])

    resposta_publicar = client.post(
        f"/revisao/api/templates-laudo/editor/{id_v2}/publicar",
        headers={"X-CSRF-Token": csrf},
        data={"csrf_token": csrf},
    )

    assert resposta_publicar.status_code == 200
    assert resposta_publicar.json() == {
        "ok": True,
        "template_id": id_v2,
        "status": "publicado",
    }

    with SessionLocal() as banco:
        template_v2 = banco.get(TemplateLaudo, id_v2)
        registro = (
            banco.query(RegistroAuditoriaEmpresa)
            .filter(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "template_publicado",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
            .first()
        )
        assert template_v2 is not None
        assert template_v2.ativo is True
        assert str(template_v2.modo_editor) == "editor_rico"
        assert str(template_v2.arquivo_pdf_base).lower().endswith(".pdf")
        assert registro is not None
        assert registro.portal == "revisao_templates"
        assert int((registro.payload_json or {}).get("template_id") or 0) == id_v2
        assert (registro.payload_json or {}).get("status_template") == "ativo"


def test_publicar_template_bloqueado_expoe_erro_estruturado_sem_ativar_template(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_template = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template bloqueado",
            "codigo_template": "contrato_publish_blocked",
            "versao": "2",
        },
        files={
            "arquivo_base": ("contrato_blocked.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_template.status_code == 201
    template_id = int(resposta_template.json()["id"])

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "template_publish_activate")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES", "contrato_publish_blocked")

    resposta_publicar = client.post(
        f"/revisao/api/templates-laudo/{template_id}/publicar",
        headers={"X-CSRF-Token": csrf},
        data={"csrf_token": csrf},
    )

    assert resposta_publicar.status_code == 422
    assert resposta_publicar.json() == {
        "ok": False,
        "template_id": template_id,
        "status": "bloqueado",
        "error": {
            "codigo": "DOCUMENT_HARD_GATE_BLOCKED",
            "permitido": False,
            "operacao": "template_publish_activate",
            "modo": "enforce_controlled",
            "mensagem": "Operação bloqueada pelo hard gate documental controlado do V2.",
            "blockers": [
                {
                    "blocker_code": "template_not_bound",
                    "blocker_kind": "template",
                    "message": "Nao havia template operacional ativo vinculado antes desta publicacao.",
                    "source": "template_publish_shadow",
                },
                {
                    "blocker_code": "template_source_unknown",
                    "blocker_kind": "template",
                    "message": "A origem operacional do template permanecia indefinida antes da ativacao publicada.",
                    "source": "template_publish_shadow",
                },
            ],
        },
    }

    with SessionLocal() as banco:
        template = banco.get(TemplateLaudo, template_id)
        assert template is not None
        assert template.ativo is False
        assert template.status_template == "rascunho"

        registros_publicacao = (
            banco.query(RegistroAuditoriaEmpresa)
            .filter(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "template_publicado",
            )
            .all()
        )
        assert not any(int((item.payload_json or {}).get("template_id") or 0) == template_id for item in registros_publicacao)

        registro_bloqueio = (
            banco.query(RegistroAuditoriaEmpresa)
            .filter(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "template_publicacao_bloqueada_hard_gate",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
            .first()
        )
        assert registro_bloqueio is not None
        payload = registro_bloqueio.payload_json or {}
        assert int(payload.get("template_id") or 0) == template_id
        assert payload.get("operacao") == "template_publish_activate"
        assert payload.get("modo") == "enforce_controlled"
