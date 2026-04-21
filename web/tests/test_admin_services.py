from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

import app.domains.admin.services as admin_services
from app.domains.admin.portal_support import get_admin_reauth_max_age_minutes
from app.domains.revisor import panel_rollout
from app.shared.database import (
    AtivacaoCatalogoEmpresaLaudo,
    CalibracaoFamiliaLaudo,
    ConfiguracaoPlataforma,
    Empresa,
    FamiliaLaudoCatalogo,
    LimitePlano,
    ModoTecnicoFamiliaLaudo,
    NivelAcesso,
    OfertaComercialFamiliaLaudo,
    PlanoEmpresa,
    RegistroAuditoriaEmpresa,
    SessaoAtiva,
    SignatarioGovernadoLaudo,
    TenantFamilyReleaseLaudo,
    Usuario,
)
from app.shared.security import criar_sessao, token_esta_ativo, verificar_senha
from app.shared.tenant_admin_policy import summarize_tenant_admin_policy


def _bootstrap_catalog_repo_assets(
    root: Path,
    family_key: str,
    *,
    material_status: str = "baseline_sintetica_externa_validada",
    create_full_chain: bool = True,
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

    (master_templates_dir / "inspection_conformity.template_master.json").write_text(
        json.dumps({"template": "premium"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (master_templates_dir / "library_registry.json").write_text(
        json.dumps(
            {
                "version": 3,
                "templates": [
                    {
                        "master_template_id": "inspection_conformity",
                        "label": "Inspection Conformity Premium",
                        "documental_type": "laudo",
                        "status": "ready",
                        "artifact_path": "docs/master_templates/inspection_conformity.template_master.json",
                        "usage": "Template mestre premium para inspeções governadas.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (family_schemas_dir / f"{family_key}.json").write_text(
        json.dumps(
            {
                "family_key": family_key,
                "nome_exibicao": family_key.replace("_", " ").title(),
                "macro_categoria": "NR13",
                "schema_version": 2,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if create_full_chain:
        for suffix in (
            ".template_master_seed.json",
            ".laudo_output_seed.json",
            ".laudo_output_exemplo.json",
        ):
            (family_schemas_dir / f"{family_key}{suffix}").write_text(
                json.dumps({"family_key": family_key}, ensure_ascii=False),
                encoding="utf-8",
            )

    (workspace_dir / "briefing_real.md").write_text("# Briefing real\n", encoding="utf-8")
    (workspace_dir / "manifesto_coleta.json").write_text(
        json.dumps({"family_key": family_key}, ensure_ascii=False),
        encoding="utf-8",
    )
    (workspace_dir / "status_refino.json").write_text(
        json.dumps(
            {
                "status_refino": material_status,
                "material_recebido": ["pdf", "zip"],
                "lacunas_abertas": ["foto de placa"],
                "artefatos_externos_validados": [{"kind": "zip", "source": "chatgpt"}],
                "proximo_passo": "Promover pacote de referência.",
            },
            ensure_ascii=False,
        ),
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


def test_stub_boas_vindas_nao_vaza_senha_em_log_dev(monkeypatch) -> None:
    monkeypatch.setattr(admin_services, "_MODO_DEV", True)
    monkeypatch.setattr(admin_services, "_BACKEND_NOTIFICACAO_BOAS_VINDAS", "log")

    with patch.object(admin_services.logger, "info") as logger_info:
        aviso = admin_services._disparar_email_boas_vindas(
            "cliente@empresa.test",
            "Empresa Teste",
            "Senha@123456",
        )

    mensagem = logger_info.call_args.args[0]
    assert "[BACKEND LOG] BOAS-VINDAS INTERCEPTADO" in mensagem
    assert "cliente@empresa.test" in mensagem
    assert "Empresa Teste" in mensagem
    assert "[REDACTED]" in mensagem
    assert "Senha@123456" not in mensagem
    assert aviso is not None
    assert "Entrega automática" in aviso


def test_boas_vindas_strict_falha_com_aviso_explicito(monkeypatch) -> None:
    monkeypatch.setattr(admin_services, "_BACKEND_NOTIFICACAO_BOAS_VINDAS", "strict")

    with pytest.raises(RuntimeError, match="Entrega automática de boas-vindas não configurada"):
        admin_services._disparar_email_boas_vindas(
            "cliente@empresa.test",
            "Empresa Teste",
            "Senha@123456",
        )


def test_registrar_novo_cliente_cria_empresa_e_admin_temporario(ambiente_critico, monkeypatch: pytest.MonkeyPatch) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    disparos: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        admin_services,
        "_disparar_email_boas_vindas",
        lambda email, empresa, senha: disparos.append((email, empresa, senha)),
    )

    with SessionLocal() as banco:
        empresa, senha_temporaria, aviso = admin_services.registrar_novo_cliente(
            banco,
            nome="Nova Empresa",
            cnpj="11222333000181",
            email_admin="novo-admin@empresa.test",
            plano=PlanoEmpresa.ILIMITADO.value,
            segmento="Industrial",
            cidade_estado="Goiania/GO",
            nome_responsavel="Responsavel Teste",
        )

        usuario = banco.query(Usuario).filter(Usuario.email == "novo-admin@empresa.test").one()

        assert empresa.id is not None
        assert empresa.escopo_plataforma is False
        assert empresa.admin_cliente_policy_json == {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
        }
        assert usuario.empresa_id == empresa.id
        assert int(usuario.nivel_acesso) == int(NivelAcesso.ADMIN_CLIENTE)
        assert usuario.senha_temporaria_ativa is True
        assert verificar_senha(senha_temporaria, usuario.senha_hash) is True

    assert disparos == [("novo-admin@empresa.test", "Nova Empresa", senha_temporaria)]
    assert aviso is None


def test_busca_detalhe_cliente_tolera_falha_no_portfolio_catalogo(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    def _falhar_portfolio(*_args, **_kwargs):
        raise RuntimeError("falha simulada no portfolio")

    monkeypatch.setattr(admin_services, "resumir_portfolio_catalogo_empresa", _falhar_portfolio)

    with SessionLocal() as banco:
        detalhe = admin_services.buscar_detalhe_cliente(banco, ids["empresa_a"])

    assert detalhe is not None
    assert detalhe["empresa"].id == ids["empresa_a"]
    assert detalhe["portfolio_catalogo"] == {
        "families": [],
        "active_activation_count": 0,
        "active_family_count": 0,
        "governed_mode": False,
        "managed_by_admin_ceo": False,
        "catalog_state": "unavailable",
        "permissions": {},
        "available_variant_count": 0,
        "operational_variant_count": 0,
    }


def test_registrar_novo_cliente_normaliza_politica_operacional_do_admin_cliente(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "_disparar_email_boas_vindas",
        lambda *_args, **_kwargs: None,
    )

    with SessionLocal() as banco:
        empresa, _senha_temporaria, _aviso = admin_services.registrar_novo_cliente(
            banco,
            nome="Tenant Resumo",
            cnpj="11222333000182",
            email_admin="tenant-resumo@empresa.test",
            plano=PlanoEmpresa.INTERMEDIARIO.value,
            admin_cliente_case_visibility_mode="summary_only",
            admin_cliente_case_action_mode="case_actions",
        )

        assert empresa.admin_cliente_policy_json == {
            "case_visibility_mode": "summary_only",
            "case_action_mode": "read_only",
        }


def test_registrar_novo_cliente_persiste_modelo_mobile_single_operator(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "_disparar_email_boas_vindas",
        lambda *_args, **_kwargs: None,
    )

    with SessionLocal() as banco:
        empresa, _senha_temporaria, _aviso = admin_services.registrar_novo_cliente(
            banco,
            nome="Tenant Mobile",
            cnpj="11222333000183",
            email_admin="tenant-mobile@empresa.test",
            plano=PlanoEmpresa.INTERMEDIARIO.value,
            admin_cliente_operating_model="mobile_single_operator",
        )

        assert empresa.admin_cliente_policy_json == {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": True,
        }
        resumo = summarize_tenant_admin_policy(empresa.admin_cliente_policy_json)
        assert resumo["mobile_primary"] is True
        assert resumo["contract_operational_user_limit"] == 1
        assert resumo["shared_mobile_operator_web_inspector_enabled"] is True
        admin_cliente = banco.scalar(select(Usuario).where(Usuario.email == "tenant-mobile@empresa.test"))
        assert admin_cliente is not None
        assert admin_cliente.allowed_portals == ("cliente", "inspetor", "revisor")


def test_registrar_novo_cliente_mobile_single_operator_permite_desligar_superficies_web(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "_disparar_email_boas_vindas",
        lambda *_args, **_kwargs: None,
    )

    with SessionLocal() as banco:
        empresa, _senha_temporaria, _aviso = admin_services.registrar_novo_cliente(
            banco,
            nome="Tenant Mobile Restrito",
            cnpj="11222333000184",
            email_admin="tenant-mobile-restrito@empresa.test",
            plano=PlanoEmpresa.INTERMEDIARIO.value,
            admin_cliente_operating_model="mobile_single_operator",
            admin_cliente_mobile_web_inspector_enabled="false",
            admin_cliente_mobile_web_review_enabled="false",
        )

        assert empresa.admin_cliente_policy_json == {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": False,
            "shared_mobile_operator_web_review_enabled": False,
        }
        resumo = summarize_tenant_admin_policy(empresa.admin_cliente_policy_json)
        assert resumo["shared_mobile_operator_surface_set"] == ["mobile"]
        admin_cliente = banco.scalar(
            select(Usuario).where(Usuario.email == "tenant-mobile-restrito@empresa.test")
        )
        assert admin_cliente is not None
        assert admin_cliente.allowed_portals == ("cliente", "inspetor")


def test_criar_usuario_empresa_aceita_portais_adicionais_dentro_da_regra_do_tenant(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        empresa = Empresa(
            nome_fantasia="Tenant Multiportal Operacional",
            cnpj="11222333000188",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
            admin_cliente_policy_json={
                "case_visibility_mode": "case_list",
                "case_action_mode": "case_actions",
                "operational_user_cross_portal_enabled": True,
                "operational_user_admin_portal_enabled": True,
            },
        )
        banco.add(empresa)
        banco.commit()
        empresa_id = int(empresa.id)

    with SessionLocal() as banco:
        usuario, _senha = admin_services.criar_usuario_empresa(
            banco,
            empresa_id=empresa_id,
            nome="Operador Multiportal",
            email="operador-multiportal@empresa.test",
            nivel_acesso=NivelAcesso.INSPETOR,
            allowed_portals=["revisor", "cliente"],
        )
        assert usuario.allowed_portals == ("inspetor", "revisor", "cliente")


def test_criar_usuario_empresa_rejeita_portal_fora_da_regra_do_tenant(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        empresa = Empresa(
            nome_fantasia="Tenant Sem Admin Operacional",
            cnpj="11222333000189",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
            admin_cliente_policy_json={
                "case_visibility_mode": "case_list",
                "case_action_mode": "case_actions",
                "operational_user_cross_portal_enabled": True,
                "operational_user_admin_portal_enabled": False,
            },
        )
        banco.add(empresa)
        banco.commit()
        empresa_id = int(empresa.id)

    with SessionLocal() as banco:
        with pytest.raises(ValueError, match="não permite conceder acesso"):
            admin_services.criar_usuario_empresa(
                banco,
                empresa_id=empresa_id,
                nome="Operador Restrito",
                email="operador-restrito@empresa.test",
                nivel_acesso=NivelAcesso.INSPETOR,
                allowed_portals=["cliente"],
            )


def test_criar_usuario_empresa_respeita_limite_do_plano(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        limite = banco.get(LimitePlano, PlanoEmpresa.ILIMITADO.value)
        assert limite is not None
        limite.usuarios_max = 3
        banco.commit()

    with SessionLocal() as banco:
        with pytest.raises(ValueError, match="Limite de usuários do plano atingido"):
            admin_services.criar_usuario_empresa(
                banco,
                empresa_id=ids["empresa_a"],
                nome="Novo Inspetor",
                email="novo-inspetor@empresa-a.test",
                nivel_acesso=NivelAcesso.INSPETOR,
            )


def test_criar_usuario_empresa_respeita_limite_operacional_do_pacote_mobile_single_operator(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        empresa = Empresa(
            nome_fantasia="Tenant Operador Único",
            cnpj="11222333000185",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
        )
        banco.add(empresa)
        banco.flush()
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": False,
        }
        banco.commit()
        empresa_id = int(empresa.id)

    with SessionLocal() as banco:
        admin_services.criar_usuario_empresa(
            banco,
            empresa_id=empresa_id,
            nome="Operador Único",
            email="operador-unico@empresa-a.test",
            nivel_acesso=NivelAcesso.INSPETOR,
        )
        banco.commit()

    with SessionLocal() as banco:
        with pytest.raises(
            ValueError,
            match="pacote mobile principal com operador único",
        ):
            admin_services.criar_usuario_empresa(
                banco,
                empresa_id=empresa_id,
                nome="Segundo Operador",
                email="segundo-operador@empresa-a.test",
                nivel_acesso=NivelAcesso.REVISOR,
                crea="CREA 9999",
            )


def test_resetar_senha_inspetor_revoga_sessoes_ativas(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    token = criar_sessao(ids["inspetor_a"], lembrar=True)

    with SessionLocal() as banco:
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["inspetor_a"]).count() == 1

    with SessionLocal() as banco:
        nova_senha = admin_services.resetar_senha_inspetor(banco, ids["inspetor_a"])
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        assert usuario.senha_temporaria_ativa is True
        assert usuario.tentativas_login == 0
        assert usuario.status_bloqueio is False
        assert verificar_senha(nova_senha, usuario.senha_hash) is True

    with SessionLocal() as banco:
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["inspetor_a"]).count() == 0

    assert token_esta_ativo(token) is False


def test_busca_clientes_suporta_filtros_combinados_ordenacao_e_paginacao(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    criar_sessao(ids["admin_cliente_a"], lembrar=True)

    with SessionLocal() as banco:
        empresa_c = Empresa(
            nome_fantasia="Empresa C",
            cnpj="32345678000190",
            plano_ativo=PlanoEmpresa.INTERMEDIARIO.value,
        )
        banco.add(empresa_c)
        banco.flush()
        banco.add(
            Usuario(
                empresa_id=empresa_c.id,
                nome_completo="Admin Cliente C",
                email="cliente@empresa-c.test",
                senha_hash="hash-nao-usado",
                nivel_acesso=NivelAcesso.ADMIN_CLIENTE.value,
                ativo=True,
            )
        )
        banco.commit()

    with SessionLocal() as banco:
        painel_filtrado = admin_services.buscar_todos_clientes(
            banco,
            filtro_nome="Empresa",
            filtro_plano=PlanoEmpresa.ILIMITADO.value,
            filtro_status="ativo",
            filtro_saude="ok",
            filtro_atividade="24h",
            ordenar_por="ultimo_acesso",
            direcao="desc",
            pagina=1,
            por_pagina=1,
        )
        assert painel_filtrado["totais"]["clientes_total"] == 1
        assert painel_filtrado["pagination"]["total_pages"] == 1
        assert [item["empresa_id"] for item in painel_filtrado["itens"]] == [ids["empresa_a"]]

    with SessionLocal() as banco:
        painel_paginado = admin_services.buscar_todos_clientes(
            banco,
            ordenar_por="nome",
            direcao="asc",
            pagina=1,
            por_pagina=5,
        )
        assert painel_paginado["pagination"]["page_size"] == 5
        assert painel_paginado["pagination"]["total_items"] >= 3
        assert painel_paginado["pagination"]["total_pages"] == 1
        assert len(painel_paginado["itens"]) >= 3
        nomes = [item["nome_fantasia"] for item in painel_paginado["itens"]]
        assert nomes == sorted(nomes)


def test_console_admin_ignora_tenant_plataforma_em_metricas_e_listagem(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        metricas = admin_services.buscar_metricas_ia_painel(banco)
        painel = admin_services.buscar_todos_clientes(banco, ordenar_por="nome", direcao="asc", pagina=1, por_pagina=20)

        assert metricas["qtd_clientes"] == 2
        assert all(int(cliente.id) != ids["empresa_plataforma"] for cliente in metricas["clientes"])
        assert all(item["empresa_id"] != ids["empresa_plataforma"] for item in painel["itens"])


def test_catalogo_de_familias_upsert_e_resumo_com_camadas_operacionais(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        familia = admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Inspeção de Caldeira",
            macro_categoria="NR13",
            descricao="Família de inspeção estruturada para caldeiras.",
            status_catalogo="publicado",
            technical_status="ready",
            schema_version=2,
            evidence_policy_json_text=json.dumps({"required": ["placa", "entorno"]}),
            review_policy_json_text=json.dumps({"mesa_required": True}),
            criado_por_id=ids["admin_a"],
        )
        modo = admin_services.upsert_modo_tecnico_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            mode_key="periodica",
            nome_exibicao="Periódica",
            descricao="Execução recorrente prevista na governança técnica.",
            criado_por_id=ids["admin_a"],
        )
        oferta = admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            offer_key="nr13_inspecao_caldeira_main",
            family_mode_key="periodica",
            nome_oferta="NR13 Premium · Caldeira",
            pacote_comercial="Premium",
            prazo_padrao_dias=5,
            lifecycle_status="active",
            showcase_enabled=True,
            material_real_status="calibrado",
            material_level="real_calibrated",
            escopo_comercial_text="- Inspeção em campo\n- Emissão final",
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Campo crítico",
            criado_por_id=ids["admin_a"],
        )
        calibracao = admin_services.upsert_calibracao_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            calibration_status="real_calibrated",
            reference_source="empresa_nr13_material_real",
            summary_of_adjustments="Ajuste de linguagem e campos do parecer.",
            criado_por_id=ids["admin_a"],
        )
        release = admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            allowed_modes=["periodica"],
            allowed_offers=["nr13_inspecao_caldeira_main"],
            allowed_templates=["nr13"],
            allowed_variants=["catalog:nr13_inspecao_caldeira:premium_campo"],
            default_template_code="nr13",
            criado_por_id=ids["admin_a"],
        )
        banco.commit()
        resumo = admin_services.resumir_catalogo_laudos_admin(banco)
        row = resumo["catalog_rows"][0]

        assert isinstance(familia, FamiliaLaudoCatalogo)
        assert isinstance(modo, ModoTecnicoFamiliaLaudo)
        assert isinstance(oferta, OfertaComercialFamiliaLaudo)
        assert isinstance(calibracao, CalibracaoFamiliaLaudo)
        assert isinstance(release, TenantFamilyReleaseLaudo)
        assert familia.technical_status == "ready"
        assert oferta.lifecycle_status == "active"

    with SessionLocal() as banco:
        resumo = admin_services.resumir_catalogo_laudos_admin(banco)
        row = resumo["catalog_rows"][0]
        assert resumo["total_familias"] == 1
        assert resumo["total_publicadas"] == 1
        assert resumo["total_ofertas_comerciais"] == 1
        assert resumo["total_ofertas_ativas"] == 1
        assert resumo["total_familias_calibradas"] == 1
        assert resumo["total_variantes_comerciais"] == 1
        assert row["mode_count"] == 1
        assert row["commercial_status"]["key"] == "active"
        assert row["calibration_status"]["key"] == "real_calibrated"
        assert row["readiness"]["key"] == "calibrated"


def test_catalogo_deriva_prontidao_por_camadas() -> None:
    assert admin_services.derivar_prontidao_catalogo(
        technical_status="draft",
        has_template_seed=True,
        has_laudo_output_seed=True,
        offer_lifecycle_status="active",
        calibration_status="real_calibrated",
        active_release_count=1,
    ) == "technical_only"
    assert admin_services.derivar_prontidao_catalogo(
        technical_status="ready",
        has_template_seed=True,
        has_laudo_output_seed=True,
        offer_lifecycle_status="active",
        calibration_status="synthetic_only",
        active_release_count=0,
    ) == "partial"
    assert admin_services.derivar_prontidao_catalogo(
        technical_status="ready",
        has_template_seed=True,
        has_laudo_output_seed=True,
        offer_lifecycle_status="active",
        calibration_status="partial_real",
        active_release_count=1,
    ) == "sellable"
    assert admin_services.derivar_prontidao_catalogo(
        technical_status="ready",
        has_template_seed=True,
        has_laudo_output_seed=True,
        offer_lifecycle_status="active",
        calibration_status="real_calibrated",
        active_release_count=1,
    ) == "calibrated"


def test_signatario_governado_do_tenant_salva_escopo_e_aparece_no_detalhe(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

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
        registro = admin_services.upsert_signatario_governado_laudo(
            banco,
            tenant_id=ids["empresa_a"],
            nome="Eng. Tariel",
            funcao="Responsável técnico",
            registro_profissional="CREA 1234",
            valid_until="2026-12-31",
            allowed_family_keys=["nr13_inspecao_caldeira"],
            ativo=True,
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

        persisted = banco.scalar(
            select(SignatarioGovernadoLaudo).where(
                SignatarioGovernadoLaudo.id == int(registro.id)
            )
        )
        detalhe = admin_services.buscar_detalhe_cliente(banco, ids["empresa_a"])

    assert persisted is not None
    assert persisted.allowed_family_keys_json == ["nr13_inspecao_caldeira"]
    assert detalhe is not None
    assert detalhe["signatarios_governados"][0]["nome"] == "Eng. Tariel"
    assert (
        detalhe["signatarios_governados"][0]["family_scope"][0]["family_key"]
        == "nr13_inspecao_caldeira"
    )


def test_catalogo_filtros_principais_respeitam_prontidao_e_lifecycle(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            nome_exibicao="NR10 · Instalações Elétricas",
            macro_categoria="NR10",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            nome_oferta="NR10 Prime",
            lifecycle_status="active",
            material_level="partial",
            material_real_status="parcial",
            variantes_comerciais_text="prime_site | Prime site | rti | Site elétrico",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr10_inspecao_instalacoes_eletricas",
            release_status="active",
            allowed_templates=["rti"],
            allowed_variants=["catalog:nr10_inspecao_instalacoes_eletricas:prime_site"],
            criado_por_id=ids["admin_a"],
        )

        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="rascunho",
            technical_status="draft",
            criado_por_id=ids["admin_a"],
        )

        resumo = admin_services.resumir_catalogo_laudos_admin(
            banco,
            filtro_macro_categoria="NR10",
            filtro_status_comercial="active",
            filtro_liberacao="active",
        )

        assert len(resumo["catalog_rows"]) == 1
        assert resumo["catalog_rows"][0]["family_key"] == "nr10_inspecao_instalacoes_eletricas"


def test_catalogo_detalhe_da_familia_separa_camadas_e_legado_fallback(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
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
            nome_oferta="NR35 Prime",
            lifecycle_status="active",
            material_real_status="sintetico",
            variantes_comerciais_text="prime_site | Prime site | nr35_linha_vida | Linha de vida",
            criado_por_id=ids["admin_a"],
        )
        detalhe = admin_services.buscar_catalogo_familia_admin(banco, "nr35_inspecao_linha_de_vida")

        assert detalhe is not None
        assert detalhe["family"]["family_key"] == "nr35_inspecao_linha_de_vida"
        assert detalhe["offer"]["offer_name"] == "NR35 Prime"
        assert detalhe["calibration"]["status"]["key"] == "synthetic_only"
        assert detalhe["tenant_releases"] == []


def test_catalogo_rollup_expoe_biblioteca_premium_e_material_real(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    family_key = "nr13_inspecao_caldeira"

    _bootstrap_catalog_repo_assets(tmp_path, family_key)
    monkeypatch.setattr(admin_services, "_repo_root_dir", lambda: tmp_path)

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key=family_key,
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key=family_key,
            nome_oferta="NR13 Premium · Caldeira",
            lifecycle_status="active",
            material_real_status="calibrado",
            material_level="real_calibrated",
            release_channel="general_release",
            bundle_key="nr13_core",
            bundle_label="NR13 Core",
            included_features_text='["mobile_review", "official_issue"]',
            template_default_code="nr13_premium",
            variantes_comerciais_text="premium | Premium | nr13 | Campo premium",
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

        resumo = admin_services.resumir_catalogo_laudos_admin(banco)

    biblioteca = resumo["template_library_rollup"]
    material_real = resumo["material_real_rollup"]
    escala = resumo["commercial_scale_rollup"]

    assert biblioteca["registry_version"] == 3
    assert biblioteca["template_count"] == 1
    assert biblioteca["ready_template_count"] == 1
    assert biblioteca["demonstration_ready_count"] == 1
    assert biblioteca["families_with_full_artifacts"] == 1
    assert biblioteca["families_with_template_default"] == 1
    assert biblioteca["sellable_family_count"] == 1
    assert biblioteca["registry_path"] == "docs/master_templates/library_registry.json"
    assert biblioteca["templates"][0]["artifact_path"] == "docs/master_templates/inspection_conformity.template_master.json"

    assert material_real["workspace_count"] == 1
    assert material_real["validated_workspace_count"] == 1
    assert material_real["reference_package_ready_count"] == 1
    assert material_real["with_briefing_count"] == 1
    assert material_real["highlights"][0]["family_key"] == family_key
    assert material_real["highlights"][0]["workspace_path"] == (
        f"docs/portfolio_empresa_nr13_material_real/{family_key}"
    )
    assert escala["bundle_count"] >= 1
    assert escala["bundle_highlights"][0]["bundle_key"] == "nr13_core"
    assert any(item["channel"]["key"] == "general_release" and item["count"] >= 1 for item in escala["release_channels"])
    assert any(item["feature"]["key"] == "mobile_review" for item in escala["feature_highlights"])
    prioridade = resumo["material_real_priority_rollup"]
    modos_prioridade = {
        item["status"]["key"]: item["count"]
        for item in prioridade["priority_modes"]
    }
    assert modos_prioridade["resolved"] == 1
    assert prioridade["highlights"][0]["family_key"] == family_key
    assert "Manter linguagem e PDF" in prioridade["highlights"][0]["next_action"]


def test_catalogo_macro_categorias_ordena_nr_em_ordem_numerica(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_ancoragem",
            nome_exibicao="NR35 · Ancoragem",
            macro_categoria="NR35",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr4_sesmt",
            nome_exibicao="NR4 · SESMT",
            macro_categoria="NR4",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr10_instalacoes_eletricas",
            nome_exibicao="NR10 · Instalações elétricas",
            macro_categoria="NR10",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )

        resumo = admin_services.resumir_catalogo_laudos_admin(banco)

    assert resumo["macro_categorias"] == ["NR4", "NR10", "NR35"]


def test_catalogo_detalhe_expoe_biblioteca_documental_e_workspace_material_real(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    family_key = "nr35_inspecao_linha_de_vida"

    _bootstrap_catalog_repo_assets(tmp_path, family_key, create_full_chain=False)
    monkeypatch.setattr(admin_services, "_repo_root_dir", lambda: tmp_path)

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key=family_key,
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key=family_key,
            nome_oferta="NR35 Premium · Linha de Vida",
            lifecycle_status="active",
            template_default_code="nr35_prime",
            variantes_comerciais_text="prime | Prime | nr35 | Linha de vida",
            criado_por_id=ids["admin_a"],
        )

        detalhe = admin_services.buscar_catalogo_familia_admin(banco, family_key)

    assert detalhe is not None
    assert detalhe["template_library"]["registry_path"] == "docs/master_templates/library_registry.json"
    assert detalhe["template_library"]["has_full_canonical_artifact_chain"] is False
    assert "Modelo base" in detalhe["template_library"]["missing_artifacts"]
    assert "Documento base" in detalhe["template_library"]["missing_artifacts"]
    assert detalhe["template_library"]["template_default_code"] == "nr35_prime"
    assert detalhe["template_library"]["registry_templates"][0]["label"] == "Inspection Conformity Premium"

    workspace = detalhe["material_real_workspace"]
    assert workspace is not None
    assert workspace["status"]["key"] == "baseline_sintetica_externa_validada"
    assert workspace["has_reference_manifest"] is True
    assert workspace["has_reference_bundle"] is True
    assert workspace["workspace_path"] == f"docs/portfolio_empresa_nr13_material_real/{family_key}"
    assert workspace["proximo_passo"] == "Promover pacote de referência."
    assert workspace["execution_track"]["phase"]["key"] == "template_refinement"
    assert workspace["worklist"]["task_count"] >= 2
    assert workspace["worklist"]["done_count"] >= 1
    assert detalhe["material_real_priority"]["status"]["key"] == "immediate"
    assert detalhe["document_preview"]["status"]["key"] == "bootstrap"
    assert detalhe["document_preview"]["required_slot_count"] == 0
    assert "QR/hash público" in detalhe["document_preview"]["premium_features"]
    assert detalhe["variant_library"]["variant_count"] == 1
    assert detalhe["variant_library"]["variants"][0]["selection_token"] == (
        f"catalog:{family_key}:prime"
    )
    assert detalhe["variant_library"]["variants"][0]["status"]["key"] == "template_mapped"
    assert detalhe["template_refinement_target"]["master_template_id"] == "inspection_conformity"
    assert detalhe["template_refinement_target"]["status"]["key"] == "refinement_due"


def test_catalogo_constroi_fila_de_calibracao_e_pressao_por_template(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _bootstrap_catalog_repo_assets(tmp_path, "nr13_inspecao_caldeira")
    _bootstrap_catalog_repo_assets(
        tmp_path,
        "nr35_inspecao_linha_de_vida",
        material_status="aguardando_material_real",
        create_full_chain=False,
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

        resumo = admin_services.resumir_catalogo_laudos_admin(banco)

    fila = resumo["calibration_queue_rollup"]
    assert fila["queue_count"] == 2
    assert fila["highlights"][0]["family_key"] == "nr13_inspecao_caldeira"
    assert fila["highlights"][0]["template_refinement_target"]["master_template_id"] == "integrity_specialized"
    assert fila["highlights"][0]["template_refinement_target"]["status"]["key"] == "registry_gap"
    assert fila["highlights"][0]["worklist_pending_count"] >= 1
    assert fila["highlights"][0]["execution_track"]["phase"]["key"] == "template_refinement"
    assert fila["template_targets"][0]["master_template_id"] == "integrity_specialized"
    assert fila["template_targets"][1]["master_template_id"] == "inspection_conformity"


def test_catalogo_governanca_review_e_release_structured(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
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
            default_review_mode="mobile_review_allowed",
            max_review_mode="mobile_autonomous",
            requires_family_lock=True,
            block_on_missing_required_evidence=True,
            requires_release_active=True,
            mobile_review_allowed_plans_text='["intermediario", "ilimitado"]',
            mobile_autonomous_allowed_plans_text='["ilimitado"]',
            red_flags_json_text=json.dumps(
                [
                    {
                        "code": "placa_ausente",
                        "title": "Placa ausente",
                        "message": "Sem placa identificada o caso deve subir para revisão.",
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
            nome_oferta="NR35 Prime",
            lifecycle_status="active",
            material_real_status="parcial",
            material_level="partial",
            release_channel="limited_release",
            bundle_key="nr35_altura",
            bundle_label="NR35 Altura",
            bundle_summary="Bundle premium de trabalho em altura.",
            bundle_audience="Operação em altura",
            bundle_highlights_text='["Linha de vida", "Checklist de campo"]',
            included_features_text='["mobile_review", "public_verification"]',
            entitlement_monthly_issues=120,
            entitlement_max_inspectors=6,
            variantes_comerciais_text="prime_site | Prime site | nr35_linha_vida | Linha de vida",
            criado_por_id=ids["admin_a"],
        )
        release = admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr35_inspecao_linha_de_vida",
            release_status="active",
            allowed_templates=["nr35_linha_vida"],
            allowed_variants=["catalog:nr35_inspecao_linha_de_vida:prime_site"],
            force_review_mode="mesa_required",
            max_review_mode="mobile_review_allowed",
            mobile_review_override="allow",
            mobile_autonomous_override="deny",
            release_channel_override="pilot",
            included_features_text='["priority_support"]',
            entitlement_monthly_issues=80,
            entitlement_max_reviewers=2,
            criado_por_id=ids["admin_a"],
        )
        detalhe = admin_services.buscar_catalogo_familia_admin(
            banco,
            "nr35_inspecao_linha_de_vida",
        )

        assert release.governance_policy_json == {
            "force_review_mode": "mesa_required",
            "max_review_mode": "mobile_review_allowed",
            "mobile_review_override": True,
            "mobile_autonomous_override": False,
            "release_channel_override": "pilot",
            "contract_entitlements": {
                "included_features": ["priority_support"],
                "limits": {"monthly_issues": 80, "max_reviewers": 2},
            },
        }
        assert detalhe is not None
        assert detalhe["review_governance"]["default_review_mode"]["key"] == "mobile_review_allowed"
        assert detalhe["review_governance"]["red_flags_count"] == 1
        assert detalhe["offer"]["release_channel"]["key"] == "limited_release"
        assert detalhe["offer"]["commercial_bundle"]["bundle_key"] == "nr35_altura"
        assert detalhe["offer"]["contract_entitlements"]["has_data"] is True
        assert detalhe["tenant_releases"][0]["governance"]["force_review_mode"]["key"] == "mesa_required"
        assert detalhe["tenant_releases"][0]["governance"]["mobile_review_override"]["key"] == "allow"
        assert detalhe["tenant_releases"][0]["effective_release_channel"]["key"] == "pilot"
        assert detalhe["tenant_releases"][0]["contract_entitlements"]["has_data"] is True


def test_admin_rollup_de_governanca_agrega_catalogo_e_dashboard(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa_a = banco.get(Empresa, ids["empresa_a"])
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_a is not None
        assert empresa_b is not None
        empresa_a.plano_ativo = PlanoEmpresa.INTERMEDIARIO.value
        empresa_b.plano_ativo = PlanoEmpresa.ILIMITADO.value

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

        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            nome_exibicao="NR10 · Instalações Elétricas",
            macro_categoria="NR10",
            status_catalogo="publicado",
            technical_status="ready",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_governanca_review_familia(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            default_review_mode="mobile_review_allowed",
            max_review_mode="mobile_review_allowed",
            mobile_review_allowed_plans_text='["ilimitado"]',
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            nome_oferta="NR10 Prime · Instalações Elétricas",
            lifecycle_status="active",
            variantes_comerciais_text="campo | Campo | nr10 | Campo",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr10_inspecao_instalacoes_eletricas",
            release_status="active",
            force_review_mode="mesa_required",
            criado_por_id=ids["admin_a"],
        )

        resumo = admin_services.resumir_catalogo_laudos_admin(banco)
        metricas = admin_services.buscar_metricas_ia_painel(banco)

        rollup_catalogo = resumo["governance_rollup"]
        modos_ativos = {
            item["mode"]["key"]: int(item["count"])
            for item in rollup_catalogo["effective_release_modes"]
        }
        strictest_tenants = {
            item["mode"]["key"]: int(item["count"])
            for item in rollup_catalogo["tenant_strictest_modes"]
        }
        defaults_familia = {
            item["mode"]["key"]: int(item["count"])
            for item in rollup_catalogo["family_default_modes"]
        }

        assert rollup_catalogo["active_release_count"] == 3
        assert rollup_catalogo["tenant_count"] == 2
        assert modos_ativos == {
            "mesa_required": 1,
            "mobile_review_allowed": 1,
            "mobile_autonomous": 1,
        }
        assert strictest_tenants == {
            "mesa_required": 1,
            "mobile_review_allowed": 0,
            "mobile_autonomous": 1,
        }
        assert defaults_familia == {
            "mesa_required": 0,
            "mobile_review_allowed": 2,
            "mobile_autonomous": 1,
        }
        assert rollup_catalogo["families_with_red_flags_count"] == 1
        assert {item["tenant_label"] for item in rollup_catalogo["tenant_highlights"]} == {
            "Empresa A",
            "Empresa B",
        }
        assert {
            item["family_key"]
            for item in rollup_catalogo["family_highlights"]
        } == {
            "nr13_inspecao_caldeira",
            "nr35_inspecao_linha_de_vida",
            "nr10_inspecao_instalacoes_eletricas",
        }

        rollup_painel = metricas["governance_rollup"]
        assert rollup_painel["active_release_count"] == 3
        assert {
            item["mode"]["key"]: int(item["count"])
            for item in rollup_painel["tenant_strictest_modes"]
        } == strictest_tenants


def test_catalogo_importa_family_schema_canonico_quando_disponivel(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    family_dir = tmp_path / "family_schemas"
    family_dir.mkdir()
    (family_dir / "nr10_inspecao_instalacoes_eletricas.json").write_text(
        json.dumps(
            {
                "family_key": "nr10_inspecao_instalacoes_eletricas",
                "nome_exibicao": "NR10 · Instalações Elétricas",
                "macro_categoria": "NR10",
                "descricao": "Schema oficial de instalações elétricas.",
                "schema_version": 3,
                "evidence_policy": {"required": ["painel", "placa"]},
                "review_policy": {"mesa_required": True},
                "output_schema_seed": {"sections": ["sumario", "parecer"]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(admin_services, "_family_schemas_dir", lambda: family_dir)

    with SessionLocal() as banco:
        familia = admin_services.importar_familia_canonica_para_catalogo(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )

        assert familia.family_key == "nr10_inspecao_instalacoes_eletricas"
        assert familia.nome_exibicao == "NR10 · Instalações Elétricas"
        assert familia.schema_version == 3
        assert familia.evidence_policy_json["required"] == ["painel", "placa"]


def test_portfolio_catalogo_empresa_sincroniza_ativacoes_do_tenant(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
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
            nome_oferta="NR13 Premium · Caldeira",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Campo crítico",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_governanca_review_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            default_review_mode="mobile_review_allowed",
            requires_release_active=True,
            red_flags_json_text=json.dumps(
                [
                    {
                        "code": "placa_ausente",
                        "title": "Placa ausente",
                        "message": "Sem placa o caso sobe para Mesa.",
                        "severity": "high",
                        "blocking": True,
                    }
                ],
                ensure_ascii=False,
            ),
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            nome_exibicao="NR10 · Instalações Elétricas",
            macro_categoria="NR10",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr10_inspecao_instalacoes_eletricas",
            nome_oferta="NR10 Prime · Instalações Elétricas",
            pacote_comercial="Prime",
            ativo_comercial=True,
            variantes_comerciais_text="campo | Prime campo | nr10_prime | Elétrica crítica",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            allowed_templates=["nr13"],
            allowed_variants=["catalog:nr13_inspecao_caldeira:premium_campo"],
            force_review_mode="mesa_required",
            mobile_review_override="allow",
            criado_por_id=ids["admin_a"],
        )

        resultado = admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[
                "catalog:nr13_inspecao_caldeira:premium_campo",
                "catalog:nr10_inspecao_instalacoes_eletricas:campo",
            ],
            admin_id=ids["admin_a"],
        )
        snapshot = admin_services.resumir_portfolio_catalogo_empresa(banco, empresa_id=ids["empresa_a"])
        ativacoes = list(
            banco.scalars(
                select(AtivacaoCatalogoEmpresaLaudo)
                .where(AtivacaoCatalogoEmpresaLaudo.empresa_id == ids["empresa_a"])
                .order_by(AtivacaoCatalogoEmpresaLaudo.family_key.asc())
            ).all()
        )

        assert resultado["selected_count"] == 2
        assert snapshot["governed_mode"] is True
        assert snapshot["active_activation_count"] == 2
        assert len(ativacoes) == 2
        assert {item.runtime_template_code for item in ativacoes} == {"nr13", "rti"}
        familia_nr13 = next(
            item for item in snapshot["families"] if item["family_key"] == "nr13_inspecao_caldeira"
        )
        assert familia_nr13["review_governance"]["default_review_mode"]["key"] == "mobile_review_allowed"
        assert familia_nr13["review_governance"]["red_flags_count"] == 1
        assert familia_nr13["tenant_release"]["release_status"]["key"] == "active"
        assert familia_nr13["tenant_release"]["force_review_mode"]["key"] == "mesa_required"
        assert familia_nr13["tenant_release"]["mobile_review_override"]["key"] == "allow"

        resultado_limpeza = admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[],
            admin_id=ids["admin_a"],
        )
        snapshot_limpo = admin_services.resumir_portfolio_catalogo_empresa(banco, empresa_id=ids["empresa_a"])

        assert resultado_limpeza["selected_count"] == 0
        assert snapshot_limpo["governed_mode"] is True
        assert snapshot_limpo["catalog_state"] == "managed_empty"
        assert snapshot_limpo["active_activation_count"] == 0


def test_autenticar_identidade_admin_vincula_subject_e_recusa_mismatch(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        admin.portal_admin_autorizado = True
        admin.admin_identity_status = "active"
        banco.commit()

    with SessionLocal() as banco:
        resultado = admin_services.autenticar_identidade_admin(
            banco,
            provider="google",
            email="admin@empresa-a.test",
            subject="google-sub-xyz",
        )
        assert resultado.authorized is True
        assert resultado.user is not None
        banco.commit()

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        assert admin.admin_identity_provider == "google"
        assert admin.admin_identity_subject == "google-sub-xyz"

        mismatch = admin_services.autenticar_identidade_admin(
            banco,
            provider="google",
            email="admin@empresa-a.test",
            subject="google-sub-diferente",
        )
        assert mismatch.authorized is False
        assert mismatch.reason == "subject_mismatch"


def test_autenticar_identidade_admin_exige_conta_platform_ativa_e_metodo_habilitado(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        admin.account_status = "blocked"
        banco.commit()

    with SessionLocal() as banco:
        bloqueado = admin_services.autenticar_identidade_admin(
            banco,
            provider="google",
            email="admin@empresa-a.test",
            subject="google-sub-xyz",
        )
        assert bloqueado.authorized is False
        assert bloqueado.reason == "account_not_platform_active"

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        admin.account_status = "active"
        admin.can_google_login = False
        banco.commit()

    with SessionLocal() as banco:
        sem_google = admin_services.autenticar_identidade_admin(
            banco,
            provider="google",
            email="admin@empresa-a.test",
            subject="google-sub-xyz",
        )
        assert sem_google.authorized is False
        assert sem_google.reason == "identity_method_disabled"


def test_alternar_bloqueio_invalida_sessoes_e_preserva_motivo_no_desbloqueio(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    criar_sessao(ids["inspetor_a"], lembrar=True)
    criar_sessao(ids["admin_cliente_a"], lembrar=True)

    with SessionLocal() as banco:
        with pytest.raises(ValueError, match="Informe o motivo do bloqueio"):
            admin_services.alternar_bloqueio(banco, ids["empresa_a"])

    with SessionLocal() as banco:
        resultado = admin_services.alternar_bloqueio(
            banco,
            ids["empresa_a"],
            motivo="Inadimplência operacional",
        )
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert resultado["blocked"] is True
        assert resultado["reason"] == "Inadimplência operacional"
        assert resultado["sessions_invalidated"] >= 2
        assert empresa is not None
        assert bool(empresa.status_bloqueio) is True
        assert empresa.motivo_bloqueio == "Inadimplência operacional"

    with SessionLocal() as banco:
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id.in_([ids["inspetor_a"], ids["admin_cliente_a"]])).count() == 0

    with SessionLocal() as banco:
        with pytest.raises(ValueError, match="Confirme o desbloqueio"):
            admin_services.alternar_bloqueio(
                banco,
                ids["empresa_a"],
                confirmar_desbloqueio=False,
            )

    with SessionLocal() as banco:
        resultado = admin_services.alternar_bloqueio(
            banco,
            ids["empresa_a"],
            confirmar_desbloqueio=True,
        )
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert resultado["blocked"] is False
        assert resultado["reason"] == "Inadimplência operacional"
        assert empresa is not None
        assert bool(empresa.status_bloqueio) is False
        assert empresa.motivo_bloqueio == "Inadimplência operacional"


def test_alternar_bloqueio_preserva_sessao_do_operador_global_e_invalida_so_portais_do_tenant(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    token_admin = criar_sessao(ids["admin_a"], lembrar=True)
    token_inspetor = criar_sessao(ids["inspetor_a"], lembrar=True)
    token_revisor = criar_sessao(ids["revisor_a"], lembrar=True)
    token_admin_cliente = criar_sessao(ids["admin_cliente_a"], lembrar=True)

    with SessionLocal() as banco:
        resultado = admin_services.alternar_bloqueio(
            banco,
            ids["empresa_a"],
            motivo="Risco operacional controlado",
        )
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert resultado["blocked"] is True
        assert resultado["sessions_invalidated"] == 3
        assert empresa is not None
        assert bool(empresa.status_bloqueio) is True

    with SessionLocal() as banco:
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["admin_a"]).count() == 1
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["inspetor_a"]).count() == 0
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["revisor_a"]).count() == 0
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["admin_cliente_a"]).count() == 0

    assert token_esta_ativo(token_admin) is True
    assert token_esta_ativo(token_inspetor) is False
    assert token_esta_ativo(token_revisor) is False
    assert token_esta_ativo(token_admin_cliente) is False


def test_alterar_plano_retorna_preview_de_impacto(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        preview = admin_services.alterar_plano(
            banco,
            ids["empresa_a"],
            PlanoEmpresa.INTERMEDIARIO.value,
        )
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert preview["plano_atual"] == PlanoEmpresa.ILIMITADO.value
        assert preview["plano_novo"] == PlanoEmpresa.INTERMEDIARIO.value
        assert "impacto" in preview
        assert "usuarios_max" in preview["impacto"]
        assert empresa is not None
        assert empresa.plano_ativo == PlanoEmpresa.INTERMEDIARIO.value


def test_forcar_troca_senha_usuario_empresa_revoga_sessao_sem_expor_senha(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    token = criar_sessao(ids["admin_cliente_a"], lembrar=True)

    with SessionLocal() as banco:
        usuario = admin_services.forcar_troca_senha_usuario_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["admin_cliente_a"],
        )
        assert int(usuario.id) == ids["admin_cliente_a"]
        assert usuario.senha_temporaria_ativa is True
        assert usuario.status_bloqueio is False
        assert usuario.tentativas_login == 0

    with SessionLocal() as banco:
        assert banco.query(SessaoAtiva).filter(SessaoAtiva.usuario_id == ids["admin_cliente_a"]).count() == 0

    assert token_esta_ativo(token) is False


def test_apply_platform_settings_update_persiste_configuracoes_e_auditoria(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        resultado = admin_services.apply_platform_settings_update(
            banco,
            actor_user=admin,
            group_key="support",
            reason="Incidente controlado com trilha reforçada",
            updates={
                "support_exceptional_mode": "incident_controlled",
                "support_exceptional_approval_required": True,
                "support_exceptional_justification_required": True,
                "support_exceptional_max_duration_minutes": 180,
                "support_exceptional_scope_level": "tenant_diagnostic",
            },
        )
        banco.commit()

        assert resultado["group"] == "support"
        assert {item["key"] for item in resultado["changes"]} == {
            "support_exceptional_mode",
            "support_exceptional_max_duration_minutes",
            "support_exceptional_scope_level",
        }

    with SessionLocal() as banco:
        modo = banco.get(ConfiguracaoPlataforma, "support_exceptional_mode")
        duracao = banco.get(ConfiguracaoPlataforma, "support_exceptional_max_duration_minutes")
        auditoria = banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_plataforma"],
                RegistroAuditoriaEmpresa.acao == "platform_setting_updated",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
        ).first()

        console = admin_services.build_admin_platform_settings_console(banco)
        section = next(item for item in console["sections"] if item["key"] == "support")
        modo_item = next(item for item in section["items"] if item["key"] == "support_exceptional_mode")

        assert modo is not None
        assert modo.valor_json == "incident_controlled"
        assert duracao is not None
        assert int(duracao.valor_json) == 180
        assert auditoria is not None
        assert auditoria.payload_json["group"] == "support"
        assert auditoria.payload_json["reason"] == "Incidente controlado com trilha reforçada"
        assert modo_item["value_label"] == "Incidente controlado"


def test_review_ui_canonical_rejeita_valor_fora_do_fluxo_ssr(ambiente_critico, monkeypatch: pytest.MonkeyPatch) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.delenv("REVIEW_UI_CANONICAL", raising=False)
    monkeypatch.delenv("TARIEL_REVIEW_DESK_PRIMARY_SURFACE", raising=False)

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        with pytest.raises(ValueError, match="Escolha uma UI canônica válida para a revisão."):
            admin_services.apply_platform_settings_update(
                banco,
                actor_user=admin,
                group_key="rollout",
                reason="Tentativa de reabrir UI paralela deve ser rejeitada",
                updates={"review_ui_canonical": "invalido"},
            )

    assert panel_rollout.get_review_panel_primary_surface() == "ssr"


def test_console_admin_expoe_runtime_item_do_report_pack_rollout(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setenv("TARIEL_V2_REPORT_PACK_ROLLOUT_OBSERVABILITY", "1")

    with SessionLocal() as banco:
        console = admin_services.build_admin_platform_settings_console(banco)

    rollout_section = next(item for item in console["sections"] if item["key"] == "rollout")
    report_pack_item = next(
        item
        for item in rollout_section["items"]
        if item.get("technical_path") == "/admin/api/report-pack-rollout/summary"
    )

    assert report_pack_item["title"] == "Observabilidade do report pack"
    assert report_pack_item["value_label"] == "Habilitada"
    assert report_pack_item["scope_label"] == "Documento e rollout"


def test_console_admin_renderiza_descritores_runtime_de_documento_e_observabilidade(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "build_document_runtime_descriptors",
        lambda: [
            {
                "title": "Documento sintético",
                "description": "Resumo runtime sintético.",
                "value_label": "Ativo",
                "status_tone_key": "warning",
                "source_kind": "environment",
                "scope_label": "Documento",
                "technical_path": "/admin/api/documento-sintetico",
            }
        ],
    )
    monkeypatch.setattr(
        admin_services,
        "build_observability_runtime_descriptors",
        lambda _privacy: [
            {
                "title": "Observabilidade sintética",
                "description": "Resumo runtime sintético.",
                "value_label": "30 dias",
                "status_tone_key": "neutral",
                "source_kind": "environment",
                "scope_label": "Observabilidade",
            }
        ],
    )

    with SessionLocal() as banco:
        console = admin_services.build_admin_platform_settings_console(banco)

    document_section = next(item for item in console["sections"] if item["key"] == "document")
    observability_section = next(
        item for item in console["sections"] if item["key"] == "observability"
    )

    assert document_section["items"][0]["technical_path"] == "/admin/api/documento-sintetico"
    assert document_section["items"][0]["status_tone"] == "warning"
    assert observability_section["items"][0]["value_label"] == "30 dias"
    assert observability_section["items"][0]["source_label"] == "Ambiente"


def test_console_admin_renderiza_descritores_runtime_de_acesso(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "build_access_runtime_descriptors",
        lambda *, operator_count: [
            {
                "title": "Acesso sintético",
                "description": "Resumo runtime sintético.",
                "value_label": str(operator_count),
                "status_tone_key": "positive",
                "source_kind": "environment",
                "scope_label": "Somente Admin-CEO",
                "reason": "Gateway configurado.",
                "technical_path": "/admin/api/acesso-sintetico",
            },
            {
                "title": "Operadores sintéticos",
                "description": "Resumo runtime sintético.",
                "value_label": str(operator_count),
                "status_tone_key": "neutral",
                "source_kind": "runtime",
                "scope_label": "Somente Admin-CEO",
            },
        ],
    )

    with SessionLocal() as banco:
        console = admin_services.build_admin_platform_settings_console(banco)

    access_section = next(item for item in console["sections"] if item["key"] == "access")

    assert access_section["items"][0]["technical_path"] == "/admin/api/acesso-sintetico"
    assert access_section["items"][0]["reason"] == "Gateway configurado."
    assert access_section["items"][0]["source_label"] == "Ambiente"
    assert access_section["items"][2]["value_label"] == access_section["items"][0]["value_label"]
    assert access_section["items"][2]["source_label"] == "Runtime"


def test_console_admin_consume_builder_de_sections(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "build_platform_settings_console_sections",
        lambda **_kwargs: [
            {
                "key": "synthetic",
                "title": "Synthetic",
                "description": "Synthetic section.",
                "badge": "Test",
                "items": [{"title": "Synthetic item"}],
            }
        ],
    )

    with SessionLocal() as banco:
        console = admin_services.build_admin_platform_settings_console(banco)

    assert console["sections"] == [
        {
            "key": "synthetic",
            "title": "Synthetic",
            "description": "Synthetic section.",
            "badge": "Test",
            "items": [{"title": "Synthetic item"}],
        }
    ]


def test_console_admin_consume_builder_de_summary_cards(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "build_platform_settings_console_overview",
        lambda **_kwargs: [
            {
                "label": "Synthetic",
                "value": "42",
                "hint": "Synthetic card.",
            }
        ],
    )

    with SessionLocal() as banco:
        console = admin_services.build_admin_platform_settings_console(banco)

    assert console["summary_cards"] == [
        {
            "label": "Synthetic",
            "value": "42",
            "hint": "Synthetic card.",
        }
    ]


def test_console_admin_consume_builder_de_setting_descriptors(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]

    monkeypatch.setattr(
        admin_services,
        "build_access_setting_descriptors",
        lambda: [
            {
                "key": "admin_reauth_max_age_minutes",
                "title": "Janela sintética",
                "description": "Descrição sintética.",
            }
        ],
    )
    monkeypatch.setattr(
        admin_services,
        "build_support_setting_descriptors",
        lambda: [
            {
                "key": "support_exceptional_mode",
                "title": "Modo sintético",
                "description": "Descrição sintética.",
            }
        ],
    )
    monkeypatch.setattr(
        admin_services,
        "build_rollout_setting_descriptors",
        lambda: [
            {
                "key": "review_ui_canonical",
                "title": "Rollout sintético",
                "description": "Descrição sintética.",
            }
        ],
    )
    monkeypatch.setattr(
        admin_services,
        "build_defaults_setting_descriptors",
        lambda: [
            {
                "key": "default_new_tenant_plan",
                "title": "Default sintético",
                "description": "Descrição sintética.",
            }
        ],
    )

    with SessionLocal() as banco:
        console = admin_services.build_admin_platform_settings_console(banco)

    access_section = next(item for item in console["sections"] if item["key"] == "access")
    support_section = next(item for item in console["sections"] if item["key"] == "support")
    rollout_section = next(item for item in console["sections"] if item["key"] == "rollout")
    defaults_section = next(item for item in console["sections"] if item["key"] == "defaults")

    assert access_section["items"][1]["title"] == "Janela sintética"
    assert support_section["items"][0]["title"] == "Modo sintético"
    assert rollout_section["items"][0]["title"] == "Rollout sintético"
    assert defaults_section["items"][0]["title"] == "Default sintético"


def test_janela_reauth_persistida_sobrescreve_fallback_do_admin(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin = banco.get(Usuario, ids["admin_a"])
        assert admin is not None
        admin_services.apply_platform_settings_update(
            banco,
            actor_user=admin,
            group_key="access",
            reason="Janela operacional ampliada para mudança crítica",
            updates={"admin_reauth_max_age_minutes": 25},
        )
        banco.commit()

    assert get_admin_reauth_max_age_minutes() == 25
