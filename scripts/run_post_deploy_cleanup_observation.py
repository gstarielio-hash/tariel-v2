#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "final_product_stamp"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    current = value or _now_utc()
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _touch_file(path: Path, *, age_days: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("observation", encoding="utf-8")
    ts = time.time() - (age_days * 86400)
    os.utime(path, (ts, ts))


def _prepare_env(observation_root: Path) -> dict[str, str]:
    uploads_root = observation_root / "persistent_storage" / "static" / "uploads"
    database_path = observation_root / "observation.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    uploads_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "AMBIENTE": "production",
            "CHAVE_SECRETA_APP": "execucao6-observacao-pos-deploy-chave-1234567890",
            "DATABASE_URL": f"sqlite:///{database_path}",
            "TARIEL_UPLOADS_STORAGE_MODE": "custom",
            "PASTA_UPLOADS_PERFIS": str(uploads_root / "perfis"),
            "PASTA_ANEXOS_MESA": str(uploads_root / "mesa_anexos"),
            "PASTA_APRENDIZADOS_VISUAIS_IA": str(uploads_root / "aprendizados_ia"),
            "TARIEL_UPLOADS_PROFILE_RETENTION_DAYS": "30",
            "TARIEL_UPLOADS_MESA_RETENTION_DAYS": "30",
            "TARIEL_UPLOADS_LEARNING_RETENTION_DAYS": "30",
            "TARIEL_UPLOADS_CLEANUP_ENABLED": "1",
            "TARIEL_UPLOADS_CLEANUP_GRACE_DAYS": "7",
            "TARIEL_UPLOADS_CLEANUP_INTERVAL_HOURS": "1",
            "TARIEL_UPLOADS_CLEANUP_MAX_DELETIONS_PER_RUN": "20",
            "TARIEL_UPLOADS_BACKUP_REQUIRED": "1",
            "TARIEL_UPLOADS_RESTORE_DRILL_REQUIRED": "1",
            "SESSAO_FAIL_CLOSED_ON_DB_ERROR": "1",
            "BOOTSTRAP_ADMIN_EMAIL": "",
            "BOOTSTRAP_ADMIN_PASSWORD": "",
        }
    )
    return env


def _import_runtime(env: dict[str, str]) -> dict[str, Any]:
    os.environ.clear()
    os.environ.update(env)
    if str(WEB_ROOT) not in sys.path:
        sys.path.insert(0, str(WEB_ROOT))

    import importlib

    banco_dados = importlib.import_module("app.shared.database")
    main = importlib.import_module("main")
    settings_module = importlib.import_module("app.core.settings")
    production_ops_module = importlib.import_module("app.domains.admin.production_ops_summary")
    uploads_cleanup_module = importlib.import_module("app.domains.admin.uploads_cleanup")
    return {
        "banco_dados": banco_dados,
        "main": main,
        "settings_module": settings_module,
        "production_ops_module": production_ops_module,
        "uploads_cleanup_module": uploads_cleanup_module,
    }


def _seed_observation_data(runtime: dict[str, Any]) -> dict[str, str]:
    banco_dados = runtime["banco_dados"]
    banco_dados.inicializar_banco()

    Empresa = banco_dados.Empresa
    Laudo = banco_dados.Laudo
    MensagemLaudo = banco_dados.MensagemLaudo
    TipoMensagem = banco_dados.TipoMensagem
    Usuario = banco_dados.Usuario
    AnexoMesa = banco_dados.AnexoMesa
    AprendizadoVisualIa = banco_dados.AprendizadoVisualIa
    NivelAcesso = banco_dados.NivelAcesso
    PlanoEmpresa = banco_dados.PlanoEmpresa
    SessaoLocal = banco_dados.SessaoLocal

    profile_root = Path(os.environ["PASTA_UPLOADS_PERFIS"])
    mesa_root = Path(os.environ["PASTA_ANEXOS_MESA"])
    learning_root = Path(os.environ["PASTA_APRENDIZADOS_VISUAIS_IA"])

    with SessaoLocal() as banco:
        empresa = Empresa(
            nome_fantasia="Empresa Observation",
            cnpj="55555555000199",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
        )
        banco.add(empresa)
        banco.flush()

        usuario = Usuario(
            empresa_id=empresa.id,
            nome_completo="Usuario Observation",
            email="observation@tariel.test",
            senha_hash="seed",
            nivel_acesso=NivelAcesso.INSPETOR.value,
        )
        banco.add(usuario)
        banco.flush()

        laudo = Laudo(
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            setor_industrial="metalurgia",
            codigo_hash="obs-cleanup-001",
        )
        banco.add(laudo)
        banco.flush()

        mensagem = MensagemLaudo(
            laudo_id=laudo.id,
            remetente_id=usuario.id,
            tipo=TipoMensagem.HUMANO_INSP.value,
            conteudo="mensagem observation",
        )
        banco.add(mensagem)
        banco.flush()

        referenced_profile = profile_root / str(empresa.id) / "referenced.png"
        orphan_profile = profile_root / str(empresa.id) / "orphan-old.png"
        recent_profile = profile_root / str(empresa.id) / "recent.png"
        referenced_attachment = mesa_root / str(empresa.id) / str(laudo.id) / "referenced.pdf"
        orphan_attachment = mesa_root / str(empresa.id) / str(laudo.id) / "orphan-old.pdf"
        recent_attachment = mesa_root / str(empresa.id) / str(laudo.id) / "recent.pdf"
        referenced_learning = learning_root / str(empresa.id) / str(laudo.id) / "referenced.webp"
        orphan_learning = learning_root / str(empresa.id) / str(laudo.id) / "orphan-old.webp"
        recent_learning = learning_root / str(empresa.id) / str(laudo.id) / "recent.webp"

        for path in (
            referenced_profile,
            orphan_profile,
            referenced_attachment,
            orphan_attachment,
            referenced_learning,
            orphan_learning,
        ):
            _touch_file(path, age_days=120)
        for path in (recent_profile, recent_attachment, recent_learning):
            _touch_file(path, age_days=3)

        usuario.foto_perfil_url = f"/static/uploads/perfis/{empresa.id}/referenced.png"
        banco.add(
            AnexoMesa(
                laudo_id=laudo.id,
                mensagem_id=mensagem.id,
                enviado_por_id=usuario.id,
                nome_original="referenced.pdf",
                nome_arquivo="referenced.pdf",
                mime_type="application/pdf",
                categoria="documento",
                tamanho_bytes=11,
                caminho_arquivo=str(referenced_attachment),
            )
        )
        banco.add(
            AprendizadoVisualIa(
                empresa_id=empresa.id,
                laudo_id=laudo.id,
                criado_por_id=usuario.id,
                setor_industrial="metalurgia",
                resumo="observation learning",
                correcao_inspetor="corrigir",
                caminho_arquivo=str(referenced_learning),
                imagem_url=f"/static/uploads/aprendizados_ia/{empresa.id}/{laudo.id}/referenced.webp",
                imagem_nome_original="referenced.webp",
                imagem_mime_type="image/webp",
                imagem_sha256="observation-sha",
            )
        )
        banco.commit()

    return {
        "referenced_profile": str(referenced_profile),
        "orphan_profile": str(orphan_profile),
        "recent_profile": str(recent_profile),
        "referenced_attachment": str(referenced_attachment),
        "orphan_attachment": str(orphan_attachment),
        "recent_attachment": str(recent_attachment),
        "referenced_learning": str(referenced_learning),
        "orphan_learning": str(orphan_learning),
        "recent_learning": str(recent_learning),
    }


def _build_operational_snapshot(production_ops_module) -> dict[str, Any]:
    summary = production_ops_module.build_admin_production_operations_summary()
    uploads = dict(summary.get("uploads") or {})
    cleanup_runtime = dict(uploads.get("cleanup_runtime") or {})
    readiness = dict(summary.get("readiness") or {})
    return {
        "production_ops_ready": readiness.get("production_ready", False),
        "uploads_cleanup_scheduler_running": cleanup_runtime.get(
            "scheduler_running",
            False,
        ),
        "uploads_cleanup_last_status": cleanup_runtime.get("scheduler_last_status"),
        "uploads_cleanup_last_source": cleanup_runtime.get("scheduler_last_source"),
        "uploads_cleanup_last_mode": cleanup_runtime.get("scheduler_last_mode"),
    }


def _wait_for_scheduler_observation(
    *,
    uploads_cleanup_module,
    production_ops_module,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    last_ready: dict[str, Any] = {}
    last_runtime: dict[str, Any] = {}
    latest_report: dict[str, Any] = {}
    while time.time() < deadline:
        last_ready = _build_operational_snapshot(production_ops_module)
        last_runtime = uploads_cleanup_module.describe_uploads_cleanup_runtime()
        latest_report = dict(last_runtime.get("latest_report") or {})
        if (
            last_ready.get("uploads_cleanup_scheduler_running") is True
            and last_ready.get("uploads_cleanup_last_source") == "web_scheduler"
            and last_ready.get("uploads_cleanup_last_mode") == "apply"
            and latest_report.get("source") == "web_scheduler"
            and latest_report.get("mode") == "apply"
            and latest_report.get("status") == "ok"
        ):
            return last_ready, last_runtime, latest_report
        time.sleep(1)
    raise TimeoutError("Scheduler automatic cleanup was not observed within the timeout window.")


def _build_observation_payload(
    *,
    ready_payload: dict[str, Any],
    runtime_payload: dict[str, Any],
    report_payload: dict[str, Any],
    seeded_paths: dict[str, str],
    artifact_dir: Path,
) -> dict[str, Any]:
    report_payload = dict(report_payload)
    if not report_payload.get("report_path"):
        report_payload["report_path"] = runtime_payload.get("scheduler_last_report_path")
    deleted_paths = {str(item) for item in report_payload.get("deleted_paths") or []}
    preserved_paths = {
        key: Path(path).exists()
        for key, path in seeded_paths.items()
        if key.startswith("referenced_") or key.startswith("recent_")
    }
    removed_paths = {
        key: not Path(path).exists()
        for key, path in seeded_paths.items()
        if key.startswith("orphan_")
    }
    observation_status = "observacao_parcial"
    final_product_status = "ready_except_post_deploy_observation"
    blockers: list[str] = []
    if not all(preserved_paths.values()):
        blockers.append("cleanup_removed_referenced_or_recent_files")
        final_product_status = "bloqueado"
    if not all(removed_paths.values()):
        blockers.append("cleanup_did_not_remove_all_expected_orphans")
        final_product_status = "bloqueado"
    if ready_payload.get("production_ops_ready") is not True:
        blockers.append("production_ops_not_ready_in_equivalent_environment")
        final_product_status = "bloqueado"

    return {
        "contract_name": "FinalProductStampV1",
        "contract_version": "v1",
        "generated_at": _iso(),
        "observation_mode": "production_like_equivalent",
        "actual_deploy_observed": False,
        "equivalent_environment_observed": True,
        "post_deploy_observation_status": observation_status,
        "final_product_status": final_product_status,
        "mobile_v2_status": "closed_with_guardrails",
        "mobile_v2_guardrail_policy": "legacy_guardrail_only",
        "ready_payload": ready_payload,
        "cleanup_runtime": runtime_payload,
        "cleanup_report": report_payload,
        "deleted_paths": sorted(deleted_paths),
        "preserved_paths": preserved_paths,
        "removed_orphan_paths": removed_paths,
        "blockers": blockers,
        "notes": [
            "Observacao executada em ambiente local production-like com storage persistente real no filesystem do host.",
            "A primeira execucao automatica foi observada com source=web_scheduler e mode=apply.",
            "Deploy real nao foi observado nesta fase; o carimbo final permanece condicionado a observacao pos-deploy real se esse nivel de prova for exigido.",
        ],
        "artifact_dir": str(artifact_dir),
    }


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    cleanup_report = dict(payload.get("cleanup_report") or {})
    cleanup_runtime = dict(payload.get("cleanup_runtime") or {})
    ready_payload = dict(payload.get("ready_payload") or {})
    lines = [
        "# Post-Deploy Cleanup Observation",
        "",
        f"Gerado em: {payload.get('generated_at')}",
        "",
        "## Contexto",
        "",
        "- modo de observacao: production_like_equivalent",
        f"- observacao pos-deploy: {payload.get('post_deploy_observation_status')}",
        f"- status final do produto: {payload.get('final_product_status')}",
        "",
        "## Evidencia automatica do cleanup",
        "",
        f"- source: {cleanup_report.get('source')}",
        f"- mode: {cleanup_report.get('mode')}",
        f"- status: {cleanup_report.get('status')}",
        f"- report_path: {cleanup_report.get('report_path')}",
        f"- scheduler_running_durante_observacao: {ready_payload.get('uploads_cleanup_scheduler_running')}",
        f"- scheduler_last_source: {ready_payload.get('uploads_cleanup_last_source')}",
        f"- scheduler_last_mode: {ready_payload.get('uploads_cleanup_last_mode')}",
        f"- scheduler_last_status: {ready_payload.get('uploads_cleanup_last_status')}",
        f"- scheduler_last_run_at: {cleanup_runtime.get('scheduler_last_run_at')}",
        "",
        "## Guardrails verificados",
        "",
        f"- orphanos antigos removidos: {payload.get('removed_orphan_paths')}",
        f"- arquivos referenciados e recentes preservados: {payload.get('preserved_paths')}",
        f"- production_ops_ready no ambiente equivalente: {ready_payload.get('production_ops_ready')}",
        "",
        "## Leitura honesta",
        "",
        "- a execucao automatica foi realmente observada",
        "- a observacao ocorreu em ambiente production-like equivalente, nao em deploy real",
        "- o produto fica pronto exceto pela observacao pos-deploy real, caso esse nivel de prova seja exigido",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Observa a primeira execucao automatica do cleanup em ambiente production-like equivalente.",
    )
    parser.add_argument("--json", action="store_true", help="Imprime o payload final em JSON.")
    parser.add_argument("--strict", action="store_true", help="Falha com exit code 1 se houver blockers reais.")
    parser.add_argument("--timeout-seconds", type=int, default=90, help="Timeout maximo de observacao do scheduler.")
    args = parser.parse_args()

    artifact_dir = ARTIFACTS_ROOT / _now_utc().strftime("%Y%m%d_%H%M%S")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    env = _prepare_env(artifact_dir / "observation_env")
    runtime = _import_runtime(env)
    seeded_paths = _seed_observation_data(runtime)

    uploads_cleanup_module = runtime["uploads_cleanup_module"]
    production_ops_module = runtime["production_ops_module"]
    uploads_cleanup_module.start_uploads_cleanup_scheduler()
    try:
        ready_payload, runtime_payload, report_payload = _wait_for_scheduler_observation(
            uploads_cleanup_module=uploads_cleanup_module,
            production_ops_module=production_ops_module,
            timeout_seconds=max(args.timeout_seconds, 10),
        )
    finally:
        uploads_cleanup_module.stop_uploads_cleanup_scheduler()

    payload = _build_observation_payload(
        ready_payload=ready_payload,
        runtime_payload=runtime_payload,
        report_payload=report_payload,
        seeded_paths=seeded_paths,
        artifact_dir=artifact_dir,
    )

    observation_md = artifact_dir / "post_deploy_cleanup_observation.md"
    final_status_json = artifact_dir / "final_product_status.json"
    source_index = artifact_dir / "source_index.txt"

    _write_markdown(observation_md, payload)
    final_status_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    source_index.write_text(
        "\n".join(
            [
                "scripts/run_post_deploy_cleanup_observation.py",
                "web/app/domains/admin/uploads_cleanup.py",
                "web/app/domains/admin/production_ops_summary.py",
                "web/app/core/http_setup_support.py",
                "web/main.py",
                "docs/final-project-audit/09_mobile_v2_final_decision.md",
                "docs/final-project-audit/10_uploads_and_attachments_cleanup.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"post_deploy_observation_status: {payload['post_deploy_observation_status']}")
        print(f"final_product_status: {payload['final_product_status']}")
        print(f"cleanup_report_path: {report_payload.get('report_path')}")
        print(f"artifact_dir: {artifact_dir}")

    return 1 if args.strict and payload.get("blockers") else 0


if __name__ == "__main__":
    raise SystemExit(main())
