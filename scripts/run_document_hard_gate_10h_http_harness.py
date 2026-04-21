#!/usr/bin/env python3
"""Segundo harness local do Epic 10H para report_finalize_stream via HTTP/TestClient."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from typing import Any

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"

sys.path.insert(0, str(WEB_ROOT))

import app.shared.database as banco_dados  # noqa: E402
import app.shared.security as seguranca  # noqa: E402
import app.domains.chat.routes as rotas_inspetor  # noqa: E402
import app.domains.revisor.routes as rotas_revisor  # noqa: E402
import main as app_main  # noqa: E402
from app.shared.database import (  # noqa: E402
    Base,
    Empresa,
    Laudo,
    LimitePlano,
    MensagemLaudo,
    NivelAcesso,
    PlanoEmpresa,
    StatusRevisao,
    TemplateLaudo,
    TipoMensagem,
    Usuario,
)
from app.shared.security import criar_hash_senha  # noqa: E402
from app.v2.document import clear_document_hard_gate_metrics_for_tests  # noqa: E402
from app.v2.document.hard_gate_evidence import get_document_hard_gate_durable_summary  # noqa: E402

DEFAULT_PASSWORD = "Senha@123"
DEFAULT_PASSWORD_HASH = criar_hash_senha(DEFAULT_PASSWORD)


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


def _extrair_csrf(html: str) -> str:
    match_meta = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html, flags=re.IGNORECASE)
    if match_meta:
        return match_meta.group(1)

    match_input = re.search(r'name="csrf_token"[^>]*\svalue="(?!\$\{)([^"]+)"', html, flags=re.IGNORECASE)
    if match_input:
        return match_input.group(1)

    match_boot = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', html)
    if match_boot:
        return match_boot.group(1)

    raise AssertionError("Token CSRF nao encontrado no HTML.")


def _csrf_pagina(client: TestClient, rota: str) -> str:
    resposta = client.get(rota)
    assert resposta.status_code == 200
    return _extrair_csrf(resposta.text)


def _login_app_inspetor(client: TestClient, email: str) -> str:
    tela_login = client.get("/app/login")
    csrf = _extrair_csrf(tela_login.text)
    resposta = client.post(
        "/app/login",
        data={
            "email": email,
            "senha": DEFAULT_PASSWORD,
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/app/"
    return _csrf_pagina(client, "/app/")


def _salvar_pdf_temporario_teste(prefixo: str = "template") -> str:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer_path = pathlib.Path(tempfile.gettempdir()) / f"{prefixo}_{uuid.uuid4().hex[:10]}.pdf"
    with buffer_path.open("wb") as arquivo:
        writer.write(arquivo)
    return str(buffer_path)


def _criar_seed_minima(banco: Session) -> dict[str, int]:
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
    inspetor = Usuario(
        empresa_id=empresa.id,
        nome_completo="Inspetor A",
        email="inspetor@empresa-a.test",
        senha_hash=DEFAULT_PASSWORD_HASH,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )
    admin = Usuario(
        empresa_id=empresa.id,
        nome_completo="Admin A",
        email="admin@empresa-a.test",
        senha_hash=DEFAULT_PASSWORD_HASH,
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
    laudo.primeira_mensagem = "Inspecao inicial em equipamento critico."
    banco.add_all(
        [
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="Foram coletadas evidencias suficientes para o laudo.",
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
            nome=f"Template {codigo_template} http",
            codigo_template=codigo_template,
            versao=1,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base=_salvar_pdf_temporario_teste(f"http_{codigo_template}"),
            mapeamento_campos_json={},
            documento_editor_json=None,
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
    )
    banco.commit()


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


def build_final_report(case_payload: dict[str, Any], durable_summary: dict[str, Any]) -> str:
    blockers = ", ".join(case_payload.get("blockers") or []) or "nenhum"
    return "\n".join(
        [
            "# Epic 10H - validacao HTTP/TestClient",
            "",
            f"- harness: {case_payload['harness_name']}",
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
        help="Diretorio de artifacts para a rodada.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifacts_dir = (
        ensure_dir(pathlib.Path(args.output_dir).expanduser().resolve())
        if args.output_dir
        else ensure_dir((REPO_ROOT / "artifacts" / "document_hard_gate_validation_10h_http" / now_local_slug()).resolve())
    )
    responses_dir = ensure_dir(artifacts_dir / "responses")
    durable_root = ensure_dir(artifacts_dir / "durable_evidence")
    clear_document_hard_gate_metrics_for_tests()
    run_boot_import_check(artifacts_dir)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

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

    case_name = "shadow_stream_gap_padrao_http" if args.case == "gap" else "shadow_stream_ok_padrao_http"

    cwd_original = pathlib.Path.cwd()

    try:
        os.chdir(WEB_ROOT)
        with TestClient(app_main.app) as client:
            csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
            response = client.post(
                "/app/api/chat",
                headers={"X-CSRF-Token": csrf},
                json={
                    "mensagem": "COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO padrao",
                    "historico": [],
                    "laudo_id": laudo_id,
                },
            )
            response_text = response.text
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

    durable_summary = get_document_hard_gate_durable_summary(root=durable_root)
    recent_entry = durable_summary["recent_entries"][0]
    blockers = [item["blocker_code"] for item in list(recent_entry.get("blockers") or [])]
    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        case_payload = {
            "harness_name": "testclient_http_harness",
            "case_name": case_name,
            "laudo_id": laudo_id,
            "tenant_id": str(ids["empresa_a"]),
            "operation_kind": recent_entry["hard_gate_result"]["decision"]["operation_kind"],
            "route_name": recent_entry["hard_gate_result"]["decision"]["route_name"],
            "route_path": recent_entry["hard_gate_result"]["decision"]["route_path"],
            "source_channel": recent_entry["hard_gate_result"]["decision"]["source_channel"],
            "correlation_id": recent_entry["correlation"]["correlation_id"],
            "artifact_path": recent_entry["artifact_path"],
            "status_code": int(response.status_code),
            "media_type": str(response.headers.get("content-type", "").split(";")[0]),
            "sse_preservado": "data: [FIM]" in response_text,
            "functional_outcome": recent_entry["functional_outcome"],
            "shadow_only": bool(recent_entry["shadow_only"]),
            "would_block": bool(recent_entry["would_block"]),
            "did_block": bool(recent_entry["did_block"]),
            "enforce_enabled": bool(recent_entry["enforce_enabled"]),
            "blockers": blockers,
            "laudo_status_revisao": str(laudo.status_revisao),
            "encerrado_pelo_inspetor_em": (
                laudo.encerrado_pelo_inspetor_em.isoformat()
                if laudo.encerrado_pelo_inspetor_em is not None
                else None
            ),
        }

    write_text(responses_dir / f"{case_name}_response.sse", response_text)
    write_json(responses_dir / f"{case_name}_artifact.json", recent_entry)
    write_json(artifacts_dir / "validation_cases.json", [case_payload])
    write_json(
        artifacts_dir / "runtime_summary.json",
        {
            "harness_name": "testclient_http_harness",
            "case_name": case_name,
            "flags": flags,
            "durable_summary": durable_summary,
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
            ]
        )
        + "\n",
    )
    write_text(
        artifacts_dir / "final_report.md",
        build_final_report(case_payload, durable_summary),
    )

    engine.dispose()
    print(str(artifacts_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
