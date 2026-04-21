from __future__ import annotations

import io

import pytest

from app.domains.chat.learning_helpers import registrar_aprendizado_visual_automatico_chat
from app.shared.database import AnexoMesa, Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from nucleo.inspetor.comandos_chat import analisar_pedido_relatorio_chat_livre
from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _imagem_png_data_uri_teste,
    _login_app_inspetor,
)


def test_analisar_pedido_relatorio_chat_livre_detecta_variacoes() -> None:
    assert analisar_pedido_relatorio_chat_livre("faça um relatório em pdf")
    assert analisar_pedido_relatorio_chat_livre("gera um relatorio profissional")
    assert analisar_pedido_relatorio_chat_livre("consegue criar um pdf com isso?")
    assert not analisar_pedido_relatorio_chat_livre("preciso analisar o equipamento")


def test_api_chat_pedido_natural_de_relatorio_gera_pdf_com_fotos(ambiente_critico) -> None:
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
        laudo.primeira_mensagem = "Inspecao livre em equipamento industrial do patio."
        laudo.parecer_ia = (
            "Analise preliminar: ha indicios de desgaste funcional e ausencia de identificacao visual suficiente."
        )
        mensagem_base = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["inspetor_a"],
            tipo=TipoMensagem.USER.value,
            conteudo="Primeira imagem mostra desgaste aparente e ausencia de identificacao visivel no conjunto inspecionado.",
        )
        banco.add(mensagem_base)
        banco.flush()
        evidencia_1 = registrar_aprendizado_visual_automatico_chat(
            banco,
            empresa_id=ids["empresa_a"],
            laudo_id=laudo_id,
            criado_por_id=ids["inspetor_a"],
            setor_industrial="geral",
            mensagem_id=int(mensagem_base.id),
            mensagem_chat=mensagem_base.conteudo,
            dados_imagem=_imagem_png_data_uri_teste(),
        )
        assert evidencia_1 is not None
        evidencia_1.sintese_consolidada = (
            "Desgaste aparente e ausencia de identificacao visual no primeiro conjunto registrado."
        )
        evidencia_1.pontos_chave_json = [
            "Verificar integridade do componente principal",
            "Confirmar identificacao e rastreabilidade do conjunto",
        ]
        evidencia_1.referencias_norma_json = [
            "Norma aplicavel item 4.2",
            "Procedimento de inspecao item 7.1",
        ]
        mensagem_ia = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["inspetor_a"],
            tipo=TipoMensagem.IA.value,
            conteudo=(
                "A IA identificou necessidade de verificar integridade do conjunto, documentacao e rastreabilidade."
            ),
        )
        banco.add(mensagem_ia)
        mensagem_base_2 = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["inspetor_a"],
            tipo=TipoMensagem.USER.value,
            conteudo="Segunda imagem mostra desalinhamento funcional e desgaste adicional em outro ponto do equipamento.",
        )
        banco.add(mensagem_base_2)
        banco.flush()
        evidencia_2 = registrar_aprendizado_visual_automatico_chat(
            banco,
            empresa_id=ids["empresa_a"],
            laudo_id=laudo_id,
            criado_por_id=ids["inspetor_a"],
            setor_industrial="geral",
            mensagem_id=int(mensagem_base_2.id),
            mensagem_chat=mensagem_base_2.conteudo,
            dados_imagem=_imagem_png_data_uri_teste(),
        )
        assert evidencia_2 is not None
        evidencia_2.sintese_consolidada = (
            "Desalinhamento funcional e desgaste adicional que justificam revisao imediata do segundo registro."
        )
        evidencia_2.pontos_chave_json = [
            "Comparar desgaste entre os componentes associados",
            "Isolar a operacao ate nova validacao tecnica",
        ]
        evidencia_2.referencias_norma_json = [
            "Norma aplicavel item 5.1",
        ]
        mensagem_ia_2 = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["inspetor_a"],
            tipo=TipoMensagem.IA.value,
            conteudo=(
                "A segunda evidencia reforca risco operacional e pede isolamento preventivo."
            ),
        )
        banco.add(mensagem_ia_2)
        banco.commit()

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "faça um relatório em pdf com base nisso",
            "historico": [],
            "laudo_id": laudo_id,
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "relatorio_chat_livre"
    assert corpo["laudo_id"] == laudo_id
    assert "Relatório técnico consolidado gerado em PDF" in corpo["texto"]
    assert len(corpo["anexos"]) == 1
    anexo = corpo["anexos"][0]
    assert anexo["categoria"] == "documento"
    assert anexo["mime_type"] == "application/pdf"
    assert anexo["url"].endswith(f"/app/api/laudo/{laudo_id}/mesa/anexos/{anexo['id']}")

    download = client.get(anexo["url"])
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
    assert "application/pdf" in (download.headers.get("content-type", "").lower())
    pypdf = pytest.importorskip("pypdf")
    leitor = pypdf.PdfReader(io.BytesIO(download.content))
    texto_pdf = "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)
    assert len(leitor.pages) >= 5
    assert "Laudo Técnico Consolidado" in texto_pdf
    assert "Sumário" in texto_pdf or "Sumario" in texto_pdf
    assert "Objetivo e Escopo" in texto_pdf
    assert "Base de Análise e Critérios" in texto_pdf or "Base de Analise e Criterios" in texto_pdf
    assert "Síntese Executiva" in texto_pdf or "Sintese Executiva" in texto_pdf
    assert "Achados Técnicos" in texto_pdf or "Achados Tecnicos" in texto_pdf
    assert "Conclusão Técnica" in texto_pdf or "Conclusao Tecnica" in texto_pdf
    assert "Recomendações e Próximos Passos" in texto_pdf or "Recomendacoes e Proximos Passos" in texto_pdf
    assert "Resumo das Evidências" in texto_pdf or "Resumo das Evidencias" in texto_pdf
    assert "Caderno de Evidências" in texto_pdf or "Caderno de Evidencias" in texto_pdf
    assert "Evidência 1" in texto_pdf or "Evidencia 1" in texto_pdf
    assert "Evidência 2" in texto_pdf or "Evidencia 2" in texto_pdf
    assert "Desgaste aparente e ausencia de identificacao visual" in texto_pdf
    assert "Desalinhamento funcional e desgaste adicional" in texto_pdf
    assert "Norma aplicavel item 4.2" in texto_pdf
    assert "Norma aplicavel item 5.1" in texto_pdf
    assert "Chat Livre" not in texto_pdf
    assert "Documento genérico consolidado" not in texto_pdf
    assert "[imagem]" not in texto_pdf
    assert "**" not in texto_pdf

    historico = client.get(f"/app/api/laudo/{laudo_id}/mensagens")
    assert historico.status_code == 200
    itens = historico.json()["itens"]
    ultima = itens[-1]
    assert ultima["tipo"] == TipoMensagem.IA.value
    assert ultima["anexos"][0]["url"].endswith(
        f"/app/api/laudo/{laudo_id}/mesa/anexos/{ultima['anexos'][0]['id']}"
    )

    with SessionLocal() as banco:
        anexo_db = banco.get(AnexoMesa, int(anexo["id"]))
        assert anexo_db is not None
        assert anexo_db.laudo_id == laudo_id
        assert anexo_db.mensagem_id == int(corpo["mensagem_id"])
        ultima_mensagem = (
            banco.query(MensagemLaudo)
            .filter(MensagemLaudo.laudo_id == laudo_id)
            .order_by(MensagemLaudo.id.desc())
            .first()
        )
        assert ultima_mensagem is not None
        assert ultima_mensagem.tipo == TipoMensagem.IA.value
        assert "Relatório técnico consolidado gerado em PDF" in ultima_mensagem.conteudo
