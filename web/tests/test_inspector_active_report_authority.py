from __future__ import annotations

import json
import re

from app.shared.database import StatusRevisao
from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _login_app_inspetor,
)


def _extrair_boot_app(html: str) -> dict[str, object]:
    match = re.search(
        r'<script[^>]+id="tariel-boot"[^>]*>\s*(\{.*?\})\s*</script>',
        html,
        flags=re.DOTALL,
    )
    assert match, "Bootstrap SSR do inspetor não encontrado."
    return json.loads(match.group(1))


def test_query_param_laudo_promove_contexto_autoritativo_no_boot_e_na_sessao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_inicial = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_destino = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta_seed = client.get(f"/app/api/laudo/{laudo_inicial}/mensagens")
    assert resposta_seed.status_code == 200
    assert resposta_seed.json()["attachment_policy"]["policy_name"] == "android_attachment_sync_policy"
    assert "imagem" in resposta_seed.json()["attachment_policy"]["supported_categories"]

    resposta = client.get(f"/app/?laudo={laudo_destino}")
    assert resposta.status_code == 200

    boot = _extrair_boot_app(resposta.text)
    assert boot["laudoAtivoId"] == laudo_destino
    assert boot["estadoRelatorio"] == "aguardando"

    status = client.get("/app/api/laudo/status")
    assert status.status_code == 200
    assert status.json()["laudo_id"] == laudo_destino


def test_home_forcado_preserva_laudo_ativo_na_sessao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_ativo = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta_seed = client.get(f"/app/api/laudo/{laudo_ativo}/mensagens")
    assert resposta_seed.status_code == 200

    resposta = client.get("/app/?home=1")
    assert resposta.status_code == 200
    assert re.search(r'id="tela-boas-vindas"[^>]*data-active="true"', resposta.text)

    boot = _extrair_boot_app(resposta.text)
    assert boot["laudoAtivoId"] == laudo_ativo
    assert boot["estadoRelatorio"] == "aguardando"

    status = client.get("/app/api/laudo/status")
    assert status.status_code == 200
    assert status.json()["laudo_id"] == laudo_ativo


def test_raiz_app_sem_query_abre_home_e_limpa_contexto_ativo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_ativo = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta_seed = client.get(f"/app/api/laudo/{laudo_ativo}/mensagens")
    assert resposta_seed.status_code == 200

    resposta = client.get("/app/")
    assert resposta.status_code == 200
    assert re.search(r'id="tela-boas-vindas"[^>]*data-active="true"', resposta.text)

    boot = _extrair_boot_app(resposta.text)
    assert boot["laudoAtivoId"] is None
    assert boot["estadoRelatorio"] == "sem_relatorio"

    status = client.get("/app/api/laudo/status")
    assert status.status_code == 200
    assert status.json()["laudo_id"] is None
    assert status.json()["estado"] == "sem_relatorio"


def test_query_param_invalido_nao_sequestra_contexto_ativo_existente(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_ativo = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta_seed = client.get(f"/app/api/laudo/{laudo_ativo}/mensagens")
    assert resposta_seed.status_code == 200

    resposta = client.get("/app/?laudo=999999")
    assert resposta.status_code == 200

    boot = _extrair_boot_app(resposta.text)
    assert boot["laudoAtivoId"] == laudo_ativo
    assert boot["estadoRelatorio"] == "aguardando"

    status = client.get("/app/api/laudo/status")
    assert status.status_code == 200
    assert status.json()["laudo_id"] == laudo_ativo
