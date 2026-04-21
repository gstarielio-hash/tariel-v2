from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.domains.chat.laudo import api_finalizar_relatorio
from app.shared.database import (
    Laudo,
    MensagemLaudo,
    RegistroAuditoriaEmpresa,
    StatusRevisao,
    TemplateLaudo,
    TipoMensagem,
    Usuario,
)
from app.v2.document import (
    clear_document_hard_gate_metrics_for_tests,
    get_document_hard_gate_operational_summary,
)
from tests.regras_rotas_criticas_support import _criar_laudo, _login_revisor, _salvar_pdf_temporario_teste


def _build_finalize_request(laudo_id: int) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": f"/app/api/laudo/{laudo_id}/finalizar",
            "headers": [(b"x-csrf-token", b"csrf-hard-gate")],
            "query_string": b"",
            "session": {
                "csrf_token_inspetor": "csrf-hard-gate",
                "laudo_ativo_id": int(laudo_id),
                "estado_relatorio": "relatorio_ativo",
            },
            "state": {},
            "client": ("testclient", 50003),
        }
    )


def _preparar_laudo_finalizavel(
    banco,
    *,
    empresa_id: int,
    usuario_id: int,
    tipo_template: str = "padrao",
    com_template_ativo: bool = False,
) -> int:
    laudo_id = _criar_laudo(
        banco,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        status_revisao=StatusRevisao.RASCUNHO.value,
        tipo_template=tipo_template,
    )
    laudo = banco.get(Laudo, laudo_id)
    assert laudo is not None
    laudo.primeira_mensagem = "Inspeção inicial em equipamento crítico."
    banco.add_all(
        [
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="Foram coletadas evidências suficientes para o laudo.",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="[imagem]",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer preliminar com apoio documental.",
            ),
        ]
    )
    if com_template_ativo:
        banco.add(
            TemplateLaudo(
                empresa_id=empresa_id,
                criado_por_id=usuario_id,
                nome="Template Ativo",
                codigo_template=tipo_template,
                versao=1,
                ativo=True,
                base_recomendada_fixa=False,
                modo_editor="legado_pdf",
                status_template="ativo",
                arquivo_pdf_base=_salvar_pdf_temporario_teste("hard_gate"),
                mapeamento_campos_json={},
                documento_editor_json=None,
                assets_json=[],
                estilo_json={},
                observacoes=None,
            )
        )
    banco.commit()
    return laudo_id


def _criar_template_publicavel(
    banco,
    *,
    empresa_id: int,
    usuario_id: int,
    codigo_template: str,
    versao: int,
    ativo: bool,
    status_template: str,
) -> int:
    template = TemplateLaudo(
        empresa_id=empresa_id,
        criado_por_id=usuario_id,
        nome=f"Template {codigo_template} v{versao}",
        codigo_template=codigo_template,
        versao=versao,
        ativo=ativo,
        base_recomendada_fixa=False,
        modo_editor="legado_pdf",
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


def test_hard_gate_shadow_only_nao_bloqueia_finalizacao(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo_id = _preparar_laudo_finalizavel(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            com_template_ativo=False,
        )

        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", raising=False)
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize")

        response = asyncio.run(
            api_finalizar_relatorio(
                laudo_id=laudo_id,
                request=_build_finalize_request(laudo_id),
                usuario=usuario,
                banco=banco,
            )
        )

        assert response.status_code == 200
        banco.refresh(banco.get(Laudo, laudo_id))
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["evaluations"] >= 1
    assert summary["totals"]["would_block"] >= 1
    assert summary["totals"]["did_block"] == 0
    assert summary["totals"]["shadow_only"] >= 1


def test_hard_gate_enforce_bloqueia_finalizacao_no_tenant_allowlisted(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo_id = _preparar_laudo_finalizavel(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            com_template_ativo=False,
        )

        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                api_finalizar_relatorio(
                    laudo_id=laudo_id,
                    request=_build_finalize_request(laudo_id),
                    usuario=usuario,
                    banco=banco,
                )
            )

        assert exc_info.value.status_code == 422
        detalhe = exc_info.value.detail
        assert detalhe["codigo"] == "DOCUMENT_HARD_GATE_BLOCKED"
        assert detalhe["operacao"] == "report_finalize"
        assert detalhe["modo"] == "enforce_controlled"
        blocker_codes = {item["blocker_code"] for item in detalhe["blockers"]}
        assert "template_not_bound" in blocker_codes or "template_source_unknown" in blocker_codes

        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.RASCUNHO.value

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["did_block"] >= 1
    assert summary["totals"]["enforce_controlled"] >= 1


def test_hard_gate_enforce_nao_bloqueia_tenant_fora_da_allowlist(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_b"])
        assert usuario is not None
        laudo_id = _preparar_laudo_finalizavel(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            com_template_ativo=False,
        )

        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize")

        response = asyncio.run(
            api_finalizar_relatorio(
                laudo_id=laudo_id,
                request=_build_finalize_request(laudo_id),
                usuario=usuario,
                banco=banco,
            )
        )

        assert response.status_code == 200
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value


def test_hard_gate_enforce_permita_finalizacao_quando_nao_ha_blockers(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo_id = _preparar_laudo_finalizavel(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            com_template_ativo=True,
        )

        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize")

        response = asyncio.run(
            api_finalizar_relatorio(
                laudo_id=laudo_id,
                request=_build_finalize_request(laudo_id),
                usuario=usuario,
                banco=banco,
            )
        )

        assert response.status_code == 200
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value


def test_hard_gate_enforce_bloqueia_template_publish_sem_alterar_estado_ativo(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()

    with SessionLocal() as banco:
        template_id = _criar_template_publicavel(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["revisor_a"],
            codigo_template="template_publish_enforce_gate",
            versao=2,
            ativo=False,
            status_template="rascunho",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "template_publish_activate")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES", "template_publish_enforce_gate")

    csrf = _login_revisor(client, "revisor@empresa-a.test")
    response = client.post(
        f"/revisao/api/templates-laudo/{template_id}/publicar",
        headers={"X-CSRF-Token": csrf},
        data={"csrf_token": csrf},
    )

    assert response.status_code == 422
    detail = response.json()
    assert detail["ok"] is False
    assert detail["template_id"] == template_id
    assert detail["status"] == "bloqueado"
    assert detail["error"]["codigo"] == "DOCUMENT_HARD_GATE_BLOCKED"
    assert detail["error"]["operacao"] == "template_publish_activate"
    assert detail["error"]["modo"] == "enforce_controlled"

    with SessionLocal() as banco:
        template = banco.get(TemplateLaudo, template_id)
        assert template is not None
        assert template.ativo is False
        assert template.status_template == "rascunho"

        registro_publicacao = (
            banco.query(RegistroAuditoriaEmpresa)
            .filter(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "template_publicado",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
            .first()
        )
        if registro_publicacao is not None:
            assert int((registro_publicacao.payload_json or {}).get("template_id") or 0) != template_id

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
        assert int((registro_bloqueio.payload_json or {}).get("template_id") or 0) == template_id

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["did_block"] >= 1
    assert summary["totals"]["enforce_controlled"] >= 1
    assert any(
        item["operation_kind"] == "template_publish_activate"
        and item["did_block"] >= 1
        and item["enforce_controlled"] >= 1
        for item in summary["by_operation_kind"]
    )
