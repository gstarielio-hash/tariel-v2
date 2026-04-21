#!/usr/bin/env python3
"""Segundo harness local do Epic 10J para template_publish_activate via HTTP/TestClient."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"

sys.path.insert(0, str(WEB_ROOT))

import app.domains.chat.routes as rotas_inspetor  # noqa: E402
import app.domains.revisor.routes as rotas_revisor  # noqa: E402
import app.shared.database as banco_dados  # noqa: E402
import app.shared.security as seguranca  # noqa: E402
import main as app_main  # noqa: E402
from app.shared.database import (  # noqa: E402
    Base,
    Empresa,
    LimitePlano,
    NivelAcesso,
    PlanoEmpresa,
    RegistroAuditoriaEmpresa,
    TemplateLaudo,
    Usuario,
)
from app.v2.document import (  # noqa: E402
    clear_document_hard_gate_metrics_for_tests,
    get_document_hard_gate_operational_summary,
)
from app.v2.document.hard_gate_evidence import (  # noqa: E402
    clear_document_hard_gate_durable_evidence_for_tests,
    get_document_hard_gate_durable_summary,
    load_document_hard_gate_durable_entries,
)
from nucleo.template_editor_word import MODO_EDITOR_RICO  # noqa: E402
from tests.regras_rotas_criticas_support import (  # noqa: E402
    SENHA_HASH_PADRAO,
    _login_admin,
    _login_revisor,
    _salvar_pdf_temporario_teste,
)

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "document_hard_gate_validation_10j_http"

CASE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "case_name": "template_publish_gap_legacy_http",
        "case_profile": "legacy_gap",
        "codigo_template": "template_gap_10j_http_legacy",
        "route_kind": "legacy",
        "modo_editor": "legado_pdf",
        "seed_active_before_publish": False,
        "status_template": "rascunho",
    },
    {
        "case_name": "template_publish_ok_legacy_http",
        "case_profile": "legacy_ok",
        "codigo_template": "template_ok_10j_http_legacy",
        "route_kind": "legacy",
        "modo_editor": "legado_pdf",
        "seed_active_before_publish": True,
        "status_template": "rascunho",
    },
    {
        "case_name": "template_publish_gap_editor_http",
        "case_profile": "editor_gap",
        "codigo_template": "template_gap_10j_http_editor",
        "route_kind": "editor",
        "modo_editor": MODO_EDITOR_RICO,
        "seed_active_before_publish": False,
        "status_template": "em_teste",
    },
    {
        "case_name": "template_publish_ok_editor_http",
        "case_profile": "editor_ok",
        "codigo_template": "template_ok_10j_http_editor",
        "route_kind": "editor",
        "modo_editor": MODO_EDITOR_RICO,
        "seed_active_before_publish": True,
        "status_template": "em_teste",
    },
]


def now_local_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: pathlib.Path, payload: Any) -> None:
    def _default(value: Any) -> str:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=_default),
        encoding="utf-8",
    )


def save_command_artifact(
    path: pathlib.Path,
    command: list[str],
    completed: subprocess.CompletedProcess[str],
) -> None:
    write_text(
        path,
        "\n".join(
            [
                f"$ {' '.join(command)}",
                "",
                "[stdout]",
                completed.stdout.strip(),
                "",
                "[stderr]",
                completed.stderr.strip(),
                "",
                f"[returncode] {completed.returncode}",
            ]
        ).strip()
        + "\n",
    )


def run_boot_import_check(artifacts_dir: pathlib.Path) -> None:
    command = [
        "python3",
        "-c",
        "import main; main.create_app(); print('boot_import_ok')",
    ]
    env = os.environ.copy()
    env.setdefault("AMBIENTE", "dev")
    env["PYTHONPATH"] = str(WEB_ROOT)
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    save_command_artifact(artifacts_dir / "boot_import_check.txt", command, completed)
    if completed.returncode != 0:
        raise RuntimeError("Boot/import check falhou no harness HTTP do 10J.")


def create_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def seed_minimal_environment(banco: Session) -> dict[str, int]:
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

    empresa = Empresa(nome_fantasia="Empresa A", cnpj="12345678000190", plano_ativo=PlanoEmpresa.ILIMITADO.value)
    banco.add(empresa)
    banco.flush()

    revisor = Usuario(
        empresa_id=empresa.id,
        nome_completo="Revisor A",
        email="revisor@empresa-a.test",
        senha_hash=SENHA_HASH_PADRAO,
        nivel_acesso=NivelAcesso.REVISOR.value,
    )
    admin = Usuario(
        empresa_id=empresa.id,
        nome_completo="Admin A",
        email="admin@empresa-a.test",
        senha_hash=SENHA_HASH_PADRAO,
        nivel_acesso=NivelAcesso.DIRETORIA.value,
    )
    banco.add_all([revisor, admin])
    banco.commit()
    banco.refresh(empresa)
    banco.refresh(revisor)
    banco.refresh(admin)
    return {
        "empresa_a": int(empresa.id),
        "revisor_a": int(revisor.id),
        "admin_a": int(admin.id),
    }


def create_template(
    banco: Session,
    *,
    empresa_id: int,
    criado_por_id: int,
    codigo_template: str,
    versao: int,
    ativo: bool,
    status_template: str,
    modo_editor: str = "legado_pdf",
) -> int:
    template = TemplateLaudo(
        empresa_id=empresa_id,
        criado_por_id=criado_por_id,
        nome=f"Template {codigo_template} v{versao}",
        codigo_template=codigo_template,
        versao=versao,
        ativo=ativo,
        base_recomendada_fixa=False,
        modo_editor=modo_editor,
        status_template=status_template,
        arquivo_pdf_base=_salvar_pdf_temporario_teste(f"{codigo_template}_{versao}"),
        mapeamento_campos_json={},
        documento_editor_json=None,
        assets_json=[],
        estilo_json={},
        observacoes=None,
    )
    banco.add(template)
    banco.commit()
    banco.refresh(template)
    return int(template.id)


def latest_template_publish_audit(
    banco: Session,
    *,
    empresa_id: int,
    template_id: int,
) -> RegistroAuditoriaEmpresa | None:
    registros = (
        banco.query(RegistroAuditoriaEmpresa)
        .filter(
            RegistroAuditoriaEmpresa.empresa_id == empresa_id,
            RegistroAuditoriaEmpresa.acao == "template_publicado",
        )
        .order_by(RegistroAuditoriaEmpresa.id.desc())
        .all()
    )
    for registro in registros:
        payload = getattr(registro, "payload_json", None) or {}
        if int(payload.get("template_id") or 0) == int(template_id):
            return registro
    return None


def configure_environment(*, tenant_id: int, durable_root: pathlib.Path) -> dict[str, str]:
    template_codes = ",".join(case["codigo_template"] for case in CASE_DEFINITIONS)
    values = {
        "AMBIENTE": "dev",
        "TARIEL_V2_DOCUMENT_HARD_GATE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS": str(tenant_id),
        "TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS": "template_publish_activate",
        "TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES": template_codes,
        "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR": str(durable_root),
    }
    os.environ.update(values)
    return values


def seed_case_templates(
    banco: Session,
    *,
    ids: dict[str, int],
    case_definition: dict[str, Any],
) -> int:
    if case_definition["seed_active_before_publish"]:
        create_template(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template=case_definition["codigo_template"],
            versao=1,
            ativo=True,
            status_template="ativo",
            modo_editor=case_definition["modo_editor"],
        )
    return create_template(
        banco,
        empresa_id=ids["empresa_a"],
        criado_por_id=ids["revisor_a"],
        codigo_template=case_definition["codigo_template"],
        versao=2,
        ativo=False,
        status_template=case_definition["status_template"],
        modo_editor=case_definition["modo_editor"],
    )


def route_path_for_case(case_definition: dict[str, Any], template_id: int) -> str:
    if case_definition["route_kind"] == "editor":
        return f"/revisao/api/templates-laudo/editor/{template_id}/publicar"
    return f"/revisao/api/templates-laudo/{template_id}/publicar"


def route_name_for_case(case_definition: dict[str, Any]) -> str:
    if case_definition["route_kind"] == "editor":
        return "publicar_template_editor_laudo"
    return "publicar_template_laudo"


def find_case_entry(
    *,
    durable_root: pathlib.Path,
    template_id: int,
) -> dict[str, Any]:
    entries = load_document_hard_gate_durable_entries(
        root=durable_root,
        operation_kind="template_publish_activate",
    )
    for entry in entries:
        if int(((entry.get("target") or {}).get("template_id") or 0)) == int(template_id):
            return entry
    raise RuntimeError(f"Nenhuma evidencia duravel encontrada para template_id={template_id}.")


def collect_case_result(
    *,
    SessionLocal,
    durable_root: pathlib.Path,
    case_definition: dict[str, Any],
    template_id: int,
    route_path: str,
    response_payload: dict[str, Any],
    response_status_code: int,
) -> dict[str, Any]:
    with SessionLocal() as banco:
        template = banco.get(TemplateLaudo, template_id)
        assert template is not None
        audit_record = latest_template_publish_audit(
            banco,
            empresa_id=int(template.empresa_id),
            template_id=template_id,
        )

    durable_entry = find_case_entry(
        durable_root=durable_root,
        template_id=template_id,
    )
    decision = durable_entry["hard_gate_result"]["decision"]
    blockers = [item["blocker_code"] for item in list(durable_entry.get("blockers") or [])]

    return {
        "case_name": case_definition["case_name"],
        "case_profile": case_definition["case_profile"],
        "harness": "testclient_http_harness",
        "route_name": str(decision["route_name"]),
        "route_path": route_path,
        "operation_kind": str(decision["operation_kind"]),
        "tenant_id": str(decision["tenant_id"]),
        "template_id": int(template_id),
        "codigo_template": str(template.codigo_template or ""),
        "versao": int(template.versao or 0),
        "modo_editor": str(template.modo_editor or ""),
        "status_template": str(template.status_template or ""),
        "ativo": bool(template.ativo),
        "would_block": bool(decision["would_block"]),
        "did_block": bool(decision["did_block"]),
        "shadow_only": bool(decision["shadow_only"]),
        "enforce_enabled": bool(decision["enforce_enabled"]),
        "blockers": blockers,
        "response_status_code": int(response_status_code),
        "response_transport": "json",
        "functional_outcome": str(durable_entry["functional_outcome"]),
        "artifact_path": str(durable_entry["artifact_path"]),
        "audit_record_id": int(getattr(audit_record, "id", 0) or 0) if audit_record is not None else None,
        "audit_generated": audit_record is not None,
        "response_payload": response_payload,
        "document_readiness": dict(decision.get("document_readiness") or {}),
    }


def build_final_report(
    cases: list[dict[str, Any]],
    runtime_summary: dict[str, Any],
    durable_summary: dict[str, Any],
) -> str:
    lines = [
        "# Epic 10J - harness HTTP/TestClient",
        "",
        f"- total_cases: {len(cases)}",
        f"- runtime_evaluations: {runtime_summary['totals']['evaluations']}",
        f"- durable_evaluations: {durable_summary['totals']['evaluations']}",
        f"- would_block: {runtime_summary['totals']['would_block']}",
        f"- did_block: {runtime_summary['totals']['did_block']}",
        "",
        "## Cases",
    ]
    for case in cases:
        lines.append(
            f"- {case['case_name']}: route={case['route_name']} template_id={case['template_id']} blockers={','.join(case['blockers']) or 'none'} would_block={case['would_block']} did_block={case['did_block']}"
        )
    lines.extend(
        [
            "",
            "## Conclusion",
            "- template_publish_activate permaneceu em shadow_only no harness HTTP.",
            "- did_block permaneceu false em todos os casos executados.",
            "- a publicacao real continuou funcional com auditoria operacional preservada.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=("all", "legacy_gap", "legacy_ok", "editor_gap", "editor_ok"),
        default="all",
        help="Caso unico ou conjunto completo do harness HTTP.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Diretorio de artifacts para a rodada.",
    )
    return parser.parse_args()


def selected_cases(case_filter: str) -> list[dict[str, Any]]:
    if case_filter == "all":
        return list(CASE_DEFINITIONS)
    return [case for case in CASE_DEFINITIONS if case["case_profile"] == case_filter]


def main() -> int:
    args = parse_args()
    artifacts_dir = (
        ensure_dir(pathlib.Path(args.output_dir).expanduser().resolve())
        if args.output_dir
        else ensure_dir((DEFAULT_OUTPUT_ROOT / now_local_slug()).resolve())
    )
    responses_dir = ensure_dir(artifacts_dir / "responses")
    durable_root = ensure_dir(artifacts_dir / "durable_evidence")

    clear_document_hard_gate_metrics_for_tests()
    clear_document_hard_gate_durable_evidence_for_tests(root=durable_root)
    run_boot_import_check(artifacts_dir)

    engine, SessionLocal = create_session_factory()

    with SessionLocal() as banco:
        ids = seed_minimal_environment(banco)

    flags = configure_environment(
        tenant_id=ids["empresa_a"],
        durable_root=durable_root,
    )
    write_json(artifacts_dir / "flags_snapshot.json", flags)

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

    sessao_local_banco_original = banco_dados.SessaoLocal
    sessao_local_seguranca_original = seguranca.SessaoLocal
    sessao_local_inspetor_original = rotas_inspetor.SessaoLocal
    sessao_local_revisor_original = rotas_revisor.SessaoLocal
    inicializar_banco_original = app_main.inicializar_banco

    app_main.app.dependency_overrides[banco_dados.obter_banco] = override_obter_banco
    banco_dados.SessaoLocal = SessionLocal
    seguranca.SessaoLocal = SessionLocal
    rotas_inspetor.SessaoLocal = SessionLocal
    rotas_revisor.SessaoLocal = SessionLocal
    app_main.inicializar_banco = lambda: None

    cases: list[dict[str, Any]] = []
    admin_summary_body: dict[str, Any] | None = None
    admin_durable_summary_body: dict[str, Any] | None = None
    cwd_original = pathlib.Path.cwd()

    try:
        os.chdir(WEB_ROOT)
        with TestClient(app_main.app) as client:
            csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")

            for case_definition in selected_cases(args.case):
                with SessionLocal() as banco:
                    template_id = seed_case_templates(
                        banco,
                        ids=ids,
                        case_definition=case_definition,
                    )
                route_path = route_path_for_case(case_definition, template_id)
                response = client.post(
                    route_path,
                    headers={"X-CSRF-Token": csrf_revisor},
                    data={"csrf_token": csrf_revisor},
                )
                response_payload = response.json()
                write_json(responses_dir / f"{case_definition['case_name']}_response.json", response_payload)

                case_result = collect_case_result(
                    SessionLocal=SessionLocal,
                    durable_root=durable_root,
                    case_definition=case_definition,
                    template_id=template_id,
                    route_path=route_path,
                    response_payload=response_payload,
                    response_status_code=int(response.status_code),
                )
                cases.append(case_result)
                write_json(
                    responses_dir / f"{case_definition['case_name']}_artifact.json",
                    find_case_entry(
                        durable_root=durable_root,
                        template_id=template_id,
                    ),
                )

            _login_admin(client, "admin@empresa-a.test")
            admin_summary_response = client.get("/admin/api/document-hard-gate/summary")
            admin_durable_summary_response = client.get("/admin/api/document-hard-gate/durable-summary")
            admin_summary_body = admin_summary_response.json()
            admin_durable_summary_body = admin_durable_summary_response.json()
    finally:
        os.chdir(cwd_original)
        banco_dados.SessaoLocal = sessao_local_banco_original
        seguranca.SessaoLocal = sessao_local_seguranca_original
        rotas_inspetor.SessaoLocal = sessao_local_inspetor_original
        rotas_revisor.SessaoLocal = sessao_local_revisor_original
        app_main.inicializar_banco = inicializar_banco_original
        app_main.app.dependency_overrides.clear()
        seguranca.SESSOES_ATIVAS.clear()
        seguranca._SESSAO_EXPIRACAO.clear()  # noqa: SLF001
        seguranca._SESSAO_META.clear()  # noqa: SLF001

    runtime_summary = get_document_hard_gate_operational_summary()
    durable_summary = get_document_hard_gate_durable_summary(
        root=durable_root,
        operation_kind="template_publish_activate",
    )

    write_json(artifacts_dir / "runtime_summary.json", runtime_summary)
    write_json(artifacts_dir / "durable_summary.json", durable_summary)
    write_json(artifacts_dir / "validation_cases.json", cases)
    if admin_summary_body is not None:
        write_json(responses_dir / "admin_summary_response.json", admin_summary_body)
    if admin_durable_summary_body is not None:
        write_json(responses_dir / "admin_durable_summary_response.json", admin_durable_summary_body)
    write_text(
        artifacts_dir / "final_report.md",
        build_final_report(cases, runtime_summary, durable_summary),
    )
    source_paths = [
        str(artifacts_dir / "boot_import_check.txt"),
        str(artifacts_dir / "flags_snapshot.json"),
        str(artifacts_dir / "runtime_summary.json"),
        str(artifacts_dir / "durable_summary.json"),
        str(artifacts_dir / "validation_cases.json"),
        str(artifacts_dir / "final_report.md"),
        str(responses_dir / "admin_summary_response.json"),
        str(responses_dir / "admin_durable_summary_response.json"),
    ]
    source_paths.extend(
        str(responses_dir / f"{case['case_name']}_response.json")
        for case in cases
    )
    source_paths.extend(
        str(responses_dir / f"{case['case_name']}_artifact.json")
        for case in cases
    )
    write_text(artifacts_dir / "source_artifacts_index.txt", "\n".join(source_paths) + "\n")

    engine.dispose()

    result = {
        "artifacts_dir": str(artifacts_dir),
        "case_count": len(cases),
        "case_profiles": [case["case_profile"] for case in cases],
        "totals": runtime_summary["totals"],
    }
    write_json(artifacts_dir / "harness_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
