from __future__ import annotations

import asyncio
import json
import os
import pathlib

from starlette.requests import Request

from app.domains.revisor.template_publish_shadow import evaluate_template_publish_activate_shadow
from app.domains.revisor.templates_laudo_management_routes import (
    publicar_template_editor_laudo,
    publicar_template_laudo,
)
from app.shared.database import RegistroAuditoriaEmpresa, TemplateLaudo, Usuario
from app.v2.document import clear_document_hard_gate_metrics_for_tests, get_document_hard_gate_operational_summary
from app.v2.document.hard_gate_evidence import (
    clear_document_hard_gate_durable_evidence_for_tests,
    get_document_hard_gate_durable_summary,
    load_document_hard_gate_durable_entries,
)
from nucleo.template_editor_word import MODO_EDITOR_RICO
from tests.regras_rotas_criticas_support import _login_revisor, _salvar_pdf_temporario_teste

WEB_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _build_publish_request(path: str, csrf: str, *, remote_host: str = "testclient") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"x-csrf-token", csrf.encode())],
            "query_string": b"",
            "session": {"csrf_token_revisor": csrf},
            "state": {},
            "client": (remote_host, 50130),
        }
    )


def _criar_template(
    banco,
    *,
    empresa_id: int,
    criado_por_id: int,
    codigo_template: str,
    versao: int,
    ativo: bool,
    status_template: str,
    modo_editor: str = "legado_pdf",
) -> int:
    template = TemplateLaudo(
        empresa_id=empresa_id,
        criado_por_id=criado_por_id,
        nome=f"Template {codigo_template} v{versao}",
        codigo_template=codigo_template,
        versao=versao,
        ativo=ativo,
        base_recomendada_fixa=False,
        modo_editor=modo_editor,
        status_template=status_template,
        arquivo_pdf_base=_salvar_pdf_temporario_teste(f"{codigo_template}_{versao}"),
        mapeamento_campos_json={},
        documento_editor_json=None,
        assets_json=[],
        estilo_json={},
        observacoes=None,
    )
    banco.add(template)
    banco.commit()
    banco.refresh(template)
    return int(template.id)


def _summary_blocker(summary: dict, blocker_code: str) -> dict:
    for item in summary["by_blocker_code"]:
        if item["blocker_code"] == blocker_code:
            return item
    raise AssertionError(f"Blocker {blocker_code} nao encontrado no summary.")


def test_hard_gate_template_publish_activate_entra_em_enforce_quando_flag_permitir(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = "csrf-template-publish-shadow-direct"

    with SessionLocal() as banco:
        template_id = _criar_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="template_gap_10i_direct",
            versao=2,
            ativo=False,
            status_template="rascunho",
        )
        usuario = banco.get(Usuario, ids["revisor_a"])
        template = banco.get(TemplateLaudo, template_id)
        assert usuario is not None
        assert template is not None

        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "template_publish_activate")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES", "template_gap_10i_direct")

        _, hard_gate_result = evaluate_template_publish_activate_shadow(
            request=_build_publish_request(f"/revisao/api/templates-laudo/{template_id}/publicar", csrf),
            usuario=usuario,
            template=template,
            route_name="publicar_template_laudo",
            has_active_template_before_publish=False,
        )

    assert hard_gate_result is not None
    decision = hard_gate_result.decision
    assert decision.operation_kind == "template_publish_activate"
    assert decision.route_name == "publicar_template_laudo"
    assert decision.route_path == f"/revisao/api/templates-laudo/{template_id}/publicar"
    assert decision.source_channel == "review_templates_api"
    assert decision.mode == "enforce_controlled"
    assert decision.shadow_only is False
    assert decision.enforce_enabled is True
    assert decision.would_block is True
    assert decision.did_block is True
    assert decision.document_readiness["template_id"] == template_id
    assert all(item.enforcement_scope == "enforce" for item in decision.blockers)


def test_template_publish_activate_enforce_bloqueia_publicacao_e_registra_summary(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    evidence_root = tmp_path / "durable_evidence"
    clear_document_hard_gate_metrics_for_tests()
    clear_document_hard_gate_durable_evidence_for_tests(root=evidence_root)

    with SessionLocal() as banco:
        template_id = _criar_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="template_gap_10i_http",
            versao=2,
            ativo=False,
            status_template="rascunho",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "template_publish_activate")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES", "template_gap_10i_http")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR", str(evidence_root))

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        resposta = asyncio.run(
            publicar_template_laudo(
                template_id=template_id,
                request=_build_publish_request(
                    f"/revisao/api/templates-laudo/{template_id}/publicar",
                    "csrf-template-gap-http",
                ),
                csrf_token="csrf-template-gap-http",
                usuario=usuario,
                banco=banco,
            )
        )
        banco.commit()

        assert resposta.status_code == 422
        assert json.loads(resposta.body) == {
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

        template = banco.get(TemplateLaudo, template_id)
        assert template is not None
        assert template.ativo is False
        assert template.status_template == "rascunho"
        auditoria = (
            banco.query(RegistroAuditoriaEmpresa)
            .filter(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "template_publicacao_bloqueada_hard_gate",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
            .first()
        )
        assert auditoria is not None

    summary = get_document_hard_gate_operational_summary()
    assert any(
        item["operation_kind"] == "template_publish_activate"
        and item["evaluations"] >= 1
        and item["did_block"] >= 1
        and item["enforce_controlled"] >= 1
        for item in summary["by_operation_kind"]
    )
    assert summary["totals"]["would_block"] >= 1
    assert summary["totals"]["did_block"] >= 1
    assert _summary_blocker(summary, "template_not_bound")["enforce"] >= 1
    assert _summary_blocker(summary, "template_source_unknown")["enforce"] >= 1

    recent_decision = summary["recent_results"][0]["decision"]
    assert recent_decision["operation_kind"] == "template_publish_activate"
    assert recent_decision["route_name"] == "publicar_template_laudo"
    assert recent_decision["route_path"] == f"/revisao/api/templates-laudo/{template_id}/publicar"
    assert recent_decision["mode"] == "enforce_controlled"
    assert recent_decision["did_block"] is True
    assert recent_decision["document_readiness"]["template_id"] == template_id

    durable_summary = get_document_hard_gate_durable_summary(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_summary["totals"]["evaluations"] >= 1
    assert durable_summary["totals"]["would_block"] >= 1
    assert durable_summary["totals"]["did_block"] >= 1

    durable_entries = load_document_hard_gate_durable_entries(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_entries
    assert durable_entries[0]["target"]["template_id"] == template_id
    assert durable_entries[0]["functional_outcome"] == "template_publish_blocked_by_hard_gate"
    assert durable_entries[0]["response"]["status_code"] == 422
    assert durable_entries[0]["response"]["audit_generated"] is True


def test_template_publish_activate_editor_route_com_template_ativo_reduz_blockers_sem_bloquear(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    evidence_root = tmp_path / "durable_evidence_editor"
    clear_document_hard_gate_metrics_for_tests()
    clear_document_hard_gate_durable_evidence_for_tests(root=evidence_root)

    with SessionLocal() as banco:
        template_ativo_id = _criar_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="template_ok_10i_editor",
            versao=1,
            ativo=True,
            status_template="ativo",
        )
        template_editor_id = _criar_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="template_ok_10i_editor",
            versao=2,
            ativo=False,
            status_template="em_teste",
            modo_editor=MODO_EDITOR_RICO,
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "template_publish_activate")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES", "template_ok_10i_editor")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR", str(evidence_root))

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        resposta = asyncio.run(
            publicar_template_editor_laudo(
                template_id=template_editor_id,
                request=_build_publish_request(
                    f"/revisao/api/templates-laudo/editor/{template_editor_id}/publicar",
                    "csrf-template-editor-ok",
                ),
                csrf_token="csrf-template-editor-ok",
                usuario=usuario,
                banco=banco,
            )
        )
        banco.commit()

        assert resposta == {"ok": True, "template_id": template_editor_id, "status": "publicado"}

        template_ativo = banco.get(TemplateLaudo, template_ativo_id)
        template_editor = banco.get(TemplateLaudo, template_editor_id)
        assert template_ativo is not None
        assert template_editor is not None
        assert template_ativo.ativo is False
        assert template_ativo.status_template == "legado"
        assert template_editor.ativo is True
        assert template_editor.status_template == "ativo"
        assert str(template_editor.arquivo_pdf_base or "").strip() != ""

    summary = get_document_hard_gate_operational_summary()
    assert any(
        item["operation_kind"] == "template_publish_activate"
        and item["evaluations"] >= 1
        and item["would_block"] == 0
        and item["did_block"] == 0
        and item["enforce_controlled"] >= 1
        for item in summary["by_operation_kind"]
    )

    recent_decision = summary["recent_results"][0]["decision"]
    assert recent_decision["operation_kind"] == "template_publish_activate"
    assert recent_decision["route_name"] == "publicar_template_editor_laudo"
    assert recent_decision["route_path"] == f"/revisao/api/templates-laudo/editor/{template_editor_id}/publicar"
    assert recent_decision["mode"] == "enforce_controlled"
    assert recent_decision["would_block"] is False
    assert recent_decision["blockers"] == []

    durable_summary = get_document_hard_gate_durable_summary(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_summary["totals"]["evaluations"] >= 1
    assert durable_summary["totals"]["would_block"] == 0
    assert durable_summary["totals"]["did_block"] == 0
    assert durable_summary["totals"]["enforce_controlled"] >= 1

    durable_entries = load_document_hard_gate_durable_entries(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_entries
    assert durable_entries[0]["target"]["template_id"] == template_editor_id
    assert durable_entries[0]["functional_outcome"] == "template_publish_completed"
    assert durable_entries[0]["blockers"] == []


def test_template_publish_activate_http_legacy_route_bloqueia_em_enforce_e_persiste_evidencia(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    evidence_root = tmp_path / "durable_evidence_http_legacy"
    clear_document_hard_gate_metrics_for_tests()
    clear_document_hard_gate_durable_evidence_for_tests(root=evidence_root)

    with SessionLocal() as banco:
        template_id = _criar_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="template_gap_10i_http_client",
            versao=2,
            ativo=False,
            status_template="rascunho",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "template_publish_activate")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES", "template_gap_10i_http_client")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR", str(evidence_root))

    cwd_original = os.getcwd()
    os.chdir(WEB_ROOT)
    try:
        csrf = _login_revisor(client, "revisor@empresa-a.test")
        resposta = client.post(
            f"/revisao/api/templates-laudo/{template_id}/publicar",
            headers={"X-CSRF-Token": csrf},
            data={"csrf_token": csrf},
        )
    finally:
        os.chdir(cwd_original)

    assert resposta.status_code == 422
    assert resposta.json()["ok"] is False
    assert resposta.json()["template_id"] == template_id
    assert resposta.json()["status"] == "bloqueado"
    assert resposta.json()["error"]["codigo"] == "DOCUMENT_HARD_GATE_BLOCKED"

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["evaluations"] >= 1
    assert summary["totals"]["would_block"] >= 1
    assert summary["totals"]["did_block"] >= 1
    assert _summary_blocker(summary, "template_not_bound")["enforce"] >= 1
    assert _summary_blocker(summary, "template_source_unknown")["enforce"] >= 1

    recent_decision = summary["recent_results"][0]["decision"]
    assert recent_decision["route_name"] == "publicar_template_laudo"
    assert recent_decision["route_path"] == f"/revisao/api/templates-laudo/{template_id}/publicar"
    assert recent_decision["would_block"] is True
    assert recent_decision["mode"] == "enforce_controlled"
    assert recent_decision["did_block"] is True

    durable_summary = get_document_hard_gate_durable_summary(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_summary["totals"]["evaluations"] >= 1
    assert durable_summary["totals"]["would_block"] >= 1
    assert durable_summary["totals"]["did_block"] >= 1

    durable_entries = load_document_hard_gate_durable_entries(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_entries
    assert durable_entries[0]["target"]["template_id"] == template_id
    assert durable_entries[0]["functional_outcome"] == "template_publish_blocked_by_hard_gate"
    assert durable_entries[0]["response"]["status_code"] == 422
    assert durable_entries[0]["response"]["audit_generated"] is True


def test_template_publish_activate_http_editor_route_ok_preserva_publicacao_e_sem_blockers(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    evidence_root = tmp_path / "durable_evidence_http_editor"
    clear_document_hard_gate_metrics_for_tests()
    clear_document_hard_gate_durable_evidence_for_tests(root=evidence_root)

    with SessionLocal() as banco:
        _criar_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="template_ok_10i_http_client_editor",
            versao=1,
            ativo=True,
            status_template="ativo",
            modo_editor=MODO_EDITOR_RICO,
        )
        template_editor_id = _criar_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="template_ok_10i_http_client_editor",
            versao=2,
            ativo=False,
            status_template="em_teste",
            modo_editor=MODO_EDITOR_RICO,
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "template_publish_activate")
    monkeypatch.setenv(
        "TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES",
        "template_ok_10i_http_client_editor",
    )
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR", str(evidence_root))

    cwd_original = os.getcwd()
    os.chdir(WEB_ROOT)
    try:
        csrf = _login_revisor(client, "revisor@empresa-a.test")
        resposta = client.post(
            f"/revisao/api/templates-laudo/editor/{template_editor_id}/publicar",
            headers={"X-CSRF-Token": csrf},
            data={"csrf_token": csrf},
        )
    finally:
        os.chdir(cwd_original)

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True, "template_id": template_editor_id, "status": "publicado"}

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["evaluations"] >= 1
    assert summary["totals"]["did_block"] == 0
    assert summary["totals"]["enforce_controlled"] >= 1

    recent_decision = summary["recent_results"][0]["decision"]
    assert recent_decision["route_name"] == "publicar_template_editor_laudo"
    assert recent_decision["route_path"] == f"/revisao/api/templates-laudo/editor/{template_editor_id}/publicar"
    assert recent_decision["mode"] == "enforce_controlled"
    assert recent_decision["would_block"] is False
    assert recent_decision["blockers"] == []

    durable_summary = get_document_hard_gate_durable_summary(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_summary["totals"]["evaluations"] >= 1
    assert durable_summary["totals"]["would_block"] == 0
    assert durable_summary["totals"]["did_block"] == 0
    assert durable_summary["totals"]["enforce_controlled"] >= 1

    durable_entries = load_document_hard_gate_durable_entries(
        root=evidence_root,
        operation_kind="template_publish_activate",
    )
    assert durable_entries
    assert durable_entries[0]["target"]["template_id"] == template_editor_id
    assert durable_entries[0]["functional_outcome"] == "template_publish_completed"
    assert durable_entries[0]["blockers"] == []
