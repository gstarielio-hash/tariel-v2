from __future__ import annotations

import os
import uuid
from pathlib import Path

from sqlalchemy import event

from app.shared.database import Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from app.shared.security import criar_sessao


def test_get_app_boot_ssr_remove_n_plus_one_de_mensagens_laudo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        for indice in range(12):
            laudo = Laudo(
                empresa_id=ids["empresa_a"],
                usuario_id=ids["inspetor_a"],
                setor_industrial=f"Laudo boot {indice}",
                tipo_template="padrao",
                status_revisao=StatusRevisao.RASCUNHO.value,
                codigo_hash=uuid.uuid4().hex,
                modo_resposta="detalhado",
                primeira_mensagem=None,
                is_deep_research=False,
                pinado=indice < 2,
            )
            if indice == 10:
                laudo.status_revisao = StatusRevisao.AGUARDANDO.value
                laudo.setor_industrial = "Laudo aguardando sem mensagem"
            if indice == 11:
                laudo.setor_industrial = "Laudo oculto sem interação"

            banco.add(laudo)
            banco.flush()

            if indice < 10:
                banco.add(
                    MensagemLaudo(
                        laudo_id=laudo.id,
                        remetente_id=ids["inspetor_a"],
                        tipo=TipoMensagem.USER.value,
                        conteudo=f"Evidência técnica {indice}",
                    )
                )
                laudo.primeira_mensagem = f"Evidência técnica {indice}"

        banco.commit()

    token = criar_sessao(ids["inspetor_a"])

    with SessionLocal() as banco:
        engine = banco.get_bind()

    consultas_mensagens: list[str] = []

    def _capturar_sql(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:  # noqa: ANN001
        sql = " ".join(str(statement or "").lower().split())
        if "from mensagens_laudo" in sql:
            consultas_mensagens.append(sql)

    event.listen(engine, "before_cursor_execute", _capturar_sql)
    cwd_anterior = os.getcwd()
    try:
        os.chdir(Path(__file__).resolve().parents[1])
        resposta = client.get("/app/?home=1", headers={"Authorization": f"Bearer {token}"})
    finally:
        os.chdir(cwd_anterior)
        event.remove(engine, "before_cursor_execute", _capturar_sql)

    assert resposta.status_code == 200
    assert "Portal do Inspetor" in resposta.text
    assert "Laudo aguardando sem mensagem" in resposta.text
    assert "Laudo oculto sem interação" not in resposta.text
    assert len(consultas_mensagens) <= 3
    assert not any("select mensagens_laudo.id" in sql and "where mensagens_laudo.laudo_id =" in sql and "limit" in sql for sql in consultas_mensagens)
