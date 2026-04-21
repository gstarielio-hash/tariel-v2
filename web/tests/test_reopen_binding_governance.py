from __future__ import annotations

from datetime import datetime, timezone

from app.shared.database import Laudo, StatusRevisao
from app.shared.tenant_report_catalog import build_catalog_selection_token
from tests.regras_rotas_criticas_support import (
    SENHA_PADRAO,
    _criar_laudo,
    _login_app_inspetor,
    _login_revisor,
)


def _login_mobile_inspetor(client) -> dict[str, str]:
    resposta = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta.status_code == 200
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_governed_binding_drift(laudo: Laudo) -> str:
    selection_token = build_catalog_selection_token(
        "nr13_inspecao_caldeira",
        "premium_campo",
    )
    laudo.tipo_template = "padrao"
    laudo.catalog_selection_token = selection_token
    laudo.catalog_family_key = "padrao"
    laudo.catalog_family_label = "Template padrao"
    laudo.catalog_variant_key = "legacy_errado"
    laudo.catalog_variant_label = "Legacy errado"
    laudo.catalog_snapshot_json = {
        "selection_token": selection_token,
        "runtime_template_code": "nr13",
        "family": {
            "key": "nr13_inspecao_caldeira",
            "label": "NR13 · Caldeira",
        },
        "variant": {
            "key": "premium_campo",
            "label": "Premium campo",
        },
    }
    laudo.pdf_template_snapshot_json = {
        "template_ref": {
            "source_kind": "snapshot",
            "family_key": "nr13_inspecao_caldeira",
            "codigo_template": "nr13",
            "versao": 1,
            "modo_editor": "rico",
            "arquivo_pdf_base": "/tmp/nr13.pdf",
            "documento_editor_json": {},
            "estilo_json": {},
            "assets_json": [],
        }
    }
    return selection_token


def test_mobile_review_command_reafirma_binding_governado_ao_devolver(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client)

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
        selection_token = _seed_governed_binding_drift(laudo)
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={
            "command": "devolver_no_mobile",
            "block_key": "identificacao",
            "reason": "Foto sem foco suficiente para aprovar.",
        },
    )

    assert resposta.status_code == 200
    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.tipo_template == "nr13"
        assert laudo.catalog_selection_token == selection_token
        assert laudo.catalog_family_key == "nr13_inspecao_caldeira"
        assert laudo.catalog_family_label == "NR13 · Caldeira"
        assert laudo.catalog_variant_key == "premium_campo"
        assert laudo.catalog_variant_label == "Premium campo"


def test_mesa_rejeicao_reafirma_binding_governado_antes_devolver_para_ajuste(
    ambiente_critico,
) -> None:
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
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        selection_token = _seed_governed_binding_drift(laudo)
        banco.commit()

    resposta = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        data={
            "acao": "rejeitar",
            "motivo": "Corrigir evidencias antes de aprovar.",
            "csrf_token": csrf,
        },
    )

    assert resposta.status_code == 200
    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.REJEITADO.value
        assert laudo.tipo_template == "nr13"
        assert laudo.catalog_selection_token == selection_token
        assert laudo.catalog_family_key == "nr13_inspecao_caldeira"
        assert laudo.catalog_variant_key == "premium_campo"
        assert laudo.reabertura_pendente_em is not None


def test_reabrir_laudo_preserva_binding_governado_congelado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.REJEITADO.value,
            tipo_template="padrao",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        selection_token = _seed_governed_binding_drift(laudo)
        laudo.reabertura_pendente_em = datetime.now(timezone.utc)
        laudo.motivo_rejeicao = "Mesa devolveu para correcoes."
        banco.commit()

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/reabrir",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.RASCUNHO.value
        assert laudo.tipo_template == "nr13"
        assert laudo.catalog_selection_token == selection_token
        assert laudo.catalog_family_key == "nr13_inspecao_caldeira"
        assert laudo.catalog_variant_key == "premium_campo"
        assert laudo.reabertura_pendente_em is None
