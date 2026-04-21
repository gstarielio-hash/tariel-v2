from __future__ import annotations

from app.domains.chat.chat_runtime import resolver_modo_entrada_caso
from app.shared.database import Laudo
from tests.regras_rotas_criticas_support import _login_app_inspetor


def test_resolver_modo_entrada_prioriza_regra_de_familia_sobre_preferencia_usuario() -> None:
    decisao = resolver_modo_entrada_caso(
        requested_preference="chat_first",
        family_required_mode="evidence_first",
    )

    assert decisao.preference == "chat_first"
    assert decisao.effective == "evidence_first"
    assert decisao.reason == "family_required_mode"


def test_iniciar_relatorio_persiste_contrato_de_modo_entrada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.post(
        "/app/api/laudo/iniciar",
        data={
            "tipo_template": "padrao",
            "entry_mode_preference": "evidence_first",
        },
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    laudo_id = int(corpo["laudo_id"])
    assert corpo["entry_mode_preference"] == "evidence_first"
    assert corpo["entry_mode_effective"] == "evidence_first"
    assert corpo["entry_mode_reason"] == "user_preference"
    assert corpo["laudo_card"]["entry_mode_preference"] == "evidence_first"
    assert corpo["laudo_card"]["entry_mode_effective"] == "evidence_first"
    assert corpo["laudo_card"]["entry_mode_reason"] == "user_preference"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.entry_mode_preference == "evidence_first"
        assert laudo.entry_mode_effective == "evidence_first"
        assert laudo.entry_mode_reason == "user_preference"


def test_status_relatorio_expoe_contrato_de_modo_entrada_do_laudo_ativo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    iniciar = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )
    assert iniciar.status_code == 200
    laudo_id = int(iniciar.json()["laudo_id"])

    mensagem_mesa = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={"texto": "Mesa, validar item antes do envio final."},
    )
    assert mensagem_mesa.status_code == 201

    status_relatorio = client.get("/app/api/laudo/status")
    assert status_relatorio.status_code == 200
    corpo_status = status_relatorio.json()

    assert corpo_status["entry_mode_preference"] == "auto_recommended"
    assert corpo_status["entry_mode_effective"] == "chat_first"
    assert corpo_status["entry_mode_reason"] == "default_product_fallback"
    assert corpo_status["laudo_card"]["entry_mode_preference"] == "auto_recommended"
    assert corpo_status["laudo_card"]["entry_mode_effective"] == "chat_first"
    assert corpo_status["laudo_card"]["entry_mode_reason"] == "default_product_fallback"
