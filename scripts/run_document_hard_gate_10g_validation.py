#!/usr/bin/env python3
"""Runner local do Epic 10G para report_finalize_stream em shadow_only."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import uuid
from typing import Any

from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "document_hard_gate_validation_10g"

sys.path.insert(0, str(WEB_ROOT))

from starlette.requests import Request  # noqa: E402

from app.shared.database import (  # noqa: E402
    Base,
    Empresa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    StatusRevisao,
    TemplateLaudo,
    TipoMensagem,
    Usuario,
)
from app.shared.security import criar_hash_senha  # noqa: E402
from app.domains.chat.chat_stream_routes import rota_chat  # noqa: E402
from app.domains.chat.schemas import DadosChat  # noqa: E402
from app.v2.document import (  # noqa: E402
    clear_document_hard_gate_metrics_for_tests,
    get_document_hard_gate_operational_summary,
)
from app.v2.document.hard_gate_evidence import (  # noqa: E402
    export_document_hard_gate_durable_snapshot,
    get_document_hard_gate_durable_summary,
)


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
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    save_command_artifact(artifacts_dir / "boot_import_check.txt", command, completed)
    if completed.returncode != 0:
        raise RuntimeError("Boot/import check falhou.")


def _salvar_pdf_temporario_teste(prefixo: str = "template") -> str:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer_path = pathlib.Path(tempfile.gettempdir()) / f"{prefixo}_{uuid.uuid4().hex[:10]}.pdf"
    with buffer_path.open("wb") as arquivo:
        writer.write(arquivo)
    return str(buffer_path)


def _criar_seed_minima(banco: Session) -> dict[str, int]:
    empresa = Empresa(nome_fantasia="Empresa A", cnpj="12345678000190", plano_ativo="ilimitado")
    banco.add(empresa)
    banco.flush()

    inspetor = Usuario(
        empresa_id=empresa.id,
        nome_completo="Inspetor A",
        email="inspetor@empresa-a.test",
        senha_hash=criar_hash_senha("Senha@123"),
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )
    admin = Usuario(
        empresa_id=empresa.id,
        nome_completo="Admin A",
        email="admin@empresa-a.test",
        senha_hash=criar_hash_senha("Senha@123"),
        nivel_acesso=NivelAcesso.DIRETORIA.value,
    )
    banco.add_all([inspetor, admin])
    banco.commit()
    banco.refresh(empresa)
    banco.refresh(inspetor)
    banco.refresh(admin)
    return {
        "empresa_a": int(empresa.id),
        "inspetor_a": int(inspetor.id),
        "admin_a": int(admin.id),
    }


def _criar_laudo(
    banco: Session,
    *,
    empresa_id: int,
    usuario_id: int,
    status_revisao: str,
    tipo_template: str = "padrao",
) -> int:
    laudo = Laudo(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        setor_industrial="geral",
        tipo_template=tipo_template,
        status_revisao=status_revisao,
        codigo_hash=uuid.uuid4().hex,
        modo_resposta="detalhado",
        is_deep_research=False,
    )
    banco.add(laudo)
    banco.commit()
    banco.refresh(laudo)
    return int(laudo.id)


def _preparar_laudo_finalizavel_stream(
    banco: Session,
    *,
    empresa_id: int,
    usuario_id: int,
    tipo_template: str = "padrao",
) -> int:
    laudo_id = _criar_laudo(
        banco,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        status_revisao=StatusRevisao.RASCUNHO.value,
        tipo_template=tipo_template,
    )
    laudo = banco.get(Laudo, laudo_id)
    assert laudo is not None
    laudo.primeira_mensagem = "Inspeção inicial em equipamento crítico."
    banco.add_all(
        [
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="Foram coletadas evidências suficientes para o laudo.",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="[imagem]",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer preliminar com apoio documental.",
            ),
        ]
    )
    banco.commit()
    return laudo_id


def _criar_template_ativo_stream(
    banco: Session,
    *,
    empresa_id: int,
    criado_por_id: int,
    codigo_template: str = "padrao",
) -> None:
    banco.add(
        TemplateLaudo(
            empresa_id=empresa_id,
            criado_por_id=criado_por_id,
            nome=f"Template {codigo_template} stream",
            codigo_template=codigo_template,
            versao=1,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base=_salvar_pdf_temporario_teste(f"stream_{codigo_template}"),
            mapeamento_campos_json={},
            documento_editor_json=None,
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
    )
    banco.commit()


def build_chat_request(laudo_id: int, csrf: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/app/api/chat",
            "headers": [(b"x-csrf-token", csrf.encode())],
            "query_string": b"",
            "session": {
                "csrf_token_inspetor": csrf,
                "laudo_ativo_id": int(laudo_id),
                "estado_relatorio": "relatorio_ativo",
            },
            "state": {},
            "client": ("testclient", 50120),
        }
    )


async def read_stream(response) -> str:
    partes: list[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            partes.append(chunk.decode())
        else:
            partes.append(str(chunk))
    return "".join(partes)


def configure_env(tenant_id: int, durable_root: pathlib.Path) -> dict[str, str]:
    flags = {
        "AMBIENTE": "dev",
        "TARIEL_V2_DOCUMENT_HARD_GATE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS": str(tenant_id),
        "TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS": "report_finalize_stream",
        "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE": "1",
        "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR": str(durable_root),
    }
    os.environ.update(flags)
    return flags


def build_final_report(case_payload: dict[str, Any], runtime_summary: dict[str, Any], durable_summary: dict[str, Any]) -> str:
    blockers = ", ".join(case_payload.get("blockers") or []) or "nenhum"
    return "\n".join(
        [
            "# Epic 10G - validacao controlada",
            "",
            f"- caso: {case_payload['case_name']}",
            f"- status_http: {case_payload['status_code']}",
            f"- media_type: {case_payload['media_type']}",
            f"- sse_preservado: {case_payload['sse_preservado']}",
            f"- shadow_only: {case_payload['shadow_only']}",
            f"- would_block: {case_payload['would_block']}",
            f"- did_block: {case_payload['did_block']}",
            f"- blockers: {blockers}",
            f"- artifact_path: {case_payload.get('artifact_path') or 'nenhum'}",
            "",
            "## Runtime summary",
            "",
            f"- evaluations: {runtime_summary['totals']['evaluations']}",
            f"- shadow_only: {runtime_summary['totals']['shadow_only']}",
            f"- did_block: {runtime_summary['totals']['did_block']}",
            "",
            "## Durable summary",
            "",
            f"- evaluations: {durable_summary['totals']['evaluations']}",
            f"- shadow_only: {durable_summary['totals']['shadow_only']}",
            f"- did_block: {durable_summary['totals']['did_block']}",
        ]
    ) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=("gap", "template_ok"),
        default="gap",
        help="Caso controlado a executar.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Diretorio de artifacts. Quando omitido, cria em artifacts/document_hard_gate_validation_10g/<timestamp>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifacts_dir = ensure_dir(pathlib.Path(args.output_dir).expanduser()) if args.output_dir else ensure_dir(ARTIFACTS_ROOT / now_local_slug())
    responses_dir = ensure_dir(artifacts_dir / "responses")
    summaries_dir = ensure_dir(artifacts_dir / "summaries")
    durable_root = ensure_dir(artifacts_dir / "durable_evidence")

    clear_document_hard_gate_metrics_for_tests()
    run_boot_import_check(artifacts_dir)

    db_path = artifacts_dir / "validation_10g.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    case_name = "shadow_stream_gap_padrao_10g" if args.case == "gap" else "shadow_stream_ok_padrao_10g"
    csrf = f"csrf-{case_name}"

    with SessionLocal() as banco:
        ids = _criar_seed_minima(banco)
        if args.case == "template_ok":
            _criar_template_ativo_stream(
                banco,
                empresa_id=ids["empresa_a"],
                criado_por_id=ids["inspetor_a"],
                codigo_template="padrao",
            )
        laudo_id = _preparar_laudo_finalizavel_stream(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="padrao",
        )

    flags = configure_env(ids["empresa_a"], durable_root)
    write_json(artifacts_dir / "flags_snapshot.json", flags)

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        request = build_chat_request(laudo_id, csrf)
        response = asyncio.run(
            rota_chat(
                dados=DadosChat(
                    mensagem="COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO padrao",
                    historico=[],
                    laudo_id=laudo_id,
                ),
                request=request,
                usuario=usuario,
                banco=banco,
            )
        )
        sse_body = asyncio.run(read_stream(response))
        laudo_atual = banco.get(Laudo, laudo_id)
        assert laudo_atual is not None

        hard_gate_payload = getattr(request.state, "v2_document_hard_gate_enforcement", None)
        observation_payload = getattr(request.state, "v2_report_finalize_stream_shadow_observation", None)
        artifact_path = getattr(request.state, "v2_report_finalize_stream_shadow_artifact_path", None)

    runtime_summary = get_document_hard_gate_operational_summary()
    durable_summary = get_document_hard_gate_durable_summary(root=durable_root)
    exported_snapshot = export_document_hard_gate_durable_snapshot(
        summaries_dir,
        operation_kind="report_finalize_stream",
    )

    artifact_payload = {}
    if artifact_path:
        artifact_payload = json.loads(pathlib.Path(artifact_path).read_text(encoding="utf-8"))

    blockers = [item["blocker_code"] for item in list((artifact_payload or {}).get("blockers") or [])]
    case_payload = {
        "case_name": case_name,
        "laudo_id": laudo_id,
        "status_code": int(response.status_code),
        "media_type": str(response.media_type or ""),
        "sse_preservado": "data: [FIM]" in sse_body,
        "shadow_only": bool((artifact_payload or {}).get("shadow_only")),
        "would_block": bool((artifact_payload or {}).get("would_block")),
        "did_block": bool((artifact_payload or {}).get("did_block")),
        "blockers": blockers,
        "artifact_path": artifact_path,
        "hard_gate_payload": hard_gate_payload,
        "observation_payload": observation_payload,
        "laudo_status_revisao": str(laudo_atual.status_revisao),
        "encerrado_pelo_inspetor_em": (
            laudo_atual.encerrado_pelo_inspetor_em.isoformat()
            if laudo_atual.encerrado_pelo_inspetor_em is not None
            else None
        ),
    }

    write_text(responses_dir / f"{case_name}_response.sse", sse_body)
    write_json(responses_dir / f"{case_name}_artifact.json", artifact_payload)
    write_json(artifacts_dir / "validation_cases.json", [case_payload])
    write_json(
        artifacts_dir / "runtime_summary.json",
        {
            "case_name": case_name,
            "flags": flags,
            "runtime_summary": runtime_summary,
            "durable_summary": durable_summary,
            "exported_snapshot": exported_snapshot,
        },
    )
    write_json(artifacts_dir / "durable_summary.json", durable_summary)
    write_text(
        artifacts_dir / "source_artifacts_index.txt",
        "\n".join(
            [
                str(artifacts_dir / "boot_import_check.txt"),
                str(artifacts_dir / "flags_snapshot.json"),
                str(artifacts_dir / "runtime_summary.json"),
                str(artifacts_dir / "durable_summary.json"),
                str(artifacts_dir / "validation_cases.json"),
                str(responses_dir / f"{case_name}_response.sse"),
                str(responses_dir / f"{case_name}_artifact.json"),
                str(pathlib.Path(exported_snapshot["summary_path"])),
                str(pathlib.Path(exported_snapshot["entries_path"])),
            ]
        )
        + "\n",
    )
    write_text(
        artifacts_dir / "final_report.md",
        build_final_report(case_payload, runtime_summary, durable_summary),
    )

    print(str(artifacts_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
