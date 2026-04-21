# ruff: noqa: E501
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

import app.shared.security as seguranca
import main
import app.domains.admin.routes as rotas_admin
import app.domains.admin.services as admin_services
import app.domains.chat.catalog_pdf_templates as catalog_pdf_templates
from app.core.paths import WEB_ROOT
from app.domains.admin.mfa import current_totp
import app.domains.chat.routes as rotas_inspetor
from app.domains.revisor.templates_laudo_support import resumir_operacao_templates_mesa
from app.shared.database import (
    AprendizadoVisualIa,
    AnexoMesa,
    ApprovedCaseSnapshot,
    EmissaoOficialLaudo,
    Laudo,
    LaudoRevisao,
    MensagemLaudo,
    NivelAcesso,
    RegistroAuditoriaEmpresa,
    SessaoAtiva,
    SignatarioGovernadoLaudo,
    StatusRevisao,
    TemplateLaudo,
    TipoMensagem,
    Usuario,
)
from app.shared.security import verificar_senha
from tests.regras_rotas_criticas_support import (
    ADMIN_TOTP_SECRET,
    SENHA_PADRAO,
    SENHA_HASH_PADRAO,
    _criar_laudo,
    _criar_template_ativo,
    _csrf_pagina,
    _extrair_csrf,
    _imagem_png_bytes_teste,
    _imagem_png_data_uri_teste,
    _login_admin,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
    _pdf_base_bytes_teste,
    _salvar_pdf_temporario_teste,
)


def test_404_em_rotas_api_app_retorna_json_sem_redirect(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.get("/app/api/rota-que-nao-existe", follow_redirects=False)

    assert resposta.status_code == 404
    assert "application/json" in (resposta.headers.get("content-type", "").lower())
    assert resposta.json()["detail"] == "Recurso não encontrado."


def test_404_em_rotas_api_revisao_retorna_json_sem_redirect(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.get("/revisao/api/rota-que-nao-existe", follow_redirects=False)

    assert resposta.status_code == 404
    assert "application/json" in (resposta.headers.get("content-type", "").lower())
    assert resposta.json()["detail"] == "Recurso não encontrado."


def test_revisor_login_funciona_e_painel_abre(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_revisor(client, "revisor@empresa-a.test")
    painel = client.get("/revisao/painel")

    assert painel.status_code == 200


def test_revisor_painel_exibe_resumo_operacional_templates(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        banco.add_all(
            [
                TemplateLaudo(
                    empresa_id=ids["empresa_a"],
                    criado_por_id=ids["revisor_a"],
                    nome="Template foco ativo",
                    codigo_template="mesa_focus_ativo",
                    versao=1,
                    ativo=True,
                    status_template="ativo",
                    arquivo_pdf_base=_salvar_pdf_temporario_teste("mesa_focus_ativo"),
                    mapeamento_campos_json={},
                    assets_json=[],
                ),
                TemplateLaudo(
                    empresa_id=ids["empresa_a"],
                    criado_por_id=ids["revisor_a"],
                    nome="Template foco gap",
                    codigo_template="mesa_focus_gap",
                    versao=3,
                    ativo=False,
                    status_template="em_teste",
                    base_recomendada_fixa=True,
                    arquivo_pdf_base=_salvar_pdf_temporario_teste("mesa_focus_gap"),
                    mapeamento_campos_json={},
                    assets_json=[],
                ),
            ]
        )
        banco.commit()
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
            tipo_template="mesa_focus_gap",
        )
        resumo = resumir_operacao_templates_mesa(
            banco,
            empresa_id=ids["empresa_a"],
        )

    assert resumo["total_codigos"] == 2
    assert resumo["total_templates"] == 2
    assert resumo["total_ativos"] == 1
    assert resumo["total_em_teste"] == 1
    assert resumo["total_codigos_em_operacao_sem_ativo"] == 1
    assert resumo["total_bases_manuais"] == 1

    _login_revisor(client, "revisor@empresa-a.test")
    painel = client.get("/revisao/painel")

    assert painel.status_code == 200
    assert "Biblioteca no fluxo operacional" in painel.text
    assert "Abrir vitrine de modelos" in painel.text
    assert "aguardando publicacao do modelo" in painel.text


def test_revisor_tela_templates_laudo_abre(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.get("/revisao/templates-laudo")

    assert resposta.status_code == 200
    assert "Vitrine de modelos" in resposta.text
    assert "Documento base" in resposta.text
    assert "Estes pontos recebem os dados do caso" in resposta.text
    assert "Escolha a base da mesa" in resposta.text
    assert 'name="csrf-token"' in resposta.text


def test_revisor_tela_editor_word_templates_abre(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.get("/revisao/templates-laudo/editor")

    assert resposta.status_code == 200
    assert "Editor visual" in resposta.text
    assert "Editor da mesa" in resposta.text
    assert "Criar modelo (A4)" in resposta.text


def test_revisor_upload_template_laudo_e_lista(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    mapeamento = {
        "pages": [
            {
                "page": 1,
                "fields": [
                    {
                        "key": "informacoes_gerais.responsavel_pela_inspecao",
                        "x": 12,
                        "y": 95,
                        "w": 90,
                        "h": 4.5,
                        "font_size": 8,
                    }
                ],
            }
        ]
    }

    resposta_upload = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Checklist CBMGO Padrão",
            "codigo_template": "cbmgo_cmar",
            "versao": "1",
            "mapeamento_campos_json": json.dumps(mapeamento),
        },
        files={
            "arquivo_base": ("cbmgo_base.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )

    assert resposta_upload.status_code == 201
    corpo_upload = resposta_upload.json()
    template_id = int(corpo_upload["id"])
    assert corpo_upload["codigo_template"] == "cbmgo_cmar"
    assert corpo_upload["versao"] == 1

    resposta_lista = client.get("/revisao/api/templates-laudo")
    assert resposta_lista.status_code == 200
    corpo_lista = resposta_lista.json()
    assert any(int(item["id"]) == template_id for item in corpo_lista["itens"])

    with SessionLocal() as banco:
        template = banco.get(TemplateLaudo, template_id)
        assert template is not None
        assert template.nome == "Checklist CBMGO Padrão"
        assert template.codigo_template == "cbmgo_cmar"
        assert template.arquivo_pdf_base.lower().endswith(".pdf")


def test_revisor_arquivo_base_template_laudo_retorna_pdf(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_upload = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template para baixar base",
            "codigo_template": "cbmgo_cmar",
            "versao": "4",
        },
        files={
            "arquivo_base": ("cbmgo_base.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_upload.status_code == 201
    template_id = int(resposta_upload.json()["id"])

    resposta_pdf_base = client.get(f"/revisao/api/templates-laudo/{template_id}/arquivo-base")

    assert resposta_pdf_base.status_code == 200
    assert "application/pdf" in (resposta_pdf_base.headers.get("content-type", "").lower())
    assert resposta_pdf_base.content.startswith(b"%PDF")


def test_revisor_preview_template_laudo_retorna_pdf(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_upload = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Checklist CBMGO Preview",
            "codigo_template": "cbmgo_cmar",
            "versao": "2",
        },
        files={
            "arquivo_base": ("cbmgo_base.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_upload.status_code == 201
    template_id = int(resposta_upload.json()["id"])

    payload_preview = {
        "dados_formulario": {
            "informacoes_gerais": {
                "responsavel_pela_inspecao": "Gabriel Santos",
                "data_inspecao": "09/03/2026",
                "local_inspecao": "Planta Norte",
            },
            "trrf_observacoes": "TRRF preliminar alinhado ao memorial.",
            "resumo_executivo": "Prévia de teste para validação da mesa.",
        }
    }

    resposta_preview = client.post(
        f"/revisao/api/templates-laudo/{template_id}/preview",
        headers={"X-CSRF-Token": csrf},
        json=payload_preview,
    )

    assert resposta_preview.status_code == 200
    assert "application/pdf" in (resposta_preview.headers.get("content-type", "").lower())
    assert resposta_preview.content.startswith(b"%PDF")

    with SessionLocal() as banco:
        template = banco.get(TemplateLaudo, template_id)
        assert template is not None
        assert template.mapeamento_campos_json is not None


def test_revisor_preview_template_laudo_promove_legado_fraco_para_preview_editor_rico(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")
    captured: dict[str, object] = {}

    with SessionLocal() as banco:
        template = TemplateLaudo(
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            nome="Template NR13 Legado Fraco",
            codigo_template="nr13_vaso_pressao",
            versao=4,
            ativo=True,
            status_template="ativo",
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            arquivo_pdf_base="/tmp/nr13_legado_fraco.pdf",
            mapeamento_campos_json={},
            documento_editor_json={},
            estilo_json={},
            assets_json=[],
            observacoes=None,
        )
        laudo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR 13",
            tipo_template="nr13",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            catalog_family_key="nr13_inspecao_vaso_pressao",
            dados_formulario={
                "identificacao": {"identificacao_do_vaso": "Vaso vertical VP-204"},
                "conclusao": {
                    "status": "ajuste",
                    "conclusao_tecnica": "Equipamento apto com acompanhamento.",
                },
            },
        )
        banco.add(template)
        banco.add(laudo)
        banco.flush()
        template_id = int(template.id)
        laudo_id = int(laudo.id)
        banco.commit()

    async def _fake_render_editor_rico(**kwargs):
        captured["documento_editor_json"] = kwargs["documento_editor_json"]
        captured["estilo_json"] = kwargs["estilo_json"]
        captured["dados_formulario"] = kwargs["dados_formulario"]
        return b"%PDF-1.4\n%mesa-rich-promoted\n"

    def _legacy_preview_should_not_run(**_kwargs):
        raise AssertionError("preview legado nao deveria ser usado")

    monkeypatch.setattr(
        "app.domains.revisor.templates_laudo.gerar_pdf_editor_rico_bytes",
        _fake_render_editor_rico,
    )
    monkeypatch.setattr(
        "app.domains.revisor.templates_laudo.gerar_preview_pdf_template",
        _legacy_preview_should_not_run,
    )

    resposta_preview = client.post(
        f"/revisao/api/templates-laudo/{template_id}/preview",
        headers={"X-CSRF-Token": csrf},
        json={"laudo_id": laudo_id},
    )

    assert resposta_preview.status_code == 200
    assert "application/pdf" in (resposta_preview.headers.get("content-type", "").lower())
    assert resposta_preview.content.startswith(b"%PDF")
    assert captured["dados_formulario"]["family_key"] == "nr13_inspecao_vaso_pressao"
    serialized_document = json.dumps(captured["documento_editor_json"], ensure_ascii=False)
    assert "Resumo Executivo" in serialized_document
    assert "Conclusao Tecnica" in serialized_document
    style = captured["estilo_json"]
    assert isinstance(style, dict)
    assert "Tariel" in str(style.get("cabecalho_texto") or "")
    assert "Revisao" in str(style.get("rodape_texto") or "")


def test_revisor_publicar_template_desativa_ativo_anterior(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_v1 = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template CBMGO v1",
            "codigo_template": "cbmgo_cmar",
            "versao": "10",
            "ativo": "true",
        },
        files={
            "arquivo_base": ("cbmgo_v1.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_v1.status_code == 201
    id_v1 = int(resposta_v1.json()["id"])

    resposta_v2 = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template CBMGO v2",
            "codigo_template": "cbmgo_cmar",
            "versao": "11",
        },
        files={
            "arquivo_base": ("cbmgo_v2.pdf", _pdf_base_bytes_teste(), "application/pdf"),
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
    assert resposta_publicar.json().get("status") == "publicado"

    with SessionLocal() as banco:
        template_v1 = banco.get(TemplateLaudo, id_v1)
        template_v2 = banco.get(TemplateLaudo, id_v2)
        assert template_v1 is not None
        assert template_v2 is not None
        assert template_v1.ativo is False
        assert template_v2.ativo is True


def test_revisor_lote_status_templates_atualiza_ciclo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_v1 = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template lote v1",
            "codigo_template": "lote_status",
            "versao": "1",
            "ativo": "true",
        },
        files={"arquivo_base": ("lote_v1.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_v1.status_code == 201
    id_v1 = int(resposta_v1.json()["id"])

    resposta_v2 = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template lote v2",
            "codigo_template": "lote_status",
            "versao": "2",
        },
        files={"arquivo_base": ("lote_v2.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_v2.status_code == 201
    id_v2 = int(resposta_v2.json()["id"])

    resposta_lote = client.post(
        "/revisao/api/templates-laudo/lote/status",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={"template_ids": [id_v1, id_v2], "status_template": "em_teste"},
    )

    assert resposta_lote.status_code == 200
    corpo = resposta_lote.json()
    assert corpo["total"] == 2
    assert corpo["status_template"] == "em_teste"

    with SessionLocal() as banco:
        template_v1 = banco.get(TemplateLaudo, id_v1)
        template_v2 = banco.get(TemplateLaudo, id_v2)
        assert template_v1 is not None
        assert template_v2 is not None
        assert template_v1.status_template == "em_teste"
        assert template_v2.status_template == "em_teste"
        assert template_v1.ativo is False
        assert template_v2.ativo is False


def test_revisor_lote_excluir_templates_remove_selecao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    ids_templates: list[int] = []
    for versao in (1, 2):
        resposta = client.post(
            "/revisao/api/templates-laudo/upload",
            headers={"X-CSRF-Token": csrf},
            data={
                "nome": f"Template excluir lote v{versao}",
                "codigo_template": "lote_excluir",
                "versao": str(versao),
            },
            files={"arquivo_base": (f"lote_delete_{versao}.pdf", _pdf_base_bytes_teste(), "application/pdf")},
        )
        assert resposta.status_code == 201
        ids_templates.append(int(resposta.json()["id"]))

    resposta_lote = client.post(
        "/revisao/api/templates-laudo/lote/excluir",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={"template_ids": ids_templates},
    )

    assert resposta_lote.status_code == 200
    corpo = resposta_lote.json()
    assert corpo["total"] == 2
    assert corpo["status"] == "excluido"

    with SessionLocal() as banco:
        assert all(banco.get(TemplateLaudo, item_id) is None for item_id in ids_templates)


def test_revisor_criar_template_editor_rico_e_detalhar(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_criar = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={
            "X-CSRF-Token": csrf,
            "Content-Type": "application/json",
        },
        json={
            "nome": "Template Word Tariel.ia",
            "codigo_template": "rti_word",
            "versao": 1,
            "origem_modo": "a4",
        },
    )

    assert resposta_criar.status_code == 201
    corpo_criar = resposta_criar.json()
    template_id = int(corpo_criar["id"])
    assert corpo_criar["modo_editor"] == "editor_rico"
    assert corpo_criar["is_editor_rico"] is True

    resposta_editor = client.get(f"/revisao/api/templates-laudo/editor/{template_id}")
    assert resposta_editor.status_code == 200
    corpo_editor = resposta_editor.json()
    assert int(corpo_editor["id"]) == template_id
    assert corpo_editor["modo_editor"] == "editor_rico"
    assert isinstance(corpo_editor.get("documento_editor_json"), dict)
    assert isinstance(corpo_editor.get("estilo_json"), dict)

    resposta_lista = client.get("/revisao/api/templates-laudo")
    assert resposta_lista.status_code == 200
    itens = resposta_lista.json().get("itens", [])
    encontrado = next((it for it in itens if int(it["id"]) == template_id), None)
    assert encontrado is not None
    assert encontrado["is_editor_rico"] is True


def test_revisor_lista_templates_expoe_grupo_e_base_recomendada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_ativo = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Grupo ativo v1",
            "codigo_template": "grupo_versionado",
            "versao": "1",
            "ativo": "true",
        },
        files={"arquivo_base": ("grupo_ativo_v1.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_ativo.status_code == 201
    id_ativo = int(resposta_ativo.json()["id"])

    resposta_word = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Grupo ativo v2 word",
            "codigo_template": "grupo_versionado",
            "versao": 2,
            "origem_modo": "a4",
        },
    )
    assert resposta_word.status_code == 201
    id_word = int(resposta_word.json()["id"])

    resposta_teste = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Grupo ativo v3 teste",
            "codigo_template": "grupo_versionado",
            "versao": "3",
            "status_template": "em_teste",
        },
        files={"arquivo_base": ("grupo_teste_v3.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_teste.status_code == 201
    id_teste = int(resposta_teste.json()["id"])

    resposta_sem_ativo_teste = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Grupo sem ativo v1 teste",
            "codigo_template": "grupo_sem_ativo",
            "versao": "1",
            "status_template": "em_teste",
        },
        files={"arquivo_base": ("grupo_sem_ativo_v1.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_sem_ativo_teste.status_code == 201
    id_sem_ativo_teste = int(resposta_sem_ativo_teste.json()["id"])

    resposta_sem_ativo_rascunho = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Grupo sem ativo v2 rascunho",
            "codigo_template": "grupo_sem_ativo",
            "versao": "2",
            "status_template": "rascunho",
        },
        files={"arquivo_base": ("grupo_sem_ativo_v2.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_sem_ativo_rascunho.status_code == 201
    id_sem_ativo_rascunho = int(resposta_sem_ativo_rascunho.json()["id"])

    resposta_lista = client.get("/revisao/api/templates-laudo")
    assert resposta_lista.status_code == 200
    itens = resposta_lista.json().get("itens", [])

    grupo_principal = [item for item in itens if item["codigo_template"] == "grupo_versionado"]
    assert len(grupo_principal) == 3
    ativo = next(item for item in grupo_principal if int(item["id"]) == id_ativo)
    word = next(item for item in grupo_principal if int(item["id"]) == id_word)
    teste = next(item for item in grupo_principal if int(item["id"]) == id_teste)
    assert ativo["is_base_recomendada"] is True
    assert ativo["base_recomendada_motivo"] == "Versão ativa em operação"
    assert ativo["grupo_total_versoes"] == 3
    assert ativo["grupo_total_word"] == 1
    assert ativo["grupo_total_pdf"] == 2
    assert ativo["grupo_versao_mais_recente"] == 3
    assert ativo["grupo_template_ativo_id"] == id_ativo
    assert ativo["grupo_base_recomendada_id"] == id_ativo
    assert ativo["grupo_versoes_disponiveis"] == [3, 2, 1]
    assert word["grupo_base_recomendada_id"] == id_ativo
    assert teste["grupo_base_recomendada_id"] == id_ativo

    grupo_sem_ativo = [item for item in itens if item["codigo_template"] == "grupo_sem_ativo"]
    assert len(grupo_sem_ativo) == 2
    sem_ativo_teste = next(item for item in grupo_sem_ativo if int(item["id"]) == id_sem_ativo_teste)
    sem_ativo_rascunho = next(item for item in grupo_sem_ativo if int(item["id"]) == id_sem_ativo_rascunho)
    assert sem_ativo_teste["is_base_recomendada"] is True
    assert sem_ativo_teste["base_recomendada_motivo"] == "Versão em teste mais madura"
    assert sem_ativo_teste["grupo_base_recomendada_id"] == id_sem_ativo_teste
    assert sem_ativo_rascunho["grupo_base_recomendada_id"] == id_sem_ativo_teste


def test_revisor_promove_base_recomendada_manual_no_grupo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_ativo = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Base operacao v1",
            "codigo_template": "grupo_promocao_base",
            "versao": "1",
            "ativo": "true",
        },
        files={"arquivo_base": ("grupo_promocao_base_v1.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_ativo.status_code == 201
    id_ativo = int(resposta_ativo.json()["id"])

    resposta_word = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Base editorial v2",
            "codigo_template": "grupo_promocao_base",
            "versao": 2,
            "origem_modo": "a4",
        },
    )
    assert resposta_word.status_code == 201
    id_word = int(resposta_word.json()["id"])

    resposta_promover = client.post(
        f"/revisao/api/templates-laudo/{id_word}/base-recomendada",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_promover.status_code == 200
    corpo_promover = resposta_promover.json()
    assert corpo_promover["status"] == "promovido"
    assert corpo_promover["base_recomendada_fixa"] is True
    assert corpo_promover["base_recomendada_origem"] == "manual"

    resposta_lista = client.get("/revisao/api/templates-laudo")
    assert resposta_lista.status_code == 200
    itens = resposta_lista.json().get("itens", [])

    grupo = [item for item in itens if item["codigo_template"] == "grupo_promocao_base"]
    assert len(grupo) == 2
    ativo = next(item for item in grupo if int(item["id"]) == id_ativo)
    word = next(item for item in grupo if int(item["id"]) == id_word)
    assert ativo["ativo"] is True
    assert ativo["grupo_base_recomendada_id"] == id_word
    assert ativo["grupo_base_recomendada_origem"] == "manual"
    assert ativo["is_base_recomendada"] is False
    assert word["is_base_recomendada"] is True
    assert word["base_recomendada_fixa"] is True
    assert word["base_recomendada_origem"] == "manual"
    assert word["base_recomendada_motivo"] == "Base promovida manualmente pela mesa"
    assert word["grupo_base_recomendada_id"] == id_word

    resposta_auditoria = client.get("/revisao/api/templates-laudo/auditoria")
    assert resposta_auditoria.status_code == 200
    itens_auditoria = resposta_auditoria.json().get("itens", [])
    promotoria = next((item for item in itens_auditoria if item["acao"] == "template_base_recomendada_promovida"), None)
    assert promotoria is not None
    assert promotoria["payload"]["template_recomendado"]["template_id"] == id_word
    assert promotoria["payload"]["base_anterior"]["template_id"] == id_ativo


def test_revisor_biblioteca_templates_registra_auditoria_operacional(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    template_ids: list[int] = []
    for versao in (1, 2, 3, 4):
        resposta = client.post(
            "/revisao/api/templates-laudo/editor",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            json={
                "nome": f"Template auditoria v{versao}",
                "codigo_template": "auditoria_templates",
                "versao": versao,
                "origem_modo": "a4",
            },
        )
        assert resposta.status_code == 201
        template_ids.append(int(resposta.json()["id"]))

    id_publicar, id_lote_a, id_lote_b, id_excluir = template_ids

    resposta_publicar = client.post(
        f"/revisao/api/templates-laudo/editor/{id_publicar}/publicar",
        headers={"X-CSRF-Token": csrf},
        data={"csrf_token": csrf},
    )
    assert resposta_publicar.status_code == 200

    resposta_lote = client.post(
        "/revisao/api/templates-laudo/lote/status",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "template_ids": [id_lote_a, id_lote_b],
            "status_template": "em_teste",
        },
    )
    assert resposta_lote.status_code == 200

    resposta_clonar = client.post(
        f"/revisao/api/templates-laudo/{id_lote_a}/clonar",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_clonar.status_code == 201
    clone_id = int(resposta_clonar.json()["id"])

    resposta_excluir_lote = client.post(
        "/revisao/api/templates-laudo/lote/excluir",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={"template_ids": [id_excluir]},
    )
    assert resposta_excluir_lote.status_code == 200

    resposta_auditoria = client.get("/revisao/api/templates-laudo/auditoria")
    assert resposta_auditoria.status_code == 200
    itens = resposta_auditoria.json()["itens"]
    acoes = {item["acao"] for item in itens}
    assert {
        "template_criado_word",
        "template_publicado",
        "template_status_lote_alterado",
        "template_clonado",
        "template_excluido_lote",
    }.issubset(acoes)
    assert all(item["portal"] == "revisao_templates" for item in itens)
    assert any(item["ator_usuario_id"] == ids["revisor_a"] for item in itens)

    registro_publicado = next(item for item in itens if item["acao"] == "template_publicado")
    assert int(registro_publicado["payload"]["template_id"]) == id_publicar
    assert registro_publicado["payload"]["status_template"] == "ativo"

    registro_lote = next(item for item in itens if item["acao"] == "template_status_lote_alterado")
    assert registro_lote["payload"]["status_destino"] == "em_teste"
    assert registro_lote["payload"]["total"] == 2
    assert {int(valor) for valor in registro_lote["payload"]["template_ids"]} == {id_lote_a, id_lote_b}

    registro_clone = next(item for item in itens if item["acao"] == "template_clonado")
    assert int(registro_clone["payload"]["template_origem"]["template_id"]) == id_lote_a
    assert int(registro_clone["payload"]["template_clone"]["template_id"]) == clone_id

    registro_exclusao = next(item for item in itens if item["acao"] == "template_excluido_lote")
    assert registro_exclusao["payload"]["total"] == 1
    assert registro_exclusao["payload"]["templates"][0]["template_id"] == id_excluir

    with SessionLocal() as banco:
        registros = list(
            banco.scalars(
                select(RegistroAuditoriaEmpresa).where(RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"]).order_by(RegistroAuditoriaEmpresa.id.desc())
            ).all()
        )
        assert registros
        assert any(item.portal == "revisao_templates" for item in registros)
        assert {item.acao for item in registros if item.portal == "revisao_templates"} >= {
            "template_publicado",
            "template_status_lote_alterado",
            "template_clonado",
            "template_excluido_lote",
        }


def test_revisor_salvar_e_preview_template_editor_rico(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_criar = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Template Word Preview",
            "codigo_template": "word_preview",
            "versao": 2,
            "origem_modo": "a4",
        },
    )
    assert resposta_criar.status_code == 201
    template_id = int(resposta_criar.json()["id"])

    resposta_salvar = client.put(
        f"/revisao/api/templates-laudo/editor/{template_id}",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Template Word Preview Atualizado",
            "documento_editor_json": {
                "version": 1,
                "doc": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "Empresa: {{json_path:informacoes_gerais.local_inspecao}}"},
                            ],
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "Cliente: {{token:cliente_nome}}"},
                            ],
                        },
                    ],
                },
            },
            "estilo_json": {
                "cabecalho_texto": "Tariel.ia {{token:cliente_nome}}",
                "rodape_texto": "Revisão Técnica",
                "marca_dagua": {"texto": "CONFIDENCIAL", "opacity": 0.08},
                "pagina": {"margens_mm": {"top": 18, "right": 14, "bottom": 18, "left": 14}},
            },
        },
    )
    assert resposta_salvar.status_code == 200
    assert resposta_salvar.json()["nome"] == "Template Word Preview Atualizado"

    resposta_preview = client.post(
        f"/revisao/api/templates-laudo/editor/{template_id}/preview",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "dados_formulario": {
                "informacoes_gerais": {"local_inspecao": "Planta Sul"},
                "tokens": {"cliente_nome": "Cliente XPTO"},
            }
        },
    )
    assert resposta_preview.status_code == 200
    assert "application/pdf" in (resposta_preview.headers.get("content-type", "").lower())
    assert resposta_preview.content.startswith(b"%PDF")
    assert len(resposta_preview.content) > 300


def test_revisor_preview_template_editor_rico_fallback_playwright(ambiente_critico, monkeypatch) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_criar = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Template Word Fallback Preview",
            "codigo_template": "word_preview_fallback",
            "versao": 3,
            "origem_modo": "a4",
        },
    )
    assert resposta_criar.status_code == 201
    template_id = int(resposta_criar.json()["id"])

    async def _playwright_falha(**_kwargs):
        raise RuntimeError("Falha forçada do Playwright")

    monkeypatch.setattr(
        "nucleo.template_editor_word.gerar_pdf_html_playwright",
        _playwright_falha,
    )

    resposta_preview = client.post(
        f"/revisao/api/templates-laudo/editor/{template_id}/preview",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={"dados_formulario": {"tokens": {"cliente_nome": "Fallback"}}},
    )

    assert resposta_preview.status_code == 200
    assert "application/pdf" in (resposta_preview.headers.get("content-type", "").lower())
    assert resposta_preview.content.startswith(b"%PDF")


def test_revisor_upload_asset_template_editor_rico(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_criar = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Template Word Asset",
            "codigo_template": "word_asset",
            "versao": 1,
            "origem_modo": "a4",
        },
    )
    assert resposta_criar.status_code == 201
    template_id = int(resposta_criar.json()["id"])

    resposta_asset = client.post(
        f"/revisao/api/templates-laudo/editor/{template_id}/assets",
        headers={"X-CSRF-Token": csrf},
        data={"csrf_token": csrf},
        files={"arquivo": ("logo.png", _imagem_png_bytes_teste(), "image/png")},
    )
    assert resposta_asset.status_code == 201
    asset = resposta_asset.json()["asset"]
    assert asset["id"]
    assert asset["src"].startswith("asset://")

    resposta_baixar_asset = client.get(f"/revisao/api/templates-laudo/editor/{template_id}/assets/{asset['id']}")
    assert resposta_baixar_asset.status_code == 200
    assert "image/png" in (resposta_baixar_asset.headers.get("content-type", "").lower())


def test_revisor_criar_template_editor_rejeita_ativo_inteiro_por_contrato(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Template Word Estrito",
            "codigo_template": "word_estrito",
            "versao": 1,
            "origem_modo": "a4",
            "ativo": 0,
        },
    )

    assert resposta.status_code == 422


def test_revisor_upload_template_rejeita_bool_form_invalido(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf},
        data={
            "nome": "Template Bool Invalido",
            "codigo_template": "bool_invalido",
            "versao": "1",
            "ativo": "0",
        },
        files={
            "arquivo_base": ("bool_invalido.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )

    assert resposta.status_code == 422


def test_revisor_publicar_template_editor_rico_desativa_ativo_anterior(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    resposta_v1 = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Word RTI v1",
            "codigo_template": "word_rti",
            "versao": 1,
            "origem_modo": "a4",
            "ativo": True,
        },
    )
    assert resposta_v1.status_code == 201
    id_v1 = int(resposta_v1.json()["id"])

    resposta_v2 = client.post(
        "/revisao/api/templates-laudo/editor",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "nome": "Word RTI v2",
            "codigo_template": "word_rti",
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
    assert resposta_publicar.json().get("status") == "publicado"

    with SessionLocal() as banco:
        template_v1 = banco.get(TemplateLaudo, id_v1)
        template_v2 = banco.get(TemplateLaudo, id_v2)
        assert template_v1 is not None
        assert template_v2 is not None
        assert template_v1.ativo is False
        assert template_v2.ativo is True
        assert str(template_v2.modo_editor) == "editor_rico"
        assert str(template_v2.arquivo_pdf_base).lower().endswith(".pdf")
        assert os.path.isfile(str(template_v2.arquivo_pdf_base))


def test_revisor_editor_rico_respeita_isolamento_multiempresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        template_b = TemplateLaudo(
            empresa_id=ids["empresa_b"],
            criado_por_id=ids["inspetor_b"],
            nome="Template B",
            codigo_template="word_b",
            versao=1,
            ativo=True,
            modo_editor="editor_rico",
            arquivo_pdf_base=_salvar_pdf_temporario_teste("word_b"),
            mapeamento_campos_json={},
            documento_editor_json={"version": 1, "doc": {"type": "doc", "content": []}},
            assets_json=[],
            estilo_json={},
        )
        banco.add(template_b)
        banco.commit()
        banco.refresh(template_b)
        template_id_b = int(template_b.id)

    resposta = client.get(f"/revisao/api/templates-laudo/editor/{template_id_b}", headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 404


def test_api_gerar_pdf_usa_template_ativo_da_empresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.tipo_template = "cbmgo"
        laudo.dados_formulario = {
            "informacoes_gerais": {
                "responsavel_pela_inspecao": "Gabriel Santos",
                "data_inspecao": "09/03/2026",
            }
        }
        banco.commit()

        _criar_template_ativo(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="cbmgo_cmar",
            versao=1,
            mapeamento={},
        )

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Diagnóstico teste para exportação por template ativo.",
            "inspetor": "Inspetor A",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/03/2026",
            "laudo_id": laudo_id,
            "tipo_template": "cbmgo",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "cbmgo_cmar_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_usa_template_editor_rico_ativo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.tipo_template = "cbmgo"
        laudo.dados_formulario = {
            "informacoes_gerais": {"local_inspecao": "Planta Leste"},
            "tokens": {"cliente_nome": "Cliente Tariel"},
        }

        banco.add(
            TemplateLaudo(
                empresa_id=ids["empresa_a"],
                criado_por_id=ids["revisor_a"],
                nome="Template Word Ativo",
                codigo_template="cbmgo_cmar",
                versao=5,
                ativo=True,
                modo_editor="editor_rico",
                arquivo_pdf_base=_salvar_pdf_temporario_teste("word_ativo"),
                mapeamento_campos_json={},
                documento_editor_json={
                    "version": 1,
                    "doc": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Cliente {{token:cliente_nome}}"}],
                            },
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Local {{json_path:informacoes_gerais.local_inspecao}}"}],
                            },
                        ],
                    },
                },
                assets_json=[],
                estilo_json={"cabecalho_texto": "Tariel.ia", "rodape_texto": "Mesa"},
            )
        )
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Diagnóstico editor rico.",
            "inspetor": "Inspetor A",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/03/2026",
            "laudo_id": laudo_id,
            "tipo_template": "cbmgo",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "cbmgo_cmar_v5" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_usa_seed_canonico_da_familia_catalogada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr13",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr13_inspecao_vaso_pressao"
        laudo.catalog_family_label = "NR13 · Vaso de Pressão"
        laudo.catalog_variant_key = "premium_campo"
        laudo.catalog_variant_label = "Premium campo"
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR13 para vaso de pressão.",
            "inspetor": "Inspetor NR13",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr13",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr13_vaso_pressao_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr10_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr10",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr10_inspecao_instalacoes_eletricas"
        laudo.catalog_family_label = "NR10 · Instalacoes eletricas"
        laudo.catalog_variant_key = "prime_site"
        laudo.catalog_variant_label = "Prime site"
        laudo.parecer_ia = "Foi identificado aquecimento localizado no borne principal com necessidade de ajuste corretivo."
        laudo.dados_formulario = {
            "local_inspecao": "Area de prensas - painel QGBT-07",
            "objeto_principal": "Painel eletrico QGBT-07",
            "codigo_interno": "QGBT-07",
            "referencia_principal": "IMG_301 - frontal do QGBT-07",
            "metodo_inspecao": "Inspecao visual com apoio de termografia e checklist NR10.",
            "evidencia_principal": "IMG_302 - hotspot no borne principal",
            "pie": "DOC_041 - pie_planta_prensas.pdf",
            "descricao_pontos_atencao": "Aquecimento anormal no borne principal.",
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR10 para painel eletrico.",
            "inspetor": "Inspetor NR10",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr10",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr10_inspecao_instalacoes_eletricas_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr10_prontuario_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr10",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr10_prontuario_instalacoes_eletricas"
        laudo.catalog_family_label = "NR10 · Prontuario instalacoes eletricas"
        laudo.catalog_variant_key = "prime_documental"
        laudo.catalog_variant_label = "Prime documental"
        laudo.parecer_ia = "Prontuario consolidado, mas ainda depende de anexar a ART de atualizacao do diagrama unifilar."
        laudo.dados_formulario = {
            "localizacao": "Area de prensas - painel QGBT-07",
            "objeto_principal": "Prontuario eletrico do painel QGBT-07",
            "codigo_interno": "PRT-QGBT-07",
            "numero_prontuario": "PRT-QGBT-07",
            "referencia_principal": "DOC_301 - indice_prontuario_qgbt07.pdf",
            "metodo_aplicado": "Consolidacao documental do prontuario NR10 com validacao do indice, diagramas e inventario de circuitos.",
            "prontuario": "DOC_301 - indice_prontuario_qgbt07.pdf",
            "inventario_instalacoes": "DOC_302 - inventario_circuitos_qgbt07.xlsx",
            "diagrama_unifilar": "DOC_303 - diagrama_qgbt07_rev04.pdf",
            "pie": "DOC_304 - pie_prensas_rev02.pdf",
            "descricao_pontos_atencao": "Pendencia de anexar a ART de atualizacao do diagrama unifilar revisado.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR10 para prontuario eletrico.",
            "inspetor": "Inspetor NR10",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr10",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr10_prontuario_instalacoes_eletricas_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr18_canteiro_obra_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr18_inspecao_canteiro_obra"
        laudo.catalog_family_label = "NR18 · Canteiro de obra"
        laudo.catalog_variant_key = "prime_obra"
        laudo.catalog_variant_label = "Prime obra"
        laudo.parecer_ia = "Foi identificada guarda-corpo incompleta no pavimento superior e necessidade de reforcar a sinalizacao de circulacao de pedestres."
        laudo.dados_formulario = {
            "local_inspecao": "Canteiro Torre Norte - pavimentos 1 a 4",
            "objeto_principal": "Canteiro da obra vertical Torre Norte",
            "codigo_interno": "OBR-TN-01",
            "referencia_principal": "IMG_1101 - vista geral do canteiro Torre Norte",
            "metodo_inspecao": "Inspecao de campo com checklist NR18, registro fotografico e leitura das frentes simultaneas.",
            "pgr_obra": "DOC_1101 - pgr_torre_norte_rev03.pdf",
            "apr": "DOC_1102 - apr_frente_estrutura_pav4.pdf",
            "protecao_periferica": "Guarda-corpo ausente em trecho da periferia do pavimento 4.",
            "sinalizacao": "Sinalizacao de circulacao de pedestres incompleta proxima ao guincho.",
            "descricao_pontos_atencao": "Trecho sem guarda-corpo no pavimento superior e segregacao incompleta da circulacao de pedestres.",
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR18 para canteiro de obra.",
            "inspetor": "Inspetor NR18",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr18_inspecao_canteiro_obra_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr18_frente_construcao_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr18_inspecao_frente_construcao"
        laudo.catalog_family_label = "NR18 · Frente de construcao"
        laudo.catalog_variant_key = "prime_obra"
        laudo.catalog_variant_label = "Prime obra"
        laudo.parecer_ia = "Frente de concretagem liberada com ressalva pela necessidade de reorganizar o isolamento da vala lateral."
        laudo.dados_formulario = {
            "local_inspecao": "Bloco B - frente de concretagem da ala oeste",
            "objeto_principal": "Frente de concretagem bloco B ala oeste",
            "codigo_interno": "FRN-B-OESTE",
            "referencia_principal": "IMG_1201 - vista geral da frente ala oeste",
            "metodo_aplicado": "Inspecao de campo da frente de construcao com checklist NR18 e verificacao do isolamento operacional.",
            "pgr_obra": "DOC_1201 - pgr_bloco_b.pdf",
            "apr": "DOC_1202 - apr_concretagem_bloco_b.pdf",
            "pte": "DOC_1203 - permissao_concretagem_bloco_b.pdf",
            "escavacoes": "Vala lateral sem barreira continua no trecho de acesso secundario.",
            "descricao_pontos_atencao": "Necessidade de recompor o isolamento continuo da vala lateral antes do turno noturno.",
            "conclusao": {"status": "Liberado com restricoes"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR18 para frente de construcao.",
            "inspetor": "Inspetor NR18",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr18_inspecao_frente_construcao_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr22_area_mineracao_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr22_inspecao_area_mineracao"
        laudo.catalog_family_label = "NR22 · Area de mineracao"
        laudo.catalog_variant_key = "prime_mineracao"
        laudo.catalog_variant_label = "Prime mineracao"
        laudo.parecer_ia = "Foram identificadas drenagem superficial parcial e sinalizacao incompleta na rota de pedestres da cava norte."
        laudo.dados_formulario = {
            "local_inspecao": "Cava Norte - bancada 3",
            "objeto_principal": "Area de lavra Cava Norte - bancada 3",
            "codigo_interno": "MIN-CN-B3",
            "referencia_principal": "IMG_2101 - vista geral da cava norte bancada 3",
            "metodo_inspecao": "Inspecao de campo em area de mineracao com checklist NR22 e leitura das frentes de lavra.",
            "pgr_mineracao": "DOC_2101 - pgr_mineracao_cava_norte_rev05.pdf",
            "plano_emergencia": "DOC_2102 - plano_emergencia_cava_norte.pdf",
            "estabilidade_taludes": "Talude principal monitorado com pequena fissura superficial sem deslocamento aparente.",
            "drenagem": "Canaleta lateral parcial com necessidade de recomposicao antes de nova chuva forte.",
            "sinalizacao": "Sinalizacao de rota de pedestres incompleta proxima ao acesso da bancada 3.",
            "descricao_pontos_atencao": "Drenagem superficial parcial e sinalizacao incompleta na rota de pedestres da bancada 3.",
            "conclusao": {"status": "Liberado com restricoes"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR22 para area de mineracao.",
            "inspetor": "Inspetor NR22",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr22_inspecao_area_mineracao_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr22_instalacao_mineira_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr22_inspecao_instalacao_mineira"
        laudo.catalog_family_label = "NR22 · Instalacao mineira"
        laudo.catalog_variant_key = "prime_mineracao"
        laudo.catalog_variant_label = "Prime mineracao"
        laudo.parecer_ia = "Foi identificada protecao parcial na correia C-04 e falta de identificacao completa dos pontos de bloqueio de energia."
        laudo.dados_formulario = {
            "local_inspecao": "Britagem primaria BM-02",
            "objeto_principal": "Instalacao mineira BM-02 - britagem primaria",
            "codigo_interno": "BM-02",
            "referencia_principal": "IMG_2201 - vista geral da britagem BM-02",
            "metodo_aplicado": "Inspecao de campo em instalacao mineira com checklist NR22, verificacao operacional, bloqueios, acessos e protecoes mecanicas.",
            "pgr_mineracao": "DOC_2201 - pgr_britagem_rev04.pdf",
            "procedimento_operacional": "DOC_2202 - procedimento_britagem_bm02.pdf",
            "pte": "DOC_2204 - permissao_intervencao_bm02.pdf",
            "bloqueio_energia": "Pontos de bloqueio de energia presentes, sem identificacao completa no painel local.",
            "correias_transportadoras": "Correia C-04 operando sem protecao integral no retorno inferior.",
            "descricao_pontos_atencao": "Protecao parcial na correia C-04 e identificacao incompleta dos pontos de bloqueio de energia.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR22 para instalacao mineira.",
            "inspetor": "Inspetor NR22",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr22_inspecao_instalacao_mineira_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr29_operacao_portuaria_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr29_inspecao_operacao_portuaria"
        laudo.catalog_family_label = "NR29 · Operacao portuaria"
        laudo.catalog_variant_key = "prime_porto"
        laudo.catalog_variant_label = "Prime porto"
        laudo.parecer_ia = "Foi identificada area de pedestres sem segregacao completa proxima ao guindaste movel e sinalizacao parcial no acesso ao cais."
        laudo.dados_formulario = {
            "local_inspecao": "Terminal Leste - berco 5",
            "objeto_principal": "Operacao de descarga no berco 5 do terminal leste",
            "codigo_interno": "PORTO-B5-2026",
            "referencia_principal": "IMG_2901 - vista geral da operacao no berco 5",
            "metodo_inspecao": "Inspecao de campo em operacao portuaria com checklist NR29, verificacao de equipamentos, fluxos de carga e acessos ao cais.",
            "pgr_portuario": "DOC_2901 - pgr_portuario_terminal_leste_rev03.pdf",
            "procedimento_operacional": "DOC_2903 - procedimento_descarga_bobinas.pdf",
            "plano_emergencia": "DOC_2904 - plano_emergencia_terminal_leste.pdf",
            "equipamento_portuario": "Guindaste movel MHC-04",
            "movimentacao_carga": "Bobinas descarregadas do porao 2 para carretas no patio temporario.",
            "sinalizacao": "Sinalizacao parcial no corredor lateral de pedestres.",
            "descricao_pontos_atencao": "Segregacao incompleta de pedestres proxima a area de descarga e sinalizacao parcial no acesso lateral do cais.",
            "conclusao": {"status": "Liberado com restricoes"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR29 para operacao portuaria.",
            "inspetor": "Inspetor NR29",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr29_inspecao_operacao_portuaria_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr30_trabalho_aquaviario_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr30_inspecao_trabalho_aquaviario"
        laudo.catalog_family_label = "NR30 · Trabalho aquaviario"
        laudo.catalog_variant_key = "prime_aquaviario"
        laudo.catalog_variant_label = "Prime aquaviario"
        laudo.parecer_ia = (
            "Foi identificada protecao parcial no acesso ao conves inferior e comunicacao operacional irregular durante a transferencia de carga."
        )
        laudo.dados_formulario = {
            "local_inspecao": "Embarcacao Atlas - conves principal",
            "objeto_principal": "Transferencia de carga na embarcacao Atlas",
            "codigo_interno": "AQUA-ATL-01",
            "referencia_principal": "IMG_3001 - vista geral do conves principal da Atlas",
            "metodo_inspecao": "Inspecao de campo em trabalho aquaviario com checklist NR30, verificacao de acessos, condicoes de bordo e controles de emergencia.",
            "pgr_embarcacao": "DOC_3001 - pgr_embarcacao_atlas_rev02.pdf",
            "procedimento_operacional": "DOC_3003 - procedimento_transferencia_conves.pdf",
            "plano_emergencia": "DOC_3004 - plano_emergencia_atlas.pdf",
            "checklist_bordo": "DOC_3005 - checklist_nr30_conves_principal.pdf",
            "tipo_embarcacao": "Carga geral",
            "comunicacao_operacional": "Comunicacao por radio com falhas intermitentes entre conves principal e equipe de apoio.",
            "descricao_pontos_atencao": "Acesso ao conves inferior sem protecao completa e comunicacao operacional irregular durante a transferencia de carga.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR30 para trabalho aquaviario.",
            "inspetor": "Inspetor NR30",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr30_inspecao_trabalho_aquaviario_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr31_frente_rural_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr31_inspecao_frente_rural"
        laudo.catalog_family_label = "NR31 · Frente rural"
        laudo.catalog_variant_key = "prime_rural"
        laudo.catalog_variant_label = "Prime rural"
        laudo.parecer_ia = (
            "Foi identificada protecao incompleta na tomada de forca do trator e armazenamento inadequado de defensivos proximo a area de vivencia."
        )
        laudo.dados_formulario = {
            "local_inspecao": "Fazenda Boa Esperanca - talhao 7",
            "objeto_principal": "Frente rural de colheita no talhao 7",
            "codigo_interno": "RURAL-T7-2026",
            "referencia_principal": "IMG_3101 - vista geral da frente de colheita no talhao 7",
            "metodo_inspecao": "Inspecao de campo em frente rural com checklist NR31, verificacao de maquinas, frentes de trabalho, areas de apoio e controles operacionais.",
            "pgr_rural": "DOC_3101 - pgr_rural_fazenda_boa_esperanca_rev03.pdf",
            "procedimento_operacional": "DOC_3103 - procedimento_colheita_mecanizada.pdf",
            "treinamento_operadores": "DOC_3104 - treinamento_operadores_talhao7.pdf",
            "maquinas_tratores": "Trator T-19 com tomada de forca sem protecao completa no eixo secundario.",
            "armazenamento_insumos": "Defensivos armazenados provisoriamente em abrigo sem segregacao adequada do ponto de refeicao.",
            "descricao_pontos_atencao": "Tomada de forca com protecao incompleta e armazenamento inadequado de defensivos proximo a area de vivencia.",
            "conclusao": {"status": "Liberado com restricoes"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR31 para frente rural.",
            "inspetor": "Inspetor NR31",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr31_inspecao_frente_rural_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr32_inspecao_servico_saude_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr32_inspecao_servico_saude"
        laudo.catalog_family_label = "NR32 · Inspecao servico saude"
        laudo.catalog_variant_key = "prime_saude"
        laudo.catalog_variant_label = "Prime saude"
        laudo.parecer_ia = "Foi identificada segregacao parcial de residuos e necessidade de reforcar o fluxo de perfurocortantes no CME."
        laudo.dados_formulario = {
            "local_inspecao": "Hospital Central - centro de material e esterilizacao",
            "objeto_principal": "CME do Hospital Central",
            "codigo_interno": "NR32-CME-01",
            "referencia_principal": "IMG_3201 - vista geral do CME do Hospital Central",
            "metodo_inspecao": "Inspecao de campo em servico de saude com checklist NR32, leitura de fluxos limpo/sujo e verificacao das barreiras de biosseguranca.",
            "pgrss": "DOC_3201 - pgrss_hospital_central_rev06.pdf",
            "plano_contingencia": "DOC_3204 - plano_contingencia_exposicao_biologica.pdf",
            "segregacao_residuos": "Segregacao presente, com coletor de residuos infectantes sem identificacao completa em uma das bancadas.",
            "perfurocortantes": "Caixa de perfurocortantes acima da linha recomendada em posto secundario.",
            "descricao_pontos_atencao": "Segregacao parcial de residuos e caixa de perfurocortantes acima da linha recomendada no posto secundario.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR32 para servico de saude.",
            "inspetor": "Inspetor NR32",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr32_inspecao_servico_saude_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr32_plano_risco_biologico_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr32_plano_risco_biologico"
        laudo.catalog_family_label = "NR32 · Plano risco biologico"
        laudo.catalog_variant_key = "prime_saude_documental"
        laudo.catalog_variant_label = "Prime saude documental"
        laudo.parecer_ia = (
            "O plano de risco biologico foi consolidado, mas ainda depende de fechar o protocolo de exposicao para o laboratorio de microbiologia."
        )
        laudo.dados_formulario = {
            "localizacao": "Hospital Central - laboratorio de microbiologia",
            "objeto_principal": "Plano de risco biologico do Hospital Central",
            "codigo_interno": "PRB-HC-2026",
            "numero_plano": "PRB-2026-04",
            "referencia_principal": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "metodo_aplicado": "Analise documental do plano de risco biologico com consolidacao do inventario de agentes, protocolos de exposicao e planos de contingencia.",
            "plano_risco_biologico": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "mapa_risco_biologico": "DOC_3211 - mapa_risco_biologico_laboratorios.pdf",
            "inventario_agentes": "DOC_3212 - inventario_agentes_biologicos_2026.xlsx",
            "protocolo_exposicao": "DOC_3213 - protocolo_exposicao_acidentes_biologicos.docx",
            "status_documentacao": "Plano consolidado com pendencia de detalhar o protocolo de exposicao do laboratorio de microbiologia.",
            "descricao_pontos_atencao": "Detalhar o protocolo de exposicao do laboratorio de microbiologia e vincular a contingencia especifica ao plano consolidado.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR32 para plano de risco biologico.",
            "inspetor": "Inspetor NR32",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr32_plano_risco_biologico_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr34_inspecao_frente_naval_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr34_inspecao_frente_naval"
        laudo.catalog_family_label = "NR34 · Frente naval"
        laudo.catalog_variant_key = "prime_naval"
        laudo.catalog_variant_label = "Prime naval"
        laudo.parecer_ia = "Foi identificada ventilacao parcial no tanque lateral e isolamento incompleto da area de trabalho a quente no bloco 12."
        laudo.dados_formulario = {
            "local_inspecao": "Estaleiro Atlantico - doca 2 bloco 12",
            "objeto_principal": "Frente de reparacao naval do bloco 12",
            "codigo_interno": "NAV-B12-2026",
            "referencia_principal": "IMG_3401 - vista geral da frente naval do bloco 12",
            "metodo_inspecao": "Inspecao de campo em frente naval com checklist NR34, verificacao de trabalho a quente, ventilacao e segregacao da area operacional.",
            "pgr_naval": "DOC_3401 - pgr_naval_estaleiro_atlantico_rev03.pdf",
            "permissao_trabalho_quente": "DOC_3403 - pte_quente_bloco12.pdf",
            "plano_emergencia": "DOC_3406 - plano_emergencia_doca2.pdf",
            "trabalho_quente": "Solda em chaparia lateral com permissao emitida e necessidade de ampliar o isolamento do entorno imediato.",
            "ventilacao_exaustao": "Ventilacao auxiliar presente, mas com renovacao insuficiente no fundo do tanque lateral.",
            "descricao_pontos_atencao": "Ventilacao parcial no tanque lateral e isolamento incompleto da area de trabalho a quente no bloco 12.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR34 para frente naval.",
            "inspetor": "Inspetor NR34",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr34_inspecao_frente_naval_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr36_unidade_abate_processamento_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr36_inspecao_unidade_abate_processamento"
        laudo.catalog_family_label = "NR36 · Unidade abate processamento"
        laudo.catalog_variant_key = "prime_frigorifico"
        laudo.catalog_variant_label = "Prime frigorifico"
        laudo.parecer_ia = "Foi identificada pausa termica insuficiente na desossa e piso umido sem segregacao completa no corredor de abastecimento."
        laudo.dados_formulario = {
            "local_inspecao": "Planta Sul - setor de desossa e corte",
            "objeto_principal": "Unidade de desossa e corte da Planta Sul",
            "codigo_interno": "FRIGO-DS-12",
            "referencia_principal": "IMG_3601 - vista geral da linha de desossa 12",
            "metodo_inspecao": "Inspecao de campo em unidade de abate e processamento com checklist NR36, verificacao de pausas, ergonomia e condicoes termicas.",
            "pgr_frigorifico": "DOC_3601 - pgr_planta_sul_rev04.pdf",
            "programa_pausas": "DOC_3604 - programa_pausas_termicas_turno_tarde.pdf",
            "pcmso": "DOC_3605 - pcmso_planta_sul_2026.pdf",
            "pausas_termicas": "Escala de pausas abaixo do previsto para o turno da tarde.",
            "ergonomia_posto": "Postos repetitivos com necessidade de rever altura da mesa secundaria.",
            "descricao_pontos_atencao": "Pausa termica insuficiente na desossa e piso umido sem segregacao completa no corredor de abastecimento.",
            "conclusao": {"status": "Liberado com restricoes"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR36 para unidade de abate e processamento.",
            "inspetor": "Inspetor NR36",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr36_inspecao_unidade_abate_processamento_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr37_plataforma_petroleo_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr37_inspecao_plataforma_petroleo"
        laudo.catalog_family_label = "NR37 · Plataforma petroleo"
        laudo.catalog_variant_key = "prime_offshore"
        laudo.catalog_variant_label = "Prime offshore"
        laudo.parecer_ia = "O pacote documental da plataforma foi consolidado, mas ainda depende de atualizar o inventario de riscos do modulo de compressao."
        laudo.dados_formulario = {
            "localizacao": "Plataforma Aurora - modulo de processo e habitacao",
            "objeto_principal": "Pacote documental da Plataforma Aurora",
            "codigo_interno": "PLAT-AUR-2026",
            "codigo_plataforma": "AUR-01",
            "referencia_principal": "DOC_3701 - pacote_nr37_plataforma_aurora_rev03.pdf",
            "metodo_aplicado": "Analise documental de plataforma de petroleo com consolidacao do inventario de riscos, planos de resposta e matriz de treinamentos.",
            "status_documentacao": "Pacote consolidado com pendencia de atualizar o inventario de riscos do modulo de compressao.",
            "inventario_riscos": "DOC_3702 - inventario_riscos_modulo_compressao.xlsx",
            "matriz_treinamentos": "DOC_3703 - matriz_treinamentos_offshore_2026.xlsx",
            "pgr_plataforma": "DOC_3704 - pgr_plataforma_aurora_rev05.pdf",
            "plano_resposta_emergencia": "DOC_3705 - plano_resposta_aurora_rev04.pdf",
            "descricao_pontos_atencao": "Atualizar o inventario de riscos do modulo de compressao e reemitir a referencia consolidada do pacote NR37.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR37 para plataforma de petroleo.",
            "inspetor": "Inspetor NR37",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr37_inspecao_plataforma_petroleo_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr38_limpeza_urbana_residuos_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr38_inspecao_limpeza_urbana_residuos"
        laudo.catalog_family_label = "NR38 · Limpeza urbana residuos"
        laudo.catalog_variant_key = "prime_urbana"
        laudo.catalog_variant_label = "Prime urbana"
        laudo.parecer_ia = (
            "Foi identificada segregacao parcial do trafego viario e necessidade de reforcar a higienizacao do compartimento traseiro do caminhão."
        )
        laudo.dados_formulario = {
            "local_inspecao": "Base Centro Norte e rota de coleta urbana",
            "objeto_principal": "Rota de coleta urbana Centro Norte",
            "codigo_interno": "URB-CN-07",
            "referencia_principal": "IMG_3801 - vista geral do caminhão coletor CN-07",
            "metodo_inspecao": "Inspecao de campo em limpeza urbana com checklist NR38, verificacao da coleta, manuseio de residuos e trafego da rota.",
            "pgr_limpeza_urbana": "DOC_3801 - pgr_limpeza_urbana_rev03.pdf",
            "checklist_frota": "DOC_3805 - checklist_caminhao_cn07.pdf",
            "treinamento_equipe": "DOC_3806 - treinamento_seguranca_coleta_2026.pdf",
            "coleta_manual": "Coleta porta a porta com equipe de tres garis na rota central.",
            "segregacao_trafego": "Corredor central sem cones suficientes em trecho de travessia intensa.",
            "descricao_pontos_atencao": "Segregacao parcial do trafego viario e necessidade de reforcar a higienizacao do compartimento traseiro do caminhão.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR38 para limpeza urbana e residuos.",
            "inspetor": "Inspetor NR38",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr38_inspecao_limpeza_urbana_residuos_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr12_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr12maquinas",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr12_inspecao_maquina_equipamento"
        laudo.catalog_family_label = "NR12 · Maquina e equipamento"
        laudo.catalog_variant_key = "prime_machine"
        laudo.catalog_variant_label = "Prime machine"
        laudo.parecer_ia = "Foi identificado intertravamento inoperante na porta frontal com necessidade de ajuste imediato."
        laudo.dados_formulario = {
            "local_inspecao": "Linha de estampagem - prensa PH-07",
            "objeto_principal": "Prensa hidraulica PH-07",
            "codigo_interno": "PH-07",
            "referencia_principal": "IMG_401 - vista frontal da PH-07",
            "metodo_inspecao": "Inspecao visual funcional com checklist NR12 e teste de parada de emergencia.",
            "evidencia_principal": "IMG_402 - porta frontal aberta com movimento habilitado",
            "manual_maquina": "DOC_051 - manual_prensa_ph07.pdf",
            "descricao_pontos_atencao": "Intertravamento da porta frontal inoperante.",
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR12 para prensa hidraulica.",
            "inspetor": "Inspetor NR12",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr12maquinas",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr12_inspecao_maquina_equipamento_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr12_apreciacao_risco_catalogada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr12maquinas",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr12_apreciacao_risco_maquina"
        laudo.catalog_family_label = "NR12 · Apreciacao de risco"
        laudo.catalog_variant_key = "prime_engineering"
        laudo.catalog_variant_label = "Prime engineering"
        laudo.parecer_ia = "Foi identificado risco alto de aprisionamento na zona de alimentacao durante setup da prensa."
        laudo.dados_formulario = {
            "local_inspecao": "Linha de estampagem - prensa PH-07",
            "objeto_principal": "Prensa hidraulica PH-07",
            "codigo_interno": "PH-07",
            "referencia_principal": "IMG_451 - vista geral da PH-07",
            "metodo_aplicado": "Apreciacao de risco com matriz HRN, checklist NR12 e memoria tecnica.",
            "evidencia_principal": "DOC_061 - matriz_risco_ph07.pdf",
            "apreciacao_risco": "DOC_061 - matriz_risco_ph07.pdf",
            "descricao_pontos_atencao": "Risco alto de aprisionamento na zona de alimentacao durante setup.",
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR12 para apreciacao de risco de prensa hidraulica.",
            "inspetor": "Inspetor NR12",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr12maquinas",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr12_apreciacao_risco_maquina_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr20_inspecao_catalogada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr20",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr20_inspecao_instalacoes_inflamaveis"
        laudo.catalog_family_label = "NR20 · Inspecao de instalacoes inflamaveis"
        laudo.catalog_variant_key = "prime_inflamaveis"
        laudo.catalog_variant_label = "Prime inflamaveis"
        laudo.parecer_ia = "Foi identificado desgaste no aterramento do skid e necessidade de recompor a sinalizacao da area classificada."
        laudo.dados_formulario = {
            "local_inspecao": "Parque de tancagem - skid SK-02",
            "objeto_principal": "Skid de abastecimento SK-02",
            "codigo_interno": "SK-02",
            "referencia_principal": "IMG_601 - vista geral do SK-02",
            "metodo_inspecao": "Inspecao visual com checklist NR20 e verificacao de aterramento e contencao.",
            "evidencia_principal": "IMG_602 - terminal de aterramento com desgaste",
            "prontuario_nr20": "DOC_071 - prontuario_nr20_sk02.pdf",
            "plano_inspecao": "DOC_072 - plano_inspecao_sk02.pdf",
            "descricao_pontos_atencao": "Desgaste no aterramento e necessidade de recompor a sinalizacao da area classificada.",
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR20 para inspecao de instalacoes inflamaveis.",
            "inspetor": "Inspetor NR20",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr20",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr20_inspecao_instalacoes_inflamaveis_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr20_prontuario_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr20",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr20_prontuario_instalacoes_inflamaveis"
        laudo.catalog_family_label = "NR20 · Prontuario de instalacoes inflamaveis"
        laudo.catalog_variant_key = "prime_documental"
        laudo.catalog_variant_label = "Prime documental"
        laudo.parecer_ia = "Prontuario consolidado, mas ainda depende de anexar revisao atualizada do estudo de risco."
        laudo.dados_formulario = {
            "localizacao": "Base de carregamento BC-05",
            "objeto_principal": "Base de carregamento BC-05",
            "codigo_interno": "PRT-20-BC05",
            "numero_prontuario": "PRT-20-BC05",
            "referencia_principal": "DOC_081 - indice_prontuario_bc05.pdf",
            "metodo_aplicado": "Consolidacao documental do prontuario NR20 com validacao de inventario, risco e emergencia.",
            "evidencia_principal": "DOC_083 - estudo_risco_bc05.pdf",
            "prontuario_nr20": "DOC_081 - indice_prontuario_bc05.pdf",
            "inventario_instalacoes": "DOC_082 - inventario_bc05.xlsx",
            "analise_riscos": "DOC_083 - estudo_risco_bc05.pdf",
            "descricao_pontos_atencao": "Necessidade de anexar revisao atualizada do estudo de risco da base.",
            "conclusao": {"status": "Liberado com ressalvas"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR20 para prontuario de instalacoes inflamaveis.",
            "inspetor": "Inspetor NR20",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr20",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr20_prontuario_instalacoes_inflamaveis_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr35_linha_de_vida_catalogada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr35",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr35_inspecao_linha_de_vida"
        laudo.catalog_family_label = "NR35 · Linha de vida"
        laudo.catalog_variant_key = "prime_altura"
        laudo.catalog_variant_label = "Prime altura"
        laudo.parecer_ia = "Linha de vida vertical com nao conformidade localizada no cabo de aco proximo ao topo."
        laudo.dados_formulario = {
            "informacoes_gerais": {
                "unidade": "Usina Orizona",
                "local": "Orizona - GO",
                "numero_laudo_fabricante": "MC-CRMR-0032",
                "numero_laudo_inspecao": "AT-IN-OZ-001-01-26",
                "art_numero": "ART 2026-00077",
            },
            "objeto_inspecao": {
                "identificacao_linha_vida": "MC-CRMRSS-0977 Escada de acesso ao elevador 01",
                "tipo_linha_vida": "Vertical",
                "escopo_inspecao": "Diagnostico geral da linha de vida vertical da escada de acesso.",
            },
            "componentes_inspecionados": {
                "fixacao_dos_pontos": {"condicao": "C", "observacao": "Fixacao integra."},
                "condicao_cabo_aco": {
                    "condicao": "NC",
                    "observacao": "Corrosao inicial proxima ao ponto superior.",
                },
                "condicao_esticador": {"condicao": "C", "observacao": "Tensionamento adequado."},
                "condicao_sapatilha": {"condicao": "C", "observacao": "Montagem integra."},
                "condicao_olhal": {"condicao": "C", "observacao": "Sem deformacao aparente."},
                "condicao_grampos": {"condicao": "C", "observacao": "Aperto visivel regular."},
            },
            "registros_fotograficos": [
                {
                    "titulo": "Vista geral",
                    "legenda": "Vista geral da linha de vida vertical.",
                    "referencia_anexo": "IMG_701 - vista_geral.png",
                },
                {
                    "titulo": "Ponto superior",
                    "legenda": "Corrosao inicial no cabo proximo ao topo.",
                    "referencia_anexo": "IMG_702 - ponto_superior.png",
                },
            ],
            "conclusao": {
                "status": "Reprovado",
                "observacoes": "Substituir o trecho comprometido do cabo e reinspecionar o sistema.",
            },
            "resumo_executivo": "Linha de vida vertical com corrosao inicial no cabo de aco e necessidade de bloqueio para correcoes.",
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR35 para linha de vida vertical.",
            "inspetor": "Inspetor NR35",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr35",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr35_inspecao_linha_de_vida_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr35_ponto_ancoragem_catalogado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr35",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr35_inspecao_ponto_ancoragem"
        laudo.catalog_family_label = "NR35 · Ponto de ancoragem"
        laudo.catalog_variant_key = "prime_altura"
        laudo.catalog_variant_label = "Prime altura"
        laudo.parecer_ia = "Ponto de ancoragem com corrosao superficial localizada no olhal e necessidade de ajuste preventivo."
        laudo.dados_formulario = {
            "local_inspecao": "Cobertura bloco C - ponto ANC-12",
            "objeto_principal": "Ponto de ancoragem ANC-12",
            "codigo_interno": "ANC-12",
            "referencia_principal": "IMG_801 - visao geral do ponto ANC-12",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao visual com verificacao de fixacao, corrosao e deformacoes aparentes.",
            "tipo_ancoragem": "Olhal quimico em base metalica",
            "fixacao": "Fixacao com chumbador quimico e base metalica.",
            "chumbador": "Chumbador com torque conferido em campo.",
            "corrosao": "Corrosao superficial no olhal com perda localizada de pintura.",
            "deformacao": "Sem deformacao permanente aparente.",
            "trinca": "Nao foram observadas trincas na base ou no olhal.",
            "evidencia_principal": "IMG_802 - detalhe do olhal com corrosao superficial",
            "certificado_ancoragem": "DOC_081 - certificado_ancoragem_anc12.pdf",
            "memorial_calculo": "DOC_082 - memorial_anc12.pdf",
            "art_numero": "ART 2026-00155",
            "descricao_pontos_atencao": "Corrosao superficial no olhal e necessidade de limpeza com protecao anticorrosiva.",
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR35 para ponto de ancoragem.",
            "inspetor": "Inspetor NR35",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr35",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr35_inspecao_ponto_ancoragem_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr33_avaliacao_catalogada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr33",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr33_avaliacao_espaco_confinado"
        laudo.catalog_family_label = "NR33 · Avaliacao de espaco confinado"
        laudo.catalog_variant_key = "prime_confinados"
        laudo.catalog_variant_label = "Prime confinados"
        laudo.parecer_ia = "Foi identificada necessidade de reforcar a ventilacao e repetir a leitura atmosferica antes da liberacao final."
        laudo.dados_formulario = {
            "local_inspecao": "Casa de bombas - tanque TQ-11",
            "objeto_principal": "Tanque TQ-11",
            "codigo_interno": "TQ-11",
            "referencia_principal": "IMG_901 - boca de visita do TQ-11",
            "metodo_aplicado": "Avaliacao de espaco confinado com leitura atmosferica e checklist NR33.",
            "evidencia_principal": "IMG_902 - leitura atmosferica inicial",
            "documento_base": "DOC_091 - avaliacao_pre_entrada_tq11.pdf",
            "descricao_pontos_atencao": "Necessidade de reforcar a ventilacao antes da liberacao final.",
            "conclusao": {"status": "Liberado com restricoes"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR33 para avaliacao de espaco confinado.",
            "inspetor": "Inspetor NR33",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr33",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr33_avaliacao_espaco_confinado_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_materializa_nr33_pet_catalogada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr33",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr33_permissao_entrada_trabalho"
        laudo.catalog_family_label = "NR33 · Permissao de entrada"
        laudo.catalog_variant_key = "prime_confinados"
        laudo.catalog_variant_label = "Prime confinados"
        laudo.parecer_ia = "PET liberada com rastreabilidade documental e monitoramento continuo registrado."
        laudo.dados_formulario = {
            "local_inspecao": "Galeria subterranea G-03",
            "objeto_principal": "Galeria subterranea G-03",
            "codigo_interno": "PET-33-118",
            "numero_pet": "PET-33-118",
            "referencia_principal": "IMG_951 - entrada da galeria G-03",
            "metodo_inspecao": "Verificacao da PET com checklist documental e leitura atmosferica de liberacao.",
            "evidencia_principal": "IMG_952 - PET assinada e instrumentos",
            "pet_documento": "DOC_101 - pet_33_118.pdf",
            "conclusao": {"status": "Liberado"},
        }
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Resumo executivo do caso piloto NR33 para permissao de entrada.",
            "inspetor": "Inspetor NR33",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr33",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr33_permissao_entrada_trabalho_v1" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_prioriza_template_ativo_especifico_da_familia_catalogada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr13",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr13_inspecao_vaso_pressao"
        laudo.catalog_family_label = "NR13 · Vaso de Pressão"
        laudo.catalog_variant_key = "premium_campo"
        laudo.catalog_variant_label = "Premium campo"

        banco.add(
            TemplateLaudo(
                empresa_id=ids["empresa_a"],
                criado_por_id=ids["revisor_a"],
                nome="Template dedicado NR13 Vaso",
                codigo_template="nr13_vaso_pressao",
                versao=3,
                ativo=True,
                modo_editor="editor_rico",
                arquivo_pdf_base=_salvar_pdf_temporario_teste("nr13_vaso"),
                mapeamento_campos_json={},
                documento_editor_json={
                    "version": 1,
                    "doc": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Cliente {{token:cliente_nome}}"}],
                            },
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Resumo {{json_path:resumo_executivo}}"}],
                            },
                        ],
                    },
                },
                assets_json=[],
                estilo_json={"cabecalho_texto": "NR13 dedicado", "rodape_texto": "Tariel"},
            )
        )
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Diagnóstico dedicado da família catalogada.",
            "inspetor": "Inspetor NR13",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "nr13",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "nr13_vaso_pressao_v3" in str(resposta.headers.get("content-disposition", "")).lower()


def test_api_gerar_pdf_fallback_legacy_quando_render_rico_falha(ambiente_critico, monkeypatch) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.tipo_template = "cbmgo"
        laudo.dados_formulario = {"tokens": {"cliente_nome": "Fallback Geral"}}

        banco.add(
            TemplateLaudo(
                empresa_id=ids["empresa_a"],
                criado_por_id=ids["revisor_a"],
                nome="Template Word Com Falha",
                codigo_template="cbmgo_cmar",
                versao=6,
                ativo=True,
                modo_editor="editor_rico",
                arquivo_pdf_base=_salvar_pdf_temporario_teste("word_falha"),
                mapeamento_campos_json={},
                documento_editor_json={
                    "version": 1,
                    "doc": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Teste"}]}]},
                },
                assets_json=[],
                estilo_json={},
            )
        )
        banco.commit()

    async def _falha_render(**_kwargs):
        raise RuntimeError("Falha forçada no render rico")

    monkeypatch.setattr("app.domains.chat.chat.gerar_pdf_editor_rico_bytes", _falha_render)

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Diagnóstico fallback por falha no render rico.",
            "inspetor": "Inspetor A",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/03/2026",
            "laudo_id": laudo_id,
            "tipo_template": "cbmgo",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    filename = str(resposta.headers.get("content-disposition", "")).lower()
    assert "laudo_art_wf.pdf" in filename or "laudo_cbmgo_cmar_v1.pdf" in filename


def test_api_gerar_pdf_fallback_legacy_quando_nao_ha_template_ativo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Diagnóstico sem template ativo.",
            "inspetor": "Inspetor A",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/03/2026",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    filename = str(resposta.headers.get("content-disposition", "")).lower()
    assert "laudo_art_wf.pdf" in filename or "laudo_cbmgo_cmar_v1.pdf" in filename


def test_api_gerar_pdf_fallback_legacy_quando_template_ativo_invalido(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.tipo_template = "cbmgo"
        laudo.dados_formulario = {
            "informacoes_gerais": {
                "responsavel_pela_inspecao": "Inspetor A",
            }
        }

        caminho_invalido = os.path.join(tempfile.gettempdir(), f"nao_existe_{uuid.uuid4().hex}.pdf")
        banco.add(
            TemplateLaudo(
                empresa_id=ids["empresa_a"],
                criado_por_id=ids["revisor_a"],
                nome="Template invalido",
                codigo_template="cbmgo_cmar",
                versao=1,
                ativo=True,
                arquivo_pdf_base=caminho_invalido,
                mapeamento_campos_json={},
            )
        )
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Diagnostico com template invalido deve usar fallback.",
            "inspetor": "Inspetor A",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/03/2026",
            "laudo_id": laudo_id,
            "tipo_template": "cbmgo",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    filename = str(resposta.headers.get("content-disposition", "")).lower()
    assert "laudo_art_wf.pdf" in filename or "laudo_cbmgo_cmar_v1.pdf" in filename


def test_api_gerar_pdf_ignora_template_ativo_de_outra_empresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.tipo_template = "cbmgo"
        laudo.dados_formulario = {
            "informacoes_gerais": {
                "responsavel_pela_inspecao": "Inspetor A",
            }
        }

        _criar_template_ativo(
            banco,
            empresa_id=ids["empresa_b"],
            criado_por_id=ids["revisor_a"],
            codigo_template="cbmgo_cmar",
            versao=1,
            mapeamento={},
        )
        banco.commit()

    resposta = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Template de outra empresa nao pode ser aplicado.",
            "inspetor": "Inspetor A",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "09/03/2026",
            "laudo_id": laudo_id,
            "tipo_template": "cbmgo",
        },
    )

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")
    assert "laudo_art_wf.pdf" in str(resposta.headers.get("content-disposition", "")).lower()


def test_home_app_nao_desloga_inspetor(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    home = client.get("/app/", follow_redirects=False)
    assert home.status_code == 200

    status_relatorio = client.get("/app/api/laudo/status", follow_redirects=False)
    assert status_relatorio.status_code == 200


def test_status_relatorio_retorna_405_em_delete_sem_cair_na_rota_dinamica(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.delete("/app/api/laudo/status", follow_redirects=False)

    assert resposta.status_code == 405
    assert resposta.json()["detail"] == "Method Not Allowed"
    assert resposta.headers.get("allow") == "GET"


def test_rotas_estaticas_laudo_retorna_405_em_delete_sem_cair_na_rota_dinamica(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    for rota in (
        "/app/api/laudo/iniciar",
        "/app/api/laudo/cancelar",
        "/app/api/laudo/desativar",
    ):
        resposta = client.delete(rota, follow_redirects=False)
        assert resposta.status_code == 405
        assert resposta.json()["detail"] == "Method Not Allowed"
        assert resposta.headers.get("allow") == "POST"


def test_rotas_estaticas_pendencias_retorna_405_em_patch_sem_cair_na_rota_dinamica(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    for rota, allow in (
        ("/app/api/laudo/1/pendencias/marcar-lidas", "POST"),
        ("/app/api/laudo/1/pendencias/exportar-pdf", "GET"),
    ):
        resposta = client.patch(rota, follow_redirects=False)
        assert resposta.status_code == 405
        assert resposta.json()["detail"] == "Method Not Allowed"
        assert resposta.headers.get("allow") == allow


def test_home_desativa_contexto_sem_excluir_laudo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    iniciar = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )
    assert iniciar.status_code == 200
    corpo_inicio = iniciar.json()
    laudo_id = int(corpo_inicio["laudo_id"])

    desativar = client.post(
        "/app/api/laudo/desativar",
        headers={"X-CSRF-Token": csrf},
    )
    assert desativar.status_code == 200
    corpo_desativar = desativar.json()
    assert corpo_desativar["success"] is True
    assert int(corpo_desativar["laudo_id"]) == laudo_id
    assert corpo_desativar["laudo_preservado"] is True

    status_relatorio = client.get("/app/api/laudo/status")
    assert status_relatorio.status_code == 200
    corpo_status = status_relatorio.json()
    assert corpo_status["estado"] == "sem_relatorio"
    assert corpo_status["laudo_id"] is None

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.RASCUNHO.value


def test_iniciar_relatorio_sem_tipo_assume_padrao_por_resiliencia(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/laudo/iniciar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["success"] is True
    assert corpo["tipo_template"] == "padrao"
    assert corpo["message"].startswith("✅ Inspeção Inspeção Geral")


def test_iniciar_relatorio_com_campo_vazio_assume_padrao_por_resiliencia(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/laudo/iniciar",
        data={"tipotemplate": ""},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["success"] is True
    assert corpo["tipo_template"] == "padrao"


def test_relatorio_so_fica_ativo_apos_primeira_interacao_no_chat(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    iniciar = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )
    assert iniciar.status_code == 200
    corpo_inicio = iniciar.json()
    laudo_id = int(corpo_inicio["laudo_id"])
    assert corpo_inicio["estado"] == "sem_relatorio"

    status_antes = client.get("/app/api/laudo/status")
    assert status_antes.status_code == 200
    assert status_antes.json()["estado"] == "sem_relatorio"
    assert status_antes.json()["laudo_id"] is None

    class ClienteIAStub:
        def gerar_resposta_stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
            yield "Resposta técnica inicial para ativar o laudo.\n"

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Primeira interação real com a IA.",
                "historico": [],
                "laudo_id": laudo_id,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat.status_code == 200
    assert "text/event-stream" in (resposta_chat.headers.get("content-type", "").lower())

    status_depois = client.get("/app/api/laudo/status")
    assert status_depois.status_code == 200
    assert status_depois.json()["estado"] == "relatorio_ativo"
    assert int(status_depois.json()["laudo_id"]) == laudo_id


def test_home_nao_exibe_rascunho_sem_interacao_na_sidebar(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    iniciar = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )
    assert iniciar.status_code == 200
    corpo_iniciar = iniciar.json()
    laudo_id = int(corpo_iniciar["laudo_id"])
    assert corpo_iniciar["laudo_card"]["id"] == laudo_id
    assert corpo_iniciar["laudo_card"]["status_card"] == "oculto"

    home = client.get("/app/", follow_redirects=False)

    assert home.status_code == 200
    assert f'data-laudo-id="{laudo_id}"' not in home.text
    assert "Nenhum laudo ainda" in home.text


def test_home_exibe_rascunho_com_contexto_inicial_na_sidebar(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    iniciar = client.post(
        "/app/api/laudo/iniciar",
        data={
            "tipo_template": "padrao",
            "cliente": "Petrobras",
            "unidade": "REPLAN - Paulínia",
            "local_inspecao": "Caldeira B-202",
            "objetivo": "Vistoria preliminar de integridade.",
            "nome_inspecao": "Caldeira B-202 - Petrobras - REPLAN - Paulínia",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert iniciar.status_code == 200
    corpo_iniciar = iniciar.json()
    laudo_id = int(corpo_iniciar["laudo_id"])
    assert corpo_iniciar["estado"] == "sem_relatorio"
    assert corpo_iniciar["laudo_card"]["status_card"] == "oculto"

    desativar = client.post(
        "/app/api/laudo/desativar",
        headers={"X-CSRF-Token": csrf},
    )
    assert desativar.status_code == 200

    status_relatorio = client.get("/app/api/laudo/status")
    assert status_relatorio.status_code == 200
    assert status_relatorio.json()["estado"] == "sem_relatorio"
    assert status_relatorio.json()["laudo_id"] is None

    home = client.get("/app/?home=1", follow_redirects=False)

    assert home.status_code == 200
    assert f'data-laudo-id="{laudo_id}"' in home.text
    assert "Caldeira B-202" in home.text
    assert "Petrobras - REPLAN - Paulínia" in home.text

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.dados_formulario is None


def test_multiplos_laudos_abertos_aceitam_mensagens_em_paralelo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    iniciar_a = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )
    iniciar_b = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "avcb"},
        headers={"X-CSRF-Token": csrf},
    )
    assert iniciar_a.status_code == 200
    assert iniciar_b.status_code == 200
    laudo_a = int(iniciar_a.json()["laudo_id"])
    laudo_b = int(iniciar_b.json()["laudo_id"])

    class ClienteIAStub:
        def gerar_resposta_stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
            yield "Resposta técnica em paralelo.\n"

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_a_1 = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Primeira conversa do laudo A.",
                "historico": [],
                "laudo_id": laudo_a,
            },
        )
        resposta_b_1 = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Primeira conversa do laudo B.",
                "historico": [],
                "laudo_id": laudo_b,
            },
        )
        resposta_a_2 = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Segunda conversa do laudo A.",
                "historico": [],
                "laudo_id": laudo_a,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_a_1.status_code == 200
    assert resposta_b_1.status_code == 200
    assert resposta_a_2.status_code == 200
    assert "Use apenas o relatório ativo" not in resposta_a_2.text

    with SessionLocal() as banco:
        laudo_a_db = banco.get(Laudo, laudo_a)
        laudo_b_db = banco.get(Laudo, laudo_b)
        assert laudo_a_db is not None
        assert laudo_b_db is not None
        assert laudo_a_db.status_revisao == StatusRevisao.RASCUNHO.value
        assert laudo_b_db.status_revisao == StatusRevisao.RASCUNHO.value
        assert (banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == laudo_a).count()) >= 4
        assert (banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == laudo_b).count()) >= 2


def test_inspetor_atualiza_perfil_chat_com_sucesso(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.put(
        "/app/api/perfil",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome_completo": "Inspetor A Atualizado",
            "email": "inspetor@empresa-a.test",
            "telefone": "(16) 99999-0001",
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ok"] is True
    assert corpo["perfil"]["nome_completo"] == "Inspetor A Atualizado"
    assert corpo["perfil"]["telefone"] == "(16) 99999-0001"

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        assert usuario.nome_completo == "Inspetor A Atualizado"
        assert usuario.telefone == "(16) 99999-0001"


def test_inspetor_upload_foto_perfil_rejeita_mime_invalido(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/perfil/foto",
        headers={"X-CSRF-Token": csrf},
        files={"foto": ("perfil.txt", b"arquivo-invalido", "text/plain")},
    )

    assert resposta.status_code == 415
    assert "Formato inválido" in resposta.text


def test_revisor_painel_exibe_laudos_em_andamento_rascunho(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        hash_curto = laudo.codigo_hash[-6:]

    painel = client.get("/revisao/painel")

    assert painel.status_code == 200
    assert "Em Andamento em Campo (1)" in painel.text
    assert f"#{hash_curto}" in painel.text


def test_revisor_painel_precarrega_whisper_em_laudo_rascunho(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.HUMANO_INSP.value,
                conteudo="Validar item de risco no campo",
                lida=False,
            )
        )
        banco.commit()

    painel = client.get("/revisao/painel")

    assert painel.status_code == 200
    assert "Chamados recentes" in painel.text
    assert "Validar item de risco no campo" in painel.text


def test_revisor_painel_abre_com_laudo_aguardando_sem_atualizado_em(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Laudo aguardando avaliação sem atualização manual."
        laudo.atualizado_em = None
        banco.commit()

    painel = client.get("/revisao/painel")

    assert painel.status_code == 200
    assert "Aguardando Avaliação" in painel.text
    assert "Laudo aguardando avaliação sem atualização manual." in painel.text


def test_revisor_painel_filtro_por_inspetor_restringe_laudos(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        inspetor_extra = Usuario(
            empresa_id=ids["empresa_a"],
            nome_completo="Inspetor Extra",
            email="inspetor-extra@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.INSPETOR.value,
        )
        banco.add(inspetor_extra)
        banco.commit()
        banco.refresh(inspetor_extra)

        laudo_a_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_extra_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=inspetor_extra.id,
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

        laudo_a = banco.get(Laudo, laudo_a_id)
        laudo_extra = banco.get(Laudo, laudo_extra_id)
        assert laudo_a is not None
        assert laudo_extra is not None
        hash_a = laudo_a.codigo_hash[-6:]
        hash_extra = laudo_extra.codigo_hash[-6:]

    painel_filtrado = client.get(f"/revisao/painel?inspetor={ids['inspetor_a']}")

    assert painel_filtrado.status_code == 200
    assert f"#{hash_a}" in painel_filtrado.text
    assert f"#{hash_extra}" not in painel_filtrado.text


def test_revisor_painel_filtro_busca_por_hash_e_texto(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_eletrico_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_caldeira_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

        laudo_eletrico = banco.get(Laudo, laudo_eletrico_id)
        laudo_caldeira = banco.get(Laudo, laudo_caldeira_id)
        assert laudo_eletrico is not None
        assert laudo_caldeira is not None

        laudo_eletrico.primeira_mensagem = "Painel eletrico com nao conformidade de isolamento"
        laudo_caldeira.primeira_mensagem = "Caldeira com ponto de corrosao na linha principal"
        banco.commit()

        hash_eletrico = laudo_eletrico.codigo_hash[-6:]
        hash_caldeira = laudo_caldeira.codigo_hash[-6:]

    painel_hash = client.get(f"/revisao/painel?q={hash_eletrico}")
    assert painel_hash.status_code == 200
    assert f"#{hash_eletrico}" in painel_hash.text
    assert f"#{hash_caldeira}" not in painel_hash.text

    painel_texto = client.get("/revisao/painel?q=corrosao")
    assert painel_texto.status_code == 200
    assert "Caldeira com ponto de corrosao" in painel_texto.text
    assert "Painel eletrico com nao conformidade" not in painel_texto.text


def test_revisor_painel_filtro_aprendizados_pendentes(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_com_aprendizado_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_sem_aprendizado_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

        laudo_com_aprendizado = banco.get(Laudo, laudo_com_aprendizado_id)
        laudo_sem_aprendizado = banco.get(Laudo, laudo_sem_aprendizado_id)
        assert laudo_com_aprendizado is not None
        assert laudo_sem_aprendizado is not None

        banco.add(
            AprendizadoVisualIa(
                empresa_id=ids["empresa_a"],
                laudo_id=laudo_com_aprendizado_id,
                criado_por_id=ids["inspetor_a"],
                setor_industrial="geral",
                resumo="Linha de vida em revisão",
                correcao_inspetor="A IA marcou o ponto errado e a mesa ainda precisa validar.",
                status="rascunho_inspetor",
                veredito_inspetor="duvida",
            )
        )
        banco.commit()

        hash_com_aprendizado = laudo_com_aprendizado.codigo_hash[-6:]
        hash_sem_aprendizado = laudo_sem_aprendizado.codigo_hash[-6:]

    painel_filtrado = client.get("/revisao/painel?aprendizados=pendentes")

    assert painel_filtrado.status_code == 200
    assert f"#{hash_com_aprendizado}" in painel_filtrado.text
    assert f"#{hash_sem_aprendizado}" not in painel_filtrado.text
    assert 'id="filtro-aprendizados"' in painel_filtrado.text
    assert "Com aprendizados pendentes" in painel_filtrado.text
    assert "1 aprend." in painel_filtrado.text


def test_revisor_painel_em_andamento_prioriza_por_sla(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_ok_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_atencao_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_critico_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

        laudo_ok = banco.get(Laudo, laudo_ok_id)
        laudo_atencao = banco.get(Laudo, laudo_atencao_id)
        laudo_critico = banco.get(Laudo, laudo_critico_id)
        assert laudo_ok is not None
        assert laudo_atencao is not None
        assert laudo_critico is not None

        laudo_ok.criado_em = datetime.now(timezone.utc) - timedelta(hours=3)
        laudo_atencao.criado_em = datetime.now(timezone.utc) - timedelta(hours=28)
        laudo_critico.criado_em = datetime.now(timezone.utc) - timedelta(hours=55)
        laudo_ok.primeira_mensagem = "TOKEN_SLA_OK"
        laudo_atencao.primeira_mensagem = "TOKEN_SLA_ATENCAO"
        laudo_critico.primeira_mensagem = "TOKEN_SLA_CRITICO"
        banco.commit()

    painel = client.get("/revisao/painel")

    assert painel.status_code == 200
    idx_critico = painel.text.find("TOKEN_SLA_CRITICO")
    idx_atencao = painel.text.find("TOKEN_SLA_ATENCAO")
    idx_ok = painel.text.find("TOKEN_SLA_OK")
    assert idx_critico != -1
    assert idx_atencao != -1
    assert idx_ok != -1
    assert idx_critico < idx_atencao < idx_ok


def test_revisor_painel_em_andamento_exibe_chip_sla_critico(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.criado_em = datetime.now(timezone.utc) - timedelta(hours=50, minutes=3)
        banco.commit()

    painel = client.get("/revisao/painel")

    assert painel.status_code == 200
    assert "sla-critico" in painel.text
    assert "Em campo h" in painel.text


def test_inspetor_com_senha_temporaria_e_obrigado_a_trocar_no_primeiro_login(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    nova_senha = "InspetorNova@123"

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "inspetor@empresa-a.test"))
        assert usuario is not None
        usuario.senha_temporaria_ativa = True
        banco.commit()

    tela_login = client.get("/app/login")
    csrf_login = _extrair_csrf(tela_login.text)
    resposta_login = client.post(
        "/app/login",
        data={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "csrf_token": csrf_login,
        },
        follow_redirects=False,
    )
    assert resposta_login.status_code == 303
    assert resposta_login.headers["location"] == "/app/trocar-senha"

    tela_troca = client.get("/app/trocar-senha")
    assert tela_troca.status_code == 200
    csrf_troca = _extrair_csrf(tela_troca.text)

    resposta_troca = client.post(
        "/app/trocar-senha",
        data={
            "senha_atual": SENHA_PADRAO,
            "nova_senha": nova_senha,
            "confirmar_senha": nova_senha,
            "csrf_token": csrf_troca,
        },
        follow_redirects=False,
    )
    assert resposta_troca.status_code == 303
    assert resposta_troca.headers["location"] == "/app/"

    acesso = client.get("/app/", follow_redirects=False)
    assert acesso.status_code == 200

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "inspetor@empresa-a.test"))
        assert usuario is not None
        assert usuario.senha_temporaria_ativa is False
        assert verificar_senha(nova_senha, usuario.senha_hash)


def test_revisor_com_senha_temporaria_e_obrigado_a_trocar_no_primeiro_login(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    nova_senha = "RevisorNova@123"

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "revisor@empresa-a.test"))
        assert usuario is not None
        usuario.senha_temporaria_ativa = True
        banco.commit()

    tela_login = client.get("/revisao/login")
    csrf_login = _extrair_csrf(tela_login.text)
    resposta_login = client.post(
        "/revisao/login",
        data={
            "email": "revisor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "csrf_token": csrf_login,
        },
        follow_redirects=False,
    )
    assert resposta_login.status_code == 303
    assert resposta_login.headers["location"] == "/revisao/trocar-senha"

    tela_troca = client.get("/revisao/trocar-senha")
    assert tela_troca.status_code == 200
    csrf_troca = _extrair_csrf(tela_troca.text)

    resposta_troca = client.post(
        "/revisao/trocar-senha",
        data={
            "senha_atual": SENHA_PADRAO,
            "nova_senha": nova_senha,
            "confirmar_senha": nova_senha,
            "csrf_token": csrf_troca,
        },
        follow_redirects=False,
    )
    assert resposta_troca.status_code == 303
    assert resposta_troca.headers["location"] == "/revisao/painel"

    painel = client.get("/revisao/painel", follow_redirects=False)
    assert painel.status_code == 200

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "revisor@empresa-a.test"))
        assert usuario is not None
        assert usuario.senha_temporaria_ativa is False
        assert verificar_senha(nova_senha, usuario.senha_hash)


def test_admin_com_senha_temporaria_e_obrigado_a_trocar_no_primeiro_login(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    nova_senha = "AdminNova@123"

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "admin@empresa-a.test"))
        assert usuario is not None
        usuario.senha_temporaria_ativa = True
        banco.commit()

    tela_login = client.get("/admin/login")
    csrf_login = _extrair_csrf(tela_login.text)
    resposta_login = client.post(
        "/admin/login",
        data={
            "email": "admin@empresa-a.test",
            "senha": SENHA_PADRAO,
            "csrf_token": csrf_login,
        },
        follow_redirects=False,
    )
    assert resposta_login.status_code == 303
    assert resposta_login.headers["location"] == "/admin/trocar-senha"

    tela_troca = client.get("/admin/trocar-senha")
    assert tela_troca.status_code == 200
    csrf_troca = _extrair_csrf(tela_troca.text)

    resposta_troca = client.post(
        "/admin/trocar-senha",
        data={
            "senha_atual": SENHA_PADRAO,
            "nova_senha": nova_senha,
            "confirmar_senha": nova_senha,
            "csrf_token": csrf_troca,
        },
        follow_redirects=False,
    )
    assert resposta_troca.status_code == 303
    assert resposta_troca.headers["location"] == "/admin/mfa/challenge"

    tela_mfa = client.get("/admin/mfa/challenge", follow_redirects=False)
    assert tela_mfa.status_code == 200
    csrf_mfa = _extrair_csrf(tela_mfa.text)
    resposta_mfa = client.post(
        "/admin/mfa/challenge",
        data={
            "codigo": current_totp(ADMIN_TOTP_SECRET),
            "csrf_token": csrf_mfa,
        },
        follow_redirects=False,
    )
    assert resposta_mfa.status_code == 303
    assert resposta_mfa.headers["location"] == "/admin/painel"

    painel = client.get("/admin/painel", follow_redirects=False)
    assert painel.status_code == 200

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "admin@empresa-a.test"))
        assert usuario is not None
        assert usuario.senha_temporaria_ativa is False
        assert verificar_senha(nova_senha, usuario.senha_hash)


def test_admin_metricas_grafico_retorna_json(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")
    resposta = client.get("/admin/api/metricas-grafico")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert isinstance(corpo.get("labels"), list)
    assert isinstance(corpo.get("valores"), list)
    assert len(corpo["labels"]) == len(corpo["valores"])


def test_iniciar_relatorio_rejeita_tipo_template_desconhecido(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "template_inexistente"},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Tipo de relatório inválido."

    with SessionLocal() as banco:
        assert banco.query(Laudo).count() == 0


def test_iniciar_relatorio_exige_variante_catalogada_quando_runtime_esta_ambiguo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
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
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_exibicao="NR13 · Vaso de Pressão",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_oferta="NR13 Premium · Vaso de Pressão",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Vaso crítico",
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[
                "catalog:nr13_inspecao_caldeira:premium_campo",
                "catalog:nr13_inspecao_vaso_pressao:premium_campo",
            ],
            admin_id=ids["admin_a"],
        )
        banco.commit()

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    home = client.get("/app/", follow_redirects=False)
    assert home.status_code == 200
    assert "catalog:nr13_inspecao_caldeira:premium_campo" in home.text
    assert "NR13 · Caldeira · Premium campo" in home.text

    resposta_ambigua = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "nr13"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_ambigua.status_code == 403
    assert "variante comercial" in resposta_ambigua.json()["detail"].lower()

    resposta_ok = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "catalog:nr13_inspecao_caldeira:premium_campo"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_ok.status_code == 200
    laudo_id = int(resposta_ok.json()["laudo_id"])

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.tipo_template == "nr13"
        assert laudo.catalog_family_key == "nr13_inspecao_caldeira"
        assert laudo.catalog_variant_key == "premium_campo"


def test_iniciar_relatorio_catalogado_persiste_snapshot_imutavel_no_laudo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
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
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=["catalog:nr13_inspecao_caldeira:premium_campo"],
            admin_id=ids["admin_a"],
        )
        banco.commit()

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "catalog:nr13_inspecao_caldeira:premium_campo"},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    laudo_id = int(resposta.json()["laudo_id"])

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.catalog_selection_token == "catalog:nr13_inspecao_caldeira:premium_campo"
        assert isinstance(laudo.catalog_snapshot_json, dict)
        assert laudo.catalog_snapshot_json["selection_token"] == "catalog:nr13_inspecao_caldeira:premium_campo"
        assert laudo.catalog_snapshot_json["family"]["key"] == "nr13_inspecao_caldeira"
        assert laudo.catalog_snapshot_json["variant"]["key"] == "premium_campo"
        assert "laudo_output_seed" in laudo.catalog_snapshot_json["artifacts"]
        assert "template_master_seed" in laudo.catalog_snapshot_json["artifact_hashes"]
        assert isinstance(laudo.pdf_template_snapshot_json, dict)
        assert laudo.pdf_template_snapshot_json["template_ref"]["codigo_template"]
        assert laudo.pdf_template_snapshot_json["template_ref"]["versao"] >= 1


def test_pdf_governado_permanece_emitivel_com_snapshot_apos_mudanca_no_catalogo(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
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
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=["catalog:nr13_inspecao_caldeira:premium_campo"],
            admin_id=ids["admin_a"],
        )
        banco.commit()

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_inicio = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "catalog:nr13_inspecao_caldeira:premium_campo"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_inicio.status_code == 200
    laudo_id = int(resposta_inicio.json()["laudo_id"])

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspecao congelada para validar snapshot"
        laudo.parecer_ia = "Snapshot do laudo deve manter o documento emitivel."
        laudo.dados_formulario = {"resumo_executivo": "Documento congelado do snapshot."}
        template_code_original = str(laudo.pdf_template_snapshot_json["template_ref"]["codigo_template"]).lower()
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[],
            admin_id=ids["admin_a"],
        )
        banco.commit()

    monkeypatch.setattr(
        catalog_pdf_templates,
        "_load_family_template_seed",
        lambda _family_key: {
            "template_code": "catalogo_alterado_em_disco",
            "versao": 99,
            "modo_editor": "editor_rico",
        },
    )
    monkeypatch.setattr(
        catalog_pdf_templates,
        "_load_family_output_seed",
        lambda _family_key: {
            "schema_type": "laudo_output",
            "schema_version": 1,
            "family_key": "nr13_inspecao_caldeira",
            "template_code": "catalogo_alterado_em_disco",
            "tokens": {"cliente_nome": "Empresa Demo (DEV)"},
        },
    )

    resposta_pdf = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf},
        json={
            "diagnostico": "Emissao congelada",
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
    assert template_code_original in str(resposta_pdf.headers.get("content-disposition", "")).lower()


def test_inspetor_nao_pode_finalizar_laudo_nao_rascunho(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Laudo já foi enviado ou finalizado."


def test_inspetor_gate_qualidade_endpoint_reprova_sem_evidencias(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.get(
        f"/app/api/laudo/{laudo_id}/gate-qualidade",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "GATE_QUALIDADE_REPROVADO"
    assert corpo["aprovado"] is False
    assert corpo["tipo_template"] == "padrao"
    assert isinstance(corpo["faltantes"], list)
    assert len(corpo["faltantes"]) >= 1
    assert corpo["roteiro_template"]["titulo"] == "Roteiro obrigatório do template"
    assert isinstance(corpo["roteiro_template"]["itens"], list)
    assert len(corpo["roteiro_template"]["itens"]) >= 5


def test_inspetor_gate_qualidade_cbmgo_expoe_roteiro_com_formulario(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="cbmgo",
        )

    resposta = client.get(
        f"/app/api/laudo/{laudo_id}/gate-qualidade",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["tipo_template"] == "cbmgo"
    faltantes_ids = {item["id"] for item in corpo["faltantes"]}
    assert "formulario_estruturado" in faltantes_ids

    roteiro_ids = {item["id"] for item in corpo["roteiro_template"]["itens"]}
    assert "roteiro_formulario_estruturado" in roteiro_ids
    assert "cbmgo_formulario_estruturado" in roteiro_ids


def test_inspetor_finalizacao_bloqueada_por_gate_qualidade(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    detalhe = corpo.get("detail", {})
    assert detalhe["codigo"] == "GATE_QUALIDADE_REPROVADO"
    assert detalhe["aprovado"] is False
    assert isinstance(detalhe["itens"], list)
    assert isinstance(detalhe["faltantes"], list)
    assert len(detalhe["faltantes"]) >= 1

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.RASCUNHO.value


def test_inspetor_finalizacao_permite_override_humano_governado_no_gate(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr13",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr13_inspecao_vaso_pressao"
        laudo.catalog_family_label = "NR13 Inspecao de Vaso de Pressao"
        laudo.primeira_mensagem = "Inspecao NR13 com rastreabilidade suficiente e uma evidencia complementar pendente."
        laudo.dados_formulario = {
            "schema_type": "laudo_output",
            "family_key": "nr13_inspecao_vaso_pressao",
            "identificacao": {"identificacao_do_vaso": "VP-700"},
            "documentacao_e_registros": {
                "prontuario": {
                    "referencias_texto": "DOC-700.pdf",
                },
            },
            "conclusao": {
                "status": "ajuste",
            },
        }
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=int(laudo_id),
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Equipamento VP-700 inspecionado em campo com foco em integridade e prontuario.",
                ),
                MensagemLaudo(
                    laudo_id=int(laudo_id),
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada limitacao controlada na evidencia complementar fotografica.",
                ),
                MensagemLaudo(
                    laudo_id=int(laudo_id),
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=int(laudo_id),
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Documento enviado: DOC-700.pdf",
                ),
                MensagemLaudo(
                    laudo_id=int(laudo_id),
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: o caso exige uma validacao humana antes do envio final.",
                ),
            ]
        )
        banco.commit()

    resposta_bloqueio = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta_bloqueio.status_code == 422
    detalhe_bloqueio = resposta_bloqueio.json()["detail"]
    assert detalhe_bloqueio["human_override_policy"]["available"] is True
    assert (
        "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade"
        in detalhe_bloqueio["human_override_policy"]["matched_override_cases"]
    )

    resposta_override = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
        data={
            "quality_gate_override": "true",
            "quality_gate_override_reason": (
                "O inspetor validou manualmente a conclusão com rastreabilidade textual suficiente "
                "e assumiu a responsabilidade técnica pela decisão."
            ),
        },
    )

    assert resposta_override.status_code == 200
    corpo = resposta_override.json()
    assert corpo["review_mode_final"] == "mesa_required"
    assert corpo["human_override_summary"]["latest"]["reason"].startswith(
        "O inspetor validou manualmente"
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        quality_gates = dict((laudo.report_pack_draft_json or {}).get("quality_gates") or {})
        override_payload = dict(quality_gates.get("human_override") or {})
        assert override_payload["reason"].startswith("O inspetor validou manualmente")


def test_inspetor_finalizacao_aprovada_com_evidencias_minimas(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspeção inicial em painel elétrico da área de prensas."

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Verifiquei risco de aquecimento em conexões do quadro principal.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: existe não conformidade e recomenda-se isolamento imediato.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["success"] is True

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value


def test_inspetor_finalizacao_aprovada_quando_imagem_real_vem_do_chat_com_texto(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspeção inicial em cabine elétrica da linha 3."

        mensagem_usuario = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["inspetor_a"],
            tipo=TipoMensagem.USER.value,
            conteudo="Registrei aquecimento anormal no borne principal e anexei foto da evidência.",
        )
        banco.add(mensagem_usuario)
        banco.flush()
        banco.add(
            AprendizadoVisualIa(
                empresa_id=ids["empresa_a"],
                laudo_id=laudo_id,
                mensagem_referencia_id=int(mensagem_usuario.id),
                criado_por_id=ids["inspetor_a"],
                setor_industrial="geral",
                resumo="Evidência visual do borne principal",
                descricao_contexto="Imagem coletada no chat do inspetor para suportar a conclusão técnica.",
                correcao_inspetor="Imagem anexada durante a coleta principal.",
                veredito_inspetor="duvida",
                imagem_url="/static/uploads/aprendizados_ia/teste/chat-evidencia.png",
                imagem_nome_original="chat-evidencia.png",
                imagem_mime_type="image/png",
                imagem_sha256=uuid.uuid4().hex,
                caminho_arquivo="/tmp/chat-evidencia.png",
            )
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer preliminar: a foto confirma degradação térmica e exige revisão da conexão.",
            )
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["success"] is True
    assert corpo["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr13(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr13",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr13_inspecao_vaso_pressao"
        laudo.catalog_family_label = "NR13 · Vaso de Pressao"
        laudo.catalog_variant_key = "premium_campo"
        laudo.catalog_variant_label = "Premium campo"
        laudo.primeira_mensagem = "Inspecao inicial em vaso vertical VP-204"
        laudo.parecer_ia = "Foi observada corrosao superficial localizada, sem vazamentos aparentes."
        laudo.dados_formulario = {
            "local_inspecao": "Casa de utilidades - Bloco B",
            "nome_equipamento": "Vaso vertical VP-204",
            "tag_patrimonial": "TAG-VP-204",
            "placa_identificacao": "IMG_001 - placa parcialmente legivel com confirmacao no prontuario.",
            "pontos_de_corrosao": "Corrosao superficial proxima ao suporte inferior.",
            "vazamentos": "Nao foram observados sinais aparentes de vazamento.",
            "dispositivos_de_seguranca": "Dispositivos de seguranca visiveis e sem anomalia aparente.",
            "manometro": "Manometro com visor legivel.",
            "valvula_seguranca": "Valvula instalada e acessivel para leitura local.",
            "prontuario": "DOC_014 - prontuario_vp204.pdf",
            "certificado": "Nao apresentado",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Equipamento localizado em casa de utilidades com placa parcialmente legivel.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Dispositivos de seguranca visiveis e sem vazamento aparente no momento da coleta.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: ajustar protecao superficial e manter acompanhamento do ponto de corrosao.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr13_inspecao_vaso_pressao"
        assert laudo.dados_formulario["identificacao"]["identificacao_do_vaso"] == "Vaso vertical VP-204"
        assert laudo.dados_formulario["documentacao_e_registros"]["prontuario"]["referencias_texto"] == "DOC_014 - prontuario_vp204.pdf"
        assert laudo.dados_formulario["nao_conformidades"]["ha_nao_conformidades"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr10(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr10",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr10_inspecao_instalacoes_eletricas"
        laudo.catalog_family_label = "NR10 · Instalacoes eletricas"
        laudo.catalog_variant_key = "prime_site"
        laudo.catalog_variant_label = "Prime site"
        laudo.primeira_mensagem = "Inspecao inicial no painel eletrico QGBT-07 da area de prensas"
        laudo.parecer_ia = "Foi identificado aquecimento localizado no borne principal e lacuna de identificacao em circuitos secundarios."
        laudo.dados_formulario = {
            "local_inspecao": "Area de prensas - painel QGBT-07",
            "objeto_principal": "Painel eletrico QGBT-07",
            "codigo_interno": "QGBT-07",
            "referencia_principal": "IMG_301 - frontal do QGBT-07",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao visual com apoio de termografia e checklist NR10.",
            "condicoes_gerais": "Painel com aquecimento localizado nas conexoes do disjuntor principal.",
            "quadro_principal": "QGBT-07 com alimentacao das prensas e da iluminacao de emergencia.",
            "circuitos_criticos": "Prensas 1 e 2, iluminacao de emergencia e exaustao.",
            "aterramento": "Barramento PE presente, com necessidade de reaperto em derivacao secundaria.",
            "protecao_eletrica": "Disjuntores identificados, sem seletividade documental anexada.",
            "evidencia_principal": "IMG_302 - hotspot no borne principal",
            "evidencia_complementar": "IMG_303 - barramento de aterramento",
            "pie": "DOC_041 - pie_planta_prensas.pdf",
            "diagrama_unifilar": "DOC_042 - diagrama_qgbt07.pdf",
            "descricao_pontos_atencao": "Aquecimento anormal no borne principal e identificacao parcial dos circuitos secundarios.",
            "observacoes": "Programar reaperto, revisar identificacao dos circuitos e atualizar o prontuario eletrico.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Painel localizado na area de prensas com acesso liberado para avaliacao frontal.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="A termografia indicou aquecimento no borne principal e a identificacao dos circuitos secundarios esta incompleta.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: executar ajuste corretivo no borne principal e atualizar a identificacao dos circuitos.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr10_inspecao_instalacoes_eletricas"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Painel eletrico QGBT-07"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "painel_eletrico"
        assert "PIE:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr10_prontuario(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr10",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr10_prontuario_instalacoes_eletricas"
        laudo.catalog_family_label = "NR10 · Prontuario instalacoes eletricas"
        laudo.catalog_variant_key = "prime_documental"
        laudo.catalog_variant_label = "Prime documental"
        laudo.primeira_mensagem = "Consolidacao do prontuario eletrico do painel QGBT-07 da area de prensas"
        laudo.parecer_ia = "Prontuario consolidado, mas ainda depende de anexar a ART de atualizacao do diagrama unifilar."
        laudo.dados_formulario = {
            "localizacao": "Area de prensas - painel QGBT-07",
            "objeto_principal": "Prontuario eletrico do painel QGBT-07",
            "codigo_interno": "PRT-QGBT-07",
            "numero_prontuario": "PRT-QGBT-07",
            "referencia_principal": "DOC_301 - indice_prontuario_qgbt07.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Consolidacao documental do prontuario NR10 com validacao do indice, diagramas e inventario de circuitos.",
            "status_documentacao": "Documentacao principal consolidada com pendencia na ART da ultima revisao.",
            "prontuario": "DOC_301 - indice_prontuario_qgbt07.pdf",
            "inventario_instalacoes": "DOC_302 - inventario_circuitos_qgbt07.xlsx",
            "diagrama_unifilar": "DOC_303 - diagrama_qgbt07_rev04.pdf",
            "pie": "DOC_304 - pie_prensas_rev02.pdf",
            "procedimento_trabalho": "DOC_305 - procedimento_intervencao_qgbt07.pdf",
            "memorial_descritivo": "DOC_306 - memorial_qgbt07.pdf",
            "art_numero": "ART 2026-00411",
            "evidencia_principal": "DOC_303 - diagrama_qgbt07_rev04.pdf",
            "descricao_pontos_atencao": "Pendencia de anexar a ART de atualizacao do diagrama unifilar revisado.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Anexar a ART da revisao do diagrama, atualizar o indice e reemitir o prontuario.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Prontuario eletrico do QGBT-07 consolidado com indice, inventario de circuitos e procedimento de intervencao.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Permanece pendente anexar a ART de atualizacao do diagrama unifilar revisado.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: anexar a ART da ultima revisao e reemitir o prontuario consolidado.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr10_prontuario_instalacoes_eletricas"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Prontuario eletrico do painel QGBT-07"
        assert laudo.dados_formulario["escopo_servico"]["tipo_entrega"] == "pacote_documental"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "analise_documental"
        assert "PIE:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr18_canteiro_obra(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr18_inspecao_canteiro_obra"
        laudo.catalog_family_label = "NR18 · Canteiro de obra"
        laudo.catalog_variant_key = "prime_obra"
        laudo.catalog_variant_label = "Prime obra"
        laudo.primeira_mensagem = "Inspecao inicial no canteiro da obra vertical Torre Norte"
        laudo.parecer_ia = "Foi identificada guarda-corpo incompleta no pavimento superior e necessidade de reforcar a sinalizacao de circulacao de pedestres."
        laudo.dados_formulario = {
            "local_inspecao": "Canteiro Torre Norte - pavimentos 1 a 4",
            "objeto_principal": "Canteiro da obra vertical Torre Norte",
            "codigo_interno": "OBR-TN-01",
            "referencia_principal": "IMG_1101 - vista geral do canteiro Torre Norte",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo com checklist NR18, registro fotografico e leitura das frentes simultaneas.",
            "condicoes_gerais": "Frentes ativas com protecao coletiva parcial no pavimento superior e circulacao de pedestres compartilhando area de descarga.",
            "etapa_obra": "Estrutura e alvenaria simultaneas",
            "protecao_periferica": "Guarda-corpo ausente em trecho da periferia do pavimento 4.",
            "circulacao": "Fluxo de pedestres cruzando area de descarga sem segregacao completa.",
            "sinalizacao": "Sinalizacao de circulacao de pedestres incompleta proxima ao guincho.",
            "areas_vivencia": "Vestiario e refeitório organizados e sinalizados.",
            "maquinas_equipamentos": "Grua e elevador cremalheira operando na rotina da frente.",
            "evidencia_principal": "IMG_1102 - trecho sem guarda-corpo no pavimento 4",
            "evidencia_complementar": "IMG_1103 - circulacao compartilhada proxima a descarga",
            "pgr_obra": "DOC_1101 - pgr_torre_norte_rev03.pdf",
            "apr": "DOC_1102 - apr_frente_estrutura_pav4.pdf",
            "descricao_pontos_atencao": "Trecho sem guarda-corpo no pavimento superior e segregacao incompleta da circulacao de pedestres.",
            "observacoes": "Regularizar a protecao coletiva e reordenar o fluxo de pedestres antes da proxima frente simultanea.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Canteiro Torre Norte com frentes simultaneas de estrutura e alvenaria entre os pavimentos 1 e 4.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observado trecho sem guarda-corpo no pavimento 4 e circulacao de pedestres cruzando a area de descarga.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: recompor a protecao coletiva e reforcar a segregacao da circulacao antes da proxima frente simultanea.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr18_inspecao_canteiro_obra"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Canteiro da obra vertical Torre Norte"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "canteiro_obra"
        assert "APR:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr18_frente_construcao(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr18_inspecao_frente_construcao"
        laudo.catalog_family_label = "NR18 · Frente de construcao"
        laudo.catalog_variant_key = "prime_obra"
        laudo.catalog_variant_label = "Prime obra"
        laudo.primeira_mensagem = "Inspecao na frente de concretagem do bloco B"
        laudo.parecer_ia = "Frente de concretagem liberada com ressalva pela necessidade de reorganizar o isolamento da vala lateral."
        laudo.dados_formulario = {
            "local_inspecao": "Bloco B - frente de concretagem da ala oeste",
            "objeto_principal": "Frente de concretagem bloco B ala oeste",
            "codigo_interno": "FRN-B-OESTE",
            "referencia_principal": "IMG_1201 - vista geral da frente ala oeste",
            "modo_execucao": "in loco",
            "metodo_aplicado": "Inspecao de campo da frente de construcao com checklist NR18 e verificacao do isolamento operacional.",
            "condicoes_observadas": "Frente com fôrmas montadas, acesso controlado e vala lateral com isolamento incompleto.",
            "etapa_obra": "Concretagem de vigas e laje",
            "escavacoes": "Vala lateral sem barreira continua no trecho de acesso secundario.",
            "circulacao": "Acesso principal segregado, com desvio temporario sinalizado parcialmente.",
            "sinalizacao": "Placas de desvio presentes, mas sem repeticao no acesso secundario.",
            "maquinas_equipamentos": "Bomba de concreto e vibradores operando na frente.",
            "evidencia_principal": "IMG_1202 - vala lateral sem barreira continua",
            "evidencia_complementar": "IMG_1203 - acesso secundario com sinalizacao parcial",
            "pgr_obra": "DOC_1201 - pgr_bloco_b.pdf",
            "apr": "DOC_1202 - apr_concretagem_bloco_b.pdf",
            "pte": "DOC_1203 - permissao_concretagem_bloco_b.pdf",
            "conclusao": {"status": "Liberado com restricoes"},
            "descricao_pontos_atencao": "Necessidade de recompor o isolamento continuo da vala lateral antes do turno noturno.",
            "observacoes": "Regularizar o isolamento e repetir a verificacao antes da retomada do concreto no turno seguinte.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Frente de concretagem bloco B em andamento com fôrmas montadas e bomba de concreto posicionada.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi identificada vala lateral sem barreira continua no acesso secundario da frente.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: recompor o isolamento continuo da vala lateral e repetir a verificacao antes do turno noturno.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr18_inspecao_frente_construcao"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Frente de concretagem bloco B ala oeste"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "frente_construcao"
        assert "PTE:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr22_area_mineracao(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr22_inspecao_area_mineracao"
        laudo.catalog_family_label = "NR22 · Area de mineracao"
        laudo.catalog_variant_key = "prime_mineracao"
        laudo.catalog_variant_label = "Prime mineracao"
        laudo.primeira_mensagem = "Inspecao na area de lavra da cava norte bancada 3"
        laudo.parecer_ia = "Foram identificadas drenagem superficial parcial e sinalizacao incompleta na rota de pedestres da cava norte."
        laudo.dados_formulario = {
            "local_inspecao": "Cava Norte - bancada 3",
            "objeto_principal": "Area de lavra Cava Norte - bancada 3",
            "codigo_interno": "MIN-CN-B3",
            "referencia_principal": "IMG_2101 - vista geral da cava norte bancada 3",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em area de mineracao com checklist NR22, leitura das frentes de lavra e verificacao visual das bancadas.",
            "condicoes_gerais": "Frente ativa com drenagem superficial parcial, talude principal monitorado e rota de pedestres com sinalizacao insuficiente.",
            "fase_operacional": "Lavra e carregamento",
            "estabilidade_taludes": "Talude principal monitorado com pequena fissura superficial sem deslocamento aparente.",
            "drenagem": "Canaleta lateral parcial com necessidade de recomposicao antes de nova chuva forte.",
            "trafego_equipamentos": "Fluxo de caminhoes fora de estrada cruzando a rota de pedestres em um ponto sem segregacao completa.",
            "sinalizacao": "Sinalizacao de rota de pedestres incompleta proxima ao acesso da bancada 3.",
            "evidencia_principal": "IMG_2102 - canaleta lateral parcial na bancada 3",
            "evidencia_complementar": "IMG_2103 - rota de pedestres sem segregacao completa",
            "pgr_mineracao": "DOC_2101 - pgr_mineracao_cava_norte_rev05.pdf",
            "plano_emergencia": "DOC_2102 - plano_emergencia_cava_norte.pdf",
            "mapa_risco": "DOC_2103 - mapa_geotecnico_cava_norte.pdf",
            "descricao_pontos_atencao": "Drenagem superficial parcial e sinalizacao incompleta na rota de pedestres da bancada 3.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Recompor a drenagem lateral e reforcar a segregacao da rota de pedestres antes do proximo turno chuvoso.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Area de lavra da cava norte em operacao na bancada 3 com trafego simultaneo de caminhoes e equipe de campo.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada drenagem lateral parcial e sinalizacao insuficiente na rota de pedestres da bancada.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: recompor a drenagem e reforcar a sinalizacao da rota de pedestres antes da proxima frente chuvosa.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr22_inspecao_area_mineracao"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Area de lavra Cava Norte - bancada 3"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "area_mineracao"
        assert "Plano emergencia:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr22_instalacao_mineira(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr22_inspecao_instalacao_mineira"
        laudo.catalog_family_label = "NR22 · Instalacao mineira"
        laudo.catalog_variant_key = "prime_mineracao"
        laudo.catalog_variant_label = "Prime mineracao"
        laudo.primeira_mensagem = "Inspecao na britagem primaria BM-02"
        laudo.parecer_ia = "Foi identificada protecao parcial na correia C-04 e falta de identificacao completa dos pontos de bloqueio de energia."
        laudo.dados_formulario = {
            "local_inspecao": "Britagem primaria BM-02",
            "objeto_principal": "Instalacao mineira BM-02 - britagem primaria",
            "codigo_interno": "BM-02",
            "referencia_principal": "IMG_2201 - vista geral da britagem BM-02",
            "modo_execucao": "in loco",
            "metodo_aplicado": "Inspecao de campo em instalacao mineira com checklist NR22, verificacao operacional, bloqueios, acessos e protecoes mecanicas.",
            "condicoes_observadas": "Britagem em operacao com acessos organizados, mas correia C-04 sem protecao completa e pontos LOTO sem identificacao total.",
            "tipo_instalacao": "Britagem primaria",
            "bloqueio_energia": "Pontos de bloqueio de energia presentes, sem identificacao completa no painel local.",
            "ventilacao_exaustao": "Sistema de exaustao ativo com acúmulo leve de particulado no enclausuramento.",
            "acessos_passarelas": "Passarelas e guarda-corpos íntegros na rota principal de inspeção.",
            "correias_transportadoras": "Correia C-04 operando sem proteção integral no retorno inferior.",
            "combate_incendio": "Extintores e hidrantes inspecionados e dentro da validade.",
            "manutencao": "Rotina preventiva em dia com OS aberta para ajuste do enclausuramento.",
            "evidencia_principal": "IMG_2202 - retorno inferior da correia C-04 sem proteção integral",
            "evidencia_complementar": "IMG_2203 - painel local sem identificação completa dos pontos LOTO",
            "pgr_mineracao": "DOC_2201 - pgr_britagem_rev04.pdf",
            "procedimento_operacional": "DOC_2202 - procedimento_britagem_bm02.pdf",
            "plano_emergencia": "DOC_2203 - plano_emergencia_beneficiamento.pdf",
            "pte": "DOC_2204 - permissao_intervencao_bm02.pdf",
            "descricao_pontos_atencao": "Protecao parcial na correia C-04 e identificacao incompleta dos pontos de bloqueio de energia.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Completar a proteção da correia e revisar a identificação LOTO antes da próxima intervenção corretiva.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Britagem primaria BM-02 operando em rotina normal com correia C-04, passarelas e painel local acessiveis para a vistoria.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada proteção parcial no retorno inferior da correia C-04 e identificação incompleta dos pontos de bloqueio de energia.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: completar a proteção da correia e revisar a identificação LOTO antes da próxima intervenção corretiva.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr22_inspecao_instalacao_mineira"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Instalacao mineira BM-02 - britagem primaria"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "instalacao_mineira"
        assert "PTE:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr29_operacao_portuaria(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr29_inspecao_operacao_portuaria"
        laudo.catalog_family_label = "NR29 · Operacao portuaria"
        laudo.catalog_variant_key = "prime_porto"
        laudo.catalog_variant_label = "Prime porto"
        laudo.primeira_mensagem = "Inspecao na operacao de descarga do berco 5 terminal leste"
        laudo.parecer_ia = "Foi identificada area de pedestres sem segregacao completa proxima ao guindaste movel e sinalizacao parcial no acesso ao cais."
        laudo.dados_formulario = {
            "local_inspecao": "Terminal Leste - berco 5",
            "objeto_principal": "Operacao de descarga no berco 5 do terminal leste",
            "codigo_interno": "PORTO-B5-2026",
            "referencia_principal": "IMG_2901 - vista geral da operacao no berco 5",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em operacao portuaria com checklist NR29, verificacao de equipamentos, fluxos de carga e acessos ao cais.",
            "condicoes_gerais": "Operacao em andamento com guindaste movel, fluxo de caminhes e area de pedestres com segregacao parcial proxima ao berco.",
            "tipo_operacao": "Descarga de bobinas de aco",
            "equipamento_portuario": "Guindaste movel MHC-04",
            "movimentacao_carga": "Bobinas descarregadas do porao 2 para carretas no patio temporario.",
            "acesso_cais": "Acesso principal sinalizado, com cruzamento pontual de pedestres proximo a area de descarga.",
            "sinalizacao": "Sinalizacao parcial no corredor lateral de pedestres.",
            "amarracao": "Atracacao e amarracao estaveis durante a vistoria.",
            "comunicacao_operacional": "Comunicacao por radio entre equipe de bordo e operador do guindaste.",
            "condicoes_piso": "Piso do cais regular, com marca de oleo seca sem escorregamento no trecho lateral.",
            "evidencia_principal": "IMG_2902 - corredor de pedestres sem segregacao completa",
            "evidencia_complementar": "IMG_2903 - operacao do guindaste MHC-04 no berco 5",
            "pgr_portuario": "DOC_2901 - pgr_portuario_terminal_leste_rev03.pdf",
            "apr": "DOC_2902 - apr_descarga_bobinas_berco5.pdf",
            "procedimento_operacional": "DOC_2903 - procedimento_descarga_bobinas.pdf",
            "plano_emergencia": "DOC_2904 - plano_emergencia_terminal_leste.pdf",
            "descricao_pontos_atencao": "Segregacao incompleta de pedestres proxima a area de descarga e sinalizacao parcial no acesso lateral do cais.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Reforcar a segregacao de pedestres e completar a sinalizacao lateral antes da proxima janela operacional.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Operacao de descarga em andamento no berco 5 com guindaste movel, equipe de bordo e carretas no patio temporario.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada segregacao incompleta de pedestres proxima a area de descarga e sinalizacao parcial no corredor lateral do cais.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: reforcar a segregacao de pedestres e completar a sinalizacao lateral antes da proxima janela operacional.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr29_inspecao_operacao_portuaria"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Operacao de descarga no berco 5 do terminal leste"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "operacao_portuaria"
        assert "Procedimento:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr30_trabalho_aquaviario(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr30_inspecao_trabalho_aquaviario"
        laudo.catalog_family_label = "NR30 · Trabalho aquaviario"
        laudo.catalog_variant_key = "prime_aquaviario"
        laudo.catalog_variant_label = "Prime aquaviario"
        laudo.primeira_mensagem = "Inspecao na embarcacao Atlas durante transferencia no conves principal"
        laudo.parecer_ia = (
            "Foi identificada protecao parcial no acesso ao conves inferior e comunicacao operacional irregular durante a transferencia de carga."
        )
        laudo.dados_formulario = {
            "local_inspecao": "Embarcacao Atlas - conves principal",
            "objeto_principal": "Transferencia de carga na embarcacao Atlas",
            "codigo_interno": "AQUA-ATL-01",
            "referencia_principal": "IMG_3001 - vista geral do conves principal da Atlas",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em trabalho aquaviario com checklist NR30, verificacao de acessos, condicoes de bordo e controles de emergencia.",
            "condicoes_gerais": "Operacao em andamento com acesso ao conves inferior sem barreira completa e ruido alto prejudicando a comunicacao da equipe.",
            "tipo_embarcacao": "Carga geral",
            "atividade_bordo": "Transferencia de carga no conves principal",
            "acesso_embarcacao": "Escada de acesso lateral com trecho inferior sem protecao completa.",
            "coletes_epis": "Tripulacao com coletes e capacetes, com necessidade de reforcar uso de protetor auricular no trecho ruidoso.",
            "comunicacao_operacional": "Comunicacao por radio com falhas intermitentes entre conves principal e equipe de apoio.",
            "estabilidade_operacao": "Operacao mantida estavel durante a vistoria, sem oscilacao anormal da embarcacao.",
            "abandono_emergencia": "Rotas de abandono sinalizadas, com ponto de encontro confirmado no portal de bombordo.",
            "condicoes_conves": "Conves principal seco, com trecho de acesso inferior sem barreira completa.",
            "evidencia_principal": "IMG_3002 - acesso inferior sem protecao completa",
            "evidencia_complementar": "IMG_3003 - equipe em comunicacao por radio durante a transferencia",
            "pgr_embarcacao": "DOC_3001 - pgr_embarcacao_atlas_rev02.pdf",
            "apr": "DOC_3002 - apr_transferencia_carga_atlas.pdf",
            "procedimento_operacional": "DOC_3003 - procedimento_transferencia_conves.pdf",
            "plano_emergencia": "DOC_3004 - plano_emergencia_atlas.pdf",
            "checklist_bordo": "DOC_3005 - checklist_nr30_conves_principal.pdf",
            "descricao_pontos_atencao": "Acesso ao conves inferior sem protecao completa e comunicacao operacional irregular durante a transferencia de carga.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Regularizar a protecao do acesso inferior e revisar a redundancia de comunicacao antes da proxima transferencia.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Transferencia de carga em andamento na embarcacao Atlas com equipe distribuida entre conves principal e apoio lateral.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada protecao parcial no acesso ao conves inferior e falha intermitente na comunicacao por radio durante a operacao.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: regularizar a protecao do acesso inferior e revisar a redundancia de comunicacao antes da proxima transferencia.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr30_inspecao_trabalho_aquaviario"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Transferencia de carga na embarcacao Atlas"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "trabalho_aquaviario"
        assert "Checklist:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr31_frente_rural(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr31_inspecao_frente_rural"
        laudo.catalog_family_label = "NR31 · Frente rural"
        laudo.catalog_variant_key = "prime_rural"
        laudo.catalog_variant_label = "Prime rural"
        laudo.primeira_mensagem = "Inspecao na frente rural do talhao 7 da Fazenda Boa Esperanca"
        laudo.parecer_ia = (
            "Foi identificada protecao incompleta na tomada de forca do trator e armazenamento inadequado de defensivos proximo a area de vivencia."
        )
        laudo.dados_formulario = {
            "local_inspecao": "Fazenda Boa Esperanca - talhao 7",
            "objeto_principal": "Frente rural de colheita no talhao 7",
            "codigo_interno": "RURAL-T7-2026",
            "referencia_principal": "IMG_3101 - vista geral da frente de colheita no talhao 7",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em frente rural com checklist NR31, verificacao de maquinas, frentes de trabalho, areas de apoio e controles operacionais.",
            "condicoes_gerais": "Frente de colheita em operacao com trator e carreta, area de apoio provisoria e deposito de defensivos proximo ao refeitorio.",
            "cultura_atividade": "Colheita de cana-de-acucar",
            "maquinas_tratores": "Trator T-19 com tomada de forca sem protecao completa no eixo secundario.",
            "aplicacao_defensivos": "Pulverizacao encerrada no dia anterior, com embalagens vazias aguardando recolhimento.",
            "armazenamento_insumos": "Defensivos armazenados provisoriamente em abrigo sem segregacao adequada do ponto de refeicao.",
            "alojamento_apoio": "Area de apoio com sombra, agua e refeitorio improvisado a 30 metros da frente principal.",
            "abastecimento_agua": "Agua potavel disponivel em reservatorio identificado e protegido.",
            "transporte_trabalhadores": "Transporte interno realizado em caminhonete com lotacao controlada.",
            "sinalizacao": "Sinalizacao parcial no limite entre frente de maquinario e circulacao de pedestres.",
            "evidencia_principal": "IMG_3102 - tomada de forca com protecao parcial",
            "evidencia_complementar": "IMG_3103 - armazenamento provisório de defensivos proximo ao refeitorio",
            "pgr_rural": "DOC_3101 - pgr_rural_fazenda_boa_esperanca_rev03.pdf",
            "apr": "DOC_3102 - apr_colheita_talhao7.pdf",
            "procedimento_operacional": "DOC_3103 - procedimento_colheita_mecanizada.pdf",
            "treinamento_operadores": "DOC_3104 - treinamento_operadores_talhao7.pdf",
            "descricao_pontos_atencao": "Tomada de forca com protecao incompleta e armazenamento inadequado de defensivos proximo a area de vivencia.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Completar a protecao da tomada de forca e reorganizar o armazenamento de defensivos antes do proximo turno.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Frente rural de colheita em operacao no talhao 7 com trator, carreta de apoio e equipe distribuida entre frente e area de apoio.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada tomada de forca com protecao incompleta e armazenamento de defensivos proximo ao ponto de refeicao da equipe.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: completar a protecao da tomada de forca e reorganizar o armazenamento de defensivos antes do proximo turno.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr31_inspecao_frente_rural"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Frente rural de colheita no talhao 7"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "frente_rural"
        assert "Treinamento:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr32_inspecao_servico_saude(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr32_inspecao_servico_saude"
        laudo.catalog_family_label = "NR32 · Inspecao servico saude"
        laudo.catalog_variant_key = "prime_saude"
        laudo.catalog_variant_label = "Prime saude"
        laudo.primeira_mensagem = "Inspecao no centro de material e esterilizacao do Hospital Central"
        laudo.parecer_ia = "Foi identificada segregacao parcial de residuos e necessidade de reforcar o fluxo de perfurocortantes no CME."
        laudo.dados_formulario = {
            "local_inspecao": "Hospital Central - centro de material e esterilizacao",
            "objeto_principal": "CME do Hospital Central",
            "codigo_interno": "NR32-CME-01",
            "referencia_principal": "IMG_3201 - vista geral do CME do Hospital Central",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em servico de saude com checklist NR32, leitura de fluxos limpo/sujo e verificacao das barreiras de biosseguranca.",
            "condicoes_gerais": "Setor em operacao com segregacao funcional adequada, mas com ponto de descarte de perfurocortantes e segregacao de residuos precisando de reforco.",
            "setor_assistencial": "Centro de material e esterilizacao",
            "segregacao_residuos": "Segregacao presente, com coletor de residuos infectantes sem identificacao completa em uma das bancadas.",
            "perfurocortantes": "Caixa de perfurocortantes acima da linha recomendada em posto secundario.",
            "higienizacao": "Rotina de limpeza e desinfeccao registrada e atualizada.",
            "epc_epi": "Equipe com avental impermeavel, luvas e protetor facial disponiveis.",
            "fluxo_material_biologico": "Fluxo limpo/sujo definido, com um ponto de cruzamento temporario em horario de pico.",
            "sinalizacao": "Sinalizacao biossegura presente, com reforco necessario no posto secundario.",
            "evidencia_principal": "IMG_3202 - coletor de perfurocortantes no posto secundario",
            "evidencia_complementar": "IMG_3203 - bancada de segregacao de residuos do CME",
            "pgrss": "DOC_3201 - pgrss_hospital_central_rev06.pdf",
            "pcmso": "DOC_3202 - pcmso_hospital_central_2026.pdf",
            "procedimento_operacional": "DOC_3203 - procedimento_cme_fluxo_limpo_sujo.pdf",
            "plano_contingencia": "DOC_3204 - plano_contingencia_exposicao_biologica.pdf",
            "treinamento_equipe": "DOC_3205 - treinamento_biosseguranca_cme_2026.pdf",
            "descricao_pontos_atencao": "Segregacao parcial de residuos e caixa de perfurocortantes acima da linha recomendada no posto secundario.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Regularizar o descarte de perfurocortantes e reforcar a identificacao dos coletores do CME.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="CME do Hospital Central em operacao com fluxo limpo e sujo segregados e equipe em atividade na bancada secundaria.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada caixa de perfurocortantes acima da linha recomendada e coletor infectante sem identificacao completa no posto secundario.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: regularizar o descarte de perfurocortantes e reforcar a identificacao dos coletores do CME antes do proximo plantao.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr32_inspecao_servico_saude"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "CME do Hospital Central"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "servico_saude"
        assert "PGRSS:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr32_plano_risco_biologico(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr32_plano_risco_biologico"
        laudo.catalog_family_label = "NR32 · Plano risco biologico"
        laudo.catalog_variant_key = "prime_saude_documental"
        laudo.catalog_variant_label = "Prime saude documental"
        laudo.primeira_mensagem = "Analise documental do plano de risco biologico do Hospital Central"
        laudo.parecer_ia = (
            "O plano de risco biologico foi consolidado, mas ainda depende de fechar o protocolo de exposicao para o laboratorio de microbiologia."
        )
        laudo.dados_formulario = {
            "localizacao": "Hospital Central - laboratorio de microbiologia",
            "objeto_principal": "Plano de risco biologico do Hospital Central",
            "codigo_interno": "PRB-HC-2026",
            "numero_plano": "PRB-2026-04",
            "referencia_principal": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Analise documental do plano de risco biologico com consolidacao do inventario de agentes, protocolos de exposicao e planos de contingencia.",
            "status_documentacao": "Plano consolidado com pendencia de detalhar o protocolo de exposicao do laboratorio de microbiologia.",
            "plano_risco_biologico": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "mapa_risco_biologico": "DOC_3211 - mapa_risco_biologico_laboratorios.pdf",
            "inventario_agentes": "DOC_3212 - inventario_agentes_biologicos_2026.xlsx",
            "protocolo_exposicao": "DOC_3213 - protocolo_exposicao_acidentes_biologicos.docx",
            "plano_contingencia": "DOC_3214 - plano_contingencia_biologica_hc.pdf",
            "treinamento_equipe": "DOC_3215 - treinamento_biosseguranca_laboratorio_2026.pdf",
            "pgrss": "DOC_3216 - pgrss_hospital_central_rev06.pdf",
            "pcmso": "DOC_3217 - pcmso_hospital_central_2026.pdf",
            "art_numero": "ART 2026-00532",
            "evidencia_principal": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "descricao_pontos_atencao": "Detalhar o protocolo de exposicao do laboratorio de microbiologia e vincular a contingencia especifica ao plano consolidado.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Fechar o protocolo de exposicao do laboratorio e reemitir a revisao do plano de risco biologico.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Plano de risco biologico consolidado para o Hospital Central com inventario de agentes, mapa de risco e protocolo base de exposicao.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Permanece pendente detalhar o protocolo de exposicao do laboratorio de microbiologia e vincular a contingencia especifica ao documento final.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: fechar o protocolo de exposicao do laboratorio e reemitir a revisao do plano de risco biologico.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr32_plano_risco_biologico"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Plano de risco biologico do Hospital Central"
        assert laudo.dados_formulario["escopo_servico"]["tipo_entrega"] == "pacote_documental"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "analise_documental"
        assert "Inventario agentes:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr34_inspecao_frente_naval(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr34_inspecao_frente_naval"
        laudo.catalog_family_label = "NR34 · Frente naval"
        laudo.catalog_variant_key = "prime_naval"
        laudo.catalog_variant_label = "Prime naval"
        laudo.primeira_mensagem = "Inspecao na frente de reparacao naval do bloco 12 no Estaleiro Atlantico"
        laudo.parecer_ia = "Foi identificada ventilacao parcial no tanque lateral e isolamento incompleto da area de trabalho a quente no bloco 12."
        laudo.dados_formulario = {
            "local_inspecao": "Estaleiro Atlantico - doca 2 bloco 12",
            "objeto_principal": "Frente de reparacao naval do bloco 12",
            "codigo_interno": "NAV-B12-2026",
            "referencia_principal": "IMG_3401 - vista geral da frente naval do bloco 12",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em frente naval com checklist NR34, verificacao de trabalho a quente, ventilacao e segregacao da area operacional.",
            "condicoes_gerais": "Frente de reparacao em andamento com solda estrutural, tanque lateral sob ventilacao auxiliar e corredor de acesso parcialmente isolado.",
            "fase_obra_naval": "Reparacao estrutural com solda e esmerilhamento",
            "trabalho_quente": "Solda em chaparia lateral com permissao emitida e necessidade de ampliar o isolamento do entorno imediato.",
            "espaco_confinado": "Tanque lateral acessado para ajuste interno com monitoramento ativo.",
            "ventilacao_exaustao": "Ventilacao auxiliar presente, mas com renovacao insuficiente no fundo do tanque lateral.",
            "movimentacao_cargas": "Içamento de chapas programado na mesma doca, fora do raio imediato da frente.",
            "protecao_contra_queda": "Linha de vida e guarda-corpos presentes no acesso superior da estrutura.",
            "isolamento_area": "Isolamento parcial no corredor lateral durante trabalho a quente.",
            "sinalizacao": "Sinalizacao de risco presente, com necessidade de reforco no acesso secundario.",
            "evidencia_principal": "IMG_3402 - ventilacao auxiliar no tanque lateral",
            "evidencia_complementar": "IMG_3403 - isolamento parcial do corredor lateral",
            "pgr_naval": "DOC_3401 - pgr_naval_estaleiro_atlantico_rev03.pdf",
            "apr": "DOC_3402 - apr_reparo_bloco12.pdf",
            "permissao_trabalho_quente": "DOC_3403 - pte_quente_bloco12.pdf",
            "permissao_espaco_confinado": "DOC_3404 - pte_tanque_lateral_bloco12.pdf",
            "procedimento_operacional": "DOC_3405 - procedimento_reparo_estrutural_bloco12.pdf",
            "plano_emergencia": "DOC_3406 - plano_emergencia_doca2.pdf",
            "descricao_pontos_atencao": "Ventilacao parcial no tanque lateral e isolamento incompleto da area de trabalho a quente no bloco 12.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Reforcar o isolamento do corredor lateral e elevar a renovacao de ar no tanque antes da proxima janela de solda.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Frente naval do bloco 12 em reparacao estrutural com solda, esmerilhamento e acesso interno ao tanque lateral.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada ventilacao insuficiente no fundo do tanque lateral e isolamento incompleto do corredor lateral durante trabalho a quente.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: reforcar o isolamento do corredor lateral e elevar a renovacao de ar no tanque antes da proxima janela de solda.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr34_inspecao_frente_naval"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Frente de reparacao naval do bloco 12"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "frente_naval"
        assert "Permissao quente:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr36_unidade_abate_processamento(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr36_inspecao_unidade_abate_processamento"
        laudo.catalog_family_label = "NR36 · Unidade abate processamento"
        laudo.catalog_variant_key = "prime_frigorifico"
        laudo.catalog_variant_label = "Prime frigorifico"
        laudo.primeira_mensagem = "Inspecao na unidade de desossa e corte da Planta Sul"
        laudo.parecer_ia = "Foi identificada pausa termica insuficiente na desossa e piso umido sem segregacao completa no corredor de abastecimento."
        laudo.dados_formulario = {
            "local_inspecao": "Planta Sul - setor de desossa e corte",
            "objeto_principal": "Unidade de desossa e corte da Planta Sul",
            "codigo_interno": "FRIGO-DS-12",
            "referencia_principal": "IMG_3601 - vista geral da linha de desossa 12",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em unidade de abate e processamento com checklist NR36, verificacao de pausas, ergonomia e condicoes termicas.",
            "condicoes_gerais": "Linha em operacao com ritmo elevado, pausas insuficientes na desossa e corredor de abastecimento com piso umido.",
            "setor_produtivo": "Desossa e corte",
            "temperatura_ambiente": "10 C no setor com exposicao continua da equipe.",
            "pausas_termicas": "Escala de pausas abaixo do previsto para o turno da tarde.",
            "ergonomia_posto": "Postos repetitivos com necessidade de rever altura da mesa secundaria.",
            "facas_ferramentas": "Facas em uso com chaira e suporte organizados no posto principal.",
            "higienizacao": "Rotina de higienizacao em andamento entre lotes.",
            "epc_epi": "Luvas, mangotes e aventais disponiveis, com reforco necessario no uso do protetor auricular.",
            "piso_drenagem": "Corredor de abastecimento com umidade e drenagem parcial no trecho lateral.",
            "evidencia_principal": "IMG_3602 - piso umido no corredor de abastecimento",
            "evidencia_complementar": "IMG_3603 - posto de desossa com ajuste ergonomico pendente",
            "pgr_frigorifico": "DOC_3601 - pgr_planta_sul_rev04.pdf",
            "apr": "DOC_3602 - apr_desossa_turno_tarde.pdf",
            "procedimento_operacional": "DOC_3603 - procedimento_desossa_corte.pdf",
            "programa_pausas": "DOC_3604 - programa_pausas_termicas_turno_tarde.pdf",
            "pcmso": "DOC_3605 - pcmso_planta_sul_2026.pdf",
            "descricao_pontos_atencao": "Pausa termica insuficiente na desossa e piso umido sem segregacao completa no corredor de abastecimento.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Ajustar a escala de pausas e reforcar a segregacao do corredor antes do proximo pico operacional.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Linha de desossa em operacao na Planta Sul com equipe completa e ritmo elevado no turno da tarde.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada pausa termica insuficiente e piso umido sem segregacao completa no corredor de abastecimento.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: ajustar a escala de pausas e reforcar a segregacao do corredor antes do proximo pico operacional.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr36_inspecao_unidade_abate_processamento"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Unidade de desossa e corte da Planta Sul"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "unidade_abate_processamento"
        assert "Programa pausas:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr37_plataforma_petroleo(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr37_inspecao_plataforma_petroleo"
        laudo.catalog_family_label = "NR37 · Plataforma petroleo"
        laudo.catalog_variant_key = "prime_offshore"
        laudo.catalog_variant_label = "Prime offshore"
        laudo.primeira_mensagem = "Analise documental da Plataforma Aurora"
        laudo.parecer_ia = "O pacote documental da plataforma foi consolidado, mas ainda depende de atualizar o inventario de riscos do modulo de compressao."
        laudo.dados_formulario = {
            "localizacao": "Plataforma Aurora - modulo de processo e habitacao",
            "objeto_principal": "Pacote documental da Plataforma Aurora",
            "codigo_interno": "PLAT-AUR-2026",
            "codigo_plataforma": "AUR-01",
            "referencia_principal": "DOC_3701 - pacote_nr37_plataforma_aurora_rev03.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Analise documental de plataforma de petroleo com consolidacao do inventario de riscos, planos de resposta e matriz de treinamentos.",
            "status_documentacao": "Pacote consolidado com pendencia de atualizar o inventario de riscos do modulo de compressao.",
            "unidade_offshore": "Plataforma fixa Aurora",
            "inventario_riscos": "DOC_3702 - inventario_riscos_modulo_compressao.xlsx",
            "trabalho_quente": "Procedimento e controle documental vigentes para o modulo de manutencao.",
            "espaco_confinado": "Permissao e matriz de controles documentadas para tanques de processo.",
            "abandono_emergencia": "Plano de abandono e pontos de encontro revisados em 2026.",
            "habitabilidade": "Acomodacoes e areas comuns com programa de manutencao e limpeza registrado.",
            "matriz_treinamentos": "DOC_3703 - matriz_treinamentos_offshore_2026.xlsx",
            "pgr_plataforma": "DOC_3704 - pgr_plataforma_aurora_rev05.pdf",
            "plano_resposta_emergencia": "DOC_3705 - plano_resposta_aurora_rev04.pdf",
            "procedimento_operacional": "DOC_3706 - procedimento_operacional_modulo_processo.pdf",
            "pcmso": "DOC_3707 - pcmso_offshore_aurora_2026.pdf",
            "art_numero": "ART 2026-00537",
            "evidencia_principal": "DOC_3701 - pacote_nr37_plataforma_aurora_rev03.pdf",
            "descricao_pontos_atencao": "Atualizar o inventario de riscos do modulo de compressao e reemitir a referencia consolidada do pacote NR37.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Fechar a revisao do inventario de riscos e republicar o pacote documental offshore.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Pacote documental offshore consolidado para a Plataforma Aurora com planos de resposta, treinamentos e inventario de riscos associado.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Permanece pendente atualizar o inventario de riscos do modulo de compressao e republicar a referencia consolidada do pacote NR37.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: atualizar o inventario de riscos do modulo de compressao e republicar o pacote documental da plataforma.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr37_inspecao_plataforma_petroleo"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Pacote documental da Plataforma Aurora"
        assert laudo.dados_formulario["escopo_servico"]["tipo_entrega"] == "pacote_documental"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "analise_documental"
        assert "Inventario riscos:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr38_limpeza_urbana_residuos(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr38_inspecao_limpeza_urbana_residuos"
        laudo.catalog_family_label = "NR38 · Limpeza urbana residuos"
        laudo.catalog_variant_key = "prime_urbana"
        laudo.catalog_variant_label = "Prime urbana"
        laudo.primeira_mensagem = "Inspecao na rota de coleta Centro Norte"
        laudo.parecer_ia = (
            "Foi identificada segregacao parcial do trafego viario e necessidade de reforcar a higienizacao do compartimento traseiro do caminhão."
        )
        laudo.dados_formulario = {
            "local_inspecao": "Base Centro Norte e rota de coleta urbana",
            "objeto_principal": "Rota de coleta urbana Centro Norte",
            "codigo_interno": "URB-CN-07",
            "referencia_principal": "IMG_3801 - vista geral do caminhão coletor CN-07",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em limpeza urbana com checklist NR38, verificacao da coleta, manuseio de residuos e trafego da rota.",
            "condicoes_gerais": "Operacao em andamento com equipe completa, trafego intenso em corredor central e compartimento traseiro com higienizacao pendente.",
            "tipo_operacao": "Coleta domiciliar convencional",
            "coleta_manual": "Coleta porta a porta com equipe de tres garis na rota central.",
            "manuseio_residuos": "Volume regular com pontos de descarte irregular misturados ao fluxo convencional.",
            "frota_equipamento": "Caminhão coletor compactador CN-07 em operacao regular.",
            "segregacao_trafego": "Corredor central sem cones suficientes em trecho de travessia intensa.",
            "higienizacao": "Lavagem do compartimento traseiro pendente ao fim do turno anterior.",
            "epc_epi": "Luvas, botinas, uniforme refletivo e protetor auricular disponiveis.",
            "sinalizacao": "Sinalizacao luminosa ativa, com reforco necessario na travessia do corredor central.",
            "evidencia_principal": "IMG_3802 - travessia com segregacao parcial do trafego",
            "evidencia_complementar": "IMG_3803 - compartimento traseiro aguardando higienizacao final",
            "pgr_limpeza_urbana": "DOC_3801 - pgr_limpeza_urbana_rev03.pdf",
            "apr": "DOC_3802 - apr_rota_centro_norte.pdf",
            "procedimento_operacional": "DOC_3803 - procedimento_coleta_domiciliar.pdf",
            "plano_emergencia": "DOC_3804 - plano_emergencia_frota_urbana.pdf",
            "checklist_frota": "DOC_3805 - checklist_caminhao_cn07.pdf",
            "treinamento_equipe": "DOC_3806 - treinamento_seguranca_coleta_2026.pdf",
            "descricao_pontos_atencao": "Segregacao parcial do trafego viario e necessidade de reforcar a higienizacao do compartimento traseiro do caminhão.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Completar a segregacao do corredor central e normalizar a higienizacao do compartimento antes do proximo turno.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Rota de coleta Centro Norte em operacao com equipe completa, caminhão compactador e trafego intenso no corredor central.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada segregacao parcial do trafego viario e compartimento traseiro aguardando higienizacao final do turno anterior.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: completar a segregacao do corredor central e normalizar a higienizacao do compartimento antes do proximo turno.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr38_inspecao_limpeza_urbana_residuos"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Rota de coleta urbana Centro Norte"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "limpeza_urbana_residuos"
        assert "Checklist:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr12(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr12maquinas",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr12_inspecao_maquina_equipamento"
        laudo.catalog_family_label = "NR12 · Maquina e equipamento"
        laudo.catalog_variant_key = "prime_machine"
        laudo.catalog_variant_label = "Prime machine"
        laudo.primeira_mensagem = "Inspecao inicial na prensa hidraulica PH-07 da linha de estampagem"
        laudo.parecer_ia = "Foi identificado intertravamento inoperante na porta frontal e acesso perigoso na zona de alimentacao."
        laudo.dados_formulario = {
            "local_inspecao": "Linha de estampagem - prensa PH-07",
            "objeto_principal": "Prensa hidraulica PH-07",
            "codigo_interno": "PH-07",
            "referencia_principal": "IMG_401 - vista frontal da PH-07",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao visual funcional com checklist NR12 e teste de parada de emergencia.",
            "condicoes_gerais": "Protecoes laterais presentes, com porta frontal abrindo sem bloqueio de movimento.",
            "guardas_protecoes": "Protecao lateral integra, com abertura frontal sem enclausuramento efetivo.",
            "parada_emergencia": "Botoeira frontal presente e reset manual disponivel.",
            "intertravamentos": "Porta frontal abre sem bloquear o movimento da maquina.",
            "zona_risco": "Acesso perigoso identificado no lado de alimentacao durante setup.",
            "procedimento_bloqueio": "LOTO aplicavel descrito no procedimento de manutencao.",
            "evidencia_principal": "IMG_402 - porta frontal aberta com movimento habilitado",
            "evidencia_complementar": "IMG_403 - botoeira de emergencia frontal",
            "manual_maquina": "DOC_051 - manual_prensa_ph07.pdf",
            "inventario_maquinas": "DOC_052 - inventario_nr12_linha_a.pdf",
            "checklist_nr12": "DOC_053 - checklist_nr12_ph07.pdf",
            "descricao_pontos_atencao": "Intertravamento da porta frontal inoperante e acesso perigoso na zona de alimentacao.",
            "observacoes": "Ajustar intertravamento, revisar enclausuramento frontal e revalidar a maquina apos correcoes.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Prensa localizada na linha de estampagem com acesso frontal e lateral liberado para a coleta.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Durante o teste funcional a porta frontal abriu sem bloquear o movimento, expondo a zona de alimentacao.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: bloquear a maquina para ajuste do intertravamento e revisar o enclausuramento frontal.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr12_inspecao_maquina_equipamento"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Prensa hidraulica PH-07"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "prensa_hidraulica"
        assert "Manual:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr12_apreciacao_risco(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr12maquinas",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr12_apreciacao_risco_maquina"
        laudo.catalog_family_label = "NR12 · Apreciacao de risco"
        laudo.catalog_variant_key = "prime_engineering"
        laudo.catalog_variant_label = "Prime engineering"
        laudo.primeira_mensagem = "Apreciacao de risco na prensa hidraulica PH-07 da linha de estampagem"
        laudo.parecer_ia = "Foi identificado risco alto de aprisionamento na zona de alimentacao durante setup da prensa."
        laudo.dados_formulario = {
            "local_inspecao": "Linha de estampagem - prensa PH-07",
            "objeto_principal": "Prensa hidraulica PH-07",
            "codigo_interno": "PH-07",
            "referencia_principal": "IMG_451 - vista geral da PH-07",
            "modo_execucao": "analise e modelagem",
            "metodo_aplicado": "Apreciacao de risco com matriz HRN, checklist NR12 e memoria tecnica.",
            "perigo_identificado": "Aprisionamento na zona de alimentacao durante setup e limpeza.",
            "zona_risco": "Zona frontal de alimentacao com acesso perigoso ao ferramental.",
            "categoria_risco": "alto",
            "severidade": "grave",
            "probabilidade": "provavel",
            "medidas_existentes": "Protecoes laterais fixas e parada de emergencia frontal.",
            "medidas_recomendadas": "Intertravar acesso frontal e revisar procedimento de setup seguro.",
            "evidencia_principal": "DOC_061 - matriz_risco_ph07.pdf",
            "evidencia_complementar": "IMG_452 - zona de alimentacao frontal",
            "apreciacao_risco": "DOC_061 - matriz_risco_ph07.pdf",
            "checklist_nr12": "DOC_062 - checklist_nr12_ph07.pdf",
            "manual_maquina": "DOC_063 - manual_prensa_ph07.pdf",
            "descricao_pontos_atencao": "Risco alto de aprisionamento na zona de alimentacao durante setup.",
            "observacoes": "Implementar intertravamento frontal, revisar o procedimento e revalidar a matriz apos ajuste.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi realizada leitura da zona de alimentacao e do ferramental durante setup controlado da prensa.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="A matriz identificou risco alto de aprisionamento na alimentacao frontal sem intertravamento efetivo.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="documento: matriz_risco_ph07.pdf",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: revisar o acesso frontal, implementar intertravamento e revalidar a matriz de risco.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr12_apreciacao_risco_maquina"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Prensa hidraulica PH-07"
        assert laudo.dados_formulario["escopo_servico"]["tipo_entrega"] == "engenharia"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "analise_e_modelagem"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "prensa_hidraulica"
        assert "Apreciacao de risco:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr20_inspecao(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr20",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr20_inspecao_instalacoes_inflamaveis"
        laudo.catalog_family_label = "NR20 · Inspecao de instalacoes inflamaveis"
        laudo.catalog_variant_key = "prime_inflamaveis"
        laudo.catalog_variant_label = "Prime inflamaveis"
        laudo.primeira_mensagem = "Inspecao NR20 no skid de abastecimento SK-02"
        laudo.parecer_ia = "Foi identificado desgaste no aterramento do skid e necessidade de recompor a sinalizacao da area classificada."
        laudo.dados_formulario = {
            "local_inspecao": "Parque de tancagem - skid SK-02",
            "objeto_principal": "Skid de abastecimento SK-02",
            "codigo_interno": "SK-02",
            "referencia_principal": "IMG_601 - vista geral do SK-02",
            "metodo_inspecao": "Inspecao visual com checklist NR20 e verificacao de aterramento e contencao.",
            "classificacao_area": "Zona 2 no entorno do skid de abastecimento",
            "bacia_contencao": "Bacia com necessidade de limpeza e recomposicao parcial do revestimento.",
            "aterramento": "Cabo de aterramento com desgaste no terminal principal.",
            "sinalizacao": "Placa de area classificada desgastada na lateral norte.",
            "combate_incendio": "Extintor classe B dentro da validade e hidrante proximo sinalizado.",
            "evidencia_principal": "IMG_602 - terminal de aterramento com desgaste",
            "prontuario_nr20": "DOC_071 - prontuario_nr20_sk02.pdf",
            "plano_inspecao": "DOC_072 - plano_inspecao_sk02.pdf",
            "procedimento_operacional": "DOC_073 - procedimento_operacao_sk02.pdf",
            "art_numero": "ART 2026-00231",
            "descricao_pontos_atencao": "Desgaste no aterramento e necessidade de recompor a sinalizacao da area classificada.",
            "observacoes": "Recompor aterramento, renovar sinalizacao e reinspecionar o skid apos as correcoes.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Skid SK-02 localizado no parque de tancagem com bacia de contencao ativa e area classificada sinalizada parcialmente.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi identificado desgaste no aterramento principal e necessidade de recompor a placa da lateral norte.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: recompor o aterramento e renovar a sinalizacao antes da liberacao definitiva.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr20_inspecao_instalacoes_inflamaveis"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Skid de abastecimento SK-02"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "NR20"
        assert "Plano de inspecao:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr20_prontuario(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr20",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr20_prontuario_instalacoes_inflamaveis"
        laudo.catalog_family_label = "NR20 · Prontuario de instalacoes inflamaveis"
        laudo.catalog_variant_key = "prime_documental"
        laudo.catalog_variant_label = "Prime documental"
        laudo.primeira_mensagem = "Consolidacao do prontuario NR20 da base de carregamento BC-05"
        laudo.parecer_ia = "Prontuario consolidado, mas ainda depende de anexar revisao atualizada do estudo de risco."
        laudo.dados_formulario = {
            "localizacao": "Base de carregamento BC-05",
            "objeto_principal": "Base de carregamento BC-05",
            "codigo_interno": "PRT-20-BC05",
            "numero_prontuario": "PRT-20-BC05",
            "referencia_principal": "DOC_081 - indice_prontuario_bc05.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Consolidacao documental do prontuario NR20 com validacao de inventario, risco e emergencia.",
            "inventario_instalacoes": "DOC_082 - inventario_bc05.xlsx",
            "analise_riscos": "DOC_083 - estudo_risco_bc05.pdf",
            "procedimentos_operacionais": "DOC_084 - procedimentos_bc05.pdf",
            "plano_resposta_emergencia": "DOC_085 - plano_emergencia_bc05.pdf",
            "matriz_treinamentos": "DOC_086 - treinamentos_bc05.xlsx",
            "classificacao_area": "Areas classificadas revisadas parcialmente em 2024",
            "evidencia_principal": "DOC_083 - estudo_risco_bc05.pdf",
            "prontuario_nr20": "DOC_081 - indice_prontuario_bc05.pdf",
            "descricao_pontos_atencao": "Necessidade de anexar revisao atualizada do estudo de risco da base.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Atualizar o estudo de risco e reemitir o indice do prontuario apos a inclusao.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Prontuario da base BC-05 revisado com inventario, plano de emergencia e matriz de treinamentos consolidados.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Permanece pendente anexar a revisao atualizada do estudo de risco antes do fechamento definitivo do prontuario.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: prontuario apto para fechamento com ressalva, condicionado a anexar a revisao do estudo de risco.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr20_prontuario_instalacoes_inflamaveis"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Base de carregamento BC-05"
        assert laudo.dados_formulario["escopo_servico"]["tipo_entrega"] == "pacote_documental"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "analise_documental"
        assert "Plano de emergencia:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr35_linha_de_vida(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr35_inspecao_linha_de_vida"
        laudo.catalog_family_label = "NR35 · Linha de vida"
        laudo.catalog_variant_key = "prime_altura"
        laudo.catalog_variant_label = "Prime altura"
        laudo.primeira_mensagem = "Inspecao NR35 da linha de vida vertical da escada de acesso ao elevador 01"
        laudo.parecer_ia = "Linha de vida vertical com nao conformidade localizada no cabo de aco proximo ao topo."
        laudo.dados_formulario = {
            "informacoes_gerais": {
                "unidade": "Usina Orizona",
                "local": "Orizona - GO",
                "numero_laudo_fabricante": "MC-CRMR-0032",
                "numero_laudo_inspecao": "AT-IN-OZ-001-01-26",
                "art_numero": "ART 2026-00077",
            },
            "objeto_inspecao": {
                "identificacao_linha_vida": "MC-CRMRSS-0977 Escada de acesso ao elevador 01",
                "tipo_linha_vida": "Vertical",
                "escopo_inspecao": "Diagnostico geral da linha de vida vertical da escada de acesso.",
            },
            "componentes_inspecionados": {
                "fixacao_dos_pontos": {"condicao": "C", "observacao": "Fixacao integra."},
                "condicao_cabo_aco": {
                    "condicao": "NC",
                    "observacao": "Corrosao inicial proxima ao ponto superior.",
                },
                "condicao_esticador": {"condicao": "C", "observacao": "Tensionamento adequado."},
                "condicao_sapatilha": {"condicao": "C", "observacao": "Montagem integra."},
                "condicao_olhal": {"condicao": "C", "observacao": "Sem deformacao aparente."},
                "condicao_grampos": {"condicao": "C", "observacao": "Aperto visivel regular."},
            },
            "registros_fotograficos": [
                {
                    "titulo": "Vista geral",
                    "legenda": "Vista geral da linha de vida vertical.",
                    "referencia_anexo": "IMG_701 - vista_geral.png",
                },
                {
                    "titulo": "Ponto superior",
                    "legenda": "Corrosao inicial no cabo proximo ao topo.",
                    "referencia_anexo": "IMG_702 - ponto_superior.png",
                },
                {
                    "titulo": "Ponto inferior",
                    "legenda": "Terminal inferior registrado durante a vistoria.",
                    "referencia_anexo": "IMG_703 - ponto_inferior.png",
                },
            ],
            "conclusao": {
                "status": "Reprovado",
                "observacoes": "Substituir o trecho comprometido do cabo e reinspecionar o sistema.",
            },
            "resumo_executivo": "Linha de vida vertical com corrosao inicial no cabo de aco e necessidade de bloqueio para correcoes.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Linha de vida vertical localizada na escada de acesso ao elevador 01, em Orizona - GO.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada corrosao inicial no cabo de aco proximo ao ponto superior durante a vistoria.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: bloquear a linha de vida ate a substituicao do trecho comprometido do cabo.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr35_inspecao_linha_de_vida"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "MC-CRMRSS-0977 Escada de acesso ao elevador 01"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "linha_de_vida_vertical"
        assert "ART:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "bloqueio"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr35_ponto_ancoragem(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr35_inspecao_ponto_ancoragem"
        laudo.catalog_family_label = "NR35 · Ponto de ancoragem"
        laudo.catalog_variant_key = "prime_altura"
        laudo.catalog_variant_label = "Prime altura"
        laudo.primeira_mensagem = "Inspecao NR35 do ponto de ancoragem ANC-12 na cobertura do bloco C"
        laudo.parecer_ia = "Ponto de ancoragem com corrosao superficial localizada no olhal e necessidade de ajuste preventivo."
        laudo.dados_formulario = {
            "local_inspecao": "Cobertura bloco C - ponto ANC-12",
            "objeto_principal": "Ponto de ancoragem ANC-12",
            "codigo_interno": "ANC-12",
            "referencia_principal": "IMG_801 - visao geral do ponto ANC-12",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao visual com verificacao de fixacao, corrosao e deformacoes aparentes.",
            "tipo_ancoragem": "Olhal quimico em base metalica",
            "fixacao": "Fixacao com chumbador quimico e base metalica.",
            "chumbador": "Chumbador com torque conferido em campo.",
            "corrosao": "Corrosao superficial no olhal com perda localizada de pintura.",
            "deformacao": "Sem deformacao permanente aparente.",
            "trinca": "Nao foram observadas trincas na base ou no olhal.",
            "carga_nominal": "15 kN",
            "evidencia_principal": "IMG_802 - detalhe do olhal com corrosao superficial",
            "evidencia_complementar": "IMG_803 - chumbador e base metalica",
            "certificado_ancoragem": "DOC_081 - certificado_ancoragem_anc12.pdf",
            "memorial_calculo": "DOC_082 - memorial_anc12.pdf",
            "art_numero": "ART 2026-00155",
            "descricao_pontos_atencao": "Corrosao superficial no olhal e necessidade de limpeza com protecao anticorrosiva.",
            "observacoes": "Executar limpeza, protecao anticorrosiva e reinspecionar o ponto apos o tratamento.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Ponto ANC-12 localizado na cobertura do bloco C com acesso liberado para coleta frontal.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Foi observada corrosao superficial no olhal, sem trincas aparentes na base de fixacao.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: tratar a corrosao do olhal e reinspecionar o ponto de ancoragem apos a protecao.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr35_inspecao_ponto_ancoragem"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Ponto de ancoragem ANC-12"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "ponto_ancoragem"
        assert "Certificado:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr33_avaliacao(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr33",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr33_avaliacao_espaco_confinado"
        laudo.catalog_family_label = "NR33 · Avaliacao de espaco confinado"
        laudo.catalog_variant_key = "prime_confinados"
        laudo.catalog_variant_label = "Prime confinados"
        laudo.primeira_mensagem = "Avaliacao NR33 do tanque TQ-11 na casa de bombas"
        laudo.parecer_ia = "Foi identificada necessidade de reforcar a ventilacao e repetir a leitura atmosferica antes da liberacao final."
        laudo.dados_formulario = {
            "local_inspecao": "Casa de bombas - tanque TQ-11",
            "objeto_principal": "Tanque TQ-11",
            "codigo_interno": "TQ-11",
            "referencia_principal": "IMG_901 - boca de visita do TQ-11",
            "metodo_aplicado": "Avaliacao de espaco confinado com leitura atmosferica e checklist NR33.",
            "classificacao_espaco": "Tanque vertical com acesso por boca de visita superior",
            "atmosfera_inicial": "O2 20,8%; LEL 0%; H2S 0 ppm",
            "ventilacao": "Ventilacao forcada prevista antes da entrada",
            "isolamento_energias": "Bloqueio eletrico e flange cego confirmados",
            "supervisor_entrada": "Carlos Lima",
            "vigia": "Patricia Souza",
            "evidencia_principal": "IMG_902 - leitura atmosferica inicial",
            "documento_base": "DOC_091 - avaliacao_pre_entrada_tq11.pdf",
            "apr": "DOC_092 - apr_tq11.pdf",
            "descricao_pontos_atencao": "Necessidade de reforcar a ventilacao antes da liberacao final.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Executar nova leitura apos ventilacao e validar a liberacao final.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Tanque TQ-11 localizado na casa de bombas com isolamento eletrico e flange cego confirmados.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Leitura atmosferica inicial dentro do limite, mas a ventilacao adicional foi recomendada antes da liberacao final.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: reforcar a ventilacao, repetir a leitura atmosferica e liberar apenas apos nova confirmacao.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr33_avaliacao_espaco_confinado"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Tanque TQ-11"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "NR33"
        assert "APR:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
        assert laudo.dados_formulario["conclusao"]["status"] == "ajuste"


def test_inspetor_finalizacao_catalogada_persiste_laudo_output_canonico_nr33_pet(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr33",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr33_permissao_entrada_trabalho"
        laudo.catalog_family_label = "NR33 · Permissao de entrada"
        laudo.catalog_variant_key = "prime_confinados"
        laudo.catalog_variant_label = "Prime confinados"
        laudo.primeira_mensagem = "Permissao de entrada para galeria subterranea G-03"
        laudo.parecer_ia = "PET liberada com rastreabilidade documental e monitoramento continuo registrado."
        laudo.dados_formulario = {
            "local_inspecao": "Galeria subterranea G-03",
            "objeto_principal": "Galeria subterranea G-03",
            "codigo_interno": "PET-33-118",
            "numero_pet": "PET-33-118",
            "referencia_principal": "IMG_951 - entrada da galeria G-03",
            "metodo_inspecao": "Verificacao da PET com checklist documental e leitura atmosferica de liberacao.",
            "validade_pet": "09/04/2026 08:00-16:00",
            "supervisor_entrada": "Juliana Ferreira",
            "vigia": "Marcos Silva",
            "atmosfera_liberacao": "O2 20,9%; LEL 0%; CO 2 ppm",
            "bloqueios": "Bloqueio eletrico e travamento mecanico executados",
            "epi_epc": "Detector multigas, ventilacao exaustora e tripe",
            "equipe_autorizada": "Equipe manutencao M-3",
            "evidencia_principal": "IMG_952 - PET assinada e instrumentos",
            "pet_documento": "DOC_101 - pet_33_118.pdf",
            "apr": "DOC_102 - apr_g03.pdf",
            "conclusao": {"status": "Liberado"},
            "observacoes": "Entrada liberada durante a vigencia da PET com monitoramento continuo.",
        }

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Galeria subterranea G-03 liberada com PET valida, bloqueios instalados e equipe autorizada em campo.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Monitoramento atmosferico continuo mantido durante a janela da PET com registros em ordem.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Parecer preliminar: PET liberada dentro da vigencia, com bloqueios e monitoramento continuo adequados.",
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json()["success"] is True
    assert resposta.json()["estado"] == "aguardando"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert isinstance(laudo.dados_formulario, dict)
        assert laudo.dados_formulario["schema_type"] == "laudo_output"
        assert laudo.dados_formulario["family_key"] == "nr33_permissao_entrada_trabalho"
        assert laudo.dados_formulario["identificacao"]["objeto_principal"] == "Galeria subterranea G-03"
        assert laudo.dados_formulario["escopo_servico"]["modo_execucao"] == "in_loco"
        assert laudo.dados_formulario["escopo_servico"]["ativo_tipo"] == "NR33"
        assert "PET:" in str(laudo.dados_formulario["documentacao_e_registros"]["documentos_disponiveis"])
        assert laudo.dados_formulario["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is False
        assert laudo.dados_formulario["conclusao"]["status"] == "conforme"


def test_api_chat_comando_finalizar_retorna_payload_gate_quando_reprovado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO padrao",
            "historico": [],
        },
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    detalhe = corpo.get("detail", {})
    assert detalhe["codigo"] == "GATE_QUALIDADE_REPROVADO"
    assert detalhe["aprovado"] is False
    assert isinstance(detalhe["faltantes"], list)
    assert len(detalhe["faltantes"]) >= 1

    with SessionLocal() as banco:
        laudo = (
            banco.query(Laudo)
            .filter(
                Laudo.empresa_id == ids["empresa_a"],
                Laudo.usuario_id == ids["inspetor_a"],
            )
            .order_by(Laudo.id.desc())
            .first()
        )
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.RASCUNHO.value


def test_api_chat_comando_rapido_pendencias_retorna_json(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Favor anexar foto adicional do painel.",
                lida=False,
            )
        )
        banco.commit()

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "/pendencias abertas",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "comando_rapido"
    assert corpo["comando"] == "/pendencias"
    assert "Pendências da Mesa" in corpo["texto"]

    with SessionLocal() as banco:
        comando_salvo = (
            banco.query(MensagemLaudo)
            .filter(
                MensagemLaudo.laudo_id == laudo_id,
                MensagemLaudo.tipo == TipoMensagem.USER.value,
                MensagemLaudo.conteudo.like("[COMANDO_RAPIDO]%"),
            )
            .count()
        )
        assert comando_salvo >= 1


def test_api_chat_comando_rapido_resumo_retorna_json(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspeção em quadro elétrico principal."
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.USER.value,
                conteudo="Foi identificado aquecimento em borne de alimentação.",
            )
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer preliminar emitido.",
            )
        )
        banco.commit()

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "/resumo",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "comando_rapido"
    assert corpo["comando"] == "/resumo"
    assert "Resumo da Sessão" in corpo["texto"]


def test_api_chat_comando_rapido_gerar_previa_retorna_json(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspeção inicial em área de caldeiras."
        laudo.parecer_ia = "Rascunho técnico com riscos e recomendações."
        banco.commit()

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "/gerar_previa",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "comando_rapido"
    assert corpo["comando"] == "/gerar_previa"
    assert "Prévia Operacional do Laudo" in corpo["texto"]


def test_api_chat_comando_rapido_enviar_mesa_gera_whisper(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "/enviar_mesa Validar extintores e sinalização da área.",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    assert "text/event-stream" in (resposta.headers.get("content-type", "").lower())
    assert "humano_insp" in resposta.text

    with SessionLocal() as banco:
        ultima = banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == laudo_id).order_by(MensagemLaudo.id.desc()).first()
        assert ultima is not None
        assert ultima.tipo == TipoMensagem.HUMANO_INSP.value
        assert "Validar extintores" in ultima.conteudo


def test_api_chat_comando_rapido_enviar_mesa_sem_texto_retorna_400(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "/enviar_mesa",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 400
    assert "Use /enviar_mesa" in resposta.json()["detail"]


def test_api_chat_comando_rapido_enviar_mesa_sem_inspecao_ativa_retorna_400(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "/enviar_mesa Validar extintores do almoxarifado.",
            "historico": [],
        },
    )

    assert resposta.status_code == 400
    assert "só é permitida após iniciar uma nova inspeção" in resposta.json()["detail"]


def test_api_chat_avisa_mesa_em_linguagem_natural_dispara_whisper(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "Avise a mesa avaliadora que terminei a inspeção da NR10.",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    assert "text/event-stream" in (resposta.headers.get("content-type", "").lower())
    assert "terminei a inspeção da NR10" in resposta.text

    with SessionLocal() as banco:
        ultima = banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == laudo_id).order_by(MensagemLaudo.id.desc()).first()
        assert ultima is not None
        assert ultima.tipo == TipoMensagem.HUMANO_INSP.value
        assert "terminei a inspeção da NR10" in ultima.conteudo


def test_api_chat_avisa_mesa_sem_texto_util_retorna_400(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "Avise a mesa avaliadora",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Mensagem para a mesa está vazia."


def test_canais_ia_e_mesa_ficam_isolados_no_historico(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Mensagem normal do chat IA",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Resposta da IA para o inspetor",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="Pergunta do inspetor para a mesa",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Retorno da mesa avaliadora",
                ),
            ]
        )
        banco.commit()

    resposta_chat = client.get(f"/app/api/laudo/{laudo_id}/mensagens")
    assert resposta_chat.status_code == 200
    itens_chat = resposta_chat.json()["itens"]
    tipos_chat = {item["tipo"] for item in itens_chat}
    assert TipoMensagem.USER.value in tipos_chat
    assert TipoMensagem.IA.value in tipos_chat
    assert TipoMensagem.HUMANO_INSP.value not in tipos_chat
    assert TipoMensagem.HUMANO_ENG.value not in tipos_chat

    resposta_mesa = client.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")
    assert resposta_mesa.status_code == 200
    itens_mesa = resposta_mesa.json()["itens"]
    tipos_mesa = {item["tipo"] for item in itens_mesa}
    assert TipoMensagem.HUMANO_INSP.value in tipos_mesa
    assert TipoMensagem.HUMANO_ENG.value in tipos_mesa
    assert TipoMensagem.USER.value not in tipos_mesa
    assert TipoMensagem.IA.value not in tipos_mesa


def test_inspetor_envia_mensagem_mesa_com_referencia_valida(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        msg_mesa = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["revisor_a"],
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="Corrigir o item de proteção coletiva.",
        )
        banco.add(msg_mesa)
        banco.commit()
        banco.refresh(msg_mesa)
        referencia_id = msg_mesa.id

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={
            "texto": "Ajuste realizado em campo, favor revalidar.",
            "referencia_mensagem_id": referencia_id,
        },
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["laudo_id"] == laudo_id
    assert corpo["mensagem"]["tipo"] == TipoMensagem.HUMANO_INSP.value
    assert corpo["mensagem"]["referencia_mensagem_id"] == referencia_id
    assert "Ajuste realizado em campo" in corpo["mensagem"]["texto"]

    with SessionLocal() as banco:
        ultima = banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == laudo_id).order_by(MensagemLaudo.id.desc()).first()
        assert ultima is not None
        assert ultima.tipo == TipoMensagem.HUMANO_INSP.value
        assert ultima.conteudo.startswith(f"[REF_MSG_ID:{referencia_id}]")


def test_inspetor_envia_anexo_para_mesa_e_download_fica_protegido(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/anexo",
        headers={"X-CSRF-Token": csrf},
        data={"texto": "Foto da proteção lateral anexada."},
        files={"arquivo": ("protecao.png", _imagem_png_bytes_teste(), "image/png")},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["mensagem"]["tipo"] == TipoMensagem.HUMANO_INSP.value
    assert "Foto da proteção lateral" in corpo["mensagem"]["texto"]
    assert len(corpo["mensagem"]["anexos"]) == 1
    anexo = corpo["mensagem"]["anexos"][0]
    assert anexo["nome"] == "protecao.png"
    assert anexo["categoria"] == "imagem"
    assert anexo["eh_imagem"] is True
    assert anexo["url"].endswith(f"/app/api/laudo/{laudo_id}/mesa/anexos/{anexo['id']}")

    resposta_lista = client.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")
    assert resposta_lista.status_code == 200
    itens = resposta_lista.json()["itens"]
    assert itens[-1]["anexos"][0]["nome"] == "protecao.png"

    resposta_download = client.get(anexo["url"])
    assert resposta_download.status_code == 200
    assert resposta_download.content == _imagem_png_bytes_teste()
    assert "image/png" in resposta_download.headers.get("content-type", "").lower()

    with SessionLocal() as banco:
        anexo_db = banco.get(AnexoMesa, int(anexo["id"]))
        assert anexo_db is not None
        assert anexo_db.laudo_id == laudo_id
        assert anexo_db.mensagem_id > 0
        assert anexo_db.categoria == "imagem"
        assert os.path.isfile(str(anexo_db.caminho_arquivo))


def test_mesa_anexo_multipart_invalido_retorna_422_json_serializavel(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    boundary = "mesa-malformado"
    corpo = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="arquivo"\r\n\r\n\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="referencia_mensagem_id"; filename="referencia_mensagem_id"\r\n\r\nNone\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="texto"\r\n\r\n\r\n'
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    resposta = client.post(
        "/app/api/laudo/0/mesa/anexo",
        headers={
            "X-CSRF-Token": csrf,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=corpo,
    )

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert isinstance(detalhe, list)
    assert detalhe[0]["loc"][0] == "body"
    assert detalhe[1]["input"]["__type__"] == "UploadFile"
    assert detalhe[1]["input"]["filename"] == "referencia_mensagem_id"


def test_primeira_interacao_com_mesa_cria_card_normal_no_historico(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    iniciar = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )
    assert iniciar.status_code == 200
    laudo_id = int(iniciar.json()["laudo_id"])

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={"texto": "Mesa, validar item estrutural antes da vistoria final."},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["estado"] == "relatorio_ativo"
    assert corpo["laudo_card"]["id"] == laudo_id
    assert corpo["laudo_card"]["status_card"] == "aberto"

    home = client.get("/app/", follow_redirects=False)
    assert home.status_code == 200
    assert f'data-laudo-id="{laudo_id}"' in home.text

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.primeira_mensagem == "Mesa, validar item estrutural antes da vistoria final."


def test_inspetor_envia_mensagem_mesa_com_referencia_invalida_retorna_404(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={
            "texto": "Resposta do inspetor para a mesa.",
            "referencia_mensagem_id": 999999,
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Mensagem de referência não encontrada."


def test_revisor_responde_e_inspetor_visualiza_no_canal_mesa(ambiente_critico) -> None:
    client_revisor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta_revisor = client_revisor.post(
        f"/revisao/api/laudo/{laudo_id}/responder",
        headers={"X-CSRF-Token": csrf_revisor},
        json={"texto": "Mesa avaliadora: incluir foto da placa de identificação."},
    )
    assert resposta_revisor.status_code == 200
    assert resposta_revisor.json()["success"] is True

    with TestClient(main.app) as client_inspetor:
        _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")
        resposta_mesa = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")

    assert resposta_mesa.status_code == 200
    itens = resposta_mesa.json()["itens"]
    assert len(itens) >= 1
    assert itens[-1]["tipo"] == TipoMensagem.HUMANO_ENG.value
    assert "Mesa avaliadora" in itens[-1]["texto"]
    assert itens[-1]["lida"] is False
    assert itens[-1]["resolvida_por_nome"] == ""
    assert itens[-1]["resolvida_em"] == ""


def test_revisor_responde_com_anexo_e_inspetor_recebe_no_canal_mesa(ambiente_critico) -> None:
    client_revisor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta_revisor = client_revisor.post(
        f"/revisao/api/laudo/{laudo_id}/responder-anexo",
        headers={"X-CSRF-Token": csrf_revisor},
        data={"texto": "Segue checklist complementar da mesa."},
        files={"arquivo": ("checklist.pdf", _pdf_base_bytes_teste(), "application/pdf")},
    )
    assert resposta_revisor.status_code == 200
    corpo_revisor = resposta_revisor.json()
    assert corpo_revisor["success"] is True
    assert corpo_revisor["mensagem"]["anexos"][0]["nome"] == "checklist.pdf"
    assert corpo_revisor["mensagem"]["anexos"][0]["categoria"] == "documento"

    with TestClient(main.app) as client_inspetor:
        _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")
        resposta_mesa = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")

    assert resposta_mesa.status_code == 200
    itens = resposta_mesa.json()["itens"]
    assert itens[-1]["tipo"] == TipoMensagem.HUMANO_ENG.value
    assert itens[-1]["anexos"][0]["nome"] == "checklist.pdf"

    resposta_download = client_inspetor.get(itens[-1]["anexos"][0]["url"])
    assert resposta_download.status_code == 200
    assert resposta_download.content.startswith(b"%PDF")
    assert "application/pdf" in resposta_download.headers.get("content-type", "").lower()


def test_laudo_com_ajustes_exige_reabertura_manual_para_chat_e_mesa(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.encerrado_pelo_inspetor_em = datetime.now(timezone.utc)
        laudo.primeira_mensagem = "Inspeção encerrada e enviada para a mesa."
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.USER.value,
                conteudo="Coleta concluída em campo.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()

    with TestClient(main.app) as client_revisor:
        csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")
        resposta_revisor = client_revisor.post(
            f"/revisao/api/laudo/{laudo_id}/responder",
            headers={"X-CSRF-Token": csrf_revisor},
            json={"texto": "Mesa: complementar foto da proteção lateral."},
        )

    assert resposta_revisor.status_code == 200
    assert resposta_revisor.json()["success"] is True

    resposta_mensagens = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mensagens")
    assert resposta_mensagens.status_code == 200
    corpo_mensagens = resposta_mensagens.json()
    assert corpo_mensagens["estado"] == "ajustes"
    assert corpo_mensagens["permite_reabrir"] is True
    assert corpo_mensagens["case_lifecycle_status"] == "devolvido_para_correcao"
    assert corpo_mensagens["case_workflow_mode"] == "laudo_com_mesa"
    assert corpo_mensagens["active_owner_role"] == "inspetor"
    assert corpo_mensagens["allowed_next_lifecycle_statuses"] == [
        "laudo_em_coleta",
        "aguardando_mesa",
    ]
    assert corpo_mensagens["laudo_card"]["status_card"] == "ajustes"
    assert corpo_mensagens["laudo_card"]["case_lifecycle_status"] == "devolvido_para_correcao"

    status = client_inspetor.get("/app/api/laudo/status")
    assert status.status_code == 200
    corpo_status = status.json()
    assert corpo_status["estado"] == "ajustes"
    assert corpo_status["permite_reabrir"] is True
    assert corpo_status["case_lifecycle_status"] == "devolvido_para_correcao"
    assert corpo_status["case_workflow_mode"] == "laudo_com_mesa"
    assert corpo_status["active_owner_role"] == "inspetor"
    assert corpo_status["allowed_next_lifecycle_statuses"] == [
        "laudo_em_coleta",
        "aguardando_mesa",
    ]
    assert corpo_status["laudo_card"]["status_card"] == "ajustes"
    assert corpo_status["laudo_card"]["case_lifecycle_status"] == "devolvido_para_correcao"

    resposta_chat_bloqueado = client_inspetor.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf_inspetor},
        json={
            "mensagem": "Quero continuar o laudo sem reabrir.",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )
    assert resposta_chat_bloqueado.status_code == 400
    assert "reaberto" in resposta_chat_bloqueado.json()["detail"].lower()

    resposta_mesa_bloqueada = client_inspetor.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf_inspetor},
        json={"texto": "Respondendo a mesa sem reabrir."},
    )
    assert resposta_mesa_bloqueada.status_code == 400
    assert "reaberto" in resposta_mesa_bloqueada.json()["detail"].lower()

    resposta_reabrir = client_inspetor.post(
        f"/app/api/laudo/{laudo_id}/reabrir",
        headers={"X-CSRF-Token": csrf_inspetor},
    )
    assert resposta_reabrir.status_code == 200
    corpo_reabrir = resposta_reabrir.json()
    assert corpo_reabrir["estado"] == "relatorio_ativo"
    assert corpo_reabrir["permite_reabrir"] is False
    assert corpo_reabrir["case_lifecycle_status"] == "devolvido_para_correcao"
    assert corpo_reabrir["active_owner_role"] == "inspetor"
    assert corpo_reabrir["allowed_next_lifecycle_statuses"] == [
        "laudo_em_coleta",
        "aguardando_mesa",
    ]
    assert corpo_reabrir["laudo_card"]["status_card"] == "aberto"
    assert (
        corpo_reabrir["laudo_card"]["case_lifecycle_status"]
        == "devolvido_para_correcao"
    )

    class ClienteIAStub:
        def gerar_resposta_stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
            yield "Laudo reaberto e pronto para complementação.\n"

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat_ok = client_inspetor.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={
                "mensagem": "Agora sim, complementando após reabrir.",
                "historico": [],
                "laudo_id": laudo_id,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat_ok.status_code == 200
    assert "text/event-stream" in (resposta_chat_ok.headers.get("content-type", "").lower())

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.RASCUNHO.value
        assert laudo.reabertura_pendente_em is None
        assert laudo.reaberto_em is not None


def test_revisor_historico_reflete_retorno_do_inspetor_apos_reabertura(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.encerrado_pelo_inspetor_em = datetime.now(timezone.utc)
        laudo.primeira_mensagem = "Inspeção encerrada e enviada para a mesa."
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.USER.value,
                conteudo="Coleta inicial concluída em campo.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()

    with TestClient(main.app) as client_revisor:
        csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")

        resposta_revisor = client_revisor.post(
            f"/revisao/api/laudo/{laudo_id}/responder",
            headers={"X-CSRF-Token": csrf_revisor},
            json={"texto": "Mesa: complementar evidência visual da proteção lateral."},
        )

        assert resposta_revisor.status_code == 200
        assert resposta_revisor.json()["success"] is True

        resposta_reabrir = client_inspetor.post(
            f"/app/api/laudo/{laudo_id}/reabrir",
            headers={"X-CSRF-Token": csrf_inspetor},
        )
        assert resposta_reabrir.status_code == 200

        resposta_followup = client_inspetor.post(
            f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={"texto": "Campo: evidência complementar enviada após a reabertura."},
        )
        assert resposta_followup.status_code == 201

        historico_revisor = client_revisor.get(f"/revisao/api/laudo/{laudo_id}/completo?incluir_historico=true")

    assert historico_revisor.status_code == 200
    historico = historico_revisor.json()["historico"]
    assert any(item["tipo"] == TipoMensagem.HUMANO_ENG.value and "Mesa: complementar evidência visual" in item["texto"] for item in historico)
    assert any(
        item["tipo"] == TipoMensagem.HUMANO_INSP.value and "Campo: evidência complementar enviada após a reabertura." in item["texto"] for item in historico
    )


def test_laudo_emitido_pode_ser_reaberto_para_novo_ciclo(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Laudo final emitido para entrega."
        laudo.nome_arquivo_pdf = "laudo_emitido_final.pdf"
        laudo.encerrado_pelo_inspetor_em = datetime.now(timezone.utc)
        banco.commit()

    resposta_status = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mensagens")
    assert resposta_status.status_code == 200
    assert resposta_status.json()["permite_reabrir"] is True
    assert resposta_status.json()["estado"] == "aprovado"
    assert resposta_status.json()["case_lifecycle_status"] == "emitido"
    assert resposta_status.json()["case_workflow_mode"] == "laudo_com_mesa"
    assert resposta_status.json()["active_owner_role"] == "none"
    assert resposta_status.json()["allowed_next_lifecycle_statuses"] == [
        "devolvido_para_correcao",
    ]

    resposta_reabrir = client_inspetor.post(
        f"/app/api/laudo/{laudo_id}/reabrir",
        headers={"X-CSRF-Token": csrf_inspetor},
    )
    assert resposta_reabrir.status_code == 200
    corpo_reabrir = resposta_reabrir.json()
    assert corpo_reabrir["estado"] == "relatorio_ativo"
    assert corpo_reabrir["permite_reabrir"] is False
    assert corpo_reabrir["case_lifecycle_status"] == "devolvido_para_correcao"
    assert corpo_reabrir["active_owner_role"] == "inspetor"
    assert corpo_reabrir["allowed_next_lifecycle_statuses"] == [
        "laudo_em_coleta",
        "aguardando_mesa",
    ]
    assert corpo_reabrir["laudo_card"]["status_card"] == "aberto"
    assert (
        corpo_reabrir["laudo_card"]["case_lifecycle_status"]
        == "devolvido_para_correcao"
    )
    assert corpo_reabrir["issued_document_policy_applied"] == "keep_visible"
    assert corpo_reabrir["had_previous_issued_document"] is True
    assert corpo_reabrir["previous_issued_document_visible_in_case"] is True
    assert corpo_reabrir["internal_learning_candidate_registered"] is True

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.RASCUNHO.value
        assert laudo.reaberto_em is not None
        assert laudo.revisado_por is None
        assert laudo.encerrado_pelo_inspetor_em is None
        assert laudo.nome_arquivo_pdf == "laudo_emitido_final.pdf"
        historico = dict(laudo.report_pack_draft_json or {}).get(
            "reopen_issued_document_history"
        )
        assert isinstance(historico, list) and historico
        assert historico[-1]["file_name"] == "laudo_emitido_final.pdf"
        assert historico[-1]["issued_document_policy"] == "keep_visible"
        assert historico[-1]["internal_learning_candidate"] is True


def test_laudo_emitido_reaberto_pode_ocultar_pdf_da_superficie_ativa(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Laudo final emitido para entrega."
        laudo.nome_arquivo_pdf = "laudo_emitido_ocultavel.pdf"
        laudo.encerrado_pelo_inspetor_em = datetime.now(timezone.utc)
        banco.commit()

    resposta_reabrir = client_inspetor.post(
        f"/app/api/laudo/{laudo_id}/reabrir",
        headers={"X-CSRF-Token": csrf_inspetor},
        json={"issued_document_policy": "hide_from_case"},
    )
    assert resposta_reabrir.status_code == 200
    corpo_reabrir = resposta_reabrir.json()
    assert corpo_reabrir["issued_document_policy_applied"] == "hide_from_case"
    assert corpo_reabrir["had_previous_issued_document"] is True
    assert corpo_reabrir["previous_issued_document_visible_in_case"] is False
    assert corpo_reabrir["internal_learning_candidate_registered"] is True

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.nome_arquivo_pdf is None
        historico = dict(laudo.report_pack_draft_json or {}).get(
            "reopen_issued_document_history"
        )
        assert isinstance(historico, list) and historico
        assert historico[-1]["file_name"] == "laudo_emitido_ocultavel.pdf"
        assert historico[-1]["issued_document_policy"] == "hide_from_case"
        assert historico[-1]["visible_in_active_case"] is False


def test_revisor_whisper_responder_rejeita_destinatario_diferente_do_responsavel(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        inspetor_extra = Usuario(
            empresa_id=ids["empresa_a"],
            nome_completo="Inspetor Extra",
            email=f"inspetor.extra.{uuid.uuid4().hex[:6]}@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.INSPETOR.value,
        )
        banco.add(inspetor_extra)
        banco.flush()

        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.commit()
        destinatario_invalido = inspetor_extra.id

    resposta = client.post(
        "/revisao/api/whisper/responder",
        headers={"X-CSRF-Token": csrf},
        json={
            "laudo_id": laudo_id,
            "destinatario_id": destinatario_invalido,
            "mensagem": "Mensagem da mesa para inspetor incorreto.",
        },
    )

    assert resposta.status_code == 400
    assert "não corresponde ao inspetor responsável" in resposta.json()["detail"]


def test_jornada_e2e_chat_ia_e_mesa_comunicacao_bilateral(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with TestClient(main.app) as client_revisor:
        csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")

        resposta_inicio = client_inspetor.post(
            "/app/api/laudo/iniciar",
            headers={"X-CSRF-Token": csrf_inspetor},
            data={"tipo_template": "padrao"},
        )
        assert resposta_inicio.status_code == 200
        laudo_id = int(resposta_inicio.json()["laudo_id"])

        class ClienteIAStub:
            def gerar_resposta_stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
                yield "Diagnóstico técnico da IA para validação.\n"
                yield "Existe risco moderado em proteção mecânica.\n"

        cliente_original = rotas_inspetor.cliente_ia
        rotas_inspetor.cliente_ia = ClienteIAStub()
        try:
            resposta_chat = client_inspetor.post(
                "/app/api/chat",
                headers={"X-CSRF-Token": csrf_inspetor},
                json={
                    "mensagem": "Analise os riscos da prensa hidráulica.",
                    "historico": [],
                    "laudo_id": laudo_id,
                },
            )
        finally:
            rotas_inspetor.cliente_ia = cliente_original

        assert resposta_chat.status_code == 200
        assert "text/event-stream" in (resposta_chat.headers.get("content-type", "").lower())
        assert "Diagnóstico técnico da IA" in resposta_chat.text

        resposta_inspetor_para_mesa = client_inspetor.post(
            f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={"texto": "Mesa, validar item 4 da NR-12 na foto enviada."},
        )
        assert resposta_inspetor_para_mesa.status_code == 201
        mensagem_inspetor_id = int(resposta_inspetor_para_mesa.json()["mensagem"]["id"])

        historico_revisor = client_revisor.get(f"/revisao/api/laudo/{laudo_id}/completo?incluir_historico=true")
        assert historico_revisor.status_code == 200
        corpo_historico_revisor = historico_revisor.json()
        assert any(item["is_whisper"] for item in corpo_historico_revisor["historico"])
        assert any(item["tipo"] == TipoMensagem.HUMANO_INSP.value for item in corpo_historico_revisor["whispers"])

        resposta_revisor = client_revisor.post(
            f"/revisao/api/laudo/{laudo_id}/responder",
            headers={"X-CSRF-Token": csrf_revisor},
            json={
                "texto": "Mesa avaliadora: ponto recebido, pode seguir com evidência complementar.",
                "referencia_mensagem_id": mensagem_inspetor_id,
            },
        )
        assert resposta_revisor.status_code == 200
        assert resposta_revisor.json()["success"] is True

        resposta_mesa_inspetor = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")
        assert resposta_mesa_inspetor.status_code == 200
        itens_mesa = resposta_mesa_inspetor.json()["itens"]
        assert any(item["tipo"] == TipoMensagem.HUMANO_ENG.value and item.get("referencia_mensagem_id") == mensagem_inspetor_id for item in itens_mesa)

        resposta_chat_inspetor = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mensagens")
        assert resposta_chat_inspetor.status_code == 200
        tipos_chat = {item["tipo"] for item in resposta_chat_inspetor.json()["itens"]}
        assert TipoMensagem.USER.value in tipos_chat
        assert TipoMensagem.IA.value in tipos_chat
        assert TipoMensagem.HUMANO_INSP.value not in tipos_chat
        assert TipoMensagem.HUMANO_ENG.value not in tipos_chat


def test_jornada_e2e_whisper_revisor_para_inspetor_com_referencia(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta_base = client_inspetor.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf_inspetor},
        json={"texto": "Favor avaliar item de aterramento da máquina."},
    )
    assert resposta_base.status_code == 201
    referencia_id = int(resposta_base.json()["mensagem"]["id"])

    with TestClient(main.app) as client_revisor:
        csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")

        resposta_whisper = client_revisor.post(
            "/revisao/api/whisper/responder",
            headers={"X-CSRF-Token": csrf_revisor},
            json={
                "laudo_id": laudo_id,
                "destinatario_id": ids["inspetor_a"],
                "mensagem": "Mesa: validar continuidade elétrica com instrumento calibrado.",
                "referencia_mensagem_id": referencia_id,
            },
        )

    assert resposta_whisper.status_code == 200
    assert resposta_whisper.json()["success"] is True
    assert int(resposta_whisper.json()["destinatario_id"]) == ids["inspetor_a"]

    resposta_mesa = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")
    assert resposta_mesa.status_code == 200
    itens_mesa = resposta_mesa.json()["itens"]
    assert any(
        item["tipo"] == TipoMensagem.HUMANO_ENG.value
        and item.get("referencia_mensagem_id") == referencia_id
        and "Mesa: validar continuidade elétrica" in item["texto"]
        for item in itens_mesa
    )


def test_jornada_e2e_isolamento_multiempresa_no_chat_e_mesa(ambiente_critico) -> None:
    client_inspetor_a = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_a = _login_app_inspetor(client_inspetor_a, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id_a,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Mensagem do inspetor A no chat IA.",
                ),
                MensagemLaudo(
                    laudo_id=laudo_id_a,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Mensagem da mesa para o inspetor A.",
                ),
            ]
        )
        banco.commit()

    with TestClient(main.app) as client_inspetor_b:
        csrf_b = _login_app_inspetor(client_inspetor_b, "inspetor@empresa-b.test")

        resposta_chat = client_inspetor_b.get(f"/app/api/laudo/{laudo_id_a}/mensagens", follow_redirects=False)
        assert resposta_chat.status_code == 404

        resposta_mesa = client_inspetor_b.get(f"/app/api/laudo/{laudo_id_a}/mesa/mensagens", follow_redirects=False)
        assert resposta_mesa.status_code == 404

        resposta_envio = client_inspetor_b.post(
            f"/app/api/laudo/{laudo_id_a}/mesa/mensagem",
            headers={"X-CSRF-Token": csrf_b},
            json={"texto": "Tentativa indevida de acesso cruzado."},
            follow_redirects=False,
        )
        assert resposta_envio.status_code == 404

    resposta_legitima = client_inspetor_a.post(
        f"/app/api/laudo/{laudo_id_a}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf_a},
        json={"texto": "Mensagem legítima do inspetor A para mesa."},
    )
    assert resposta_legitima.status_code == 201


def test_chat_ignora_aprendizado_visual_ainda_nao_validado_pela_mesa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta_aprendizado = client.post(
        f"/app/api/laudo/{laudo_id}/aprendizados",
        headers={"X-CSRF-Token": csrf},
        json={
            "resumo": "Linha de vida provisória",
            "descricao_contexto": "Foto inicial do conjunto de ancoragem.",
            "correcao_inspetor": "O ponto A da linha de vida parece correto nesta cena.",
            "veredito_inspetor": "conforme",
            "dados_imagem": _imagem_png_data_uri_teste(),
            "nome_imagem": "linha-vida.png",
            "pontos_chave": ["ponto A", "linha de vida"],
            "referencias_norma": ["NR-35"],
        },
    )
    assert resposta_aprendizado.status_code == 201

    captura: dict[str, str] = {}

    class ClienteIAStub:
        def gerar_resposta_stream(self, mensagem: str, *args, **kwargs):  # noqa: ANN002, ANN003
            captura["mensagem"] = mensagem
            yield "Resposta de teste."

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Analise a linha de vida desta evidência.",
                "historico": [],
                "laudo_id": laudo_id,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat.status_code == 200
    assert "text/event-stream" in (resposta_chat.headers.get("content-type", "").lower())
    assert "aprendizados_visuais_validados" not in captura["mensagem"]
    assert "ponto A da linha de vida parece correto" not in captura["mensagem"].lower()


def test_chat_com_imagem_cria_rascunho_visual_para_mesa_mesmo_sem_correcao_explicita(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    class ClienteIAStub:
        def gerar_resposta_stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
            yield "Análise inicial da IA."

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat = client_inspetor.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={
                "mensagem": "Analise esta linha de vida.",
                "historico": [],
                "laudo_id": laudo_id,
                "dados_imagem": _imagem_png_data_uri_teste(),
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat.status_code == 200

    with TestClient(main.app) as client_revisor:
        csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")
        resposta_aprendizados = client_revisor.get(
            f"/revisao/api/laudo/{laudo_id}/aprendizados",
            headers={"X-CSRF-Token": csrf_revisor},
        )
        assert resposta_aprendizados.status_code == 200
        itens = resposta_aprendizados.json()["itens"]
        assert len(itens) == 1
        assert itens[0]["status"] == "rascunho_inspetor"
        assert itens[0]["imagem_url"].startswith("/static/uploads/aprendizados_ia/")
        assert "Sem correção explícita do inspetor" in itens[0]["correcao_inspetor"]

        resposta_completo = client_revisor.get(f"/revisao/api/laudo/{laudo_id}/completo?incluir_historico=true")
        assert resposta_completo.status_code == 200
        assert len(resposta_completo.json()["aprendizados_visuais"]) == 1


def test_chat_com_correcao_textual_atualiza_rascunho_visual_automatico(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    class ClienteIAStub:
        def gerar_resposta_stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
            yield "A IA marcou o ponto como incorreto."

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_imagem = client_inspetor.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={
                "mensagem": "Verifique esta ancoragem.",
                "historico": [],
                "laudo_id": laudo_id,
                "dados_imagem": _imagem_png_data_uri_teste(),
            },
        )
        resposta_correcao = client_inspetor.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={
                "mensagem": "Isso está correto, faça o relatório pra mim.",
                "historico": [],
                "laudo_id": laudo_id,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_imagem.status_code == 200
    assert resposta_correcao.status_code == 200

    with SessionLocal() as banco:
        itens = (
            banco.query(AprendizadoVisualIa)
            .filter(
                AprendizadoVisualIa.laudo_id == laudo_id,
                AprendizadoVisualIa.empresa_id == ids["empresa_a"],
            )
            .order_by(AprendizadoVisualIa.id.asc())
            .all()
        )
        assert len(itens) == 1
        assert "Isso está correto" in str(itens[0].correcao_inspetor)
        assert str(getattr(itens[0].veredito_inspetor, "value", itens[0].veredito_inspetor)) == "conforme"


def test_mesa_valida_aprendizado_visual_e_chat_consulta_sintese_final(ambiente_critico) -> None:
    client_inspetor = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf_inspetor = _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta_aprendizado = client_inspetor.post(
        f"/app/api/laudo/{laudo_id}/aprendizados",
        headers={"X-CSRF-Token": csrf_inspetor},
        json={
            "resumo": "Ancoragem da linha de vida",
            "descricao_contexto": "Correção inicial feita pelo inspetor em campo.",
            "correcao_inspetor": "O ponto A é o ponto correto da linha de vida nesta imagem.",
            "veredito_inspetor": "conforme",
            "dados_imagem": _imagem_png_data_uri_teste(),
            "nome_imagem": "ancoragem.png",
            "pontos_chave": ["ponto A", "linha de vida"],
            "referencias_norma": ["NR-35 item 35.5"],
            "marcacoes": [{"rotulo": "Ponto A", "observacao": "Marcado pelo inspetor"}],
        },
    )
    assert resposta_aprendizado.status_code == 201
    aprendizado_id = int(resposta_aprendizado.json()["aprendizado"]["id"])

    with TestClient(main.app) as client_revisor:
        csrf_revisor = _login_revisor(client_revisor, "revisor@empresa-a.test")
        resposta_validacao = client_revisor.post(
            f"/revisao/api/aprendizados/{aprendizado_id}/validar",
            headers={"X-CSRF-Token": csrf_revisor},
            json={
                "acao": "aprovar",
                "parecer_mesa": "Mesa validou que o ponto B é o ponto correto; o ponto A estava incorreto.",
                "sintese_consolidada": (
                    "Usar como referência que o ponto B identifica a ancoragem correta da linha de vida e o ponto A deve ser tratado como incorreto."
                ),
                "veredito_mesa": "nao_conforme",
                "pontos_chave": ["ponto B", "ancoragem correta", "linha de vida"],
                "referencias_norma": ["NR-35 item 35.5", "ancoragem certificada"],
                "marcacoes": [{"rotulo": "Ponto B", "observacao": "Referência validada pela mesa"}],
            },
        )
    assert resposta_validacao.status_code == 200
    assert resposta_validacao.json()["aprendizado"]["status"] == "validado_mesa"

    captura: dict[str, str] = {}

    class ClienteIAStub:
        def gerar_resposta_stream(self, mensagem: str, *args, **kwargs):  # noqa: ANN002, ANN003
            captura["mensagem"] = mensagem
            yield "Resposta de teste."

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat = client_inspetor.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={
                "mensagem": "Confirme qual é o ponto correto da linha de vida nesta foto.",
                "historico": [],
                "laudo_id": laudo_id,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat.status_code == 200
    assert "aprendizados_visuais_validados" in captura["mensagem"]
    assert "ponto b identifica a ancoragem correta" in captura["mensagem"].lower()
    assert "ponto a é o ponto correto" not in captura["mensagem"].lower()


def test_chat_nao_vaza_aprendizado_visual_validado_de_outra_empresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        aprendizado = AprendizadoVisualIa(
            empresa_id=ids["empresa_b"],
            laudo_id=laudo_b,
            criado_por_id=ids["inspetor_b"],
            setor_industrial="geral",
            resumo="Caso externo de ancoragem",
            correcao_inspetor="Empresa B indicou ponto externo.",
            sintese_consolidada="Empresa B validou que o ponto externo Z é a única ancoragem correta.",
            status="validado_mesa",
            veredito_inspetor="duvida",
            veredito_mesa="conforme",
            pontos_chave_json=["ponto externo Z"],
            referencias_norma_json=["NR-35"],
            marcacoes_json=[{"rotulo": "Ponto Z", "observacao": "Aprendizado empresa B"}],
        )
        banco.add(aprendizado)
        banco.commit()

    captura: dict[str, str] = {}

    class ClienteIAStub:
        def gerar_resposta_stream(self, mensagem: str, *args, **kwargs):  # noqa: ANN002, ANN003
            captura["mensagem"] = mensagem
            yield "Resposta de teste."

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Analise a ancoragem desta linha de vida.",
                "historico": [],
                "laudo_id": laudo_a,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat.status_code == 200
    assert "empresa b validou" not in captura["mensagem"].lower()
    assert "ponto externo z" not in captura["mensagem"].lower()


def test_api_chat_stream_emite_confianca_e_salva_revisao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspecao inicial da area de prensas."
        banco.commit()

    class ClienteIAStub:
        def gerar_resposta_stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
            yield "### Diagnostico Tecnico\n"
            yield "Foram verificadas evidencias na NR-12 e medicao de 12 mm.\n"
            yield "Ha ponto com possivel desgaste; necessario validar em campo.\n"

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Analise os riscos da linha de prensas e entregue parecer tecnico.",
                "historico": [],
                "laudo_id": laudo_id,
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta.status_code == 200
    assert "text/event-stream" in (resposta.headers.get("content-type", "").lower())
    assert "confianca_ia" in resposta.text

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert isinstance(laudo.confianca_ia_json, dict)
        assert laudo.confianca_ia_json.get("geral") in {"alta", "media", "baixa"}

        revisoes = banco.query(LaudoRevisao).filter(LaudoRevisao.laudo_id == laudo_id).order_by(LaudoRevisao.numero_versao.asc()).all()
        assert len(revisoes) == 1
        assert revisoes[0].numero_versao == 1
        assert revisoes[0].confianca_geral in {"alta", "media", "baixa"}


def test_inspetor_api_revisoes_lista_e_diff(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add_all(
            [
                LaudoRevisao(
                    laudo_id=laudo_id,
                    numero_versao=1,
                    origem="ia",
                    resumo="Versao inicial",
                    conteudo="Linha A: sem nao conformidade.",
                    confianca_geral="alta",
                    confianca_json={"geral": "alta", "secoes": [], "pontos_validacao_humana": []},
                ),
                LaudoRevisao(
                    laudo_id=laudo_id,
                    numero_versao=2,
                    origem="ia",
                    resumo="Versao atualizada",
                    conteudo="Linha A: sem nao conformidade.\nLinha B: ajustar bloqueio LOTO.",
                    confianca_geral="media",
                    confianca_json={"geral": "media", "secoes": [], "pontos_validacao_humana": []},
                ),
            ]
        )
        banco.commit()

    resposta_lista = client.get(f"/app/api/laudo/{laudo_id}/revisoes")
    assert resposta_lista.status_code == 200
    corpo_lista = resposta_lista.json()
    assert corpo_lista["laudo_id"] == laudo_id
    assert corpo_lista["total_revisoes"] == 2
    assert corpo_lista["ultima_versao"] == 2
    assert len(corpo_lista["revisoes"]) == 2

    resposta_diff = client.get(f"/app/api/laudo/{laudo_id}/revisoes/diff?base=1&comparar=2")
    assert resposta_diff.status_code == 200
    corpo_diff = resposta_diff.json()
    assert corpo_diff["base"]["versao"] == 1
    assert corpo_diff["comparar"]["versao"] == 2
    assert "versao_base" in corpo_diff["diff_unificado"]
    assert "versao_comparada" in corpo_diff["diff_unificado"]
    assert corpo_diff["resumo_diff"]["linhas_adicionadas"] >= 1
    assert corpo_diff["resumo_diff"]["total_alteracoes"] >= 1


def test_api_chat_comando_resumo_exibe_confianca_e_versionamento(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspecao eletrica em painel principal."
        laudo.confianca_ia_json = {
            "geral": "baixa",
            "secoes": [],
            "pontos_validacao_humana": [
                "Sintese geral: validar medicao com instrumento calibrado.",
            ],
        }
        banco.add(
            LaudoRevisao(
                laudo_id=laudo_id,
                numero_versao=1,
                origem="ia",
                resumo="Primeira versao",
                conteudo="Versao inicial do parecer tecnico.",
                confianca_geral="baixa",
                confianca_json=laudo.confianca_ia_json,
            )
        )
        banco.commit()

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "/resumo",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "comando_rapido"
    assert "Confiança IA" in corpo["texto"]
    assert "Versionamento: **v1**" in corpo["texto"]
    assert "Pontos para validação humana" in corpo["texto"]


def test_inspetor_nao_pode_deletar_laudo_aguardando(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta = client.request(
        "DELETE",
        f"/app/api/laudo/{laudo_id}",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Esse laudo não pode ser excluído no estado atual."


def test_inspetor_pendencias_lista_somente_mensagens_da_mesa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendência 1",
                    lida=False,
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendência 2",
                    lida=True,
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Mensagem comum do inspetor",
                    lida=False,
                ),
            ]
        )
        banco.commit()

    resposta = client.get(f"/app/api/laudo/{laudo_id}/pendencias")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["laudo_id"] == laudo_id
    assert corpo["filtro"] == "abertas"
    assert corpo["abertas"] == 1
    assert corpo["resolvidas"] == 1
    assert corpo["total"] == 2
    assert corpo["total_filtrado"] == 1
    assert len(corpo["pendencias"]) == 1
    assert all("Pendência" in item["texto"] for item in corpo["pendencias"])
    assert all(item["lida"] is False for item in corpo["pendencias"])


def test_inspetor_pendencias_rejeita_parametro_extra_com_formato_padrao_422(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.get(f"/app/api/laudo/{laudo_id}/pendencias?x-schemathesis-unknown-property=42")

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert isinstance(corpo["detail"], list)
    assert corpo["detail"][0]["loc"] == ["query", "x-schemathesis-unknown-property"]
    assert corpo["detail"][0]["msg"] == "Extra inputs are not permitted"
    assert corpo["detail"][0]["type"] == "extra_forbidden"


def test_inspetor_pendencias_filtros_todas_e_resolvidas(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendência aberta",
                    lida=False,
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendência resolvida",
                    lida=True,
                ),
            ]
        )
        banco.commit()

    resposta_todas = client.get(f"/app/api/laudo/{laudo_id}/pendencias?filtro=todas")
    assert resposta_todas.status_code == 200
    corpo_todas = resposta_todas.json()
    assert corpo_todas["filtro"] == "todas"
    assert corpo_todas["total"] == 2
    assert corpo_todas["total_filtrado"] == 2
    assert len(corpo_todas["pendencias"]) == 2

    resposta_resolvidas = client.get(f"/app/api/laudo/{laudo_id}/pendencias?filtro=resolvidas")
    assert resposta_resolvidas.status_code == 200
    corpo_resolvidas = resposta_resolvidas.json()
    assert corpo_resolvidas["filtro"] == "resolvidas"
    assert corpo_resolvidas["total"] == 2
    assert corpo_resolvidas["total_filtrado"] == 1
    assert len(corpo_resolvidas["pendencias"]) == 1
    assert corpo_resolvidas["pendencias"][0]["lida"] is True


def test_inspetor_pendencias_paginacao_respeita_filtro(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

        mensagens = []
        for indice in range(17):
            mensagens.append(
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo=f"Pendência aberta {indice}",
                    lida=False,
                )
            )

        for indice in range(4):
            mensagens.append(
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo=f"Pendência resolvida {indice}",
                    lida=True,
                )
            )

        banco.add_all(mensagens)
        banco.commit()

    resposta = client.get(f"/app/api/laudo/{laudo_id}/pendencias?filtro=abertas&pagina=2&tamanho=5")
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert corpo["filtro"] == "abertas"
    assert corpo["pagina"] == 2
    assert corpo["tamanho"] == 5
    assert corpo["total"] == 21
    assert corpo["total_filtrado"] == 17
    assert corpo["tem_mais"] is True
    assert len(corpo["pendencias"]) == 5
    assert all(item["lida"] is False for item in corpo["pendencias"])


def test_inspetor_pendencias_marcar_lidas_atualiza_apenas_humano_eng(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendente A",
                    lida=False,
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendente B",
                    lida=False,
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="Whisper do inspetor",
                    lida=False,
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/pendencias/marcar-lidas",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ok"] is True
    assert corpo["marcadas"] == 2

    with SessionLocal() as banco:
        abertas_humano_eng = (
            banco.query(MensagemLaudo)
            .filter(
                MensagemLaudo.laudo_id == laudo_id,
                MensagemLaudo.tipo == TipoMensagem.HUMANO_ENG.value,
                MensagemLaudo.lida.is_(False),
            )
            .count()
        )
        assert abertas_humano_eng == 0

        aberto_humano_insp = (
            banco.query(MensagemLaudo)
            .filter(
                MensagemLaudo.laudo_id == laudo_id,
                MensagemLaudo.tipo == TipoMensagem.HUMANO_INSP.value,
                MensagemLaudo.lida.is_(False),
            )
            .count()
        )
        assert aberto_humano_insp == 1


def test_inspetor_pendencia_individual_registra_historico_e_reabre(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        msg = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["revisor_a"],
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="Corrigir item de segurança da NR.",
            lida=False,
        )
        banco.add(msg)
        banco.commit()
        banco.refresh(msg)
        mensagem_id = msg.id

    resposta_resolver = client.patch(
        f"/app/api/laudo/{laudo_id}/pendencias/{mensagem_id}",
        json={"lida": True},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta_resolver.status_code == 200
    corpo_resolver = resposta_resolver.json()
    assert corpo_resolver["ok"] is True
    assert corpo_resolver["lida"] is True
    assert corpo_resolver["resolvida_por_id"] == ids["inspetor_a"]
    assert corpo_resolver["resolvida_em"]

    with SessionLocal() as banco:
        msg_db = banco.get(MensagemLaudo, mensagem_id)
        assert msg_db is not None
        assert msg_db.lida is True
        assert msg_db.resolvida_por_id == ids["inspetor_a"]
        assert msg_db.resolvida_em is not None

    resposta_reabrir = client.patch(
        f"/app/api/laudo/{laudo_id}/pendencias/{mensagem_id}",
        json={"lida": False},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta_reabrir.status_code == 200
    corpo_reabrir = resposta_reabrir.json()
    assert corpo_reabrir["ok"] is True
    assert corpo_reabrir["lida"] is False
    assert corpo_reabrir["resolvida_por_id"] is None
    assert corpo_reabrir["resolvida_em"] == ""

    with SessionLocal() as banco:
        msg_db = banco.get(MensagemLaudo, mensagem_id)
        assert msg_db is not None
        assert msg_db.lida is False
        assert msg_db.resolvida_por_id is None
        assert msg_db.resolvida_em is None


def test_inspetor_exportar_pendencias_pdf_retorna_arquivo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None
        revisor.crea = "123456-SP"

        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Ajustar item do laudo para adequacao.",
                lida=False,
            )
        )
        banco.commit()

    resposta = client.get(f"/app/api/laudo/{laudo_id}/pendencias/exportar-pdf?filtro=abertas")

    assert resposta.status_code == 200
    content_type = resposta.headers.get("content-type", "").lower()
    assert "application/pdf" in content_type

    content_disposition = resposta.headers.get("content-disposition", "").lower()
    assert "filename=" in content_disposition
    assert len(resposta.content) > 300

    pypdf = pytest.importorskip("pypdf")
    leitor = pypdf.PdfReader(io.BytesIO(resposta.content))
    texto_pdf = "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)
    texto_pdf_maiusculo = texto_pdf.upper()

    assert "RELATORIO DE PENDENCIAS DA MESA AVALIADORA" in texto_pdf_maiusculo
    assert "CARIMBO DIGITAL TARIEL.IA" in texto_pdf_maiusculo
    assert "REVISOR A" in texto_pdf_maiusculo
    assert "123456-SP" in texto_pdf_maiusculo


def test_revisor_rejeitar_exige_motivo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        data={"acao": "rejeitar", "motivo": "", "csrf_token": csrf},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Motivo obrigatório."


def test_revisor_aprovar_atualiza_status_e_registra_mensagem(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        data={"acao": "aprovar", "motivo": "", "csrf_token": csrf},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/revisao/painel"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.APROVADO.value
        assert laudo.revisado_por == ids["revisor_a"]

        msg = banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == laudo_id).order_by(MensagemLaudo.id.desc()).first()
        assert msg is not None
        assert msg.tipo == TipoMensagem.HUMANO_ENG.value
        assert "APROVADO" in msg.conteudo


def test_revisor_rejeitar_via_api_com_header_sem_motivo_assume_padrao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        data={"acao": "rejeitar", "motivo": "", "csrf_token": ""},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["success"] is True
    assert corpo["acao"] == "rejeitar"
    assert corpo["motivo"] == "Devolvido pela mesa sem motivo detalhado."

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.REJEITADO.value
        assert laudo.motivo_rejeicao == "Devolvido pela mesa sem motivo detalhado."


def test_inspetor_login_permite_bloqueio_temporario_expirado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "inspetor@empresa-a.test"))
        assert usuario is not None
        usuario.status_bloqueio = True
        usuario.bloqueado_ate = datetime.now(timezone.utc) - timedelta(minutes=1)
        banco.commit()

    tela_login = client.get("/app/login")
    csrf = _extrair_csrf(tela_login.text)

    resposta = client.post(
        "/app/login",
        data={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/app/"


def test_revisor_websocket_rejeita_sessao_inativa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    _login_revisor(client, "revisor@empresa-a.test")

    seguranca.SESSOES_ATIVAS.clear()
    seguranca._SESSAO_EXPIRACAO.clear()  # noqa: SLF001
    seguranca._SESSAO_META.clear()  # noqa: SLF001
    with SessionLocal() as banco:
        banco.query(SessaoAtiva).delete()
        banco.commit()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/revisao/ws/whispers"):
            pass

    assert exc.value.code == 4401


def test_sessao_admin_recupera_do_banco_apos_limpar_cache_memoria(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    _login_admin(client, "admin@empresa-a.test")

    with SessionLocal() as banco:
        assert banco.query(SessaoAtiva).count() == 1

    seguranca.SESSOES_ATIVAS.clear()
    seguranca._SESSAO_EXPIRACAO.clear()  # noqa: SLF001
    seguranca._SESSAO_META.clear()  # noqa: SLF001

    resposta = client.get("/admin/painel", follow_redirects=False)

    assert resposta.status_code == 200
    assert len(seguranca.SESSOES_ATIVAS) == 1


def test_sessao_admin_invalida_cache_local_quando_registro_some_do_banco(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    _login_admin(client, "admin@empresa-a.test")

    with SessionLocal() as banco:
        sessao = banco.query(SessaoAtiva).one()
        token = sessao.token
        banco.query(SessaoAtiva).filter(SessaoAtiva.token == token).delete()
        banco.commit()

    assert token in seguranca.SESSOES_ATIVAS
    assert seguranca.token_esta_ativo(token) is False
    assert token not in seguranca.SESSOES_ATIVAS

    resposta = client.get("/admin/painel", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/login"


def test_reset_senha_revoga_sessoes_ativas_do_usuario(ambiente_critico) -> None:
    client_admin = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with TestClient(main.app) as client_cliente:
        _login_cliente(client_cliente, "cliente@empresa-a.test")

        resposta_autenticada = client_cliente.get("/cliente/painel", follow_redirects=False)
        assert resposta_autenticada.status_code == 200

        _login_admin(client_admin, "admin@empresa-a.test")
        csrf_admin = _csrf_pagina(client_admin, f"/admin/clientes/{ids['empresa_a']}")

        reset = client_admin.post(
            f"/admin/clientes/{ids['empresa_a']}/resetar-senha/{ids['admin_cliente_a']}",
            data={"csrf_token": csrf_admin},
            follow_redirects=False,
        )
        assert reset.status_code == 303

        with SessionLocal() as banco:
            sessoes_usuario = banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["admin_cliente_a"]).count()
            assert sessoes_usuario == 0

        resposta_pos_reset = client_cliente.get("/cliente/painel", follow_redirects=False)
        assert resposta_pos_reset.status_code == 303
        assert resposta_pos_reset.headers["location"] == "/cliente/login"


def test_admin_reset_senha_exige_troca_no_proximo_login_sem_expor_senha(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/resetar-senha/{ids['admin_cliente_a']}",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )

    assert resposta.status_code == 303

    primeira_view = client.get(resposta.headers["location"])
    assert primeira_view.status_code == 200
    assert "deverá trocar a senha no próximo login" in primeira_view.text
    assert "Senha temporária para" not in primeira_view.text

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        assert bool(usuario.senha_temporaria_ativa) is True

    segunda_view = client.get(f"/admin/clientes/{ids['empresa_a']}")
    assert segunda_view.status_code == 200
    assert "Senha temporária para" not in segunda_view.text


def test_admin_adicionar_admin_cliente_exibe_senha_temporaria_em_flash(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/adicionar-admin-cliente",
        data={
            "csrf_token": csrf,
            "nome": "Novo Admin",
            "email": "novo.admin@empresa-a.test",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303

    primeira_view = client.get(resposta.headers["location"])
    assert primeira_view.status_code == 200
    assert "Senha temporária para Novo Admin (novo.admin@empresa-a.test):" in primeira_view.text

    segunda_view = client.get(f"/admin/clientes/{ids['empresa_a']}")
    assert segunda_view.status_code == 200
    assert "Senha temporária para Novo Admin (novo.admin@empresa-a.test):" not in segunda_view.text


def test_admin_ceo_nao_atualiza_crea_da_operacao_por_privacidade(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/usuarios/{ids['revisor_a']}/atualizar-crea",
        data={"csrf_token": csrf, "crea": " 123456-sp "},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    pagina = client.get(resposta.headers["location"])
    assert "Por privacidade, a equipe de campo e a equipe de analise sao geridas pelo administrador da empresa no portal dela." in pagina.text

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None
        assert revisor.crea in (None, "")


def test_admin_atualizar_crea_rejeita_inspetor(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/usuarios/{ids['inspetor_a']}/atualizar-crea",
        data={"csrf_token": csrf, "crea": "123456-SP"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    pagina = client.get(resposta.headers["location"])
    assert "Por privacidade, a equipe de campo e a equipe de analise sao geridas pelo administrador da empresa no portal dela." in pagina.text

    with SessionLocal() as banco:
        inspetor = banco.get(Usuario, ids["inspetor_a"])
        assert inspetor is not None
        assert inspetor.crea in (None, "")


def test_admin_detalhe_empresa_exibe_admins_cliente_e_revisores(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")

    resposta = client.get(f"/admin/clientes/{ids['empresa_a']}")

    assert resposta.status_code == 200
    assert "Administradores da empresa" in resposta.text
    assert "cliente@empresa-a.test" in resposta.text
    assert "Equipe operacional privada da empresa" in resposta.text


def test_admin_cadastrar_empresa_exibe_senha_temporaria_em_flash(ambiente_critico, monkeypatch: pytest.MonkeyPatch) -> None:
    client = ambiente_critico["client"]
    senha_temporaria = "Onboard@Temp123"

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/painel")

    class _EmpresaStub:
        id = 999
        nome_fantasia = "Cliente Stub"

    def _registrar_stub(_db: Session, **_kwargs) -> tuple[_EmpresaStub, str]:
        return _EmpresaStub(), senha_temporaria

    monkeypatch.setattr(rotas_admin, "registrar_novo_cliente", _registrar_stub)

    resposta = client.post(
        "/admin/cadastrar-empresa",
        data={
            "csrf_token": csrf,
            "nome": "Cliente Stub",
            "cnpj": "99999999000199",
            "email": "admin@cliente-stub.test",
            "plano": "Ilimitado",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert senha_temporaria not in resposta.headers["location"]

    primeira_view = client.get(resposta.headers["location"])
    assert primeira_view.status_code == 200
    assert senha_temporaria in primeira_view.text

    segunda_view = client.get("/admin/clientes")
    assert segunda_view.status_code == 200
    assert senha_temporaria not in segunda_view.text


def test_revisor_api_pacote_mesa_consolida_resumo_e_pendencias(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        agora = datetime.now(timezone.utc)
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Descrição técnica da inspeção de campo.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="documento: checklist_nr12.pdf",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="[@mesa] preciso validar um ponto de segurança.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.IA.value,
                    conteudo="Análise preliminar da IA com riscos mapeados.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendência aberta: enviar foto detalhada do quadro.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendência resolvida: evidência validada.",
                    lida=True,
                    resolvida_por_id=ids["revisor_a"],
                    resolvida_em=agora,
                    custo_api_reais=Decimal("0.0000"),
                ),
                LaudoRevisao(
                    laudo_id=laudo_id,
                    numero_versao=1,
                    origem="ia",
                    resumo="Rascunho inicial da IA",
                    conteudo="Conteúdo da versão inicial",
                    confianca_geral="media",
                ),
                LaudoRevisao(
                    laudo_id=laudo_id,
                    numero_versao=2,
                    origem="mesa",
                    resumo="Ajustes da engenharia",
                    conteudo="Conteúdo revisado com ajustes",
                    confianca_geral="alta",
                ),
            ]
        )
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert int(corpo["laudo_id"]) == laudo_id

    resumo_mensagens = corpo["resumo_mensagens"]
    assert int(resumo_mensagens["total"]) == 7
    assert int(resumo_mensagens["inspetor"]) == 4
    assert int(resumo_mensagens["ia"]) == 1
    assert int(resumo_mensagens["mesa"]) == 2

    resumo_evidencias = corpo["resumo_evidencias"]
    assert int(resumo_evidencias["total"]) == 3
    assert int(resumo_evidencias["textuais"]) == 1
    assert int(resumo_evidencias["fotos"]) == 1
    assert int(resumo_evidencias["documentos"]) == 1

    resumo_pendencias = corpo["resumo_pendencias"]
    assert int(resumo_pendencias["total"]) == 2
    assert int(resumo_pendencias["abertas"]) == 1
    assert int(resumo_pendencias["resolvidas"]) == 1
    assert corpo["collaboration"]["summary"]["open_pendency_count"] == 1
    assert corpo["collaboration"]["summary"]["recent_whisper_count"] == 3

    assert len(corpo["pendencias_abertas"]) == 1
    assert len(corpo["pendencias_resolvidas_recentes"]) == 1
    assert corpo["pendencias_resolvidas_recentes"][0]["resolvida_por_nome"] == "Revisor A"
    assert len(corpo["whispers_recentes"]) == 3
    assert len(corpo["revisoes_recentes"]) == 2


def test_revisor_api_pacote_mesa_serializa_anexos_por_mensagem(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    caminho_anexo = os.path.join(tempfile.gettempdir(), f"mesa_pkg_{uuid.uuid4().hex[:8]}.pdf")
    with open(caminho_anexo, "wb") as arquivo:
        arquivo.write(_pdf_base_bytes_teste())

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        mensagem = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["revisor_a"],
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="[ANEXO_MESA_SEM_TEXTO]",
            custo_api_reais=Decimal("0.0000"),
        )
        banco.add(mensagem)
        banco.flush()
        banco.add(
            AnexoMesa(
                laudo_id=laudo_id,
                mensagem_id=mensagem.id,
                enviado_por_id=ids["revisor_a"],
                nome_original="complemento.pdf",
                nome_arquivo="complemento.pdf",
                mime_type="application/pdf",
                categoria="documento",
                tamanho_bytes=len(_pdf_base_bytes_teste()),
                caminho_arquivo=caminho_anexo,
            )
        )
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["pendencias_abertas"]) == 1
    assert corpo["pendencias_abertas"][0]["texto"] == ""
    assert corpo["pendencias_abertas"][0]["anexos"][0]["nome"] == "complemento.pdf"
    assert corpo["pendencias_abertas"][0]["anexos"][0]["categoria"] == "documento"


def test_revisor_api_pacote_mesa_expoe_documento_estruturado_canonico_nr13(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_family_key = "nr13_inspecao_vaso_pressao"
        laudo.catalog_family_label = "NR13 · Vaso de Pressao"
        laudo.dados_formulario = {
            "schema_type": "laudo_output",
            "family_key": "nr13_inspecao_vaso_pressao",
            "resumo_executivo": "Vaso com corrosao localizada e necessidade de ajuste superficial.",
            "mesa_review": {
                "pendencias_resolvidas_texto": "Prontuario: validado pela mesa.",
                "observacoes_mesa": "Manter revisao da corrosao localizada.",
            },
            "identificacao": {
                "identificacao_do_vaso": "Vaso vertical VP-204",
                "localizacao": "Casa de utilidades - Bloco B",
                "tag_patrimonial": "TAG-VP-204",
                "placa_identificacao": {
                    "disponivel": True,
                    "descricao": "Placa parcialmente legivel durante a coleta.",
                },
            },
            "caracterizacao_do_equipamento": {
                "descricao_sumaria": "Vaso vertical em operacao com pintura desgastada.",
                "condicao_de_operacao_no_momento": "em_operacao",
            },
            "inspecao_visual": {
                "condicao_geral": "Pintura desgastada e integridade geral preservada.",
                "pontos_de_corrosao": {
                    "descricao": "Corrosao superficial localizada proxima ao suporte inferior.",
                },
                "vazamentos": {
                    "descricao": "Sem vazamentos aparentes no momento da inspecao.",
                },
            },
            "dispositivos_e_acessorios": {
                "dispositivos_de_seguranca": {
                    "descricao": "Valvula de seguranca registrada visualmente.",
                },
                "manometro": {
                    "descricao": "Manometro com visor legivel.",
                },
            },
            "documentacao_e_registros": {
                "prontuario": {
                    "disponivel": True,
                    "referencias_texto": "DOC_014 - prontuario_vp204.pdf",
                },
                "certificado": {
                    "disponivel": False,
                },
                "relatorio_anterior": {
                    "disponivel": True,
                    "referencias_texto": "DOC_015 - relatorio_anterior_2025.pdf",
                },
            },
            "nao_conformidades": {
                "ha_nao_conformidades": True,
                "descricao": "Corrosao superficial localizada na regiao inferior do vaso.",
            },
            "recomendacoes": {
                "texto": "Recomenda-se tratar a corrosao e recompor a pintura protetiva.",
            },
            "conclusao": {
                "status": "ajuste",
                "conclusao_tecnica": "Equipamento apto condicionado ao tratamento superficial.",
                "justificativa": "A corrosao localizada exige ajuste antes do fechamento final.",
            },
        }
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")

    assert resposta.status_code == 200
    corpo = resposta.json()
    documento = corpo["documento_estruturado"]
    assert documento["schema_type"] == "laudo_output"
    assert documento["family_key"] == "nr13_inspecao_vaso_pressao"
    assert documento["family_label"] == "NR13 · Vaso de Pressao"
    assert "corrosao localizada" in documento["summary"].lower()
    assert documento["review_notes"] == "Prontuario: validado pela mesa."

    secoes = {item["key"]: item for item in documento["sections"]}
    assert "identificacao" in secoes
    assert "documentacao_e_registros" in secoes
    assert "nao_conformidades" in secoes
    assert "conclusao" in secoes
    assert secoes["identificacao"]["status"] == "filled"
    assert "VP-204" in str(secoes["identificacao"]["summary"])
    assert "Certificado: ausente" in str(secoes["documentacao_e_registros"]["summary"])
    assert "Prontuario" in str(secoes["documentacao_e_registros"]["diff_short"])
    assert secoes["nao_conformidades"]["status"] == "attention"
    assert "corrosao superficial" in str(secoes["nao_conformidades"]["summary"]).lower()
    assert secoes["conclusao"]["status"] == "attention"
    assert "Ajuste" in str(secoes["conclusao"]["summary"])


def test_revisor_api_mensagens_e_completo_aceitam_cursor_nullish(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.USER.value,
                conteudo="Mensagem seed para histórico do revisor.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")

    resposta_mensagens = client.get(f"/revisao/api/laudo/{laudo_id}/mensagens?cursor=null")
    assert resposta_mensagens.status_code == 200
    assert resposta_mensagens.json()["laudo_id"] == laudo_id

    resposta_completo = client.get(f"/revisao/api/laudo/{laudo_id}/completo?incluir_historico=true&cursor=null")
    assert resposta_completo.status_code == 200
    assert int(resposta_completo.json()["id"]) == laudo_id


def test_revisor_api_pacote_rejeita_parametro_extra_com_formato_padrao_422(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote?x-schemathesis-unknown-property=42")

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert isinstance(corpo["detail"], list)
    assert corpo["detail"][0]["loc"] == ["query", "x-schemathesis-unknown-property"]
    assert corpo["detail"][0]["msg"] == "Extra inputs are not permitted"
    assert corpo["detail"][0]["type"] == "extra_forbidden"


def test_revisor_pode_resolver_e_reabrir_pendencia_da_mesa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        msg = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["revisor_a"],
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="Pendência aberta para validar aterramento.",
            lida=False,
            custo_api_reais=Decimal("0.0000"),
        )
        banco.add(msg)
        banco.commit()
        banco.refresh(msg)
        mensagem_id = int(msg.id)

    resposta_resolver = client.patch(
        f"/revisao/api/laudo/{laudo_id}/pendencias/{mensagem_id}",
        json={"lida": True},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta_resolver.status_code == 200
    corpo_resolver = resposta_resolver.json()
    assert corpo_resolver["success"] is True
    assert corpo_resolver["lida"] is True
    assert corpo_resolver["resolvida_por_id"] == ids["revisor_a"]
    assert corpo_resolver["resolvida_por_nome"] == "Revisor A"
    assert corpo_resolver["resolvida_em"]
    assert int(corpo_resolver["pendencias_abertas"]) == 0

    with SessionLocal() as banco:
        msg_db = banco.get(MensagemLaudo, mensagem_id)
        assert msg_db is not None
        assert msg_db.lida is True
        assert msg_db.resolvida_por_id == ids["revisor_a"]
        assert msg_db.resolvida_em is not None

    with TestClient(main.app) as client_inspetor:
        _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")
        resposta_mesa_resolvida = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")

    assert resposta_mesa_resolvida.status_code == 200
    item_resolvido = next(item for item in resposta_mesa_resolvida.json()["itens"] if int(item["id"]) == mensagem_id)
    assert item_resolvido["lida"] is True
    assert item_resolvido["resolvida_por_nome"] == "Revisor A"
    assert item_resolvido["resolvida_em"]

    resposta_reabrir = client.patch(
        f"/revisao/api/laudo/{laudo_id}/pendencias/{mensagem_id}",
        json={"lida": False},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta_reabrir.status_code == 200
    corpo_reabrir = resposta_reabrir.json()
    assert corpo_reabrir["success"] is True
    assert corpo_reabrir["lida"] is False
    assert corpo_reabrir["resolvida_por_id"] is None
    assert corpo_reabrir["resolvida_por_nome"] == ""
    assert corpo_reabrir["resolvida_em"] == ""
    assert int(corpo_reabrir["pendencias_abertas"]) == 1

    with SessionLocal() as banco:
        msg_db = banco.get(MensagemLaudo, mensagem_id)
        assert msg_db is not None
        assert msg_db.lida is False
        assert msg_db.resolvida_por_id is None
        assert msg_db.resolvida_em is None

    with TestClient(main.app) as client_inspetor:
        _login_app_inspetor(client_inspetor, "inspetor@empresa-a.test")
        resposta_mesa_reaberta = client_inspetor.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")

    assert resposta_mesa_reaberta.status_code == 200
    item_reaberto = next(item for item in resposta_mesa_reaberta.json()["itens"] if int(item["id"]) == mensagem_id)
    assert item_reaberto["lida"] is False
    assert item_reaberto["resolvida_por_nome"] == ""
    assert item_reaberto["resolvida_em"] == ""


def test_revisor_marca_whispers_como_lidos_no_servidor(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="Whisper 1",
                    lida=False,
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="Whisper 2",
                    lida=False,
                    custo_api_reais=Decimal("0.0000"),
                ),
            ]
        )
        banco.commit()

    resposta = client.post(
        f"/revisao/api/laudo/{laudo_id}/marcar-whispers-lidos",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["success"] is True
    assert int(corpo["marcadas"]) == 2

    with SessionLocal() as banco:
        total_aberto = (
            banco.query(MensagemLaudo)
            .filter(
                MensagemLaudo.laudo_id == laudo_id,
                MensagemLaudo.tipo == TipoMensagem.HUMANO_INSP.value,
                MensagemLaudo.lida.is_(False),
            )
            .count()
        )
        assert total_aberto == 0


def test_revisor_api_pacote_mesa_respeita_isolamento_multiempresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_empresa_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_empresa_b}/pacote")

    assert resposta.status_code == 404


def test_revisor_exportar_pacote_mesa_pdf_retorna_arquivo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None
        revisor.crea = "987654-SP"

        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Descricao de campo para consolidacao do pacote.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendencia aberta para revisar instalacao eletrica.",
                    lida=False,
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="[@mesa] Preciso confirmar o trecho final do parecer técnico.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                LaudoRevisao(
                    laudo_id=laudo_id,
                    numero_versao=1,
                    origem="mesa",
                    resumo="Ajuste inicial da mesa",
                    conteudo="Conteudo revisado pela engenharia.",
                    confianca_geral="media",
                    criado_em=datetime.now(timezone.utc),
                ),
            ]
        )
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf")

    assert resposta.status_code == 200
    content_type = resposta.headers.get("content-type", "").lower()
    assert "application/pdf" in content_type

    content_disposition = resposta.headers.get("content-disposition", "").lower()
    assert "filename=" in content_disposition
    assert len(resposta.content) > 300

    pypdf = pytest.importorskip("pypdf")
    leitor = pypdf.PdfReader(io.BytesIO(resposta.content))
    texto_pdf = "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)
    texto_pdf_maiusculo = texto_pdf.upper()

    assert "PACOTE TECNICO DA MESA AVALIADORA" in texto_pdf_maiusculo
    assert "RESUMO CONSOLIDADO" in texto_pdf_maiusculo
    assert "REVISOR A" in texto_pdf_maiusculo
    assert "987654-SP" in texto_pdf_maiusculo
    assert "PARECER TÉCNICO" in texto_pdf.upper()


def test_revisor_exportar_pacote_oficial_zip_retorna_manifesto_e_hashes(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    caminho_anexo = os.path.join(tempfile.gettempdir(), f"mesa_zip_{uuid.uuid4().hex[:8]}.pdf")
    caminho_pdf_emitido: Path | None = None
    payload_pdf_emitido = _pdf_base_bytes_teste()
    with open(caminho_anexo, "wb") as arquivo:
        arquivo.write(_pdf_base_bytes_teste())

    try:
        with SessionLocal() as banco:
            laudo_id = _criar_laudo(
                banco,
                empresa_id=ids["empresa_a"],
                usuario_id=ids["inspetor_a"],
                status_revisao=StatusRevisao.APROVADO.value,
            )
            laudo = banco.get(Laudo, laudo_id)
            assert laudo is not None
            laudo.nome_arquivo_pdf = "laudo_emitido.pdf"
            laudo.report_pack_draft_json = {"quality_gates": {"missing_evidence": []}}

            mensagem = MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Checklist final consolidado para emissao oficial.",
                custo_api_reais=Decimal("0.0000"),
            )
            whisper = MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.HUMANO_INSP.value,
                conteudo="[@mesa] Confirmem se o checklist final está coerente com a emissão.",
                custo_api_reais=Decimal("0.0000"),
            )
            banco.add_all([mensagem, whisper])
            banco.flush()
            banco.add(
                AnexoMesa(
                    laudo_id=laudo_id,
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
            banco.add(
                SignatarioGovernadoLaudo(
                    tenant_id=ids["empresa_a"],
                    nome="Eng. Revisor A",
                    funcao="Responsável técnico",
                    registro_profissional="CREA 987654-SP",
                    valid_until=datetime.now(timezone.utc) + timedelta(days=120),
                    allowed_family_keys_json=[str(laudo.catalog_family_key or laudo.tipo_template)],
                    ativo=True,
                    criado_por_id=ids["admin_a"],
                )
            )
            banco.commit()
            caminho_pdf_emitido = (
                WEB_ROOT
                / "storage"
                / "laudos_emitidos"
                / f"empresa_{ids['empresa_a']}"
                / f"laudo_{laudo_id}"
                / "v0003"
                / "laudo_emitido.pdf"
            )
            caminho_pdf_emitido.parent.mkdir(parents=True, exist_ok=True)
            caminho_pdf_emitido.write_bytes(payload_pdf_emitido)

        _login_revisor(client, "revisor@empresa-a.test")
        resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-oficial")

        assert resposta.status_code == 200
        assert "application/zip" in resposta.headers.get("content-type", "").lower()

        with zipfile.ZipFile(io.BytesIO(resposta.content)) as arquivo_zip:
            nomes = set(arquivo_zip.namelist())
            assert "manifest.json" in nomes
            assert "payloads/pacote_mesa.json" in nomes
            assert "payloads/emissao_oficial.json" in nomes
            assert "exports/pacote_mesa_review.pdf" in nomes
            assert "documentos/laudo_emitido.pdf" in nomes
            assert "governanca/catalog_binding_trace.json" in nomes
            assert any(nome.startswith("anexos_mesa/") for nome in nomes)
            assert arquivo_zip.read("documentos/laudo_emitido.pdf") == payload_pdf_emitido

            manifest = json.loads(arquivo_zip.read("manifest.json").decode("utf-8"))

        assert manifest["bundle_kind"] == "tariel_official_issue_package"
        assert isinstance(manifest["ready_for_issue"], bool)
        assert manifest["artifact_count"] >= 5
        assert manifest["audit_trail_count"] >= 1
        assert any(
            item["archive_path"] == "exports/pacote_mesa_review.pdf" and item["sha256"]
            for item in manifest["artifacts"]
        )
        assert any(
            item["archive_path"] == "documentos/laudo_emitido.pdf"
            and item["present"] is True
            and item["sha256"] == hashlib.sha256(payload_pdf_emitido).hexdigest()
            for item in manifest["artifacts"]
        )
        assert any(
            item["archive_path"] == "governanca/catalog_binding_trace.json" and item["sha256"]
            for item in manifest["artifacts"]
        )
        assert any(
            str(item["archive_path"]).startswith("anexos_mesa/") and item["present"] is True
            for item in manifest["artifacts"]
        )
    finally:
        if os.path.exists(caminho_anexo):
            os.remove(caminho_anexo)
        if caminho_pdf_emitido is not None and caminho_pdf_emitido.exists():
            caminho_pdf_emitido.unlink()


def test_revisor_emite_oficialmente_bundle_congelado_com_replay_idempotente(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    caminho_anexo = os.path.join(tempfile.gettempdir(), f"mesa_issue_{uuid.uuid4().hex[:8]}.pdf")
    with open(caminho_anexo, "wb") as arquivo:
        arquivo.write(_pdf_base_bytes_teste())

    try:
        with SessionLocal() as banco:
            laudo_id = _criar_laudo(
                banco,
                empresa_id=ids["empresa_a"],
                usuario_id=ids["inspetor_a"],
                status_revisao=StatusRevisao.APROVADO.value,
            )
            laudo = banco.get(Laudo, laudo_id)
            assert laudo is not None
            laudo.nome_arquivo_pdf = "laudo_emitido.pdf"
            laudo.tipo_template = "nr13"
            laudo.catalog_family_key = "nr13_inspecao_caldeira"
            laudo.report_pack_draft_json = {"quality_gates": {"missing_evidence": []}}

            mensagem = MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Checklist final consolidado para emissao transacional.",
                custo_api_reais=Decimal("0.0000"),
            )
            banco.add(mensagem)
            banco.flush()

            banco.add(
                ApprovedCaseSnapshot(
                    laudo_id=laudo_id,
                    empresa_id=ids["empresa_a"],
                    family_key="nr13_inspecao_caldeira",
                    approval_version=1,
                    document_outcome="approved",
                    laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
                )
            )
            banco.add(
                AnexoMesa(
                    laudo_id=laudo_id,
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
            signatario = SignatarioGovernadoLaudo(
                tenant_id=ids["empresa_a"],
                nome="Eng. Revisor A",
                funcao="Responsável técnico",
                registro_profissional="CREA 987654-SP",
                valid_until=datetime.now(timezone.utc) + timedelta(days=120),
                allowed_family_keys_json=["nr13_inspecao_caldeira"],
                ativo=True,
                criado_por_id=ids["admin_a"],
            )
            banco.add(signatario)
            banco.commit()
            signatory_id = int(signatario.id)

        csrf = _login_revisor(client, "revisor@empresa-a.test")
        resposta = client.post(
            f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            json={"signatory_id": signatory_id},
        )

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["success"] is True
        assert corpo["idempotent_replay"] is False
        assert corpo["issue_number"].startswith("TAR-")
        assert corpo["record"]["package_storage_ready"] is True
        assert corpo["download_url"].endswith("/emissao-oficial/download")

        replay = client.post(
            f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            json={"signatory_id": signatory_id},
        )

        assert replay.status_code == 200
        corpo_replay = replay.json()
        assert corpo_replay["success"] is True
        assert corpo_replay["idempotent_replay"] is True
        assert corpo_replay["issue_number"] == corpo["issue_number"]
        assert corpo_replay["record"]["id"] == corpo["record"]["id"]

        resposta_download = client.get(corpo["download_url"])
        assert resposta_download.status_code == 200
        assert "application/zip" in resposta_download.headers.get("content-type", "").lower()
        with zipfile.ZipFile(io.BytesIO(resposta_download.content)) as arquivo_zip:
            manifest = json.loads(arquivo_zip.read("manifest.json").decode("utf-8"))
        assert manifest["bundle_kind"] == "tariel_official_issue_package"

        with SessionLocal() as banco:
            registros = banco.scalars(
                select(EmissaoOficialLaudo)
                .where(EmissaoOficialLaudo.laudo_id == laudo_id)
                .order_by(EmissaoOficialLaudo.id.asc())
            ).all()
            assert len(registros) == 1
            assert registros[0].issue_number == corpo["issue_number"]
            assert registros[0].issue_state == "issued"
            assert registros[0].package_storage_path
            with open(str(registros[0].package_storage_path), "rb") as arquivo_congelado:
                assert arquivo_congelado.read() == resposta_download.content
    finally:
        if os.path.exists(caminho_anexo):
            os.remove(caminho_anexo)


def test_revisor_reemite_oficialmente_quando_pdf_diverge_e_limpa_alerta(
    ambiente_critico,
    monkeypatch,
    tmp_path: Path,
) -> None:
    import app.shared.official_issue_package as official_issue_package
    import app.shared.official_issue_transaction as official_issue_transaction

    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(official_issue_package, "WEB_ROOT", tmp_path)
    monkeypatch.setattr(official_issue_transaction, "WEB_ROOT", tmp_path)

    payload_pdf_emitido_v3 = _pdf_base_bytes_teste()
    payload_pdf_emitido_v4 = payload_pdf_emitido_v3 + b"\n% reissue-v0004\n"

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.nome_arquivo_pdf = "laudo_emitido.pdf"
        laudo.tipo_template = "nr13"
        laudo.catalog_family_key = "nr13_inspecao_caldeira"
        laudo.report_pack_draft_json = {"quality_gates": {"missing_evidence": []}}
        codigo_hash = str(laudo.codigo_hash)

        banco.add(
            ApprovedCaseSnapshot(
                laudo_id=laudo_id,
                empresa_id=ids["empresa_a"],
                family_key="nr13_inspecao_caldeira",
                approval_version=1,
                document_outcome="approved",
                laudo_output_snapshot={"codigo_hash": laudo.codigo_hash},
            )
        )
        signatario = SignatarioGovernadoLaudo(
            tenant_id=ids["empresa_a"],
            nome="Eng. Revisor A",
            funcao="Responsável técnico",
            registro_profissional="CREA 987654-SP",
            valid_until=datetime.now(timezone.utc) + timedelta(days=120),
            allowed_family_keys_json=["nr13_inspecao_caldeira"],
            ativo=True,
            criado_por_id=ids["admin_a"],
        )
        banco.add(signatario)
        banco.commit()
        signatory_id = int(signatario.id)

    caminho_pdf_v3 = (
        tmp_path
        / "storage"
        / "laudos_emitidos"
        / f"empresa_{ids['empresa_a']}"
        / f"laudo_{laudo_id}"
        / "v0003"
        / "laudo_emitido.pdf"
    )
    caminho_pdf_v3.parent.mkdir(parents=True, exist_ok=True)
    caminho_pdf_v3.write_bytes(payload_pdf_emitido_v3)

    csrf = _login_revisor(client, "revisor@empresa-a.test")
    primeira = client.post(
        f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={"signatory_id": signatory_id},
    )

    assert primeira.status_code == 200
    corpo_primeira = primeira.json()
    assert corpo_primeira["success"] is True
    assert corpo_primeira["reissued"] is False
    assert corpo_primeira["idempotent_replay"] is False
    assert corpo_primeira["record"]["primary_pdf_storage_version"] == "v0003"
    assert corpo_primeira["record"]["primary_pdf_diverged"] is False

    caminho_pdf_v4 = caminho_pdf_v3.parent.parent / "v0004" / "laudo_emitido.pdf"
    caminho_pdf_v4.parent.mkdir(parents=True, exist_ok=True)
    caminho_pdf_v4.write_bytes(payload_pdf_emitido_v4)

    pacote_divergente = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert pacote_divergente.status_code == 200
    emissao_divergente = pacote_divergente.json()["emissao_oficial"]
    assert emissao_divergente["reissue_recommended"] is True
    assert emissao_divergente["issue_action_label"] == "Reemitir oficialmente"
    assert emissao_divergente["current_issue"]["issue_number"] == corpo_primeira["issue_number"]
    assert emissao_divergente["current_issue"]["primary_pdf_diverged"] is True
    assert emissao_divergente["current_issue"]["current_primary_pdf_storage_version"] == "v0004"

    segunda = client.post(
        f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "signatory_id": signatory_id,
            "expected_current_issue_id": corpo_primeira["record"]["id"],
            "expected_current_issue_number": corpo_primeira["issue_number"],
        },
    )

    assert segunda.status_code == 200
    corpo_segunda = segunda.json()
    assert corpo_segunda["success"] is True
    assert corpo_segunda["idempotent_replay"] is False
    assert corpo_segunda["reissued"] is True
    assert corpo_segunda["superseded_issue_number"] == corpo_primeira["issue_number"]
    assert "primary_pdf_diverged" in corpo_segunda["reissue_reason_codes"]
    assert corpo_segunda["record"]["reissue_of_issue_id"] == corpo_primeira["record"]["id"]
    assert corpo_segunda["record"]["reissue_of_issue_number"] == corpo_primeira["issue_number"]
    assert corpo_segunda["record"]["primary_pdf_storage_version"] == "v0004"
    assert corpo_segunda["record"]["current_primary_pdf_storage_version"] == "v0004"
    assert corpo_segunda["record"]["primary_pdf_diverged"] is False

    replay_desatualizado = client.post(
        f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        json={
            "signatory_id": signatory_id,
            "expected_current_issue_id": corpo_primeira["record"]["id"],
            "expected_current_issue_number": corpo_primeira["issue_number"],
        },
    )
    assert replay_desatualizado.status_code == 409
    assert "mudou antes da reemissão" in replay_desatualizado.json()["detail"]

    pacote_alinhado = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert pacote_alinhado.status_code == 200
    emissao_alinhada = pacote_alinhado.json()["emissao_oficial"]
    assert emissao_alinhada["reissue_recommended"] is False
    assert emissao_alinhada["issue_status"] == "issued_officially"
    assert emissao_alinhada["current_issue"]["issue_number"] == corpo_segunda["issue_number"]
    assert emissao_alinhada["current_issue"]["reissue_of_issue_number"] == corpo_primeira["issue_number"]
    assert "primary_pdf_diverged" in emissao_alinhada["current_issue"]["reissue_reason_codes"]
    assert emissao_alinhada["current_issue"]["reissue_reason_summary"] == "Reemissão motivada por divergência do PDF principal."
    assert emissao_alinhada["current_issue"]["primary_pdf_diverged"] is False

    resposta_download = client.get(corpo_segunda["download_url"])
    assert resposta_download.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resposta_download.content)) as arquivo_zip:
        assert arquivo_zip.read("documentos/laudo_emitido.pdf") == payload_pdf_emitido_v4

    verificacao_publica = client.get(
        f"/app/public/laudo/verificar/{codigo_hash}?format=json",
        headers={"Accept": "application/json"},
    )
    assert verificacao_publica.status_code == 200
    payload_publico = verificacao_publica.json()
    assert payload_publico["official_issue_number"] == corpo_segunda["issue_number"]
    assert payload_publico["official_issue_primary_pdf_diverged"] is False
    assert payload_publico["official_issue_primary_pdf_comparison_status"] == "aligned"

    with SessionLocal() as banco:
        registros = banco.scalars(
            select(EmissaoOficialLaudo)
            .where(EmissaoOficialLaudo.laudo_id == laudo_id)
            .order_by(EmissaoOficialLaudo.id.asc())
        ).all()
        assert len(registros) == 2
        anterior, atual = registros
        assert anterior.issue_state == "superseded"
        assert anterior.superseded_by_issue_id == atual.id
        assert atual.issue_state == "issued"
        assert atual.issue_context_json["reissue_of_issue_id"] == anterior.id
        assert atual.issue_context_json["reissue_of_issue_number"] == anterior.issue_number
        assert "primary_pdf_diverged" in atual.issue_context_json["reissue_reason_codes"]
        assert anterior.issue_context_json["superseded_by_issue_number"] == atual.issue_number
        assert "primary_pdf_diverged" in anterior.issue_context_json["superseded_reason_codes"]


def test_revisor_exportar_pacote_mesa_pdf_suporta_anexos_nas_pendencias(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    caminho_anexo = os.path.join(tempfile.gettempdir(), f"mesa_pdf_{uuid.uuid4().hex[:8]}.pdf")
    with open(caminho_anexo, "wb") as arquivo:
        arquivo.write(_pdf_base_bytes_teste())

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        mensagem = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["revisor_a"],
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="[ANEXO_MESA_SEM_TEXTO]",
            lida=False,
            custo_api_reais=Decimal("0.0000"),
        )
        banco.add(mensagem)
        banco.flush()
        banco.add(
            AnexoMesa(
                laudo_id=laudo_id,
                mensagem_id=mensagem.id,
                enviado_por_id=ids["revisor_a"],
                nome_original="complemento.pdf",
                nome_arquivo="complemento.pdf",
                mime_type="application/pdf",
                categoria="documento",
                tamanho_bytes=os.path.getsize(caminho_anexo),
                caminho_arquivo=caminho_anexo,
            )
        )
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf")

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert len(resposta.content) > 300


def test_revisor_exportar_pacote_pdf_rejeita_parametro_extra_com_formato_padrao_422(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf?x-schemathesis-unknown-property=42")

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert isinstance(corpo["detail"], list)
    assert corpo["detail"][0]["loc"] == ["query", "x-schemathesis-unknown-property"]
    assert corpo["detail"][0]["msg"] == "Extra inputs are not permitted"
    assert corpo["detail"][0]["type"] == "extra_forbidden"


def test_revisor_exportar_pacote_pdf_em_modo_schemathesis_retorna_placeholder_estavel(ambiente_critico, monkeypatch) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    monkeypatch.setenv("SCHEMATHESIS_TEST_HINTS", "1")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf")

    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type", "").lower())
    assert resposta.content.startswith(b"%PDF")


def test_revisor_exportar_pacote_mesa_pdf_respeita_isolamento_multiempresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_empresa_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    _login_revisor(client, "revisor@empresa-a.test")
    resposta = client.get(f"/revisao/api/laudo/{laudo_empresa_b}/pacote/exportar-pdf")
    assert resposta.status_code == 404
