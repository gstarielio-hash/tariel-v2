from __future__ import annotations

import uuid

import app.domains.chat.routes as rotas_inspetor
from app.shared.database import Laudo, StatusRevisao, Usuario
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


def test_mobile_settings_persistem_preferencia_de_modo_de_entrada(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    resposta_padrao = client.get("/app/api/mobile/account/settings", headers=headers)
    assert resposta_padrao.status_code == 200
    assert (
        resposta_padrao.json()["settings"]["experiencia_ia"]["entry_mode_preference"]
        == "auto_recommended"
    )
    assert (
        resposta_padrao.json()["settings"]["experiencia_ia"]["remember_last_case_mode"]
        is False
    )

    resposta_salva = client.put(
        "/app/api/mobile/account/settings",
        headers=headers,
        json={
            "experiencia_ia": {
                "modelo_ia": "avançado",
                "entry_mode_preference": "evidence_first",
                "remember_last_case_mode": True,
            }
        },
    )

    assert resposta_salva.status_code == 200
    assert resposta_salva.json()["settings"]["experiencia_ia"]["modelo_ia"] == "avançado"
    assert (
        resposta_salva.json()["settings"]["experiencia_ia"]["entry_mode_preference"]
        == "evidence_first"
    )
    assert (
        resposta_salva.json()["settings"]["experiencia_ia"]["remember_last_case_mode"]
        is True
    )

    resposta_lida = client.get("/app/api/mobile/account/settings", headers=headers)
    assert resposta_lida.status_code == 200
    assert (
        resposta_lida.json()["settings"]["experiencia_ia"]["entry_mode_preference"]
        == "evidence_first"
    )
    assert (
        resposta_lida.json()["settings"]["experiencia_ia"]["remember_last_case_mode"]
        is True
    )


def test_iniciar_relatorio_herda_preferencia_persistida_do_usuario(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
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

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    laudo_id = int(corpo["laudo_id"])
    assert corpo["entry_mode_preference"] == "evidence_first"
    assert corpo["entry_mode_effective"] == "evidence_first"
    assert corpo["entry_mode_reason"] == "user_preference"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.entry_mode_preference == "evidence_first"
        assert laudo.entry_mode_effective == "evidence_first"
        assert laudo.entry_mode_reason == "user_preference"


def test_iniciar_relatorio_recupera_ultimo_modo_quando_usuario_configura_lembrar(
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

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta = client.post(
        "/app/api/laudo/iniciar",
        data={"tipo_template": "padrao"},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["entry_mode_preference"] == "auto_recommended"
    assert corpo["entry_mode_effective"] == "evidence_first"
    assert corpo["entry_mode_reason"] == "last_case_mode"


def test_chat_cria_laudo_com_preferencia_persistida_do_usuario(ambiente_critico) -> None:
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

    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    class ClienteIAStub:
        def stream_response(self, *_args, **_kwargs):
            yield "Resposta técnica inicial.\n"

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Abrindo coleta com preferência persistida.",
                "historico": [],
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat.status_code == 200
    status = client.get("/app/api/laudo/status")
    assert status.status_code == 200
    corpo_status = status.json()
    assert corpo_status["entry_mode_preference"] == "evidence_first"
    assert corpo_status["entry_mode_effective"] == "evidence_first"
    assert corpo_status["entry_mode_reason"] == "user_preference"
    assert corpo_status["laudo_card"]["entry_mode_preference"] == "evidence_first"
    assert corpo_status["laudo_card"]["entry_mode_effective"] == "evidence_first"
    assert corpo_status["laudo_card"]["entry_mode_reason"] == "user_preference"
