#!/usr/bin/env python3
"""Benchmarks repetiveis das superfícies críticas pós-plano."""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import statistics
import sys
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "post_plan_benchmarks"

if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.domains.chat.routes as rotas_inspetor
import app.domains.revisor.routes as rotas_revisor
import app.shared.database as banco_dados
import app.shared.security as seguranca
import main as app_main
from app.shared.database import (
    Base,
    Empresa,
    Laudo,
    LimitePlano,
    MensagemLaudo,
    NivelAcesso,
    PlanoEmpresa,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from tests.regras_rotas_criticas_support import (
    SENHA_HASH_PADRAO,
    _criar_laudo,
    _criar_template_ativo,
    _login_app_inspetor,
    _login_revisor,
)


def now_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def temporary_cwd(path: pathlib.Path) -> Iterator[None]:
    previous = pathlib.Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def write_text(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: pathlib.Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def percentile(sorted_samples: list[float], ratio: float) -> float:
    if not sorted_samples:
        return 0.0
    index = max(0, min(len(sorted_samples) - 1, round((len(sorted_samples) - 1) * ratio)))
    return sorted_samples[index]


def summarize_samples(*, samples_ms: list[float], iterations: int, warmups: int) -> dict[str, Any]:
    ordered = sorted(float(item) for item in samples_ms)
    return {
        "iterations": int(iterations),
        "warmups": int(warmups),
        "sample_count": len(ordered),
        "min_ms": round(min(ordered), 3) if ordered else 0.0,
        "median_ms": round(statistics.median(ordered), 3) if ordered else 0.0,
        "mean_ms": round(statistics.fmean(ordered), 3) if ordered else 0.0,
        "p95_ms": round(percentile(ordered, 0.95), 3) if ordered else 0.0,
        "max_ms": round(max(ordered), 3) if ordered else 0.0,
        "samples_ms": [round(item, 3) for item in ordered],
    }


@contextmanager
def critical_benchmark_env() -> Iterator[dict[str, Any]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)
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

        empresa_a = Empresa(nome_fantasia="Empresa A", cnpj="12345678000190", plano_ativo=PlanoEmpresa.ILIMITADO.value)
        empresa_b = Empresa(nome_fantasia="Empresa B", cnpj="22345678000190", plano_ativo=PlanoEmpresa.ILIMITADO.value)
        banco.add_all([empresa_a, empresa_b])
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
            empresa_id=empresa_a.id,
            nome_completo="Admin A",
            email="admin@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.DIRETORIA.value,
        )
        admin_cliente_a = Usuario(
            empresa_id=empresa_a.id,
            nome_completo="Admin Cliente A",
            email="cliente@empresa-a.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.ADMIN_CLIENTE.value,
        )
        inspetor_b = Usuario(
            empresa_id=empresa_b.id,
            nome_completo="Inspetor B",
            email="inspetor@empresa-b.test",
            senha_hash=SENHA_HASH_PADRAO,
            nivel_acesso=NivelAcesso.INSPETOR.value,
        )
        banco.add_all([inspetor_a, revisor_a, admin_a, admin_cliente_a, inspetor_b])
        banco.commit()

        ids = {
            "empresa_a": empresa_a.id,
            "empresa_b": empresa_b.id,
            "inspetor_a": inspetor_a.id,
            "revisor_a": revisor_a.id,
            "admin_a": admin_a.id,
            "admin_cliente_a": admin_cliente_a.id,
            "inspetor_b": inspetor_b.id,
        }

    def override_obter_banco() -> Iterator[Session]:
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

    app_main.app.dependency_overrides[banco_dados.obter_banco] = override_obter_banco

    sessao_local_banco_original = banco_dados.SessaoLocal
    sessao_local_seguranca_original = seguranca.SessaoLocal
    sessao_local_inspetor_original = rotas_inspetor.SessaoLocal
    sessao_local_revisor_original = rotas_revisor.SessaoLocal
    inicializar_banco_original = app_main.inicializar_banco
    banco_dados.SessaoLocal = SessionLocal
    seguranca.SessaoLocal = SessionLocal
    rotas_inspetor.SessaoLocal = SessionLocal
    rotas_revisor.SessaoLocal = SessionLocal
    app_main.inicializar_banco = lambda: None

    try:
        yield {"SessionLocal": SessionLocal, "ids": ids}
    finally:
        banco_dados.SessaoLocal = sessao_local_banco_original
        seguranca.SessaoLocal = sessao_local_seguranca_original
        rotas_inspetor.SessaoLocal = sessao_local_inspetor_original
        rotas_revisor.SessaoLocal = sessao_local_revisor_original
        app_main.inicializar_banco = inicializar_banco_original
        app_main.app.dependency_overrides.clear()
        seguranca.SESSOES_ATIVAS.clear()
        seguranca._SESSAO_EXPIRACAO.clear()  # noqa: SLF001
        seguranca._SESSAO_META.clear()  # noqa: SLF001
        engine.dispose()


def _seed_chat_case(*, banco: Session, ids: dict[str, int]) -> int:
    laudo_id = _criar_laudo(
        banco,
        empresa_id=ids["empresa_a"],
        usuario_id=ids["inspetor_a"],
        status_revisao=StatusRevisao.AGUARDANDO.value,
    )
    laudo = banco.get(Laudo, laudo_id)
    assert laudo is not None
    laudo.revisado_por = ids["revisor_a"]
    banco.flush()

    for index in range(24):
        tipo = TipoMensagem.HUMANO_INSP.value if index % 2 == 0 else TipoMensagem.HUMANO_ENG.value
        mensagem = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["inspetor_a"] if tipo == TipoMensagem.HUMANO_INSP.value else ids["revisor_a"],
            tipo=tipo,
            conteudo=f"Mensagem benchmark {index + 1}",
            lida=tipo == TipoMensagem.HUMANO_INSP.value,
            client_message_id=f"bench:{laudo_id}:{index + 1}",
        )
        banco.add(mensagem)
    banco.commit()
    return laudo_id


def _seed_pdf_case(*, banco: Session, ids: dict[str, int]) -> tuple[int, dict[str, Any]]:
    laudo_id = _criar_laudo(
        banco,
        empresa_id=ids["empresa_a"],
        usuario_id=ids["inspetor_a"],
        status_revisao=StatusRevisao.RASCUNHO.value,
    )
    laudo = banco.get(Laudo, laudo_id)
    assert laudo is not None
    laudo.tipo_template = "cbmgo"
    laudo.dados_formulario = {
        "informacoes_gerais": {
            "responsavel_pela_inspecao": "Gabriel Santos",
            "data_inspecao": "09/03/2026",
        }
    }
    banco.flush()

    _criar_template_ativo(
        banco,
        empresa_id=ids["empresa_a"],
        criado_por_id=ids["revisor_a"],
        codigo_template="cbmgo_cmar",
        versao=1,
        mapeamento={},
    )
    banco.commit()
    return laudo_id, {
        "diagnostico": "Diagnóstico benchmark pós-plano.",
        "inspetor": "Inspetor A",
        "empresa": "Empresa A",
        "setor": "geral",
        "data": "09/03/2026",
        "laudo_id": laudo_id,
        "tipo_template": "cbmgo",
    }


def run_named_benchmark(
    *,
    name: str,
    callback: Callable[[], dict[str, Any]],
    iterations: int,
    warmups: int,
) -> dict[str, Any]:
    for _ in range(max(0, int(warmups))):
        callback()

    samples_ms: list[float] = []
    last_observation: dict[str, Any] | None = None
    for _ in range(max(1, int(iterations))):
        started = time.perf_counter()
        last_observation = callback()
        finished = time.perf_counter()
        samples_ms.append((finished - started) * 1000.0)

    return {
        "name": name,
        "status": "ok",
        "stats": summarize_samples(
            samples_ms=samples_ms,
            iterations=iterations,
            warmups=warmups,
        ),
        "last_observation": last_observation or {},
    }


def run_post_plan_benchmarks(*, iterations: int = 3, warmups: int = 1) -> dict[str, Any]:
    with temporary_cwd(WEB_ROOT):
        with critical_benchmark_env() as env:
            SessionLocal = env["SessionLocal"]
            ids = env["ids"]
            with SessionLocal() as banco:
                chat_laudo_id = _seed_chat_case(banco=banco, ids=ids)
                pdf_laudo_id, pdf_payload = _seed_pdf_case(banco=banco, ids=ids)

            with TestClient(app_main.app) as inspector_client, TestClient(app_main.app) as revisor_client:
                inspector_csrf = _login_app_inspetor(inspector_client, "inspetor@empresa-a.test")
                _login_revisor(revisor_client, "revisor@empresa-a.test")

                def benchmark_chat_messages() -> dict[str, Any]:
                    response = inspector_client.get(f"/app/api/laudo/{chat_laudo_id}/mensagens")
                    assert response.status_code == 200
                    payload = response.json()
                    return {
                        "route": f"/app/api/laudo/{chat_laudo_id}/mensagens",
                        "status_code": response.status_code,
                        "message_count": len(payload.get("itens", [])),
                    }

                def benchmark_review_package() -> dict[str, Any]:
                    response = revisor_client.get(f"/revisao/api/laudo/{chat_laudo_id}/pacote")
                    assert response.status_code == 200
                    payload = response.json()
                    return {
                        "route": f"/revisao/api/laudo/{chat_laudo_id}/pacote",
                        "status_code": response.status_code,
                        "pending_count": len(payload.get("pendencias_abertas", [])),
                        "recent_message_count": len(payload.get("whispers_recentes", [])),
                    }

                def benchmark_document_pdf() -> dict[str, Any]:
                    response = inspector_client.post(
                        "/app/api/gerar_pdf",
                        headers={"X-CSRF-Token": inspector_csrf},
                        json=pdf_payload,
                    )
                    assert response.status_code == 200
                    assert response.content.startswith(b"%PDF")
                    return {
                        "route": "/app/api/gerar_pdf",
                        "status_code": response.status_code,
                        "laudo_id": pdf_laudo_id,
                        "pdf_size_bytes": len(response.content),
                    }

                benchmarks = [
                    run_named_benchmark(
                        name="chat_messages_request",
                        callback=benchmark_chat_messages,
                        iterations=iterations,
                        warmups=warmups,
                    ),
                    run_named_benchmark(
                        name="review_package_request",
                        callback=benchmark_review_package,
                        iterations=iterations,
                        warmups=warmups,
                    ),
                    run_named_benchmark(
                        name="document_pdf_request",
                        callback=benchmark_document_pdf,
                        iterations=iterations,
                        warmups=warmups,
                    ),
                ]

    return {
        "status": "ok",
        "executed_at": dt.datetime.now().isoformat(),
        "iterations": int(iterations),
        "warmups": int(warmups),
        "benchmarks": benchmarks,
    }


def build_final_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Post-plan benchmarks",
        "",
        f"- status: {summary.get('status', 'unknown')}",
        f"- executed_at: {summary.get('executed_at', '')}",
        f"- iterations: {summary.get('iterations', 0)}",
        f"- warmups: {summary.get('warmups', 0)}",
        "",
        "## Benchmarks",
    ]
    for item in summary.get("benchmarks", []):
        stats = item.get("stats", {})
        lines.extend(
            [
                f"- `{item.get('name', 'unknown')}`",
                f"  min/median/p95/max: {stats.get('min_ms', 0)} / {stats.get('median_ms', 0)} / {stats.get('p95_ms', 0)} / {stats.get('max_ms', 0)} ms",
                f"  observation: {json.dumps(item.get('last_observation', {}), ensure_ascii=False, sort_keys=True)}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    summary = run_post_plan_benchmarks()
    artifacts_dir = ensure_dir(ARTIFACTS_ROOT / now_slug())
    write_json(artifacts_dir / "post_plan_benchmarks_summary.json", summary)
    write_text(artifacts_dir / "final_report.md", build_final_report(summary))
    print(str(artifacts_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
