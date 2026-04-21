from __future__ import annotations

from app.shared.database import Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from tests.regras_rotas_criticas_support import _criar_laudo, _login_app_inspetor


def test_inspetor_pode_excluir_rascunho_local_com_historico_visivel(ambiente_critico) -> None:
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
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Rascunho local visivel no historico."
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["inspetor_a"],
                tipo=TipoMensagem.USER.value,
                conteudo="Primeira evidencia do rascunho local.",
                lida=True,
            )
        )
        banco.commit()

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta = client.delete(
        f"/app/api/laudo/{laudo_id}",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}

    with SessionLocal() as banco:
        assert banco.get(Laudo, laudo_id) is None


def test_inspetor_nao_pode_excluir_laudo_aguardando_mesa(ambiente_critico) -> None:
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

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta = client.delete(
        f"/app/api/laudo/{laudo_id}",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Esse laudo não pode ser excluído no estado atual."

    with SessionLocal() as banco:
        assert banco.get(Laudo, laudo_id) is not None
