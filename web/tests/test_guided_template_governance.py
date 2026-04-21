from __future__ import annotations

import json

import app.domains.admin.services as admin_services

from app.shared.database import Laudo, StatusRevisao
from app.shared.tenant_report_catalog import build_catalog_selection_token
from tests.regras_rotas_criticas_support import SENHA_PADRAO, _criar_laudo, _login_app_inspetor


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


def _guided_draft_payload(template_key: str, template_label: str) -> dict[str, object]:
    return {
        "guided_inspection_draft": {
            "template_key": template_key,
            "template_label": template_label,
            "started_at": "2026-04-15T14:00:00.000Z",
            "current_step_index": 0,
            "completed_step_ids": [],
            "checklist": [
                {
                    "id": "identificacao",
                    "title": "Identificacao do ativo",
                    "prompt": "registre a identificacao do ativo",
                    "evidence_hint": "tag e local",
                }
            ],
        }
    }


def _release_variant_for_tenant(
    *,
    banco,
    family_key: str,
    family_label: str,
    macro_categoria: str,
    variant_key: str,
    variant_label: str,
    template_code: str,
    tenant_id: int,
    admin_id: int,
) -> str:
    admin_services.upsert_familia_catalogo(
        banco,
        family_key=family_key,
        nome_exibicao=family_label,
        macro_categoria=macro_categoria,
        status_catalogo="publicado",
        criado_por_id=admin_id,
    )
    admin_services.upsert_oferta_comercial_familia(
        banco,
        family_key=family_key,
        nome_oferta=f"{family_label} · Oferta principal",
        pacote_comercial="Prime",
        ativo_comercial=True,
        variantes_comerciais_text=json.dumps(
            [
                {
                    "variant_key": variant_key,
                    "nome_exibicao": variant_label,
                    "template_code": template_code,
                }
            ]
        ),
        criado_por_id=admin_id,
    )
    selection_token = build_catalog_selection_token(family_key, variant_key)
    admin_services.upsert_tenant_family_release(
        banco,
        tenant_id=tenant_id,
        family_key=family_key,
        release_status="active",
        allowed_variants=[selection_token],
        criado_por_id=admin_id,
    )
    return selection_token


def test_mobile_guided_draft_rejeita_template_fora_do_recorte_governado(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        token_nr35 = _release_variant_for_tenant(
            banco=banco,
            family_key="nr35_inspecao_linha_de_vida",
            family_label="NR35 · Linha de Vida",
            macro_categoria="NR35",
            variant_key="prime_site",
            variant_label="Prime Site",
            template_code="nr35_linha_vida",
            tenant_id=ids["empresa_a"],
            admin_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[token_nr35],
            admin_id=ids["admin_a"],
        )
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="padrao",
        )

    resposta = client.put(
        f"/app/api/mobile/laudo/{laudo_id}/guided-inspection-draft",
        headers=headers,
        json=_guided_draft_payload("nr11_movimentacao", "NR11 Movimentacao"),
    )

    assert resposta.status_code == 403
    assert "habilitado para o tenant" in resposta.json()["detail"].lower()

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.guided_inspection_draft_json is None
        assert laudo.tipo_template == "padrao"


def test_chat_guiado_rejeita_template_fora_do_recorte_governado(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        token_nr35 = _release_variant_for_tenant(
            banco=banco,
            family_key="nr35_inspecao_linha_de_vida",
            family_label="NR35 · Linha de Vida",
            macro_categoria="NR35",
            variant_key="prime_site",
            variant_label="Prime Site",
            template_code="nr35_linha_vida",
            tenant_id=ids["empresa_a"],
            admin_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[token_nr35],
            admin_id=ids["admin_a"],
        )
        banco.commit()

    resposta = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "Iniciar coleta guiada fora do recorte.",
            "historico": [],
            "entry_mode_preference": "evidence_first",
            "guided_inspection_draft": _guided_draft_payload(
                "nr11_movimentacao",
                "NR11 Movimentacao",
            )["guided_inspection_draft"],
        },
    )

    assert resposta.status_code == 403
    assert "habilitado para o tenant" in resposta.json()["detail"].lower()


def test_mobile_guided_draft_nao_troca_binding_de_caso_governado(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        token_nr35 = _release_variant_for_tenant(
            banco=banco,
            family_key="nr35_inspecao_linha_de_vida",
            family_label="NR35 · Linha de Vida",
            macro_categoria="NR35",
            variant_key="prime_site",
            variant_label="Prime Site",
            template_code="nr35_linha_vida",
            tenant_id=ids["empresa_a"],
            admin_id=ids["admin_a"],
        )
        token_nr13 = build_catalog_selection_token(
            "nr13_inspecao_caldeira",
            "premium_campo",
        )
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
            nome_oferta="NR13 · Caldeira · Oferta principal",
            pacote_comercial="Prime",
            ativo_comercial=True,
            variantes_comerciais_text=json.dumps(
                [
                    {
                        "variant_key": "premium_campo",
                        "nome_exibicao": "Premium Campo",
                        "template_code": "nr13",
                    }
                ]
            ),
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            allowed_variants=[token_nr13],
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[token_nr35, token_nr13],
            admin_id=ids["admin_a"],
        )
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr35_linha_vida",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_selection_token = token_nr35
        laudo.catalog_family_key = "nr35_inspecao_linha_de_vida"
        laudo.catalog_family_label = "NR35 · Linha de Vida"
        laudo.catalog_variant_key = "prime_site"
        laudo.catalog_variant_label = "Prime Site"
        banco.commit()

    resposta = client.put(
        f"/app/api/mobile/laudo/{laudo_id}/guided-inspection-draft",
        headers=headers,
        json=_guided_draft_payload("nr13", "NR13 Caldeira"),
    )

    assert resposta.status_code == 409
    assert "nao pode trocar de binding" in resposta.json()["detail"].lower()

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.tipo_template == "nr35_linha_vida"
        assert laudo.catalog_selection_token == token_nr35
        assert laudo.guided_inspection_draft_json is None
