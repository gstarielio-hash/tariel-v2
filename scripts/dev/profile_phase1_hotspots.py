#!/usr/bin/env python3
# ruff: noqa: E402
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = REPO_ROOT / "web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ["AMBIENTE"] = "dev"
os.environ["PERF_MODE"] = "1"
os.environ.setdefault("TARIEL_BACKEND_HOTSPOT_OBSERVABILITY", "1")

import app.domains.chat.routes as rotas_inspetor
import app.domains.revisor.routes as rotas_revisor
import app.shared.database as banco_dados
import app.shared.security as seguranca
import main
from app.core.perf_support import registrar_instrumentacao_sql, relatorio_perf, resetar_perf
from app.domains.admin.document_operations_summary import (
    build_document_operations_operational_summary,
)
from app.shared.backend_hotspot_metrics import (
    clear_backend_hotspot_metrics_for_tests,
    get_backend_hotspot_operational_summary,
)
from app.shared.database import (
    Base,
    Empresa,
    Laudo,
    LaudoRevisao,
    LimitePlano,
    MensagemLaudo,
    NivelAcesso,
    PlanoEmpresa,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from tests.regras_rotas_criticas_support import (
    ADMIN_TOTP_SECRET,
    SENHA_HASH_PADRAO,
    _criar_laudo,
    _criar_template_ativo,
    _login_admin,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
    _pdf_base_bytes_teste,
)

ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "observability_phase_acceptance"


def _prepare_environment() -> tuple[TestClient, sessionmaker[Session], dict[str, int], Callable[[], None]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    registrar_instrumentacao_sql(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as banco:
        banco.add(
            LimitePlano(
                plano=PlanoEmpresa.ILIMITADO.value,
                laudos_mes=None,
                usuarios_max=None,
                upload_doc=True,
                deep_research=True,
                integracoes_max=None,
                retencao_dias=None,
            )
        )

        empresa_plataforma = Empresa(
            nome_fantasia="Tariel.ia Platform",
            cnpj="99999999999999",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
            escopo_plataforma=True,
        )
        empresa_a = Empresa(
            nome_fantasia="Empresa A",
            cnpj="12345678000190",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
        )
        empresa_b = Empresa(
            nome_fantasia="Empresa B",
            cnpj="22345678000190",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
        )
        banco.add_all([empresa_plataforma, empresa_a, empresa_b])
        banco.flush()

        inspetor_a = Usuario(
            empresa_id=empresa_a.id,
            nome_completo="Inspetor A",
            email="inspetor@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.INSPETOR.value,
        )
        revisor_a = Usuario(
            empresa_id=empresa_a.id,
            nome_completo="Revisor A",
            email="revisor@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.REVISOR.value,
        )
        admin_a = Usuario(
            empresa_id=empresa_plataforma.id,
            nome_completo="Admin A",
            email="admin@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.DIRETORIA.value,
            account_scope="platform",
            account_status="active",
            allowed_portals_json=["admin"],
            platform_role="PLATFORM_OWNER",
            mfa_required=True,
            mfa_secret_b32=ADMIN_TOTP_SECRET,
            mfa_enrolled_at=banco_dados.agora_utc(),
            can_password_login=True,
            can_google_login=True,
            can_microsoft_login=True,
            portal_admin_autorizado=True,
            admin_identity_status="active",
        )
        admin_cliente_a = Usuario(
            empresa_id=empresa_a.id,
            nome_completo="Admin Cliente A",
            email="cliente@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.ADMIN_CLIENTE.value,
        )
        banco.add_all([inspetor_a, revisor_a, admin_a, admin_cliente_a])
        banco.commit()

        ids = {
            "empresa_plataforma": int(empresa_plataforma.id),
            "empresa_a": int(empresa_a.id),
            "empresa_b": int(empresa_b.id),
            "inspetor_a": int(inspetor_a.id),
            "revisor_a": int(revisor_a.id),
            "admin_a": int(admin_a.id),
            "admin_cliente_a": int(admin_cliente_a.id),
        }

    def override_obter_banco():
        banco = SessionLocal()
        try:
            yield banco
            if banco_dados.sessao_tem_mutacoes_pendentes(banco):
                banco.commit()
        except Exception:
            banco.rollback()
            raise
        finally:
            banco.close()

    main.app.dependency_overrides[banco_dados.obter_banco] = override_obter_banco

    sessao_local_banco_original = banco_dados.SessaoLocal
    sessao_local_seguranca_original = seguranca.SessaoLocal
    sessao_local_inspetor_original = rotas_inspetor.SessaoLocal
    sessao_local_revisor_original = rotas_revisor.SessaoLocal
    inicializar_banco_original = main.inicializar_banco
    limiter_main = getattr(main, "limiter", None)
    limiter_app = getattr(getattr(main.app, "state", None), "limiter", None)
    original_main_enabled = getattr(limiter_main, "enabled", None)
    original_app_enabled = getattr(limiter_app, "enabled", None)

    banco_dados.SessaoLocal = SessionLocal
    seguranca.SessaoLocal = SessionLocal
    rotas_inspetor.SessaoLocal = SessionLocal
    rotas_revisor.SessaoLocal = SessionLocal
    main.inicializar_banco = lambda: None
    if limiter_main is not None:
        limiter_main.enabled = False
    if limiter_app is not None:
        limiter_app.enabled = False

    client_ctx = TestClient(main.app)
    client = client_ctx.__enter__()

    def cleanup() -> None:
        client_ctx.__exit__(None, None, None)
        banco_dados.SessaoLocal = sessao_local_banco_original
        seguranca.SessaoLocal = sessao_local_seguranca_original
        rotas_inspetor.SessaoLocal = sessao_local_inspetor_original
        rotas_revisor.SessaoLocal = sessao_local_revisor_original
        main.inicializar_banco = inicializar_banco_original
        if limiter_main is not None and original_main_enabled is not None:
            limiter_main.enabled = original_main_enabled
        if limiter_app is not None and original_app_enabled is not None:
            limiter_app.enabled = original_app_enabled
        main.app.dependency_overrides.clear()
        seguranca.SESSOES_ATIVAS.clear()
        seguranca._SESSAO_EXPIRACAO.clear()  # noqa: SLF001
        seguranca._SESSAO_META.clear()  # noqa: SLF001
        engine.dispose()

    return client, SessionLocal, ids, cleanup


def _run_profiled_flows(client: TestClient, SessionLocal: sessionmaker[Session], ids: dict[str, int]) -> dict[str, int]:
    with SessionLocal() as banco:
        _criar_template_ativo(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="cbmgo_cmar",
            versao=1,
        )
        laudo_pdf_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="cbmgo_cmar",
        )
        laudo_pdf = banco.get(Laudo, laudo_pdf_id)
        assert laudo_pdf is not None
        laudo_pdf.primeira_mensagem = "Inspecao eletrica em painel principal."
        laudo_pdf.parecer_ia = "Resumo do laudo para emissao de preview."
        laudo_pdf.dados_formulario = {
            "informacoes_gerais": {
                "responsavel_pela_inspecao": "Gabriel Santos",
                "data_inspecao": "15/04/2026",
                "local_inspecao": "Planta Norte",
            },
            "resumo_executivo": "Preview do inspetor para observabilidade.",
        }

        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None
        revisor.crea = "987654-SP"
        laudo_export_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_export_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Descricao de campo para consolidacao do pacote.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_export_id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendencia aberta para revisar instalacao eletrica.",
                    lida=False,
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_export_id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="[@mesa] Preciso confirmar o trecho final do parecer tecnico.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                LaudoRevisao(
                    laudo_id=laudo_export_id,
                    numero_versao=1,
                    origem="mesa",
                    resumo="Ajuste inicial da mesa",
                    conteudo="Conteudo revisado pela engenharia.",
                    confianca_geral="media",
                    criado_em=datetime.now(timezone.utc),
                ),
            ]
        )
        banco.commit()

    _login_admin(client, "admin@empresa-a.test")
    for _ in range(3):
        assert client.get("/admin/painel").status_code == 200

    _login_cliente(client, "cliente@empresa-a.test")
    for _ in range(3):
        assert client.get("/cliente/api/bootstrap").status_code == 200

    csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")
    for _ in range(3):
        assert client.get("/revisao/painel").status_code == 200

    resposta_upload = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf_revisor},
        data={
            "nome": "Template observability profile",
            "codigo_template": "cbmgo_cmar",
            "versao": "41",
        },
        files={
            "arquivo_base": ("observability_base.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_upload.status_code == 201
    template_id = int(resposta_upload.json()["id"])

    for _ in range(3):
        resposta_preview = client.post(
            f"/revisao/api/templates-laudo/{template_id}/preview",
            headers={"X-CSRF-Token": csrf_revisor},
            json={
                "laudo_id": laudo_pdf_id,
                "dados_formulario": {
                    "informacoes_gerais": {
                        "responsavel_pela_inspecao": "Gabriel Santos",
                        "data_inspecao": "15/04/2026",
                        "local_inspecao": "Planta Norte",
                    },
                    "resumo_executivo": "Preview da mesa para observabilidade.",
                },
            },
        )
        assert resposta_preview.status_code == 200

    for _ in range(3):
        resposta_export = client.get(f"/revisao/api/laudo/{laudo_export_id}/pacote/exportar-pdf")
        assert resposta_export.status_code == 200

    csrf_inspetor = _login_app_inspetor(client, "inspetor@empresa-a.test")
    for _ in range(3):
        resposta_pdf = client.post(
            "/app/api/gerar_pdf",
            headers={"X-CSRF-Token": csrf_inspetor},
            json={
                "diagnostico": "Inspecao eletrica concluida.",
                "inspetor": "Gabriel Santos",
                "empresa": "Empresa A",
                "setor": "geral",
                "data": "15/04/2026",
                "laudo_id": laudo_pdf_id,
                "tipo_template": "cbmgo_cmar",
            },
        )
        assert resposta_pdf.status_code == 200

    return {
        "laudo_pdf_id": laudo_pdf_id,
        "laudo_export_id": laudo_export_id,
        "template_id": template_id,
    }


def _route_matchers() -> dict[str, Callable[[str], bool]]:
    return {
        "admin_dashboard_html": lambda path: path == "/admin/painel",
        "cliente_bootstrap": lambda path: path == "/cliente/api/bootstrap",
        "review_panel_html": lambda path: path == "/revisao/painel",
        "review_template_preview": (
            lambda path: path.startswith("/revisao/api/templates-laudo/") and path.endswith("/preview")
        ),
        "mesa_export_package_pdf": (
            lambda path: path.startswith("/revisao/api/laudo/") and path.endswith("/pacote/exportar-pdf")
        ),
        "inspector_pdf_generation": lambda path: path == "/app/api/gerar_pdf",
    }


def _summarize_requests(perf_report: dict[str, Any]) -> list[dict[str, Any]]:
    requests = list(perf_report.get("requests") or [])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in requests:
        path = str(item.get("path") or "")
        for name, matcher in _route_matchers().items():
            if matcher(path):
                grouped[name].append(item)
                break

    rows: list[dict[str, Any]] = []
    for name, items in grouped.items():
        count = max(len(items), 1)
        total_duration = sum(float(item.get("duration_ms") or 0.0) for item in items)
        total_sql = sum(int(item.get("sql_count") or 0) for item in items)
        total_slow_sql = sum(int(item.get("slow_sql_count") or 0) for item in items)
        total_render = sum(float(item.get("render_total_ms") or 0.0) for item in items)
        rows.append(
            {
                "endpoint": name,
                "count": len(items),
                "avg_duration_ms": round(total_duration / count, 3),
                "max_duration_ms": round(
                    max(float(item.get("duration_ms") or 0.0) for item in items),
                    3,
                ),
                "avg_sql_count": round(total_sql / count, 3),
                "max_sql_count": max(int(item.get("sql_count") or 0) for item in items),
                "avg_slow_sql_count": round(total_slow_sql / count, 3),
                "avg_render_ms": round(total_render / count, 3),
                "status_codes": sorted({int(item.get("status_code") or 0) for item in items}),
            }
        )
    rows.sort(
        key=lambda item: (
            float(item["avg_duration_ms"]),
            float(item["avg_sql_count"]),
            float(item["max_duration_ms"]),
        ),
        reverse=True,
    )
    return rows


def _consolidate_top5(
    request_rows: list[dict[str, Any]],
    hotspot_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    hotspot_by_endpoint = {
        str(item.get("endpoint") or ""): item
        for item in list(hotspot_summary.get("by_endpoint") or [])
    }
    top5: list[dict[str, Any]] = []
    for row in request_rows[:5]:
        hotspot = hotspot_by_endpoint.get(str(row["endpoint"]), {})
        top5.append(
            {
                "endpoint": row["endpoint"],
                "avg_duration_ms": row["avg_duration_ms"],
                "max_duration_ms": row["max_duration_ms"],
                "avg_sql_count": row["avg_sql_count"],
                "max_sql_count": row["max_sql_count"],
                "avg_render_ms": row["avg_render_ms"],
                "hotspot_success": int(hotspot.get("success") or 0),
                "hotspot_blocked": int(hotspot.get("blocked") or 0),
                "hotspot_error": int(hotspot.get("error") or 0),
                "hotspot_slow_count": int(hotspot.get("slow_count") or 0),
                "outcomes": list(hotspot.get("outcomes") or []),
            }
        )
    return top5


def main_profile() -> int:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    artifact_dir = ARTIFACT_ROOT / timestamp
    artifact_dir.mkdir(parents=True, exist_ok=True)

    client, SessionLocal, ids, cleanup = _prepare_environment()
    try:
        resetar_perf()
        clear_backend_hotspot_metrics_for_tests()

        ids_profile = _run_profiled_flows(client, SessionLocal, ids)
        hotspot_summary = get_backend_hotspot_operational_summary()
        perf_report = relatorio_perf()
        request_rows = _summarize_requests(perf_report)
        top5 = _consolidate_top5(request_rows, hotspot_summary)

        with SessionLocal() as banco:
            document_summary = build_document_operations_operational_summary(banco)

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "env": {
                "AMBIENTE": os.environ.get("AMBIENTE"),
                "PERF_MODE": os.environ.get("PERF_MODE"),
                "TARIEL_BACKEND_HOTSPOT_OBSERVABILITY": os.environ.get(
                    "TARIEL_BACKEND_HOTSPOT_OBSERVABILITY"
                ),
            },
            "ids_profile": ids_profile,
            "top5_hotspots": top5,
            "request_hotspots_ranked": request_rows,
            "backend_hotspots_summary": hotspot_summary,
            "perf_report_summary": {
                "counts": perf_report.get("counts", {}),
                "top_routes": perf_report.get("top_routes", []),
                "top_queries": perf_report.get("top_queries", []),
                "top_render_ops": perf_report.get("top_render_ops", []),
                "slow_requests": perf_report.get("slow_requests", []),
            },
            "document_operations_summary": document_summary,
        }

        artifact_path = artifact_dir / "phase1_hotspots_profile.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"artifact={artifact_path}")
        print("top5_hotspots=")
        for item in top5:
            print(
                json.dumps(
                    {
                        "endpoint": item["endpoint"],
                        "avg_duration_ms": item["avg_duration_ms"],
                        "avg_sql_count": item["avg_sql_count"],
                        "avg_render_ms": item["avg_render_ms"],
                    },
                    ensure_ascii=False,
                )
            )
        return 0
    finally:
        cleanup()


if __name__ == "__main__":
    raise SystemExit(main_profile())
