from __future__ import annotations

import io

import pytest

from nucleo.template_editor_word import (
    _gerar_pdf_fallback_texto,
    _substituir_placeholders_texto,
    montar_html_documento_editor,
)


def test_substituir_placeholders_texto_aceita_duas_chaves() -> None:
    texto = "Cliente {{token:cliente_nome}} | Codigo {{json_path:document_control.document_code}}"
    payload = {
        "tokens": {"cliente_nome": "Cliente XPTO"},
        "document_control": {"document_code": "DOC-123"},
    }

    resolvido = _substituir_placeholders_texto(texto, payload)

    assert "Cliente XPTO" in resolvido
    assert "DOC-123" in resolvido


def test_substituir_placeholders_texto_aceita_uma_chave_para_templates_legados() -> None:
    texto = "Cliente {token:cliente_nome} | Revisao {token:documento_revisao}"
    payload = {
        "tokens": {
            "cliente_nome": "Cliente XPTO",
            "documento_revisao": "v4",
        }
    }

    resolvido = _substituir_placeholders_texto(texto, payload)

    assert "Cliente XPTO" in resolvido
    assert "v4" in resolvido


def test_montar_html_documento_editor_preserva_classes_e_tema() -> None:
    html = montar_html_documento_editor(
        documento_editor_json={
            "version": 1,
            "doc": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"className": "doc-kicker"},
                        "content": [{"type": "text", "text": "Biblioteca Tariel"}],
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 1},
                        "content": [{"type": "placeholder", "attrs": {"mode": "token", "key": "documento_titulo"}}],
                    },
                    {
                        "type": "table",
                        "attrs": {"className": "doc-compact doc-cover"},
                        "content": [
                            {
                                "type": "tableRow",
                                "content": [
                                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Campo"}]}]},
                                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Valor"}]}]},
                                ],
                            }
                        ],
                    },
                ],
            },
        },
        estilo_json={
            "tema": {
                "primaria": "#102030",
                "secundaria": "#405060",
                "acento": "#708090",
                "suave": "#eef1f4",
                "borda": "#ccd4dc",
            }
        },
        assets_json=[],
        dados_formulario={"tokens": {"documento_titulo": "Laudo Mestre"}},
    )

    assert 'class="doc-kicker"' in html
    assert 'class="doc-compact doc-cover"' in html
    assert "<h1>Laudo Mestre</h1>" in html
    assert "--tariel-primary: #102030;" in html
    assert "--tariel-border: #ccd4dc;" in html


def test_montar_html_documento_editor_renderiza_bloco_de_verificacao_publica() -> None:
    html = montar_html_documento_editor(
        documento_editor_json={
            "version": 1,
            "doc": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Conteudo principal do laudo."}],
                    }
                ],
            },
        },
        estilo_json=None,
        assets_json=[],
        dados_formulario={},
        public_verification={
            "codigo_hash": "abc123ef",
            "verification_url": "https://tariel.app/app/public/laudo/verificar/abc123ef",
            "qr_image_data_uri": "data:image/png;base64,ZmFrZQ==",
        },
    )

    assert "Verificacao Publica" in html
    assert "https://tariel.app/app/public/laudo/verificar/abc123ef" in html
    assert "data:image/png;base64,ZmFrZQ==" in html


def test_gerar_pdf_fallback_texto_monta_documento_estruturado_para_payload_catalogado() -> None:
    payload = {
        "schema_type": "laudo_output",
        "family_label": "NR13 - Inspecao de Vaso de Pressao",
        "document_control": {
            "document_code": "DOC-NR13-204",
            "revision": "R2",
            "title": "NR13 - Inspecao de Vaso de Pressao",
        },
        "case_context": {
            "empresa_nome": "Cliente XPTO",
            "unidade_nome": "Planta Sul",
            "data_execucao": "2026-04-09",
            "data_emissao": "2026-04-10",
        },
        "tokens": {
            "engenheiro_responsavel": "Gabriel Santos",
        },
        "escopo_servico": {
            "tipo_entrega": "inspecao_tecnica",
            "modo_execucao": "in_loco",
        },
        "identificacao": {
            "identificacao_do_vaso": "Vaso vertical VP-204",
            "localizacao": "Planta Sul",
        },
        "documentacao_e_registros": {
            "prontuario": {"referencias_texto": "DOC_014 - prontuario_vp204.pdf"},
        },
        "evidencias_e_anexos": {
            "documento_base": {"referencias_texto": "DOC_014 - prontuario_vp204.pdf"},
        },
        "mesa_review": {
            "status": "aprovado",
            "family_lock": True,
            "scope_mismatch": False,
        },
        "conclusao": {
            "status": "ajuste",
            "conclusao_tecnica": "Equipamento apto com acompanhamento do ponto de corrosao.",
        },
    }

    pdf_bytes = _gerar_pdf_fallback_texto(
        documento_editor_json={},
        dados_formulario=payload,
    )

    pypdf = pytest.importorskip("pypdf")
    leitor = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    texto_pdf = "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)
    texto_pdf_maiusculo = texto_pdf.upper()

    assert "QUADRO DE CONTROLE DO DOCUMENTO" in texto_pdf_maiusculo
    assert "RESUMO EXECUTIVO" in texto_pdf_maiusculo
    assert "MATRIZ DE EVIDENCIAS" in texto_pdf_maiusculo
    assert "VASO VERTICAL VP-204" in texto_pdf_maiusculo
    assert "PREVIEW DE TEMPLATE (FALLBACK)" not in texto_pdf_maiusculo
    assert "FAMILY LOCK" not in texto_pdf_maiusculo
