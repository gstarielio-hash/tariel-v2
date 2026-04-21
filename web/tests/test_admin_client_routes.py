from __future__ import annotations

import json
from pathlib import Path

import app.domains.admin.client_routes as admin_client_routes
import app.domains.admin.routes as rotas_admin
import app.domains.admin.portal_support as admin_portal_support
import app.domains.admin.services as admin_services
from app.domains.revisor import panel_rollout
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.admin.mfa import current_totp
from app.shared.database import (
    AtivacaoCatalogoEmpresaLaudo,
    ConfiguracaoPlataforma,
    Empresa,
    Laudo,
    NivelAcesso,
    RegistroAuditoriaEmpresa,
    SessaoAtiva,
    Usuario,
)
from tests.regras_rotas_criticas_support import ADMIN_TOTP_SECRET, _csrf_pagina, _login_admin


def _totp_grouped(secret: str) -> str:
    secret_norm = str(secret or "").strip().upper()
    return " ".join(secret_norm[i : i + 4] for i in range(0, len(secret_norm), 4))


def _bootstrap_catalog_repo_assets(
    root: Path,
    family_key: str,
    *,
    material_status: str = "baseline_sintetica_externa_validada",
) -> None:
    docs_dir = root / "docs"
    family_schemas_dir = docs_dir / "family_schemas"
    master_templates_dir = docs_dir / "master_templates"
    workspace_dir = docs_dir / "portfolio_empresa_nr13_material_real" / family_key
    pacote_dir = workspace_dir / "pacote_referencia"
    coleta_dir = workspace_dir / "coleta_entrada"

    family_schemas_dir.mkdir(parents=True, exist_ok=True)
    master_templates_dir.mkdir(parents=True, exist_ok=True)
    pacote_dir.mkdir(parents=True, exist_ok=True)
    coleta_dir.mkdir(parents=True, exist_ok=True)

    (master_templates_dir / "library_registry.json").write_text(
        json.dumps(
            {
                "version": 5,
                "templates": [
                    {
                        "master_template_id": "inspection_conformity",
                        "label": "Inspection Conformity Premium",
                        "status": "ready",
                        "artifact_path": "docs/master_templates/inspection_conformity.template_master.json",
                        "usage": "Template premium da biblioteca.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (master_templates_dir / "inspection_conformity.template_master.json").write_text(
        json.dumps({"template": "premium"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (family_schemas_dir / f"{family_key}.json").write_text(
        json.dumps(
            {
                "family_key": family_key,
                "nome_exibicao": "NR13 · Vaso de Pressão",
                "macro_categoria": "NR13",
                "schema_version": 2,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    for suffix in (
        ".template_master_seed.json",
        ".laudo_output_seed.json",
        ".laudo_output_exemplo.json",
    ):
        (family_schemas_dir / f"{family_key}{suffix}").write_text(
            json.dumps({"family_key": family_key}, ensure_ascii=False),
            encoding="utf-8",
        )
    (workspace_dir / "briefing_real.md").write_text("# Briefing\n", encoding="utf-8")
    (workspace_dir / "status_refino.json").write_text(
        json.dumps(
            {
                "status_refino": material_status,
                "material_recebido": ["pdf", "zip"],
                "lacunas_abertas": ["foto de placa"],
                "artefatos_externos_validados": [{"kind": "zip"}],
                "proximo_passo": "Promover pacote de referência.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (workspace_dir / "manifesto_coleta.json").write_text(
        json.dumps({"family_key": family_key}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pacote_dir / "manifest.json").write_text(
        json.dumps({"family_key": family_key}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pacote_dir / "tariel_filled_reference_bundle.json").write_text(
        json.dumps({"family_key": family_key}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_admin_cadastrar_empresa_exibe_aviso_operacional_quando_boas_vindas_nao_sao_entregues(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/painel")

    class _EmpresaStub:
        id = 777
        nome_fantasia = "Cliente Operacional"

    def _registrar_stub(_db: Session, **_kwargs) -> tuple[_EmpresaStub, str, str]:
        return _EmpresaStub(), "Senha@Temp123", "Entrega automática de boas-vindas não configurada."

    monkeypatch.setattr(rotas_admin, "registrar_novo_cliente", _registrar_stub)

    resposta = client.post(
        "/admin/cadastrar-empresa",
        data={
            "csrf_token": csrf,
            "nome": "Cliente Operacional",
            "cnpj": "88999888000199",
            "email": "cliente-operacional@test.local",
            "plano": "Ilimitado",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/admin/clientes/777/acesso-inicial")
    pagina = client.get(resposta.headers["location"])
    assert pagina.status_code == 200
    assert "Cliente Cliente Operacional cadastrado com sucesso." in pagina.text
    assert "Entrega automática de boas-vindas não configurada." in pagina.text
    assert "/cliente/login" in pagina.text
    assert "cliente-operacional@test.local" in pagina.text
    assert "Senha@Temp123" in pagina.text


def test_admin_cadastrar_empresa_exibe_pacote_inicial_com_operacao_provisionada(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/novo-cliente")

    resposta = client.post(
        "/admin/novo-cliente",
        data={
            "csrf_token": csrf,
            "nome": "Tenant Provisionado Demo",
            "cnpj": "88999888000155",
            "email": "admin.demo@tenant-provisionado.test",
            "plano": "Ilimitado",
            "provisionar_inspetor_inicial": "true",
            "inspetor_nome": "Inspetor Demo",
            "inspetor_email": "inspetor.demo@tenant-provisionado.test",
            "provisionar_revisor_inicial": "true",
            "revisor_nome": "Mesa Demo",
            "revisor_email": "mesa.demo@tenant-provisionado.test",
            "revisor_crea": "123456/GO",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/admin/clientes/")
    assert "/acesso-inicial?sucesso=" in resposta.headers["location"]

    pagina = client.get(resposta.headers["location"])
    assert pagina.status_code == 200
    assert "Equipe inicial provisionada quando solicitada." in pagina.text
    assert "admin.demo@tenant-provisionado.test" in pagina.text
    assert "inspetor.demo@tenant-provisionado.test" in pagina.text
    assert "mesa.demo@tenant-provisionado.test" in pagina.text
    assert "/cliente/login" in pagina.text
    assert "/app/login" in pagina.text
    assert "/revisao/login" in pagina.text
    assert "Area de analise" in pagina.text


def test_admin_clientes_renderiza_console_operacional_na_lista_e_no_detalhe(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")

    resposta_lista = client.get("/admin/clientes?ordenar=ultimo_acesso&por_pagina=10")
    assert resposta_lista.status_code == 200
    assert "Código, ID ou CNPJ" in resposta_lista.text
    assert "Toda saúde" in resposta_lista.text
    assert "Empresas no recorte" in resposta_lista.text
    assert "Exportar diagnóstico" in resposta_lista.text
    assert "Forçar reset" in resposta_lista.text
    assert 'id="modal-bloqueio-empresa-lista"' in resposta_lista.text
    assert "window.prompt" not in resposta_lista.text

    resposta_detalhe = client.get(f"/admin/clientes/{ids['empresa_a']}")
    assert resposta_detalhe.status_code == 200
    assert "Resumo administrativo" in resposta_detalhe.text
    assert "Segurança" in resposta_detalhe.text
    assert "Ações críticas" in resposta_detalhe.text
    assert "Suporte excepcional" in resposta_detalhe.text
    assert "Responsaveis pela assinatura" in resposta_detalhe.text
    assert "Administradores da empresa (" in resposta_detalhe.text
    assert 'id="modal-bloqueio-empresa"' in resposta_detalhe.text
    assert "window.prompt" not in resposta_detalhe.text


def test_admin_detalhe_cliente_mostra_erro_generico_quando_empresa_existe_mas_leitura_falha(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")

    def _falhar_detalhe(*_args, **_kwargs):
        raise RuntimeError("falha simulada no detalhe")

    monkeypatch.setattr(admin_client_routes, "buscar_detalhe_cliente", _falhar_detalhe)

    resposta = client.get(f"/admin/clientes/{ids['empresa_a']}", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/admin/clientes?erro=")

    pagina = client.get(resposta.headers["location"])
    assert pagina.status_code == 200
    assert "Não foi possível carregar os detalhes da empresa." in pagina.text


def test_admin_ceo_atualiza_politica_operacional_do_admin_cliente(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/politica-admin-cliente",
        data={
            "csrf_token": csrf,
            "admin_cliente_case_visibility_mode": "summary_only",
            "admin_cliente_case_action_mode": "case_actions",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    pagina = client.get(resposta.headers["location"])
    assert pagina.status_code == 200
    assert "Configuracao de acesso da empresa atualizada." in pagina.text
    assert "Somente resumos agregados" in pagina.text
    assert "Somente acompanhamento" in pagina.text

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        assert empresa.admin_cliente_policy_json == {
            "case_visibility_mode": "summary_only",
            "case_action_mode": "read_only",
        }
        auditoria = (
            banco.query(RegistroAuditoriaEmpresa)
            .filter(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "tenant_admin_client_policy_updated",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
            .first()
        )
        assert auditoria is not None


def test_admin_ceo_pode_definir_modelo_mobile_single_operator_no_tenant(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/politica-admin-cliente",
        data={
            "csrf_token": csrf,
            "admin_cliente_operating_model": "mobile_single_operator",
            "admin_cliente_mobile_web_inspector_enabled": "true",
            "admin_cliente_mobile_web_review_enabled": "false",
            "admin_cliente_case_visibility_mode": "case_list",
            "admin_cliente_case_action_mode": "case_actions",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    pagina = client.get(resposta.headers["location"])
    assert pagina.status_code == 200
    assert "Aplicativo principal com uma pessoa responsavel" in pagina.text

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        assert empresa.admin_cliente_policy_json == {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": False,
        }


def test_admin_cliente_salva_signatario_governado_no_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Caldeira",
            lifecycle_status="active",
            variantes_comerciais_text="padrao | Padrão | nr13_core | Operação base",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            allowed_variants=["catalog:nr13_inspecao_caldeira:padrao"],
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/signatarios-governados",
        data={
            "csrf_token": csrf,
            "nome": "Eng. Tariel",
            "funcao": "Responsável técnico",
            "registro_profissional": "CREA 1234",
            "valid_until": "2026-12-31",
            "allowed_family_keys": ["nr13_inspecao_caldeira"],
            "ativo": "on",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    pagina = client.get(resposta.headers["location"])
    assert pagina.status_code == 200
    assert "Responsavel pela assinatura salvo para a empresa." in pagina.text
    assert "Eng. Tariel" in pagina.text


def test_admin_paginas_de_governanca_renderizam_disclosures(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")

    resposta_auditoria = client.get("/admin/auditoria")
    assert resposta_auditoria.status_code == 200
    assert "Eventos carregados" in resposta_auditoria.text
    assert "Detalhes do registro" in resposta_auditoria.text

    resposta_config = client.get("/admin/configuracoes")
    assert resposta_config.status_code == 200
    assert "Acesso e seguranca da plataforma" in resposta_config.text
    assert "Política de suporte excepcional" in resposta_config.text
    assert "Liberacao da revisao" in resposta_config.text
    assert "Historico e armazenamento" in resposta_config.text
    assert "Motivo da alteracao" in resposta_config.text
    assert "Apenas consulta" in resposta_config.text
    assert "Resumo apenas para consulta." in resposta_config.text
    assert 'role="tablist"' in resposta_config.text
    assert 'data-config-tab="access"' in resposta_config.text
    assert 'data-config-tab="support"' in resposta_config.text
    assert "/static/js/admin/admin_settings_page.js" in resposta_config.text


def test_admin_catalogo_laudos_renderiza_home_e_detalhe_com_camadas_separadas(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")

    resposta_catalogo = client.get("/admin/catalogo-laudos")
    assert resposta_catalogo.status_code == 200
    assert "Catálogo de modelos" in resposta_catalogo.text
    assert "Modelos governados" in resposta_catalogo.text
    assert "Importar base completa" in resposta_catalogo.text
    assert 'data-catalog-open-drawer="family-create"' in resposta_catalogo.text
    assert 'data-catalog-drawer="family-create"' in resposta_catalogo.text

    csrf = _csrf_pagina(client, "/admin/catalogo-laudos")
    resposta_familia = client.post(
        "/admin/catalogo-laudos/familias",
        data={
            "csrf_token": csrf,
            "family_key": "nr13_inspecao_vaso_pressao",
            "nome_exibicao": "NR13 · Vaso de Pressão",
            "macro_categoria": "NR13",
            "nr_key": "nr13",
            "descricao": "Família crítica de integridade mecânica.",
            "status_catalogo": "publicado",
            "technical_status": "ready",
            "schema_version": "2",
            "evidence_policy_json": '{"required":["placa"]}',
        },
        follow_redirects=False,
    )
    assert resposta_familia.status_code == 303

    csrf = _csrf_pagina(client, "/admin/catalogo-laudos")
    resposta_oferta = client.post(
        "/admin/catalogo-laudos/ofertas-comerciais",
        data={
            "csrf_token": csrf,
            "family_key": "nr13_inspecao_vaso_pressao",
            "offer_key": "nr13_inspecao_vaso_pressao_main",
            "nome_oferta": "NR13 Premium · Vaso de Pressão",
            "descricao_comercial": "Leitura premium com mesa e emissão final.",
            "pacote_comercial": "Premium",
            "release_channel": "limited_release",
            "bundle_key": "nr13_core",
            "bundle_label": "NR13 Core",
            "bundle_summary": "Pacote principal de integridade mecânica.",
            "bundle_audience": "Indústria",
            "bundle_highlights": json.dumps(["Inspeção em campo", "Emissão oficial"], ensure_ascii=False),
            "included_features": json.dumps(["mobile_review", "public_verification"], ensure_ascii=False),
            "entitlement_monthly_issues": "80",
            "prazo_padrao_dias": "4",
            "lifecycle_status": "active",
            "showcase_enabled": "on",
            "versao_oferta": "1",
            "material_real_status": "calibrado",
            "material_level": "real_calibrated",
            "escopo_comercial": "- Inspeção em campo\n- Emissão final",
            "variantes_comerciais": "premium_campo | Premium campo | nr13_premium | Operação crítica",
        },
        follow_redirects=False,
    )
    assert resposta_oferta.status_code == 303

    pagina = client.get("/admin/catalogo-laudos")
    assert pagina.status_code == 200
    assert "NR13 · Vaso de Pressão" in pagina.text
    assert "NR13 Premium · Vaso de Pressão" in pagina.text
    assert "Modelo demonstrativo" in pagina.text
    assert "Modelo demonstrativo pronto" in pagina.text
    assert "Objetivo da NR13" in pagina.text
    assert "Casca profissional" in pagina.text
    assert "Ver documento" in pagina.text
    assert "Disponível para assinatura" in pagina.text
    assert "Starter" in pagina.text
    assert "Enterprise" in pagina.text
    assert 'id="catalog-preview-modal"' in pagina.text
    assert "/admin/catalogo-laudos/familias/nr13_inspecao_vaso_pressao/preview.pdf" in pagina.text

    detalhe = client.get("/admin/catalogo-laudos/familias/nr13_inspecao_vaso_pressao")
    assert detalhe.status_code == 200
    assert "Visão geral" in detalhe.text
    assert "Base" in detalhe.text
    assert "Modos" in detalhe.text
    assert "Pacote comercial" in detalhe.text
    assert "Validação" in detalhe.text
    assert "Acesso das empresas" in detalhe.text
    assert "Visão geral da família" in detalhe.text
    assert "Schema tecnico e governanca" not in detalhe.text
    assert "Código interno:" not in detalhe.text

    detalhe_ofertas = client.get("/admin/catalogo-laudos/familias/nr13_inspecao_vaso_pressao?tab=ofertas")
    assert detalhe_ofertas.status_code == 200
    assert 'data-catalog-active-tab="ofertas"' in detalhe_ofertas.text
    assert "Pacote comercial" in detalhe_ofertas.text
    assert "Editar pacote" in detalhe_ofertas.text
    assert "NR13 Core" in detalhe_ofertas.text
    assert "Liberacao controlada" in detalhe_ofertas.text
    assert "Emissões/mês" in detalhe_ofertas.text
    assert "Schema tecnico e governanca" not in detalhe_ofertas.text
    assert "catalog:" not in detalhe_ofertas.text


def test_admin_catalogo_renderiza_biblioteca_premium_e_material_real(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    SessionLocal = ambiente_critico["SessionLocal"]
    family_key = "nr13_inspecao_vaso_pressao"

    _bootstrap_catalog_repo_assets(tmp_path, family_key)
    monkeypatch.setattr(admin_services, "_repo_root_dir", lambda: tmp_path)

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key=family_key,
            nome_exibicao="NR13 · Vaso de Pressão",
            macro_categoria="NR13",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key=family_key,
            nome_oferta="NR13 Premium · Vaso de Pressão",
            lifecycle_status="active",
            material_real_status="calibrado",
            material_level="real_calibrated",
            template_default_code="nr13_premium",
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Operação crítica",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_calibracao_familia(
            banco,
            family_key=family_key,
            calibration_status="real_calibrated",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key=family_key,
            release_status="active",
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")

    pagina = client.get("/admin/catalogo-laudos")
    assert pagina.status_code == 200
    assert "Biblioteca oficial" in pagina.text
    assert "Modelos demonstrativos" in pagina.text
    assert "Material real" in pagina.text
    assert "Resolvido" in pagina.text
    assert "registro sincronizado" in pagina.text
    assert "Material real em andamento" in pagina.text

    detalhe = client.get(f"/admin/catalogo-laudos/familias/{family_key}")
    assert detalhe.status_code == 200
    assert "Base oficial de modelos" in detalhe.text
    assert "Validação com material real" in detalhe.text
    assert "Base completa" in detalhe.text
    assert "Pacote de referencia pronto" in detalhe.text
    assert "Promover pacote de referência." in detalhe.text

    detalhe_templates = client.get(f"/admin/catalogo-laudos/familias/{family_key}?tab=templates")
    assert detalhe_templates.status_code == 200
    assert "Modelo oficial de referência" in detalhe_templates.text
    assert "Visão do documento" in detalhe_templates.text
    assert "Informações obrigatórias" in detalhe_templates.text

    detalhe_ofertas = client.get(f"/admin/catalogo-laudos/familias/{family_key}?tab=ofertas")
    assert detalhe_ofertas.status_code == 200
    assert (
        "Opções disponiveis" in detalhe_ofertas.text
        or "Opções disponíveis" in detalhe_ofertas.text
        or "Opcoes disponiveis" in detalhe_ofertas.text
    )
    assert "Como o documento se apresenta" in detalhe_ofertas.text
    assert "Premium campo" in detalhe_ofertas.text
    assert "catalog:" not in detalhe_ofertas.text

    detalhe_calibracao = client.get(f"/admin/catalogo-laudos/familias/{family_key}?tab=calibracao")
    assert detalhe_calibracao.status_code == 200
    assert "Prioridade da validacao" in detalhe_calibracao.text or "Prioridade da validação" in detalhe_calibracao.text
    assert "Proximos passos" in detalhe_calibracao.text
    assert "Plano de trabalho" in detalhe_calibracao.text
    assert "Checklist" in detalhe_calibracao.text


def test_admin_catalogo_preview_pdf_retorna_documento_canonico(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    SessionLocal = ambiente_critico["SessionLocal"]
    family_key = "nr13_inspecao_vaso_pressao"

    _bootstrap_catalog_repo_assets(tmp_path, family_key)
    monkeypatch.setattr(admin_services, "_repo_root_dir", lambda: tmp_path)
    monkeypatch.setenv("TARIEL_CANONICAL_DOCS_DIR", str(tmp_path / "docs"))

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key=family_key,
            nome_exibicao="NR13 · Vaso de Pressão",
            macro_categoria="NR13",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key=family_key,
            nome_oferta="NR13 Premium · Vaso de Pressão",
            lifecycle_status="active",
            material_real_status="calibrado",
            material_level="real_calibrated",
            template_default_code="nr13_premium",
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Operação crítica",
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")

    resposta = client.get(f"/admin/catalogo-laudos/familias/{family_key}/preview.pdf")
    assert resposta.status_code == 200
    assert "application/pdf" in (resposta.headers.get("content-type") or "").lower()
    assert resposta.content.startswith(b"%PDF")
    assert len(resposta.content) > 300


def test_admin_dashboard_e_catalogo_exibem_fila_de_calibracao(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    SessionLocal = ambiente_critico["SessionLocal"]

    _bootstrap_catalog_repo_assets(tmp_path, "nr13_inspecao_caldeira")
    _bootstrap_catalog_repo_assets(
        tmp_path,
        "nr35_inspecao_linha_de_vida",
        material_status="aguardando_material_real",
    )
    monkeypatch.setattr(admin_services, "_repo_root_dir", lambda: tmp_path)

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Premium · Caldeira",
            lifecycle_status="active",
            material_real_status="parcial",
            material_level="partial",
            template_default_code="nr13_prime",
            variantes_comerciais_text="premium | Premium | nr13_prime | Campo premium",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_oferta="NR35 Prime · Linha de Vida",
            lifecycle_status="active",
            template_default_code="nr35_prime",
            variantes_comerciais_text="prime | Prime | nr35_prime | Altura premium",
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")

    pagina_catalogo = client.get("/admin/catalogo-laudos")
    assert pagina_catalogo.status_code == 200
    assert "Fila de validacao por familia" in pagina_catalogo.text
    assert "Modelos oficiais que pedem ajuste" in pagina_catalogo.text
    assert "Modelo oficial priorizado" in pagina_catalogo.text
    assert "pendencia(s)" in pagina_catalogo.text

    pagina_dashboard = client.get("/admin/painel")
    assert pagina_dashboard.status_code == 200
    assert "Fila de calibração por família" in pagina_dashboard.text
    assert "Modelos oficiais com prioridade de melhoria" in pagina_dashboard.text
    assert "NR13 · Caldeira" in pagina_dashboard.text
    assert "Modelo oficial priorizado" in pagina_dashboard.text
    assert "Checkpoint" in pagina_dashboard.text


def test_admin_catalogo_familia_salva_modo_calibracao_e_liberacao_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/catalogo-laudos")
    client.post(
        "/admin/catalogo-laudos/familias",
        data={
            "csrf_token": csrf,
            "family_key": "nr10_inspecao_instalacoes_eletricas",
            "nome_exibicao": "NR10 · Instalações Elétricas",
            "macro_categoria": "NR10",
            "nr_key": "nr10",
            "status_catalogo": "publicado",
            "technical_status": "ready",
        },
        follow_redirects=False,
    )
    csrf = _csrf_pagina(client, "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas")
    resposta_modo = client.post(
        "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas/modos",
        data={
            "csrf_token": csrf,
            "mode_key": "periodica",
            "nome_exibicao": "Periódica",
            "descricao": "Execução recorrente.",
        },
        follow_redirects=False,
    )
    assert resposta_modo.status_code == 303
    assert "?tab=modos" in resposta_modo.headers["location"]
    assert resposta_modo.headers["location"].endswith("#modos")

    csrf = _csrf_pagina(client, "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas")
    resposta_governanca = client.post(
        "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas/governanca-review",
        data={
            "csrf_token": csrf,
            "default_review_mode": "mobile_review_allowed",
            "max_review_mode": "mobile_autonomous",
            "requires_family_lock": "on",
            "block_on_missing_required_evidence": "on",
            "requires_release_active": "on",
            "mobile_review_allowed_plans": '["intermediario", "ilimitado"]',
            "mobile_autonomous_allowed_plans": '["ilimitado"]',
            "red_flags_json": json.dumps(
                [
                    {
                        "code": "foto_borrada",
                        "title": "Foto borrada",
                        "message": "Bloquear aprovação quando a evidência visual estiver inadequada.",
                        "severity": "high",
                        "blocking": True,
                    }
                ],
                ensure_ascii=False,
            ),
        },
        follow_redirects=False,
    )
    assert resposta_governanca.status_code == 303
    assert "?tab=schema-tecnico" in resposta_governanca.headers["location"]

    csrf = _csrf_pagina(client, "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas")
    client.post(
        "/admin/catalogo-laudos/ofertas-comerciais",
        data={
            "csrf_token": csrf,
            "family_key": "nr10_inspecao_instalacoes_eletricas",
            "offer_key": "nr10_prime",
            "nome_oferta": "NR10 Prime",
            "lifecycle_status": "active",
            "release_channel": "general_release",
            "bundle_key": "nr10_eletrica",
            "bundle_label": "NR10 Elétrica",
            "included_features": json.dumps(["mobile_review", "official_issue"], ensure_ascii=False),
            "entitlement_monthly_issues": "60",
            "material_real_status": "parcial",
            "material_level": "partial",
            "variantes_comerciais": "prime_site | Prime site | rti | Site elétrico",
        },
        follow_redirects=False,
    )
    csrf = _csrf_pagina(client, "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas")
    resposta_calibracao = client.post(
        "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas/calibracao",
        data={
            "csrf_token": csrf,
            "calibration_status": "partial_real",
            "reference_source": "empresa_nr10_material_real",
            "summary_of_adjustments": "Ajuste de linguagem de risco.",
            "changed_fields_json": '["parecer", "riscos"]',
        },
        follow_redirects=False,
    )
    assert resposta_calibracao.status_code == 303
    assert "?tab=calibracao" in resposta_calibracao.headers["location"]
    assert resposta_calibracao.headers["location"].endswith("#calibracao")

    csrf = _csrf_pagina(client, "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas")
    resposta_release = client.post(
        "/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas/liberacao-tenant",
        data={
            "csrf_token": csrf,
            "tenant_id": str(ids["empresa_a"]),
            "release_status": "active",
            "allowed_modes": "periodica",
            "allowed_offers": "nr10_prime",
            "allowed_templates": "rti",
            "allowed_variants": "catalog:nr10_inspecao_instalacoes_eletricas:prime_site",
            "force_review_mode": "mesa_required",
            "max_review_mode": "mobile_review_allowed",
            "mobile_review_override": "allow",
            "mobile_autonomous_override": "deny",
            "release_channel_override": "pilot",
            "included_features": json.dumps(["priority_support"], ensure_ascii=False),
            "entitlement_monthly_issues": "40",
            "default_template_code": "rti",
        },
        follow_redirects=False,
    )
    assert resposta_release.status_code == 303
    assert "?tab=liberacao" in resposta_release.headers["location"]
    assert resposta_release.headers["location"].endswith("#liberacao")

    pagina_modos = client.get("/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas?tab=modos")
    assert pagina_modos.status_code == 200
    assert "Periódica" in pagina_modos.text

    pagina_calibracao = client.get("/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas?tab=calibracao")
    assert pagina_calibracao.status_code == 200
    assert "Empresa Nr10 Material Real" in pagina_calibracao.text

    pagina_schema = client.get("/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas?tab=schema-tecnico")
    assert pagina_schema.status_code == 200
    assert "Editar fluxo de revisão" in pagina_schema.text
    assert "Foto borrada" in pagina_schema.text

    pagina_liberacao = client.get("/admin/catalogo-laudos/familias/nr10_inspecao_instalacoes_eletricas?tab=liberacao")
    assert pagina_liberacao.status_code == 200
    assert "1 opção(ões) liberada(s)" in pagina_liberacao.text
    assert "RTI" in pagina_liberacao.text
    assert "Analise interna" in pagina_liberacao.text
    assert "Permitir" in pagina_liberacao.text
    assert "Piloto" in pagina_liberacao.text
    assert "limite(s) em uso" in pagina_liberacao.text


def test_admin_catalogo_ofertas_sem_pacote_renderiza_estado_vazio_sem_erro(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr77_sem_pacote",
            nome_exibicao="NR77 · Família sem pacote",
            macro_categoria="NR77",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")

    resposta = client.get("/admin/catalogo-laudos/familias/nr77_sem_pacote?tab=ofertas")

    assert resposta.status_code == 200
    assert "Nenhum pacote comercial montado para esta família." in resposta.text
    assert "O próximo passo é definir posicionamento, modelo principal e escopo de entrega." in resposta.text


def test_admin_catalogo_importa_family_schema_canonico_em_lote(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    client = ambiente_critico["client"]
    family_dir = tmp_path / "family_schemas"
    family_dir.mkdir()
    (family_dir / "nr35_inspecao_linha_de_vida.json").write_text(
        json.dumps(
            {
                "family_key": "nr35_inspecao_linha_de_vida",
                "nome_exibicao": "NR35 · Linha de Vida",
                "macro_categoria": "NR35",
                "descricao": "Schema oficial para linha de vida.",
                "schema_version": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(admin_services, "_family_schemas_dir", lambda: family_dir)

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/catalogo-laudos")
    resposta = client.post(
        "/admin/catalogo-laudos/familias/importar-canonico-lote",
        data={
            "csrf_token": csrf,
            "status_catalogo": "publicado",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    pagina = client.get("/admin/catalogo-laudos")
    assert "NR35 · Linha de Vida" in pagina.text
    assert "nr35_inspecao_linha_de_vida" in pagina.text


def test_admin_detalhe_cliente_sincroniza_portfolio_comercial_do_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_exibicao="NR13 · Vaso de Pressão",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_oferta="NR13 Premium · Vaso de Pressão",
            pacote_comercial="Premium",
            release_channel="limited_release",
            bundle_key="nr13_core",
            bundle_label="NR13 Core",
            included_features_text='["mobile_review", "public_verification"]',
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Operação crítica",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_governanca_review_familia(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            default_review_mode="mobile_review_allowed",
            requires_release_active=True,
            red_flags_json_text=json.dumps(
                [
                    {
                        "code": "foto_inadequada",
                        "title": "Foto inadequada",
                        "message": "Sem evidência visual suficiente o caso sobe para Mesa.",
                        "severity": "high",
                        "blocking": True,
                    }
                ],
                ensure_ascii=False,
            ),
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")
    resposta_detalhe = client.get(f"/admin/clientes/{ids['empresa_a']}")
    assert resposta_detalhe.status_code == 200
    assert "Laudos liberados para esta empresa" in resposta_detalhe.text
    assert "Sincronizar portfólio" in resposta_detalhe.text
    assert "Ajustes da empresa" in resposta_detalhe.text
    assert "Foto inadequada" not in resposta_detalhe.text
    assert "Aplicativo com apoio da analise" in resposta_detalhe.text

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")
    resposta_release = client.post(
        "/admin/catalogo-laudos/familias/nr13_inspecao_vaso_pressao/liberacao-tenant",
        data={
            "csrf_token": csrf,
            "tenant_id": str(ids["empresa_a"]),
            "return_to": f"/admin/clientes/{ids['empresa_a']}",
            "release_status": "active",
            "allowed_offers": "nr13_inspecao_vaso_pressao",
            "allowed_templates": "nr13_premium",
            "allowed_variants": "catalog:nr13_inspecao_vaso_pressao:premium_campo",
            "force_review_mode": "mesa_required",
            "mobile_review_override": "allow",
            "mobile_autonomous_override": "deny",
            "release_channel_override": "pilot",
            "included_features": "priority_support\nofficial_issue",
            "entitlement_monthly_issues": "45",
            "default_template_code": "nr13_premium",
            "observacoes": "Tenant precisa de revisão humana explícita.",
        },
        follow_redirects=False,
    )

    assert resposta_release.status_code == 303
    assert resposta_release.headers["location"].startswith(f"/admin/clientes/{ids['empresa_a']}")

    resposta_sync = client.post(
        f"/admin/clientes/{ids['empresa_a']}/catalogo-laudos",
        data={
            "csrf_token": csrf,
            "catalog_variant": "catalog:nr13_inspecao_vaso_pressao:premium_campo",
        },
        follow_redirects=False,
    )

    assert resposta_sync.status_code == 303

    with SessionLocal() as banco:
        ativacoes = list(
            banco.scalars(
                select(AtivacaoCatalogoEmpresaLaudo).where(
                    AtivacaoCatalogoEmpresaLaudo.empresa_id == ids["empresa_a"],
                    AtivacaoCatalogoEmpresaLaudo.ativo.is_(True),
                )
            ).all()
        )
        assert len(ativacoes) == 1

    resposta_atualizada = client.get(f"/admin/clientes/{ids['empresa_a']}")
    assert resposta_atualizada.status_code == 200
    assert "Mesa obrigatória" in resposta_atualizada.text
    assert "Permitir" in resposta_atualizada.text
    assert "Bloquear" in resposta_atualizada.text
    assert "NR13 Core" in resposta_atualizada.text
    assert "Piloto" in resposta_atualizada.text
    assert "priority_support" in resposta_atualizada.text
    assert ativacoes[0].family_key == "nr13_inspecao_vaso_pressao"
    assert ativacoes[0].variant_key == "premium_campo"


def test_headers_http_nao_reintroduzem_permissions_policy_incompativel(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    resposta = client.get("/admin/login")

    assert resposta.status_code == 200
    permissions_policy = resposta.headers.get("Permissions-Policy", "")
    assert "bluetooth" not in permissions_policy
    assert "camera=()" in permissions_policy


def test_admin_catalogo_e_dashboard_exibem_rollup_de_governanca(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa_a = banco.get(Empresa, ids["empresa_a"])
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_a is not None
        assert empresa_b is not None
        empresa_a.plano_ativo = "Intermediario"
        empresa_b.plano_ativo = "Ilimitado"

        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_governanca_review_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            default_review_mode="mobile_review_allowed",
            max_review_mode="mobile_review_allowed",
            mobile_review_allowed_plans_text='["intermediario", "ilimitado"]',
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Prime · Caldeira",
            lifecycle_status="active",
            release_channel="general_release",
            bundle_key="nr13_core",
            bundle_label="NR13 Core",
            included_features_text='["mobile_review", "official_issue"]',
            variantes_comerciais_text="campo | Campo | nr13 | Campo",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            criado_por_id=ids["admin_a"],
        )

        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_governanca_review_familia(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            default_review_mode="mobile_autonomous",
            max_review_mode="mobile_autonomous",
            mobile_review_allowed_plans_text='["ilimitado"]',
            mobile_autonomous_allowed_plans_text='["ilimitado"]',
            red_flags_json_text=json.dumps(
                [
                    {
                        "code": "ancoragem",
                        "title": "Ancoragem crítica",
                        "message": "Exige rigor adicional.",
                        "severity": "high",
                        "blocking": True,
                    }
                ],
                ensure_ascii=False,
            ),
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_oferta="NR35 Prime · Linha de Vida",
            lifecycle_status="active",
            release_channel="limited_release",
            bundle_key="nr35_altura",
            bundle_label="NR35 Altura",
            included_features_text='["mobile_autonomous", "priority_support"]',
            variantes_comerciais_text="campo | Campo | nr35 | Campo",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_b"],
            family_key="nr35_inspecao_linha_de_vida",
            release_status="active",
            mobile_review_override="allow",
            mobile_autonomous_override="allow",
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")

    pagina_catalogo = client.get("/admin/catalogo-laudos")
    assert pagina_catalogo.status_code == 200
    assert "Clientes com acesso liberado" in pagina_catalogo.text
    assert "Modo padrao das familias" in pagina_catalogo.text
    assert "Abrir cliente" in pagina_catalogo.text
    assert "Empresa A" in pagina_catalogo.text
    assert "NR35 · Linha de Vida" in pagina_catalogo.text
    assert "Pacotes e etapas de liberacao" in pagina_catalogo.text
    assert "NR13 Core" in pagina_catalogo.text

    painel = client.get("/admin/painel")
    assert painel.status_code == 200
    assert "Governança operacional" in painel.text
    assert "Empresas com regra mais rígida" in painel.text
    assert "Famílias com regra ativa" in painel.text
    assert "Pacotes e etapas de liberacao" in painel.text
    assert "Recursos mais usados nos pacotes" in painel.text
    assert "Analise interna" in painel.text
    assert "Empresa B" in painel.text


def test_admin_configuracoes_persistem_governanca_funcional(ambiente_critico, monkeypatch: pytest.MonkeyPatch) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.delenv("REVIEW_UI_CANONICAL", raising=False)
    monkeypatch.delenv("TARIEL_REVIEW_DESK_PRIMARY_SURFACE", raising=False)

    _login_admin(client, "admin@empresa-a.test")

    csrf = _csrf_pagina(client, "/admin/configuracoes")
    resposta_acesso = client.post(
        "/admin/configuracoes/acesso",
        data={
            "csrf_token": csrf,
            "admin_reauth_max_age_minutes": "25",
            "motivo_alteracao": "Ampliação da janela operacional",
        },
        follow_redirects=False,
    )
    assert resposta_acesso.status_code == 303
    assert resposta_acesso.headers["location"].startswith("/admin/configuracoes")
    assert admin_portal_support.get_admin_reauth_max_age_minutes() == 25

    csrf = _csrf_pagina(client, "/admin/configuracoes")
    resposta_rollout = client.post(
        "/admin/configuracoes/rollout",
        data={
            "csrf_token": csrf,
            "review_ui_canonical": "ssr",
            "motivo_alteracao": "Consolidação do fluxo oficial no SSR",
        },
        follow_redirects=False,
    )
    assert resposta_rollout.status_code == 303
    assert panel_rollout.get_review_panel_primary_surface() == "ssr"

    csrf = _csrf_pagina(client, "/admin/configuracoes")
    resposta_defaults = client.post(
        "/admin/configuracoes/defaults",
        data={
            "csrf_token": csrf,
            "default_new_tenant_plan": "Intermediario",
            "motivo_alteracao": "Novo padrão comercial de onboarding",
        },
        follow_redirects=False,
    )
    assert resposta_defaults.status_code == 303

    with SessionLocal() as banco:
        janela = banco.get(ConfiguracaoPlataforma, "admin_reauth_max_age_minutes")
        rollout = banco.get(ConfiguracaoPlataforma, "review_ui_canonical")
        plano = banco.get(ConfiguracaoPlataforma, "default_new_tenant_plan")
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_plataforma"],
                RegistroAuditoriaEmpresa.acao == "platform_setting_updated",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert janela is not None
        assert int(janela.valor_json) == 25
        assert rollout is None or rollout.valor_json == "ssr"
        assert plano is not None
        assert plano.valor_json == "Intermediario"
        assert auditoria is not None

    pagina_novo_cliente = client.get("/admin/novo-cliente")
    assert pagina_novo_cliente.status_code == 200
    assert '<option value="Intermediario" selected>' in pagina_novo_cliente.text


def test_admin_configuracoes_limpam_empresas_temporarias_ui_em_cascata(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa_temp = Empresa(
            nome_fantasia="Tariel UI Audit 001",
            cnpj="55555555000101",
            plano_ativo="Intermediario",
        )
        empresa_real = Empresa(
            nome_fantasia="Cliente Preservado",
            cnpj="55555555000102",
            plano_ativo="Intermediario",
        )
        banco.add_all([empresa_temp, empresa_real])
        banco.flush()

        admin_temp = Usuario(
            empresa_id=int(empresa_temp.id),
            nome_completo="Admin Temp",
            email="admin.temp.audit@example.com",
            senha_hash="hash",
            nivel_acesso=int(NivelAcesso.ADMIN_CLIENTE),
            ativo=True,
        )
        inspetor_temp = Usuario(
            empresa_id=int(empresa_temp.id),
            nome_completo="Inspetor Temp",
            email="inspetor.temp.audit@example.com",
            senha_hash="hash",
            nivel_acesso=int(NivelAcesso.INSPETOR),
            ativo=True,
        )
        admin_real = Usuario(
            empresa_id=int(empresa_real.id),
            nome_completo="Admin Real",
            email="admin.real@example.com",
            senha_hash="hash",
            nivel_acesso=int(NivelAcesso.ADMIN_CLIENTE),
            ativo=True,
        )
        banco.add_all([admin_temp, inspetor_temp, admin_real])
        banco.flush()

        banco.add(
            Laudo(
                empresa_id=int(empresa_temp.id),
                usuario_id=int(inspetor_temp.id),
                setor_industrial="Energia",
                status_revisao="rascunho",
                codigo_hash="audit-temp-hash-001",
            )
        )
        banco.commit()
        empresa_temp_id = int(empresa_temp.id)
        empresa_real_id = int(empresa_real.id)

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/configuracoes")

    resposta = client.post(
        "/admin/configuracoes/manutencao/limpar-auditoria-ui",
        data={
            "csrf_token": csrf,
            "company_ids": str(empresa_temp_id),
            "confirmation_phrase": "EXCLUIR TARIEL UI AUDIT",
            "motivo_operacao": "Limpeza de artefatos temporários de produção",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/admin/configuracoes")

    with SessionLocal() as banco:
        assert banco.get(Empresa, empresa_temp_id) is None
        assert banco.get(Empresa, empresa_real_id) is not None
        assert banco.scalar(select(Laudo).where(Laudo.empresa_id == empresa_temp_id)) is None
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_plataforma"],
                RegistroAuditoriaEmpresa.acao == "ui_audit_tenants_purged",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert auditoria is not None
        payload = dict(auditoria.payload_json or {})
        assert payload["requested_company_ids"] == [empresa_temp_id]
        assert payload["companies"][0]["empresa_id"] == empresa_temp_id


def test_admin_configuracoes_recusam_limpeza_ui_sem_confirmacao(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/configuracoes")

    resposta = client.post(
        "/admin/configuracoes/manutencao/limpar-auditoria-ui",
        data={
            "csrf_token": csrf,
            "company_ids": "999",
            "confirmation_phrase": "CONFIRMACAO ERRADA",
            "motivo_operacao": "Teste",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert "erro=Confirma%C3%A7%C3%A3o" in resposta.headers["location"]


def test_admin_configuracoes_removem_empresas_cliente_por_ids_sem_afetar_plataforma(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa_a = banco.get(Empresa, ids["empresa_a"])
        assert empresa_a is not None
        empresa_cliente_extra = Empresa(
            nome_fantasia="Cliente Temporario B",
            cnpj="55443322000199",
            plano_ativo="Intermediario",
        )
        banco.add(empresa_cliente_extra)
        banco.flush()

        admin_extra = Usuario(
            empresa_id=int(empresa_cliente_extra.id),
            nome_completo="Admin Extra",
            email="admin.extra@example.com",
            senha_hash="hash",
            nivel_acesso=int(NivelAcesso.ADMIN_CLIENTE),
            ativo=True,
        )
        banco.add(admin_extra)
        banco.flush()

        banco.add(
            Laudo(
                empresa_id=int(empresa_cliente_extra.id),
                usuario_id=int(admin_extra.id),
                setor_industrial="Energia",
                status_revisao="rascunho",
                codigo_hash="cliente-extra-hash-001",
            )
        )
        banco.commit()
        empresa_cliente_extra_id = int(empresa_cliente_extra.id)

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/configuracoes")

    resposta = client.post(
        "/admin/configuracoes/manutencao/remover-tenants-cliente",
        data={
            "csrf_token": csrf,
            "company_ids": f"{ids['empresa_a']},{empresa_cliente_extra_id}",
            "confirmation_phrase": "EXCLUIR EMPRESAS CLIENTE",
            "motivo_operacao": "Limpeza geral do ambiente de teste",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/admin/configuracoes")

    with SessionLocal() as banco:
        assert banco.get(Empresa, ids["empresa_a"]) is None
        assert banco.get(Empresa, empresa_cliente_extra_id) is None
        assert banco.get(Empresa, ids["empresa_plataforma"]) is not None
        assert banco.scalar(select(Laudo).where(Laudo.empresa_id == empresa_cliente_extra_id)) is None
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_plataforma"],
                RegistroAuditoriaEmpresa.acao == "client_tenants_purged",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert auditoria is not None
        payload = dict(auditoria.payload_json or {})
        assert payload["requested_company_ids"] == sorted([ids["empresa_a"], empresa_cliente_extra_id])
        assert {item["empresa_id"] for item in payload["companies"]} == {
            ids["empresa_a"],
            empresa_cliente_extra_id,
        }


def test_admin_configuracoes_recusam_remocao_cliente_sem_confirmacao(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/configuracoes")

    resposta = client.post(
        "/admin/configuracoes/manutencao/remover-tenants-cliente",
        data={
            "csrf_token": csrf,
            "company_ids": "999",
            "confirmation_phrase": "CONFIRMACAO ERRADA",
            "motivo_operacao": "Teste",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert "erro=Confirma%C3%A7%C3%A3o" in resposta.headers["location"]


def test_admin_login_exige_role_diretoria_sem_autoacesso_e_oculta_sso_inativo(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    pagina_login = client.get("/admin/login")
    assert pagina_login.status_code == 200
    assert "Quer um acesso? Fale com a Tariel." in pagina_login.text
    assert "Continuar com Google" not in pagina_login.text
    assert "Continuar com Microsoft" not in pagina_login.text
    assert "/cliente/login" not in pagina_login.text
    assert "/app/login" not in pagina_login.text
    assert "/revisao/login" not in pagina_login.text

    csrf = _csrf_pagina(client, "/admin/login")
    resposta = client.post(
        "/admin/login",
        data={
            "email": "cliente@empresa-a.test",
            "senha": "Senha@123",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 403
    assert "não está autorizado para o portal Admin-CEO" in resposta.text


def test_admin_login_identity_callback_denies_unknown_google_identity_without_autoprovision(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(admin_portal_support, "ADMIN_LOGIN_GOOGLE_ENABLED", True)
    csrf = _csrf_pagina(client, "/admin/login")

    resposta = client.get(
        f"/admin/login/identity/google/callback?state={csrf}&email=desconhecido@externo.test&subject=google-sub-001",
        follow_redirects=False,
    )

    assert resposta.status_code == 403
    assert "não está autorizado para o portal Admin-CEO" in resposta.text

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.email == "desconhecido@externo.test"))
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_plataforma"],
                RegistroAuditoriaEmpresa.acao == "admin_identity_denied",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert usuario is None
        assert auditoria is not None
        assert auditoria.payload_json["provider"] == "google"
        assert auditoria.payload_json["email"] == "desconhecido@externo.test"
        assert auditoria.payload_json["reason"] == "identity_not_found"


def test_admin_login_identity_callback_autoriza_operador_pre_cadastrado_e_vincula_subject(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(admin_portal_support, "ADMIN_LOGIN_GOOGLE_ENABLED", True)
    csrf = _csrf_pagina(client, "/admin/login")

    resposta = client.get(
        f"/admin/login/identity/google/callback?state={csrf}&email=admin@empresa-a.test&subject=google-sub-123",
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/mfa/challenge"

    pagina_mfa = client.get("/admin/mfa/challenge", follow_redirects=False)
    assert pagina_mfa.status_code == 200
    csrf_mfa = _csrf_pagina(client, "/admin/mfa/challenge")
    resposta_mfa = client.post(
        "/admin/mfa/challenge",
        data={"csrf_token": csrf_mfa, "codigo": current_totp(ADMIN_TOTP_SECRET)},
        follow_redirects=False,
    )
    assert resposta_mfa.status_code == 303
    assert resposta_mfa.headers["location"] == "/admin/painel"

    painel = client.get("/admin/painel", follow_redirects=False)
    assert painel.status_code == 200

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_plataforma"],
                RegistroAuditoriaEmpresa.acao == "admin_identity_authenticated",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert admin is not None
        assert admin.admin_identity_provider == "google"
        assert admin.admin_identity_subject == "google-sub-123"
        assert admin.admin_identity_verified_em is not None
        assert auditoria is not None
        assert auditoria.alvo_usuario_id == ids["admin_a"]
        assert auditoria.payload_json["reason"] == "authorized"


def test_admin_login_local_exige_mfa_para_emitir_sessao(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    csrf = _csrf_pagina(client, "/admin/login")
    resposta = client.post(
        "/admin/login",
        data={
            "email": "admin@empresa-a.test",
            "senha": "Senha@123",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/mfa/challenge"

    painel_sem_mfa = client.get("/admin/painel", follow_redirects=False)
    assert painel_sem_mfa.status_code == 303
    assert painel_sem_mfa.headers["location"] == "/admin/login"

    _login_admin(client, "admin@empresa-a.test")
    with SessionLocal() as banco:
        sessao = banco.scalar(select(SessaoAtiva).where(SessaoAtiva.usuario_id == ids["admin_a"]))
        assert sessao is not None
        assert sessao.portal == "admin"
        assert sessao.account_scope == "platform"
        assert sessao.mfa_level == "totp"
        assert sessao.reauth_at is not None


def test_admin_login_local_pode_bypassar_totp_quando_flag_desabilitada(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(admin_portal_support, "ADMIN_TOTP_ENABLED", False)

    csrf = _csrf_pagina(client, "/admin/login")
    resposta = client.post(
        "/admin/login",
        data={
            "email": "admin@empresa-a.test",
            "senha": "Senha@123",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/painel"

    painel = client.get("/admin/painel", follow_redirects=False)
    assert painel.status_code == 200

    with SessionLocal() as banco:
        sessao = banco.scalar(select(SessaoAtiva).where(SessaoAtiva.usuario_id == ids["admin_a"]))
        assert sessao is not None
        assert sessao.portal == "admin"
        assert sessao.account_scope == "platform"
        assert sessao.mfa_level == "disabled"
        assert sessao.reauth_at is not None


def test_admin_mfa_setup_post_nao_revela_segredo_para_operador_ja_cadastrado(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    csrf = _csrf_pagina(client, "/admin/login")
    resposta = client.post(
        "/admin/login",
        data={
            "email": "admin@empresa-a.test",
            "senha": "Senha@123",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/mfa/challenge"

    resposta_setup = client.post(
        "/admin/mfa/setup",
        data={"csrf_token": "csrf-invalido", "codigo": "000000"},
        follow_redirects=False,
    )

    assert resposta_setup.status_code == 303
    assert resposta_setup.headers["location"] == "/admin/mfa/challenge"

    pagina_mfa = client.get("/admin/mfa/challenge", follow_redirects=False)
    assert pagina_mfa.status_code == 200
    assert ADMIN_TOTP_SECRET not in pagina_mfa.text
    assert _totp_grouped(ADMIN_TOTP_SECRET) not in pagina_mfa.text


def test_admin_mfa_setup_csrf_invalido_nao_revela_segredo_no_html(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        admin.mfa_required = True
        admin.mfa_secret_b32 = ADMIN_TOTP_SECRET
        admin.mfa_enrolled_at = None
        banco.commit()

    csrf = _csrf_pagina(client, "/admin/login")
    resposta = client.post(
        "/admin/login",
        data={
            "email": "admin@empresa-a.test",
            "senha": "Senha@123",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/mfa/setup"

    resposta_setup = client.post(
        "/admin/mfa/setup",
        data={"csrf_token": "csrf-invalido", "codigo": current_totp(ADMIN_TOTP_SECRET)},
        follow_redirects=False,
    )

    assert resposta_setup.status_code == 400
    assert "Requisição inválida." in resposta_setup.text
    assert ADMIN_TOTP_SECRET not in resposta_setup.text
    assert _totp_grouped(ADMIN_TOTP_SECRET) not in resposta_setup.text
    assert "otpauth://" not in resposta_setup.text


def test_admin_acao_critica_exige_step_up_quando_reauth_expira(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    SessionLocal = ambiente_critico["SessionLocal"]

    _login_admin(client, "admin@empresa-a.test")
    with SessionLocal() as banco:
        token = banco.scalar(select(SessaoAtiva.token).where(SessaoAtiva.usuario_id == ids["admin_a"]))
    assert token
    admin_portal_support.atualizar_meta_sessao(
        token,
        reauth_at=admin_portal_support._agora_utc() - admin_portal_support.timedelta(minutes=30),
    )

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")
    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/bloquear",
        data={"csrf_token": csrf, "motivo": "Teste"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/admin/reauth")


def test_admin_acao_critica_nao_exige_step_up_quando_totp_esta_desabilitado(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(admin_portal_support, "ADMIN_TOTP_ENABLED", False)

    _login_admin(client, "admin@empresa-a.test")
    with SessionLocal() as banco:
        token = banco.scalar(select(SessaoAtiva.token).where(SessaoAtiva.usuario_id == ids["admin_a"]))
    assert token
    admin_portal_support.atualizar_meta_sessao(
        token,
        reauth_at=admin_portal_support._agora_utc() - admin_portal_support.timedelta(minutes=30),
    )

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")
    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/bloquear",
        data={"csrf_token": csrf, "motivo": "Teste"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert not resposta.headers["location"].startswith("/admin/reauth")


def test_verificar_acesso_admin_exige_role_e_portal_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    usuario = Usuario(
        nivel_acesso=NivelAcesso.DIRETORIA.value,
        account_scope="platform",
        account_status="active",
        allowed_portals_json=["admin"],
    )

    monkeypatch.setattr(admin_portal_support, "usuario_tem_acesso_portal", lambda *_args, **_kwargs: False)
    assert admin_portal_support._verificar_acesso_admin(usuario) is False

    monkeypatch.setattr(admin_portal_support, "usuario_tem_acesso_portal", lambda *_args, **_kwargs: True)
    assert admin_portal_support._verificar_acesso_admin(usuario) is True


def test_admin_block_company_does_not_logout_current_platform_operator(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/bloquear",
        data={"csrf_token": csrf, "motivo": "Congelamento controlado"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith(f"/admin/clientes/{ids['empresa_a']}?sucesso=")

    detalhe = client.get(f"/admin/clientes/{ids['empresa_a']}", follow_redirects=False)
    assert detalhe.status_code == 200

    painel = client.get("/admin/painel", follow_redirects=False)
    assert painel.status_code == 200

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "tenant_block_toggled",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert empresa is not None
        assert bool(empresa.status_bloqueio) is True
        assert auditoria is not None
        assert auditoria.ator_usuario_id == ids["admin_a"]
        assert auditoria.payload_json["reason"] == "Congelamento controlado"
        assert int(auditoria.payload_json["sessions_invalidated"]) == 0


def test_admin_abre_e_encerra_suporte_excepcional_com_trilha_auditavel(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta_abrir = client.post(
        f"/admin/clientes/{ids['empresa_a']}/suporte-excepcional/abrir",
        data={
            "csrf_token": csrf,
            "justificativa": "Incidente controlado no tenant exige janela administrativa.",
            "referencia_aprovacao": "APR-2026-041",
        },
        follow_redirects=False,
    )
    assert resposta_abrir.status_code == 303
    assert resposta_abrir.headers["location"].startswith(f"/admin/clientes/{ids['empresa_a']}?sucesso=")

    detalhe = client.get(f"/admin/clientes/{ids['empresa_a']}")
    assert detalhe.status_code == 200
    assert "Suporte excepcional ativo" in detalhe.text
    assert "APR-2026-041" in detalhe.text

    with SessionLocal() as banco:
        abertura = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "tenant_exceptional_support_opened",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert abertura is not None
        assert abertura.ator_usuario_id == ids["admin_a"]
        assert abertura.payload_json["approval_reference"] == "APR-2026-041"
        assert abertura.payload_json["scope_level"] == "administrative"

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")
    resposta_encerrar = client.post(
        f"/admin/clientes/{ids['empresa_a']}/suporte-excepcional/encerrar",
        data={
            "csrf_token": csrf,
            "motivo_encerramento": "Incidente estabilizado.",
        },
        follow_redirects=False,
    )
    assert resposta_encerrar.status_code == 303
    assert resposta_encerrar.headers["location"].startswith(f"/admin/clientes/{ids['empresa_a']}?sucesso=")

    with SessionLocal() as banco:
        fechamento = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "tenant_exceptional_support_closed",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert fechamento is not None
        assert fechamento.payload_json["closed_reason"] == "Incidente estabilizado."
        assert fechamento.payload_json["expired"] is False


def test_admin_logout_encera_sessao_do_portal(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/painel")

    resposta = client.post(
        "/admin/logout",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/login"

    painel = client.get("/admin/painel", follow_redirects=False)
    assert painel.status_code == 303
    assert painel.headers["location"] == "/admin/login"


def test_admin_geral_exige_motivo_para_bloqueio_e_confirmacao_para_desbloqueio(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_b']}")

    resposta_sem_motivo = client.post(
        f"/admin/clientes/{ids['empresa_b']}/bloquear",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert resposta_sem_motivo.status_code == 303
    pagina_erro = client.get(resposta_sem_motivo.headers["location"])
    assert "Informe o motivo do bloqueio." in pagina_erro.text

    with SessionLocal() as banco:
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_b is not None
        assert bool(empresa_b.status_bloqueio) is False

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_b']}")
    resposta_bloqueio = client.post(
        f"/admin/clientes/{ids['empresa_b']}/bloquear",
        data={"csrf_token": csrf, "motivo": "Inadimplência"},
        follow_redirects=False,
    )
    assert resposta_bloqueio.status_code == 303
    pagina_bloqueio = client.get(resposta_bloqueio.headers["location"])
    assert "Acesso bloqueado com sucesso." in pagina_bloqueio.text

    with SessionLocal() as banco:
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_b is not None
        assert bool(empresa_b.status_bloqueio) is True
        assert empresa_b.motivo_bloqueio == "Inadimplência"

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_b']}")
    resposta_sem_confirmacao = client.post(
        f"/admin/clientes/{ids['empresa_b']}/bloquear",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert resposta_sem_confirmacao.status_code == 303
    pagina_confirmacao = client.get(resposta_sem_confirmacao.headers["location"])
    assert "Confirme o desbloqueio da empresa." in pagina_confirmacao.text

    with SessionLocal() as banco:
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_b is not None
        assert bool(empresa_b.status_bloqueio) is True

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_b']}")
    resposta_desbloqueio = client.post(
        f"/admin/clientes/{ids['empresa_b']}/bloquear",
        data={"csrf_token": csrf, "confirmar_desbloqueio": "1"},
        follow_redirects=False,
    )
    assert resposta_desbloqueio.status_code == 303
    pagina_desbloqueio = client.get(resposta_desbloqueio.headers["location"])
    assert "Acesso restaurado com sucesso." in pagina_desbloqueio.text

    with SessionLocal() as banco:
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_b is not None
        assert bool(empresa_b.status_bloqueio) is False
        assert empresa_b.motivo_bloqueio == "Inadimplência"


def test_admin_geral_troca_plano_reset_seguro_e_exporta_bundle_administrativo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_b']}")
    resposta_plano = client.post(
        f"/admin/clientes/{ids['empresa_b']}/trocar-plano",
        data={"csrf_token": csrf, "plano": "Intermediario"},
        follow_redirects=False,
    )
    assert resposta_plano.status_code == 303
    pagina_plano = client.get(resposta_plano.headers["location"])
    assert "Plano atualizado para Pro." in pagina_plano.text

    with SessionLocal() as banco:
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        auditoria_plano = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_b"],
                RegistroAuditoriaEmpresa.acao == "tenant_plan_changed",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert empresa_b is not None
        assert empresa_b.plano_ativo == "Intermediario"
        assert auditoria_plano is not None
        assert auditoria_plano.payload_json["plano_novo"] == "Intermediario"
        assert "impacto" in auditoria_plano.payload_json

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")
    resposta_reset = client.post(
        f"/admin/clientes/{ids['empresa_a']}/resetar-senha/{ids['admin_cliente_a']}",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert resposta_reset.status_code == 303
    pagina_reset = client.get(resposta_reset.headers["location"])
    assert "deverá trocar a senha no próximo login" in pagina_reset.text
    assert "Senha temporária para" not in pagina_reset.text

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        assert usuario.senha_temporaria_ativa is True

    resposta_diagnostico = client.get(f"/admin/clientes/{ids['empresa_b']}/diagnostico")
    assert resposta_diagnostico.status_code == 200
    assert "attachment; filename=" in resposta_diagnostico.headers["content-disposition"]
    payload = json.loads(resposta_diagnostico.text)
    assert payload["contract_name"] == "PlatformTenantOperationalDiagnosticV1"
    assert int(payload["tenant"]["id"]) == ids["empresa_b"]
    assert "resumo_operacional" in payload
    assert "seguranca" in payload
    assert "falhas_recentes" in payload
    assert "laudos_recentes" not in payload


def test_admin_geral_bloqueia_usuario_do_tenant_com_auditoria(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta_bloqueio = client.post(
        f"/admin/clientes/{ids['empresa_a']}/usuarios/{ids['admin_cliente_a']}/bloquear",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert resposta_bloqueio.status_code == 303
    pagina_bloqueio = client.get(resposta_bloqueio.headers["location"])
    assert "bloqueado com sucesso" in pagina_bloqueio.text

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "tenant_user_block_toggled",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()
        assert usuario is not None
        assert bool(usuario.ativo) is False
        assert auditoria is not None
        assert auditoria.alvo_usuario_id == ids["admin_cliente_a"]

    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")
    resposta_reativacao = client.post(
        f"/admin/clientes/{ids['empresa_a']}/usuarios/{ids['admin_cliente_a']}/bloquear",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert resposta_reativacao.status_code == 303

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        assert bool(usuario.ativo) is True
