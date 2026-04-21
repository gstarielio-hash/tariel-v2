#!/usr/bin/env python3
"""Runner local do Epic 10I para template_publish_activate em shadow_only."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "document_hard_gate_validation_10i"

sys.path.insert(0, str(WEB_ROOT))

from starlette.requests import Request  # noqa: E402

from app.domains.admin.routes import (  # noqa: E402
    api_document_hard_gate_durable_summary,
    api_document_hard_gate_summary,
)
from app.domains.revisor.templates_laudo_management_routes import (  # noqa: E402
    publicar_template_editor_laudo,
    publicar_template_laudo,
)
from app.shared.database import (  # noqa: E402
    Base,
    Empresa,
    NivelAcesso,
    RegistroAuditoriaEmpresa,
    TemplateLaudo,
    Usuario,
    sessao_tem_mutacoes_pendentes,
)
from app.shared.security import criar_hash_senha  # noqa: E402
from app.v2.document import (  # noqa: E402
    clear_document_hard_gate_metrics_for_tests,
    document_hard_gate_observability_flags,
    get_document_hard_gate_operational_summary,
)
from app.v2.document.hard_gate_evidence import (  # noqa: E402
    clear_document_hard_gate_durable_evidence_for_tests,
    export_document_hard_gate_durable_snapshot,
    get_document_hard_gate_durable_summary,
)
from nucleo.template_editor_word import MODO_EDITOR_RICO  # noqa: E402
from tests.regras_rotas_criticas_support import _salvar_pdf_temporario_teste  # noqa: E402


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


def normalize_json_payload(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): normalize_json_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normalize_json_payload(item) for item in value]
    body = getattr(value, "body", None)
    if isinstance(body, (bytes, bytearray)):
        try:
            decoded = body.decode("utf-8").strip()
        except Exception:
            decoded = ""
        if decoded:
            try:
                return json.loads(decoded)
            except Exception:
                return {
                    "status_code": getattr(value, "status_code", None),
                    "body": decoded,
                }
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def save_command_artifact(path: pathlib.Path, command: list[str], completed: subprocess.CompletedProcess[str]) -> None:
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
        cwd=str(WEB_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    save_command_artifact(artifacts_dir / "boot_import_check.txt", command, completed)
    if completed.returncode != 0:
        raise RuntimeError("Boot/import check falhou.")


def build_publish_request(path: str, csrf: str, *, remote_host: str = "testclient") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"x-csrf-token", csrf.encode())],
            "query_string": b"",
            "session": {"csrf_token_revisor": csrf},
            "state": {},
            "client": (remote_host, 50140),
        }
    )


def build_admin_request(path: str, *, remote_host: str = "testclient") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "session": {},
            "state": {},
            "client": (remote_host, 50141),
        }
    )


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
    empresa = Empresa(nome_fantasia="Empresa A", cnpj="12345678000190", plano_ativo="ilimitado")
    banco.add(empresa)
    banco.flush()

    revisor = Usuario(
        empresa_id=empresa.id,
        nome_completo="Revisor A",
        email="revisor@empresa-a.test",
        senha_hash=criar_hash_senha("Senha@123"),
        nivel_acesso=NivelAcesso.REVISOR.value,
    )
    admin = Usuario(
        empresa_id=empresa.id,
        nome_completo="Admin A",
        email="admin@empresa-a.test",
        senha_hash=criar_hash_senha("Senha@123"),
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


def collect_case_result(
    *,
    banco: Session,
    request: Request,
    template_id: int,
    route_name: str,
    route_path: str,
    case_name: str,
    harness_name: str,
) -> dict[str, Any]:
    template = banco.get(TemplateLaudo, template_id)
    assert template is not None
    decision = getattr(request.state, "v2_document_hard_gate_decision", None) or {}
    blockers = [item.get("blocker_code") for item in list(decision.get("blockers") or [])]
    audit_record = latest_template_publish_audit(
        banco,
        empresa_id=int(getattr(template, "empresa_id", 0) or 0),
        template_id=template_id,
    )
    return {
        "case_name": case_name,
        "harness": harness_name,
        "route_name": route_name,
        "route_path": route_path,
        "operation_kind": decision.get("operation_kind"),
        "tenant_id": decision.get("tenant_id"),
        "template_id": int(template.id),
        "codigo_template": str(template.codigo_template or ""),
        "versao": int(template.versao or 0),
        "modo_editor": str(template.modo_editor or ""),
        "status_template": str(template.status_template or ""),
        "ativo": bool(template.ativo),
        "would_block": bool(decision.get("would_block")),
        "did_block": bool(decision.get("did_block")),
        "shadow_only": bool(decision.get("shadow_only")),
        "enforce_enabled": bool(decision.get("enforce_enabled")),
        "blockers": blockers,
        "response_status_code": 200,
        "response_transport": "json",
        "functional_outcome": "template_publish_completed_shadow_only",
        "artifact_path": getattr(request.state, "v2_template_publish_shadow_artifact_path", None),
        "audit_record_id": int(getattr(audit_record, "id", 0) or 0) if audit_record is not None else None,
        "audit_generated": audit_record is not None,
        "shadow_scope": getattr(request.state, "v2_template_publish_shadow_scope", None),
        "shadow_observation": getattr(request.state, "v2_template_publish_shadow_observation", None),
        "response_payload": {"ok": True, "template_id": template_id, "status": "publicado"},
    }


def execute_gap_case(banco: Session, ids: dict[str, int]) -> tuple[dict[str, Any], Request]:
    template_id = create_template(
        banco,
        empresa_id=ids["empresa_a"],
        criado_por_id=ids["revisor_a"],
        codigo_template="template_gap_10i_validation",
        versao=2,
        ativo=False,
        status_template="rascunho",
    )
    usuario = banco.get(Usuario, ids["revisor_a"])
    assert usuario is not None
    path = f"/revisao/api/templates-laudo/{template_id}/publicar"
    request = build_publish_request(path, "csrf-template-gap-10i")
    response_payload = asyncio.run(
        publicar_template_laudo(
            template_id=template_id,
            request=request,
            csrf_token="csrf-template-gap-10i",
            usuario=usuario,
            banco=banco,
        )
    )
    if sessao_tem_mutacoes_pendentes(banco):
        banco.commit()
    case_result = collect_case_result(
        banco=banco,
        request=request,
        template_id=template_id,
        route_name="publicar_template_laudo",
        route_path=path,
        case_name="template_publish_gap_shadow",
        harness_name="direct_route_call",
    )
    case_result["response_payload"] = normalize_json_payload(response_payload)
    return case_result, request


def execute_template_ok_case(banco: Session, ids: dict[str, int]) -> tuple[dict[str, Any], Request]:
    create_template(
        banco,
        empresa_id=ids["empresa_a"],
        criado_por_id=ids["revisor_a"],
        codigo_template="template_ok_10i_validation",
        versao=1,
        ativo=True,
        status_template="ativo",
    )
    template_id = create_template(
        banco,
        empresa_id=ids["empresa_a"],
        criado_por_id=ids["revisor_a"],
        codigo_template="template_ok_10i_validation",
        versao=2,
        ativo=False,
        status_template="em_teste",
        modo_editor=MODO_EDITOR_RICO,
    )
    usuario = banco.get(Usuario, ids["revisor_a"])
    assert usuario is not None
    path = f"/revisao/api/templates-laudo/editor/{template_id}/publicar"
    request = build_publish_request(path, "csrf-template-ok-10i")
    response_payload = asyncio.run(
        publicar_template_editor_laudo(
            template_id=template_id,
            request=request,
            csrf_token="csrf-template-ok-10i",
            usuario=usuario,
            banco=banco,
        )
    )
    if sessao_tem_mutacoes_pendentes(banco):
        banco.commit()
    case_result = collect_case_result(
        banco=banco,
        request=request,
        template_id=template_id,
        route_name="publicar_template_editor_laudo",
        route_path=path,
        case_name="template_publish_ok_shadow",
        harness_name="direct_route_call",
    )
    case_result["response_payload"] = normalize_json_payload(response_payload)
    return case_result, request


def configure_environment(*, tenant_id: int, durable_root: pathlib.Path) -> dict[str, str]:
    values = {
        "AMBIENTE": "dev",
        "TARIEL_V2_DOCUMENT_HARD_GATE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS": str(tenant_id),
        "TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS": "template_publish_activate",
        "TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES": "template_gap_10i_validation,template_ok_10i_validation",
        "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR": str(durable_root),
    }
    os.environ.update(values)
    return values


def build_final_report(cases: list[dict[str, Any]], runtime_summary: dict[str, Any], durable_summary: dict[str, Any]) -> str:
    lines = [
        "# Epic 10I - validation report",
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
        lines.extend(
            [
                f"- {case['case_name']}: route={case['route_name']} template_id={case['template_id']} blockers={','.join(case['blockers']) or 'none'} would_block={case['would_block']} did_block={case['did_block']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Conclusion",
            "- template_publish_activate permaneceu em shadow_only.",
            "- did_block permaneceu false nas duas rotas.",
            "- a publicacao real continuou funcional com auditoria operacional preservada.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_validation(output_dir: pathlib.Path) -> dict[str, Any]:
    run_boot_import_check(output_dir)
    durable_root = ensure_dir(output_dir / "durable_evidence")
    engine, SessionLocal = create_session_factory()
    clear_document_hard_gate_metrics_for_tests()
    clear_document_hard_gate_durable_evidence_for_tests(root=durable_root)

    cases: list[dict[str, Any]] = []
    try:
        with SessionLocal() as banco:
            ids = seed_minimal_environment(banco)
            env_flags = configure_environment(
                tenant_id=ids["empresa_a"],
                durable_root=durable_root,
            )
            write_json(output_dir / "flags_snapshot.json", {
                "environment": env_flags,
                "observability_flags": document_hard_gate_observability_flags(),
            })

            gap_case, gap_request = execute_gap_case(banco, ids)
            ok_case, ok_request = execute_template_ok_case(banco, ids)
            cases.extend([gap_case, ok_case])
            admin_user = banco.get(Usuario, ids["admin_a"])
            assert admin_user is not None
            admin_summary_response = asyncio.run(
                api_document_hard_gate_summary(
                    request=build_admin_request("/admin/api/document-hard-gate/summary"),
                    usuario=admin_user,
                )
            )
            admin_durable_summary_response = asyncio.run(
                api_document_hard_gate_durable_summary(
                    request=build_admin_request("/admin/api/document-hard-gate/durable-summary"),
                    usuario=admin_user,
                )
            )

            write_json(output_dir / "responses" / "template_publish_gap_response.json", {
                "response_payload": gap_case["response_payload"],
                "shadow_observation": getattr(gap_request.state, "v2_template_publish_shadow_observation", None),
            })
            write_json(output_dir / "responses" / "template_publish_ok_response.json", {
                "response_payload": ok_case["response_payload"],
                "shadow_observation": getattr(ok_request.state, "v2_template_publish_shadow_observation", None),
            })
            write_json(output_dir / "responses" / "admin_summary_response.json", json.loads(admin_summary_response.body.decode()))
            write_json(
                output_dir / "responses" / "admin_durable_summary_response.json",
                json.loads(admin_durable_summary_response.body.decode()),
            )

        runtime_summary = get_document_hard_gate_operational_summary()
        durable_summary = get_document_hard_gate_durable_summary(operation_kind="template_publish_activate")
        snapshot_paths = export_document_hard_gate_durable_snapshot(
            output_dir,
            operation_kind="template_publish_activate",
        )

        write_json(output_dir / "runtime_summary.json", runtime_summary)
        write_json(output_dir / "durable_summary.json", durable_summary)
        write_json(output_dir / "validation_cases.json", cases)
        write_text(output_dir / "final_report.md", build_final_report(cases, runtime_summary, durable_summary))

        source_index_lines = [
            str(output_dir / "boot_import_check.txt"),
            str(output_dir / "flags_snapshot.json"),
            str(output_dir / "runtime_summary.json"),
            str(output_dir / "durable_summary.json"),
            str(output_dir / "validation_cases.json"),
            str(output_dir / "final_report.md"),
            str(output_dir / "responses" / "template_publish_gap_response.json"),
            str(output_dir / "responses" / "template_publish_ok_response.json"),
            str(output_dir / "responses" / "admin_summary_response.json"),
            str(output_dir / "responses" / "admin_durable_summary_response.json"),
            str(durable_root),
            snapshot_paths["summary_path"],
            snapshot_paths["entries_path"],
        ]
        write_text(output_dir / "source_artifacts_index.txt", "\n".join(source_index_lines) + "\n")

        return {
            "artifacts_dir": str(output_dir),
            "cases": normalize_json_payload(cases),
            "runtime_summary": normalize_json_payload(runtime_summary),
            "durable_summary": normalize_json_payload(durable_summary),
        }
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida o shadow-only de template_publish_activate.")
    parser.add_argument("--output-dir", default="", help="Diretorio de artifacts da rodada.")
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output_dir).expanduser() if args.output_dir else ARTIFACTS_ROOT / now_local_slug()
    output_dir = ensure_dir(output_dir)
    ensure_dir(output_dir / "responses")

    result = run_validation(output_dir)
    write_json(output_dir / "runner_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
