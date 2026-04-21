"""Emissão oficial transacional com congelamento do bundle emitido."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.paths import WEB_ROOT
from app.domains.chat.media_helpers import safe_remove_file
from app.domains.mesa.service import montar_pacote_mesa_laudo
from app.domains.revisor.service_contracts import PacoteMesaCarregado
from app.domains.revisor.service_package import gerar_exportacao_pacote_mesa_laudo_zip
from app.shared.database import Laudo, Usuario
from app.shared.official_issue_package import (
    build_official_issue_fingerprint,
    build_official_issue_summary,
    load_active_official_issue_record,
    load_latest_approved_case_snapshot,
    persist_official_issue_record,
    resolve_official_issue_primary_pdf_artifact,
    resolve_signatory_for_official_issue,
    serialize_official_issue_record,
)


def _official_issue_storage_dir(*, tenant_id: int) -> Path:
    path = WEB_ROOT / "storage" / "laudos_emitidos" / f"empresa_{int(tenant_id)}" / "official_issues"
    path.mkdir(parents=True, exist_ok=True)
    return path


def emitir_oficialmente_transacional(
    banco: Session,
    *,
    laudo: Laudo,
    actor_user: Usuario,
    signatory_id: int | None = None,
    expected_active_issue_id: int | None = None,
    expected_active_issue_number: str | None = None,
) -> dict[str, Any]:
    summary = build_official_issue_summary(banco, laudo=laudo)
    if not bool(summary.get("ready_for_issue")):
        blockers = list(summary.get("blockers") or [])
        message = str((blockers[0] or {}).get("message") or "A emissão oficial ainda está bloqueada.")
        raise ValueError(message)

    signatory, _selected = resolve_signatory_for_official_issue(
        banco,
        laudo=laudo,
        signatory_id=signatory_id,
    )
    latest_snapshot = load_latest_approved_case_snapshot(banco, laudo=laudo)
    pacote = montar_pacote_mesa_laudo(banco, laudo=laudo)
    pacote_carregado = PacoteMesaCarregado(laudo=laudo, pacote=pacote)
    exportacao = gerar_exportacao_pacote_mesa_laudo_zip(
        banco,
        pacote_carregado=pacote_carregado,
        usuario=actor_user,
    )

    try:
        package_bytes = Path(exportacao.caminho_zip).read_bytes()
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()
        with zipfile.ZipFile(io.BytesIO(package_bytes)) as zip_file:
            manifest_payload = json.loads(zip_file.read("manifest.json").decode("utf-8"))

        package_fingerprint_sha256 = build_official_issue_fingerprint(
            laudo=laudo,
            signatory_id=int(signatory.id),
            approval_snapshot_id=int(getattr(latest_snapshot, "id", 0) or 0) or None,
            manifest_payload=manifest_payload,
        )
        primary_pdf_artifact = resolve_official_issue_primary_pdf_artifact(laudo)
        verification_url = str((summary or {}).get("verification_url") or "").strip() or None
        record, idempotent_replay = persist_official_issue_record(
            banco,
            laudo=laudo,
            signatory=signatory,
            issued_by_user_id=int(getattr(actor_user, "id", 0) or 0) or None,
            package_sha256=package_sha256,
            package_fingerprint_sha256=package_fingerprint_sha256,
            package_filename=exportacao.filename,
            package_storage_path=None,
            package_size_bytes=len(package_bytes),
            manifest_payload=manifest_payload,
            primary_pdf_artifact=primary_pdf_artifact,
            verification_url=verification_url,
            expected_active_issue_id=expected_active_issue_id,
            expected_active_issue_number=expected_active_issue_number,
        )

        if not idempotent_replay:
            storage_dir = _official_issue_storage_dir(tenant_id=int(getattr(laudo, "empresa_id", 0) or 0))
            safe_issue_number = str(getattr(record, "issue_number", "") or "issue").replace("/", "_")
            storage_name = f"{safe_issue_number}.zip"
            storage_path = storage_dir / storage_name
            storage_path.write_bytes(package_bytes)
            record.package_filename = storage_name
            record.package_storage_path = str(storage_path)
            record.package_size_bytes = len(package_bytes)
            banco.flush()

        current_record = load_active_official_issue_record(banco, laudo=laudo)
        serialized = serialize_official_issue_record(current_record or record)
        return {
            "record": current_record or record,
            "record_payload": serialized,
            "idempotent_replay": idempotent_replay,
            "download_filename": str(getattr(current_record or record, "package_filename", "") or ""),
            "download_storage_path": str(getattr(current_record or record, "package_storage_path", "") or ""),
        }
    finally:
        safe_remove_file(exportacao.caminho_zip)


__all__ = [
    "emitir_oficialmente_transacional",
]
