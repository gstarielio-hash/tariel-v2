from __future__ import annotations

import pytest

from sqlalchemy import event

import app.domains.revisor.panel as review_panel_module
from app.shared.database import Laudo, MensagemLaudo, NivelAcesso, StatusRevisao, TipoMensagem, Usuario
from tests.regras_rotas_criticas_support import SENHA_HASH_PADRAO, _criar_laudo, _login_revisor


def _normalizar_sql(statement: object) -> str:
    return " ".join(str(statement or "").split())


def test_revisor_painel_boot_precarrega_relacoes_sem_lazy_load_por_item(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        inspetores_ids = [ids["inspetor_a"]]
        for indice in range(1, 5):
            inspetor = Usuario(
                empresa_id=ids["empresa_a"],
                nome_completo=f"Inspetor painel {indice}",
                email=f"inspetor-painel-{indice}@empresa-a.test",
                senha_hash=SENHA_HASH_PADRAO,
                nivel_acesso=NivelAcesso.INSPETOR.value,
            )
            banco.add(inspetor)
            banco.flush()
            inspetores_ids.append(inspetor.id)

        for indice, inspetor_id in enumerate(inspetores_ids, start=1):
            laudo_id = _criar_laudo(
                banco,
                empresa_id=ids["empresa_a"],
                usuario_id=inspetor_id,
                status_revisao=StatusRevisao.RASCUNHO.value,
            )
            laudo = banco.get(Laudo, laudo_id)
            assert laudo is not None
            laudo.primeira_mensagem = f"Painel boot #{indice}"
            banco.add(
                MensagemLaudo(
                    laudo_id=laudo_id,
                    remetente_id=inspetor_id,
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo=f"Whisper painel #{indice}",
                    lida=False,
                )
            )

        banco.commit()

    engine = SessionLocal.kw["bind"]
    assert engine is not None
    statements: list[str] = []

    def _capturar_sql(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(_normalizar_sql(statement))

    event.listen(engine, "before_cursor_execute", _capturar_sql)
    try:
        painel = client.get("/revisao/painel")
    finally:
        event.remove(engine, "before_cursor_execute", _capturar_sql)

    assert painel.status_code == 200
    assert "Whisper painel #1" in painel.text

    lazy_loads_usuario = [
        statement
        for statement in statements
        if "FROM usuarios" in statement and "WHERE usuarios.id = ?" in statement
    ]
    lazy_loads_laudo = [
        statement
        for statement in statements
        if "FROM laudos" in statement and "WHERE laudos.id = ?" in statement
    ]

    assert len(lazy_loads_usuario) <= 1
    assert not lazy_loads_laudo


def test_revisor_painel_renderiza_ssr_por_padrao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.get(
        "/revisao/painel?q=corrosao&operacao=responder_agora&aprendizados=pendentes",
        follow_redirects=False,
    )

    assert resposta.status_code == 200
    assert "painel_revisor" in resposta.text


@pytest.mark.parametrize(
    "legacy_query",
    [
        "operacao=fechamento_mesa",
        "operacao=validar_aprendizado",
        "operacao=aguardando_inspetor",
        "operacao=acompanhamento",
        "aprendizados=pendentes",
    ],
)
def test_revisor_painel_mantem_render_ssr_com_filtros_operacionais_legados(
    ambiente_critico,
    legacy_query,
) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.get(f"/revisao/painel?{legacy_query}", follow_redirects=False)

    assert resposta.status_code == 200
    assert "painel_revisor" in resposta.text


def test_revisor_painel_ignora_flags_legadas_de_rollout_e_mantem_shadow_ssr(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")
    monkeypatch.setenv("REVIEW_UI_CANONICAL", "ssr")
    monkeypatch.setenv("TARIEL_REVIEW_DESK_PRIMARY_SURFACE", "legacy")

    shadow_calls: list[object] = []

    def _registrar_shadow(*_args, **_kwargs) -> None:
        shadow_calls.append(object())

    monkeypatch.setattr(review_panel_module, "registrar_shadow_review_queue_dashboard", _registrar_shadow)

    resposta = client.get("/revisao/painel", follow_redirects=False)

    assert resposta.status_code == 200
    assert "painel_revisor" in resposta.text
    assert len(shadow_calls) == 1


def test_revisor_painel_surface_ssr_mantem_render_ssr_e_shadow(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")

    shadow_calls: list[object] = []

    def _registrar_shadow(*_args, **_kwargs) -> None:
        shadow_calls.append(object())

    monkeypatch.setattr(review_panel_module, "registrar_shadow_review_queue_dashboard", _registrar_shadow)

    resposta = client.get("/revisao/painel?surface=ssr")

    assert resposta.status_code == 200
    assert "painel_revisor" in resposta.text
    assert len(shadow_calls) == 1


def test_revisor_painel_ignora_configuracao_invalida_sem_quebrar_fluxo_ssr(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")
    monkeypatch.setenv("REVIEW_UI_CANONICAL", "invalido")
    monkeypatch.setenv("TARIEL_REVIEW_DESK_PRIMARY_SURFACE", "invalido")

    resposta = client.get("/revisao/painel", follow_redirects=False)

    assert resposta.status_code == 200
    assert "painel_revisor" in resposta.text


def test_revisor_painel_aceita_superficie_legacy_como_alias_de_ssr(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    _login_revisor(client, "revisor@empresa-a.test")
    monkeypatch.setenv("TARIEL_REVIEW_DESK_PRIMARY_SURFACE", "legacy")

    resposta = client.get("/revisao/painel", follow_redirects=False)

    assert resposta.status_code == 200
    assert "painel_revisor" in resposta.text
