from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import get_settings
import app.domains.admin.uploads_cleanup as uploads_cleanup
from app.domains.admin.uploads_cleanup import (
    describe_uploads_cleanup_runtime,
    run_uploads_cleanup,
    start_uploads_cleanup_scheduler,
    stop_uploads_cleanup_scheduler,
)
from app.shared.database import AnexoMesa, AprendizadoVisualIa, Laudo, MensagemLaudo, TipoMensagem, Usuario


def _touch_old_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("seed", encoding="utf-8")
    old = time.time() - (400 * 86400)
    os.utime(path, (old, old))


def _wait_until(predicate, *, timeout: float = 1.5, interval: float = 0.02) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


def test_uploads_cleanup_remove_apenas_orfaos_com_guardrails(ambiente_critico, monkeypatch, tmp_path: Path) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    perfis = tmp_path / "uploads" / "perfis"
    anexos = tmp_path / "uploads" / "mesa_anexos"
    aprendizados = tmp_path / "uploads" / "aprendizados_ia"

    referenced_profile = perfis / str(ids["empresa_a"]) / "referenced.png"
    orphan_profile = perfis / str(ids["empresa_a"]) / "orphan.png"
    referenced_attachment = anexos / str(ids["empresa_a"]) / "10" / "referenced.pdf"
    orphan_attachment = anexos / str(ids["empresa_a"]) / "10" / "orphan.pdf"
    referenced_learning = aprendizados / str(ids["empresa_a"]) / "10" / "referenced.webp"
    orphan_learning = aprendizados / str(ids["empresa_a"]) / "10" / "orphan.webp"

    for path in (
        referenced_profile,
        orphan_profile,
        referenced_attachment,
        orphan_attachment,
        referenced_learning,
        orphan_learning,
    ):
        _touch_old_file(path)

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        usuario.foto_perfil_url = f"/static/uploads/perfis/{ids['empresa_a']}/referenced.png"

        laudo = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="metalurgia",
            codigo_hash="cleanup-laudo-001",
        )
        banco.add(laudo)
        banco.flush()

        mensagem = MensagemLaudo(
            laudo_id=laudo.id,
            remetente_id=ids["inspetor_a"],
            tipo=TipoMensagem.HUMANO_INSP.value,
            conteudo="mensagem seed",
        )
        banco.add(mensagem)
        banco.flush()

        banco.add(
            AnexoMesa(
                laudo_id=laudo.id,
                mensagem_id=mensagem.id,
                enviado_por_id=ids["inspetor_a"],
                nome_original="referenced.pdf",
                nome_arquivo="referenced.pdf",
                mime_type="application/pdf",
                categoria="documento",
                tamanho_bytes=4,
                caminho_arquivo=str(referenced_attachment),
            )
        )
        banco.add(
            AprendizadoVisualIa(
                empresa_id=ids["empresa_a"],
                laudo_id=laudo.id,
                criado_por_id=ids["inspetor_a"],
                setor_industrial="metalurgia",
                resumo="aprendizado seed",
                correcao_inspetor="corrigir",
                caminho_arquivo=str(referenced_learning),
                imagem_url=f"/static/uploads/aprendizados_ia/{ids['empresa_a']}/{laudo.id}/referenced.webp",
                imagem_nome_original="referenced.webp",
                imagem_mime_type="image/webp",
                imagem_sha256="abc123",
            )
        )
        banco.commit()

    monkeypatch.setenv("PASTA_UPLOADS_PERFIS", str(perfis))
    monkeypatch.setenv("PASTA_ANEXOS_MESA", str(anexos))
    monkeypatch.setenv("PASTA_APRENDIZADOS_VISUAIS_IA", str(aprendizados))
    monkeypatch.setenv("TARIEL_UPLOADS_PROFILE_RETENTION_DAYS", "365")
    monkeypatch.setenv("TARIEL_UPLOADS_MESA_RETENTION_DAYS", "365")
    monkeypatch.setenv("TARIEL_UPLOADS_LEARNING_RETENTION_DAYS", "365")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_GRACE_DAYS", "14")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_MAX_DELETIONS_PER_RUN", "20")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_ENABLED", "1")
    get_settings.cache_clear()

    try:
        payload_dry_run = run_uploads_cleanup(apply=False, source="pytest_dry_run", strict=True)
        assert payload_dry_run["totals"]["eligible_files"] == 3
        assert referenced_profile.exists() is True
        assert referenced_attachment.exists() is True
        assert referenced_learning.exists() is True
        assert orphan_profile.exists() is True
        assert orphan_attachment.exists() is True
        assert orphan_learning.exists() is True

        payload_apply = run_uploads_cleanup(apply=True, source="pytest_apply", strict=True)
        assert payload_apply["totals"]["deleted_files"] == 3
        runtime = describe_uploads_cleanup_runtime()
        assert dict(runtime.get("latest_report") or {}).get("source") == "pytest_apply"
        assert dict(runtime.get("latest_report") or {}).get("mode") == "apply"
        assert referenced_profile.exists() is True
        assert referenced_attachment.exists() is True
        assert referenced_learning.exists() is True
        assert orphan_profile.exists() is False
        assert orphan_attachment.exists() is False
        assert orphan_learning.exists() is False
    finally:
        get_settings.cache_clear()


def test_uploads_cleanup_scheduler_aguarda_bootstrap_do_banco(monkeypatch, tmp_path: Path) -> None:
    perfis = tmp_path / "uploads" / "perfis"
    anexos = tmp_path / "uploads" / "mesa_anexos"
    aprendizados = tmp_path / "uploads" / "aprendizados_ia"
    chamadas: list[dict[str, object]] = []
    gate = {"ready": False}

    monkeypatch.setenv("PASTA_UPLOADS_PERFIS", str(perfis))
    monkeypatch.setenv("PASTA_ANEXOS_MESA", str(anexos))
    monkeypatch.setenv("PASTA_APRENDIZADOS_VISUAIS_IA", str(aprendizados))
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_ENABLED", "1")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_INTERVAL_HOURS", "24")
    monkeypatch.setattr(uploads_cleanup, "_SLEEP_SECONDS", 0.05, raising=False)

    def _fake_run_uploads_cleanup(*, apply: bool, source: str, strict: bool = False, now=None):
        chamadas.append(
            {
                "apply": apply,
                "source": source,
                "strict": strict,
                "now": now,
            }
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "report_path": str(tmp_path / "report.json"),
            "mode": "apply" if apply else "dry_run",
            "source": source,
        }

    monkeypatch.setattr(uploads_cleanup, "run_uploads_cleanup", _fake_run_uploads_cleanup)
    get_settings.cache_clear()

    try:
        start_uploads_cleanup_scheduler(
            ready_probe=lambda: gate["ready"],
            wait_reason="db_bootstrap_pending",
        )

        assert _wait_until(
            lambda: describe_uploads_cleanup_runtime()["scheduler_running"] is True
        )
        time.sleep(0.15)
        assert chamadas == []
        assert (
            describe_uploads_cleanup_runtime()["scheduler_wait_reason"]
            == "db_bootstrap_pending"
        )

        gate["ready"] = True
        assert _wait_until(lambda: len(chamadas) >= 1)
        runtime = describe_uploads_cleanup_runtime()
        assert runtime["scheduler_wait_reason"] is None
        assert runtime["scheduler_last_source"] == "web_scheduler"
        assert runtime["scheduler_last_mode"] == "apply"
    finally:
        stop_uploads_cleanup_scheduler()
        get_settings.cache_clear()
