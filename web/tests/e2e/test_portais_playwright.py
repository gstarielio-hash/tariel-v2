from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Browser, Page, expect

from app.domains.admin.mfa import current_totp

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E", "0") != "1",
    reason="Defina RUN_E2E=1 para executar os testes Playwright.",
)

PNG_1X1_TRANSPARENTE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0X8AAAAASUVORK5CYII="
_ADMIN_TOTP_SECRET_CACHE: str | None = None
_LOGIN_REDIRECT_TIMEOUT_MS = 15_000


def _obter_segredo_totp_admin_no_banco(email: str = "admin@tariel.ia") -> str | None:
    database_url = (
        os.getenv("E2E_LOCAL_DATABASE_URL", "").strip()
        or os.getenv("DATABASE_URL", "").strip()
    )
    if not database_url.startswith("sqlite:///"):
        return None

    caminho_db = database_url.removeprefix("sqlite:///").split("?", 1)[0].strip()
    if not caminho_db:
        return None

    conexao = sqlite3.connect(caminho_db)
    try:
        cursor = conexao.execute(
            "select mfa_secret_b32 from usuarios where email = ? and ativo = 1 limit 1",
            (email,),
        )
        linha = cursor.fetchone()
    finally:
        conexao.close()

    if not linha or not linha[0]:
        return None
    return str(linha[0]).strip() or None


def _extrair_segredo_totp_admin(page: Page) -> str:
    conteudo = page.content()
    match_uri = re.search(r"secret=([A-Z2-7]+)", conteudo)
    if match_uri:
        return match_uri.group(1)

    match_segredo = re.search(r"Segredo TOTP:\s*</li>|Segredo TOTP:\s*<code>([A-Z2-7 ]+)</code>", conteudo)
    if match_segredo and match_segredo.group(1):
        return re.sub(r"\s+", "", match_segredo.group(1))

    texto = page.locator("body").inner_text()
    match_texto = re.search(r"Segredo TOTP:\s*([A-Z2-7 ]+)", texto)
    if match_texto:
        return re.sub(r"\s+", "", match_texto.group(1))

    raise AssertionError("Segredo TOTP do Admin-CEO não encontrado na tela de setup.")


def _concluir_mfa_admin(page: Page, *, rota_sucesso_regex: str) -> None:
    global _ADMIN_TOTP_SECRET_CACHE

    if re.search(r"/admin/mfa/setup/?$", page.url):
        _ADMIN_TOTP_SECRET_CACHE = _extrair_segredo_totp_admin(page)
        page.locator('input[name="codigo"]').fill(current_totp(_ADMIN_TOTP_SECRET_CACHE))
        page.locator('button[type="submit"]').click()

    if re.search(r"/admin/mfa/challenge/?$", page.url):
        if not _ADMIN_TOTP_SECRET_CACHE:
            _ADMIN_TOTP_SECRET_CACHE = _obter_segredo_totp_admin_no_banco()
        if not _ADMIN_TOTP_SECRET_CACHE:
            raise AssertionError("Segredo TOTP do Admin-CEO indisponível para concluir o challenge MFA.")
        page.locator('input[name="codigo"]').fill(current_totp(_ADMIN_TOTP_SECRET_CACHE))
        page.locator('button[type="submit"]').click()

    expect(page).to_have_url(
        re.compile(rota_sucesso_regex),
        timeout=_LOGIN_REDIRECT_TIMEOUT_MS,
    )


def _fazer_login(
    page: Page,
    *,
    base_url: str,
    portal: str,
    email: str,
    senha: str,
    rota_sucesso_regex: str,
) -> str:
    page.goto(f"{base_url}/{portal}/login", wait_until="domcontentloaded")
    token_input = page.locator('input[name="csrf_token"]').first
    csrf_token = token_input.input_value() if token_input.count() else ""
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="senha"]').fill(senha)
    page.locator('button[type="submit"]').first.click()
    if portal == "admin" and re.search(r"/admin/mfa/(setup|challenge)/?$", page.url):
        _concluir_mfa_admin(page, rota_sucesso_regex=rota_sucesso_regex)
    else:
        expect(page).to_have_url(
            re.compile(rota_sucesso_regex),
            timeout=_LOGIN_REDIRECT_TIMEOUT_MS,
        )
    if portal == "app":
        page.wait_for_function(
            """() => Boolean(
                document.getElementById("painel-chat") &&
                window.TarielInspetorRuntime &&
                typeof window.TarielInspetorRuntime.actions?.abrirModalNovaInspecao === "function"
            )"""
        )
    return csrf_token


def _api_fetch(
    page: Page,
    *,
    path: str,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, str] | None = None,
    csrf_token_override: str | None = None,
) -> dict[str, Any]:
    csrf_token = str(csrf_token_override or "").strip() or _csrf_token_from_page(page)

    headers: dict[str, str] = {}
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token

    kwargs: dict[str, Any] = {
        "method": method.upper(),
        "headers": headers,
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        kwargs["data"] = json.dumps(json_body, ensure_ascii=False)
    elif form_body is not None:
        kwargs["form"] = form_body

    resposta = page.request.fetch(urljoin(page.url, path), **kwargs)
    raw = resposta.text()
    try:
        parsed = resposta.json()
    except Exception:
        parsed = None

    content_type = resposta.headers.get("content-type", "")
    return {
        "status": resposta.status,
        "ok": resposta.ok,
        "url": resposta.url,
        "body": parsed,
        "raw": raw,
        "contentType": content_type,
    }


def _csrf_token_from_page(page: Page) -> str:
    csrf_meta = page.locator('meta[name="csrf-token"]').first
    csrf_token = csrf_meta.get_attribute("content") if csrf_meta.count() else ""
    if csrf_token:
        return csrf_token
    token_input = page.locator('input[name="csrf_token"]').first
    return token_input.input_value() if token_input.count() else ""


def _csrf_token_from_authenticated_html(page: Page, *, path: str) -> str:
    html = page.content()
    if not html.strip():
        resposta = page.request.fetch(urljoin(page.url, path), method="GET")
        assert resposta.status == 200, f"Falha ao obter HTML autenticado para CSRF: {resposta.status}"
        html = resposta.text()
    match_meta = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
    if match_meta:
        return match_meta.group(1)
    match_input = re.search(r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"', html)
    if match_input:
        return match_input.group(1)
    resumo_html = re.sub(r"\s+", " ", html).strip()[:400]
    raise AssertionError(f"Token CSRF autenticado não encontrado no HTML do painel. HTML parcial: {resumo_html}")


def _csrf_token_from_session_cookie(page: Page) -> str:
    cookie_debug: list[str] = []
    for cookie in page.context.cookies():
        cookie_name = str(cookie.get("name") or "")
        cookie_debug.append(cookie_name)
        if cookie_name not in {"session", "cracha_tariel_seguro"}:
            continue
        raw_value = str(cookie.get("value") or "").strip()
        if not raw_value:
            continue
        payload_segment = raw_value.split(".", 1)[0].strip()
        if not payload_segment:
            continue
        padding = "=" * (-len(payload_segment) % 4)
        try:
            decoded = base64.urlsafe_b64decode(f"{payload_segment}{padding}".encode("ascii"))
            payload = json.loads(decoded.decode("utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        for key in ("csrf_token_revisor", "csrf_token"):
            candidate = str(payload.get(key) or "").strip()
            if candidate:
                return candidate
    raise AssertionError(
        "Token CSRF do revisor não encontrado no cookie de sessão. "
        f"Cookies visíveis: {', '.join(cookie_debug) or '<nenhum>'}"
    )


def _api_fetch_bytes(
    page: Page,
    *,
    path: str,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, str] | None = None,
    csrf_token_override: str | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    csrf_token = str(csrf_token_override or "").strip() or _csrf_token_from_page(page)
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token

    kwargs: dict[str, Any] = {
        "method": method.upper(),
        "headers": headers,
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        kwargs["data"] = json.dumps(json_body, ensure_ascii=False)
    elif form_body is not None:
        kwargs["form"] = form_body

    resposta = page.request.fetch(urljoin(page.url, path), **kwargs)
    return {
        "status": resposta.status,
        "ok": resposta.ok,
        "url": resposta.url,
        "body": resposta.body(),
        "contentType": resposta.headers.get("content-type", ""),
    }


def _database_path_from_url(database_url: str | None) -> Path:
    normalized = str(database_url or "").strip()
    if not normalized.startswith("sqlite:///"):
        raise AssertionError(f"Banco SQLite da sessão Playwright indisponível: {normalized or '<vazio>'}")
    return Path(normalized.removeprefix("sqlite:///").split("?", 1)[0].strip())


def _consultar_laudo_seed(database_url: str | None, laudo_id: int) -> dict[str, Any]:
    caminho_db = _database_path_from_url(database_url)
    with sqlite3.connect(caminho_db) as conexao:
        linha = conexao.execute(
            """
            select id, empresa_id, usuario_id, tipo_template, codigo_hash, nome_arquivo_pdf
              from laudos
             where id = ?
             limit 1
            """,
            (int(laudo_id),),
        ).fetchone()
    if linha is None:
        raise AssertionError(f"Laudo E2E não encontrado para seed: {laudo_id}")
    return {
        "id": int(linha[0]),
        "empresa_id": int(linha[1]),
        "usuario_id": int(linha[2]),
        "tipo_template": str(linha[3] or "").strip() or "padrao",
        "codigo_hash": str(linha[4] or "").strip(),
        "nome_arquivo_pdf": str(linha[5] or "").strip() or None,
    }


def _seed_signatario_governado_e2e(
    database_url: str | None,
    *,
    laudo_id: int,
    nome: str | None = None,
) -> dict[str, Any]:
    caminho_db = _database_path_from_url(database_url)
    laudo = _consultar_laudo_seed(database_url, laudo_id)
    sufixo = uuid.uuid4().hex[:6]
    agora = datetime.now(timezone.utc)
    nome_signatario = nome or f"Eng. E2E {sufixo}"
    funcao = "Responsável técnico"
    registro = f"CREA-E2E-{sufixo.upper()}"

    with sqlite3.connect(caminho_db) as conexao:
        conexao.execute(
            """
            insert into signatarios_governados_laudo (
                tenant_id,
                nome,
                funcao,
                registro_profissional,
                valid_until,
                allowed_family_keys_json,
                governance_metadata_json,
                ativo,
                observacoes,
                criado_por_id,
                criado_em,
                atualizado_em
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(laudo["empresa_id"]),
                nome_signatario,
                funcao,
                registro,
                (agora + timedelta(days=365)).isoformat(),
                json.dumps([], ensure_ascii=False),
                json.dumps({"source": "playwright_e2e_seed"}, ensure_ascii=False),
                1,
                "Seed controlado pela suíte Playwright para emissão oficial.",
                None,
                agora.isoformat(),
                agora.isoformat(),
            ),
        )
        signatory_id = int(conexao.execute("select last_insert_rowid()").fetchone()[0])
        conexao.commit()

    return {
        "id": signatory_id,
        "nome": nome_signatario,
        "funcao": funcao,
        "registro_profissional": registro,
        "tenant_id": int(laudo["empresa_id"]),
    }


def _seed_gate_qualidade_minimo_e2e(database_url: str | None, *, laudo_id: int) -> None:
    caminho_db = _database_path_from_url(database_url)
    laudo = _consultar_laudo_seed(database_url, laudo_id)
    agora = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(caminho_db) as conexao:
        mensagem_campo = conexao.execute(
            """
            select id
              from mensagens_laudo
             where laudo_id = ?
               and tipo in ('user', 'humano_insp')
             order by id asc
             limit 1
            """,
            (int(laudo_id),),
        ).fetchone()
        if mensagem_campo is None:
            raise AssertionError(
                f"Laudo E2E sem mensagem de campo para compor o gate de qualidade: {laudo_id}"
            )

        conexao.execute(
            """
            insert into mensagens_laudo (
                laudo_id,
                remetente_id,
                tipo,
                conteudo,
                lida,
                resolvida_por_id,
                resolvida_em,
                custo_api_reais,
                criado_em,
                client_message_id,
                metadata_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(laudo_id),
                None,
                "ia",
                "Parecer técnico preliminar da IA consolidado para a finalização E2E.",
                1,
                None,
                None,
                0,
                agora,
                None,
                json.dumps({"source": "playwright_e2e_seed"}, ensure_ascii=False),
            ),
        )
        conexao.execute(
            """
            insert into aprendizados_visuais_ia (
                empresa_id,
                laudo_id,
                mensagem_referencia_id,
                criado_por_id,
                validado_por_id,
                setor_industrial,
                resumo,
                descricao_contexto,
                correcao_inspetor,
                parecer_mesa,
                sintese_consolidada,
                pontos_chave_json,
                referencias_norma_json,
                marcacoes_json,
                status,
                veredito_inspetor,
                veredito_mesa,
                imagem_url,
                imagem_nome_original,
                imagem_mime_type,
                imagem_sha256,
                caminho_arquivo,
                validado_em,
                criado_em,
                atualizado_em
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(laudo["empresa_id"]),
                int(laudo_id),
                int(mensagem_campo[0]),
                int(laudo["usuario_id"]),
                None,
                "geral",
                "Foto técnica controlada da suíte Playwright.",
                "Seed mínimo para satisfazer o gate de qualidade do laudo.",
                "Imagem válida para compor evidência visual obrigatória.",
                None,
                None,
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                "rascunho_inspetor",
                "conforme",
                None,
                "https://tariel.invalid/e2e-evidencia.jpg",
                "e2e-evidencia.jpg",
                "image/jpeg",
                hashlib.sha256(f"e2e-photo-{laudo_id}".encode("utf-8")).hexdigest(),
                f"/tmp/tariel_e2e_photo_{laudo_id}.jpg",
                None,
                agora,
                agora,
            ),
        )
        conexao.execute(
            """
            update laudos
               set parecer_ia = ?,
                   atualizado_em = ?
             where id = ?
            """,
            (
                "Parecer técnico preliminar da IA consolidado para a finalização E2E.",
                agora,
                int(laudo_id),
            ),
        )
        conexao.commit()


def _seed_report_pack_pronto_para_emissao_e2e(database_url: str | None, *, laudo_id: int) -> None:
    caminho_db = _database_path_from_url(database_url)
    agora = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(caminho_db) as conexao:
        linha = conexao.execute(
            "select report_pack_draft_json from laudos where id = ? limit 1",
            (int(laudo_id),),
        ).fetchone()
        payload_bruto = linha[0] if linha else None
        if isinstance(payload_bruto, str) and payload_bruto.strip():
            try:
                report_pack = json.loads(payload_bruto)
            except Exception:
                report_pack = {}
        elif isinstance(payload_bruto, dict):
            report_pack = dict(payload_bruto)
        else:
            report_pack = {}

        quality_gates = (
            dict(report_pack.get("quality_gates") or {})
            if isinstance(report_pack.get("quality_gates"), dict)
            else {}
        )
        quality_gates["missing_evidence"] = []
        quality_gates["final_validation_mode"] = (
            str(quality_gates.get("final_validation_mode") or "").strip() or "mesa_required"
        )
        report_pack["quality_gates"] = quality_gates

        conexao.execute(
            """
            update laudos
               set report_pack_draft_json = ?,
                   atualizado_em = ?
             where id = ?
            """,
            (
                json.dumps(report_pack, ensure_ascii=False),
                agora,
                int(laudo_id),
            ),
        )
        conexao.commit()


def _seed_pdf_emitido_versionado_e2e(
    database_url: str | None,
    *,
    laudo_id: int,
    version_label: str,
    pdf_bytes: bytes,
    file_name: str = "laudo_emitido.pdf",
) -> Path:
    laudo = _consultar_laudo_seed(database_url, laudo_id)
    web_root = Path(__file__).resolve().parents[2]
    caminho_pdf = (
        web_root
        / "storage"
        / "laudos_emitidos"
        / f"empresa_{int(laudo['empresa_id'])}"
        / f"laudo_{int(laudo_id)}"
        / str(version_label)
        / file_name
    )
    caminho_pdf.parent.mkdir(parents=True, exist_ok=True)
    caminho_pdf.write_bytes(pdf_bytes)

    caminho_db = _database_path_from_url(database_url)
    with sqlite3.connect(caminho_db) as conexao:
        conexao.execute(
            "update laudos set nome_arquivo_pdf = ?, atualizado_em = ? where id = ?",
            (
                file_name,
                datetime.now(timezone.utc).isoformat(),
                int(laudo_id),
            ),
        )
        conexao.commit()
    return caminho_pdf


def _gerar_pdf_real_via_api(
    page: Page,
    *,
    laudo_id: int,
    tipo_template: str,
    diagnostico: str,
) -> bytes:
    resposta_pdf = _api_fetch_bytes(
        page,
        path="/app/api/gerar_pdf",
        method="POST",
        json_body={
            "diagnostico": diagnostico,
            "inspetor": "Gabriel Santos",
            "empresa": "Empresa E2E",
            "setor": "geral",
            "data": "17/04/2026",
            "laudo_id": int(laudo_id),
            "tipo_template": tipo_template,
        },
    )
    assert resposta_pdf["status"] == 200, resposta_pdf
    assert "application/pdf" in str(resposta_pdf["contentType"]).lower(), resposta_pdf["contentType"]
    corpo = bytes(resposta_pdf["body"] or b"")
    assert corpo.startswith(b"%PDF"), "A emissão E2E não retornou um PDF válido."
    return corpo


def _abrir_modal_nova_inspecao(page: Page) -> None:
    gatilho_modal = page.locator(
        "[data-open-inspecao-modal]:visible, #btn-abrir-modal-novo:visible"
    ).first
    expect(gatilho_modal).to_be_visible(timeout=10000)
    gatilho_modal.click()


def _preencher_modal_nova_inspecao(
    page: Page,
    *,
    tipo_template: str | None = "padrao",
    equipamento: str = "Caldeira B-202",
    cliente: str = "Petrobras",
    unidade: str = "REPLAN - Paulínia",
    objetivo: str = "",
) -> dict[str, str]:
    expect(page.locator("#modal-nova-inspecao")).to_be_visible()
    if tipo_template is not None:
        page.locator("#select-template-inspecao").select_option(tipo_template, force=True)
    page.locator("#input-local-inspecao").fill(equipamento)
    page.locator("#input-cliente-inspecao").fill(cliente)
    page.locator("#input-unidade-inspecao").fill(unidade)
    page.locator("#textarea-objetivo-inspecao").fill(objetivo)
    expect(page.locator("#btn-confirmar-inspecao")).to_be_enabled()
    return {
        "equipamento": equipamento,
        "cliente": cliente,
        "unidade": unidade,
        "objetivo": objetivo,
    }


def _confirmar_modal_nova_inspecao(
    page: Page,
    *,
    equipamento: str,
    cliente: str,
    unidade: str,
    objetivo: str = "",
    validar_contexto_visual: bool = True,
) -> None:
    page.locator("#btn-confirmar-inspecao").click()
    expect(page.locator("#modal-nova-inspecao")).to_be_hidden(timeout=10000)
    page.wait_for_function(
        "() => Number(window.TarielAPI?.obterLaudoAtualId?.() || 0) > 0",
        timeout=10000,
    )
    expect(page.locator("#painel-chat")).to_have_attribute("data-inspecao-ui", "workspace", timeout=10000)
    expect(page.locator("#tela-boas-vindas")).to_be_hidden()
    if validar_contexto_visual:
        expect(page.locator("#workspace-titulo-laudo")).to_have_text(equipamento)
        expect(page.locator("#workspace-subtitulo-laudo")).to_contain_text(cliente)
        expect(page.locator("#workspace-subtitulo-laudo")).to_contain_text(unidade)
        expect(page.locator("#workspace-status-badge")).to_contain_text(re.compile(r"EM COLETA", re.IGNORECASE))


def _iniciar_inspecao_via_modal(page: Page, *, tipo_template: str = "padrao") -> dict[str, str]:
    _abrir_modal_nova_inspecao(page)
    contexto = _preencher_modal_nova_inspecao(page, tipo_template=tipo_template)
    _confirmar_modal_nova_inspecao(page, validar_contexto_visual=False, **contexto)
    return contexto


def _iniciar_inspecao_via_api(page: Page, *, tipo_template: str = "padrao") -> int:
    resposta = _api_fetch(
        page,
        path="/app/api/laudo/iniciar",
        method="POST",
        form_body={"tipo_template": tipo_template},
    )
    assert resposta["status"] == 200
    assert isinstance(resposta["body"], dict)
    laudo_id = int(resposta["body"]["laudo_id"])
    return laudo_id


def _obter_laudo_ativo(page: Page, *, laudo_esperado: int | None = None) -> int:
    prazo = time.time() + 12.0
    recarregamento_forcado = False

    while time.time() < prazo:
        laudo_id = int(page.evaluate("() => Number(window.TarielAPI?.obterLaudoAtualId?.() || 0)"))
        if laudo_id > 0 and (laudo_esperado is None or laudo_id == laudo_esperado):
            return laudo_id

        # Fallback defensivo para evitar flake de sincronização inicial
        # (estado vindo do backend antes do bootstrap concluir no front).
        try:
            status = _api_fetch(page, path="/app/api/laudo/status", method="GET")
            if status.get("status") == 200 and isinstance(status.get("body"), dict):
                laudo_status = int(status["body"].get("laudo_id") or 0)
                if laudo_status > 0:
                    page.evaluate(
                        """(laudoId) => {
                            if (window.TarielAPI?.carregarLaudo) {
                                window.TarielAPI.carregarLaudo(laudoId, { forcar: true, silencioso: true });
                            }
                        }""",
                        laudo_status,
                    )
                    page.wait_for_timeout(220)
                    laudo_front = int(page.evaluate("() => Number(window.TarielAPI?.obterLaudoAtualId?.() || 0)"))
                    if laudo_front > 0 and (laudo_esperado is None or laudo_front == laudo_esperado):
                        return laudo_front

                    if not recarregamento_forcado and laudo_esperado and laudo_status == laudo_esperado:
                        page.goto(
                            urljoin(page.url, f"/app/?laudo={laudo_esperado}"),
                            wait_until="domcontentloaded",
                        )
                        recarregamento_forcado = True
        except Exception:
            pass

        page.wait_for_timeout(220)

    assert False, "Laudo ativo não foi disponibilizado no front dentro do tempo esperado."


def _carregar_laudo_no_inspetor(page: Page, laudo_id: int) -> int:
    page.goto(
        urljoin(page.url, f"/app/?laudo={laudo_id}"),
        wait_until="domcontentloaded",
    )

    try:
        laudo_frente = _obter_laudo_ativo(page, laudo_esperado=laudo_id)
    except AssertionError:
        front_tem_loader = bool(page.evaluate("() => typeof window.TarielAPI?.carregarLaudo === 'function'"))
        if front_tem_loader:
            page.evaluate(
                """async (idLaudo) => {
                    await window.TarielAPI.carregarLaudo(idLaudo, { forcar: true, silencioso: true });
                }""",
                laudo_id,
            )
        laudo_frente = _obter_laudo_ativo(page, laudo_esperado=laudo_id)

    try:
        page.wait_for_function(
            """(idLaudo) => {
                const ativo = Number(
                    window.TarielAPI?.obterLaudoAtualId?.() ||
                    document.body?.dataset?.laudoAtualId ||
                    0
                );
                const estado = String(
                    document.body?.dataset?.estadoRelatorio ||
                    window.TarielAPI?.obterEstadoRelatorioNormalizado?.() ||
                    window.TarielAPI?.obterEstadoRelatorio?.() ||
                    ""
                ).trim().toLowerCase();
                return ativo === Number(idLaudo) && (!estado || estado === "relatorio_ativo");
            }""",
            arg=laudo_id,
            timeout=5000,
        )
    except Exception:
        page.wait_for_timeout(250)

    if page.locator("#painel-chat").get_attribute("data-inspecao-ui") != "workspace":
        _forcar_estado_relatorio_workspace(page, laudo_frente)
        expect(page.locator("#painel-chat")).to_have_attribute(
            "data-inspecao-ui",
            "workspace",
            timeout=10000,
        )
    return laudo_frente


def _esperar_contexto_workspace_inspetor(
    page: Page,
    *,
    laudo_id: int,
    aba: str,
    view: str | None = None,
) -> None:
    page.wait_for_function(
        """(ctx) => {
            const url = new URL(window.location.href);
            const laudoAtual = Number(url.searchParams.get("laudo") || 0);
            const abaAtual = String(url.searchParams.get("aba") || "").trim();
            const tabAtual = String(document.body?.dataset?.threadTab || "").trim();
            const viewAtual = String(document.body?.dataset?.workspaceView || "").trim();
            return (
                laudoAtual === Number(ctx.laudoId)
                && abaAtual === String(ctx.aba)
                && tabAtual === String(ctx.aba)
                && (!ctx.view || viewAtual === String(ctx.view))
            );
        }""",
        arg={"laudoId": laudo_id, "aba": aba, "view": view},
        timeout=10000,
    )


def _selecionar_aba_laudos_sidebar(page: Page, aba: str) -> None:
    botao = page.locator(f'[data-sidebar-laudos-tab-trigger="{aba}"]').first
    if botao.count():
        expect(botao).to_be_visible(timeout=10000)
        botao.click(force=True)
        return

    expect(page.locator("#lista-historico")).to_be_visible(timeout=10000)


def _selecionar_thread_tab_workspace(page: Page, aba: str) -> None:
    for seletor in (
        f'.thread-tab[data-tab="{aba}"]:visible',
        f'[data-rail-thread-tab="{aba}"]:visible',
    ):
        botao = page.locator(seletor).first
        if botao.count():
            expect(botao).to_be_visible(timeout=10000)
            botao.click(force=True)
            return

    raise AssertionError(f"Nenhum controle visível encontrado para a aba do workspace: {aba}")


def _abrir_laudo_no_revisor(page: Page, laudo_id: int) -> None:
    item_laudo = page.locator(f'.js-item-laudo[data-id="{laudo_id}"]').first
    if item_laudo.count():
        expect(item_laudo).to_be_visible(timeout=10000)
        item_laudo.click()
    else:
        page.wait_for_function(
            """() => Boolean(
                window.TarielRevisorPainel &&
                typeof window.TarielRevisorPainel.carregarLaudo === "function"
            )""",
            timeout=10000,
        )
        page.evaluate(
            """async (idLaudo) => {
                await window.TarielRevisorPainel.carregarLaudo(Number(idLaudo), { forcar: true });
            }""",
            laudo_id,
        )

    expect(page.locator("#view-content")).to_be_visible(timeout=10000)
    expect(page.locator("#view-hash")).to_contain_text(
        re.compile(r"Inspe[cç][aã]o #", re.IGNORECASE),
        timeout=10000,
    )
    expect(page.locator("#input-resposta")).to_be_enabled(timeout=10000)
    page.wait_for_function(
        """() => {
            const timeline = document.getElementById("view-timeline");
            if (!timeline) return false;
            const texto = String(timeline.textContent || "").trim();
            return texto !== "" && !/carregando/i.test(texto);
        }""",
        timeout=10000,
    )


def _abrir_painel_decisao_mesa_no_revisor(page: Page) -> None:
    painel_operacao = page.locator("#mesa-operacao-painel")
    if painel_operacao.is_visible():
        return

    toggle_contexto = page.locator("#btn-toggle-contexto-mesa")
    expect(toggle_contexto).to_be_visible(timeout=10000)
    toggle_contexto.click()
    expect(painel_operacao).to_be_visible(timeout=10000)


def _aceitar_proximo_dialogo(page: Page) -> None:
    page.once("dialog", lambda dialog: dialog.accept())


def _disparar_click_mesa_lista(page: Page, laudo_id: int) -> None:
    page.evaluate(
        """(idLaudo) => {
            const item = document.querySelector(`#lista-mesa-laudos [data-mesa="${Number(idLaudo)}"]`);
            if (!(item instanceof HTMLElement)) {
                throw new Error(`Item da fila da mesa não encontrado: ${idLaudo}`);
            }
            item.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
        }""",
        laudo_id,
    )


def _mockar_resposta_chat_json(page: Page, *, texto_resposta: str) -> None:
    def _handler(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"texto": texto_resposta}, ensure_ascii=False),
        )

    page.route("**/app/api/chat*", _handler)


def _forcar_estado_relatorio_workspace(page: Page, laudo_id: int, *, estado: str = "relatorio_ativo") -> None:
    page.evaluate(
        """(payload) => {
            window.__TARIEL_E2E_ESTADO_RELATORIO_FORCADO__ = {
                laudoId: payload.laudoId,
                estado: payload.estado,
            };

            if (
                !window.__TARIEL_E2E_SYNC_ESTADO_RELATORIO_WRAPPED__
                && typeof window.TarielAPI?.sincronizarEstadoRelatorio === "function"
            ) {
                const originalSync = window.TarielAPI.sincronizarEstadoRelatorio.bind(window.TarielAPI);
                window.__TARIEL_E2E_SYNC_ESTADO_RELATORIO_WRAPPED__ = true;
                window.__TARIEL_E2E_SYNC_ESTADO_RELATORIO_ORIGINAL__ = originalSync;
                window.TarielAPI.sincronizarEstadoRelatorio = async (...args) => {
                    const forced = window.__TARIEL_E2E_ESTADO_RELATORIO_FORCADO__;
                    if (!forced) {
                        return originalSync(...args);
                    }

                    const forcedPayload = {
                        laudoAtualId: forced.laudoId,
                        estadoRelatorio: forced.estado,
                    };
                    if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
                        window.TarielInspectorState.sincronizarEstadoInspector(forcedPayload, {
                            persistirStorage: false,
                        });
                    }
                    if (typeof window.TarielChatPainel?.sincronizarEstadoPainel === "function") {
                        window.TarielChatPainel.sincronizarEstadoPainel(forcedPayload);
                    }
                    if (typeof window.TarielAPI?.sincronizarEstadoCompat === "function") {
                        window.TarielAPI.sincronizarEstadoCompat(forcedPayload);
                    }

                    return {
                        laudo_id: forced.laudoId,
                        laudoId: forced.laudoId,
                        estado: forced.estado,
                        estado_normalizado: forced.estado,
                    };
                };
            }

            const compatPayload = {
                laudoAtualId: payload.laudoId,
                estadoRelatorio: payload.estado,
            };
            if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
                window.TarielInspectorState.sincronizarEstadoInspector(compatPayload, {
                    persistirStorage: false,
                });
            }
            if (typeof window.TarielChatPainel?.sincronizarEstadoPainel === "function") {
                window.TarielChatPainel.sincronizarEstadoPainel(compatPayload);
            }
            if (typeof window.TarielAPI?.sincronizarEstadoCompat === "function") {
                window.TarielAPI.sincronizarEstadoCompat(compatPayload);
            }
            if (window.TarielAPI?.setLaudoAtualId) {
                window.TarielAPI.setLaudoAtualId(payload.laudoId);
            }
            if (window.TarielAPI?.setEstadoRelatorio) {
                window.TarielAPI.setEstadoRelatorio(payload.estado);
            }
            const detail = {
                estado: payload.estado,
                laudo_id: payload.laudoId,
                laudoId: payload.laudoId,
            };
            if (typeof window.TarielInspectorEvents?.emit === "function") {
                window.TarielInspectorEvents.emit("tariel:estado-relatorio", detail, {
                    target: document,
                    bubbles: true,
                });
                return;
            }

            document.dispatchEvent(new CustomEvent("tariel:estado-relatorio", {
                detail,
                bubbles: true,
            }));
        }""",
        {"estado": estado, "laudoId": laudo_id},
    )


def _esperar_convergencia_estado_inspetor(
    page: Page,
    *,
    laudo_id: int,
    estado: str,
    workspace_stage: str = "inspection",
) -> None:
    payload = {"laudoId": laudo_id, "estado": estado, "workspaceStage": workspace_stage}
    script = """(payload) => {
        const snapshot = window.TarielInspectorState?.obterSnapshotEstadoInspectorAtual?.();
        const api = window.TarielAPI;
        const core = window.TarielChatPainel;
        const body = document.body?.dataset || {};
        if (!snapshot || !api || !core) return false;

        const apiCompat = api.obterSnapshotEstadoCompat?.() || {};
        const coreSnapshot = core.obterSnapshotEstadoPainel?.() || {};
        const laudoEsperado = Number(payload.laudoId || 0) || 0;
        const laudoCanonico = Number(snapshot.laudoAtualId || 0) || 0;
        const apiLaudo = Number(api.obterLaudoAtualId?.() || 0) || 0;
        const coreLaudo = Number(coreSnapshot.laudoAtualId || 0) || 0;
        const apiCompatLaudo = Number(apiCompat.laudoAtualId || 0) || 0;

        return laudoCanonico === laudoEsperado
            && String(snapshot.estadoRelatorio || "") === payload.estado
            && apiLaudo === laudoEsperado
            && String(api.obterEstadoRelatorioNormalizado?.() || "") === payload.estado
            && apiCompatLaudo === laudoEsperado
            && String(apiCompat.estadoRelatorio || "") === payload.estado
            && coreLaudo === laudoEsperado
            && String(coreSnapshot.estadoRelatorio || "") === payload.estado
            && String(body.laudoAtualId || "") === String(laudoEsperado)
            && String(body.estadoRelatorio || "") === payload.estado
            && String(body.workspaceStage || "") === payload.workspaceStage
            && String(body.threadTab || "") === String(snapshot.threadTab || "chat")
            && String(body.inspectorScreen || "") === String(snapshot.inspectorScreen || "")
            && String(body.inspectorStateDivergence || "false") === "false";
    }"""

    try:
        page.wait_for_function(script, arg=payload, timeout=10000)
    except Exception as exc:
        diagnostico = page.evaluate(
            """() => {
                const snapshot = window.TarielInspectorState?.obterSnapshotEstadoInspectorAtual?.() || null;
                const api = window.TarielAPI || null;
                const core = window.TarielChatPainel || null;
                return {
                    snapshot,
                    apiLaudoAtualId: api?.obterLaudoAtualId?.() ?? null,
                    apiEstadoRelatorio: api?.obterEstadoRelatorioNormalizado?.() ?? null,
                    apiCompat: api?.obterSnapshotEstadoCompat?.() ?? null,
                    coreSnapshot: core?.obterSnapshotEstadoPainel?.() ?? null,
                    bodyDataset: { ...(document.body?.dataset || {}) },
                };
            }""",
        )
        raise AssertionError(
            "Estado do inspetor não convergiu: "
            + json.dumps(diagnostico, ensure_ascii=False, sort_keys=True)
        ) from exc


def _atrasar_requisicoes(page: Page, *, padroes: list[str], atraso_ms: int = 700) -> None:
    atraso_s = max(int(atraso_ms), 0) / 1000.0

    def _handler(route) -> None:
        if atraso_s > 0:
            time.sleep(atraso_s)
        route.continue_()

    for padrao in padroes:
        page.route(padrao, _handler)


def _assert_sem_overflow_horizontal(page: Page, *, tolerancia_px: int = 2) -> None:
    metricas = page.evaluate(
        """() => {
            const innerWidth = window.innerWidth;
            const scrollWidth = document.documentElement.scrollWidth;
            const xAntes = window.scrollX;
            window.scrollTo({ left: 10_000, top: 0, behavior: "instant" });
            const xDepois = window.scrollX;
            window.scrollTo({ left: xAntes, top: 0, behavior: "instant" });
            const offenders = Array.from(document.querySelectorAll("body *"))
                .map((el) => {
                    const r = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    if (style.display === "none" || style.visibility === "hidden") return null;
                    if (r.width <= 0 || r.height <= 0) return null;
                    if (r.right <= innerWidth + 1) return null;
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id || "",
                        cls: (el.className || "").toString().split(" ").slice(0, 3).join("."),
                        right: Math.round(r.right),
                        width: Math.round(r.width)
                    };
                })
                .filter(Boolean)
                .slice(0, 8);
            return { innerWidth, scrollWidth, xDepois, offenders };
        }"""
    )
    sem_overflow_real = int(metricas["xDepois"]) <= int(tolerancia_px)
    sem_estouro_layout = int(metricas["scrollWidth"]) <= int(metricas["innerWidth"]) + int(tolerancia_px)
    assert sem_overflow_real or sem_estouro_layout, str(metricas)


def _extrair_senha_temporaria(texto: str) -> str:
    match = re.search(r"Senha tempor[áa]ria para .*?:\s*(.+?)\.\s*Compartilhe", texto, flags=re.IGNORECASE | re.DOTALL)
    assert match, f"Senha temporária não encontrada no texto: {texto!r}"
    return match.group(1).strip()


def _extrair_senha_temporaria_da_pagina(page: Page) -> str:
    campo_senha = page.locator('input[id^="credencial-senha-"]').first
    if campo_senha.count():
        senha = campo_senha.input_value().strip()
        if senha:
            return senha

    return _extrair_senha_temporaria(page.locator("body").inner_text())


def _login_cliente_primeiro_acesso(
    page: Page,
    *,
    base_url: str,
    email: str,
    senha_temporaria: str,
    nova_senha: str,
) -> None:
    page.goto(f"{base_url}/cliente/login", wait_until="domcontentloaded")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="senha"]').fill(senha_temporaria)
    page.locator('button[type="submit"]').first.click()
    expect(page).to_have_url(re.compile(rf"{re.escape(base_url)}/cliente/trocar-senha/?$"))

    page.locator('input[name="senha_atual"]').fill(senha_temporaria)
    page.locator('input[name="nova_senha"]').fill(nova_senha)
    page.locator('input[name="confirmar_senha"]').fill(nova_senha)
    page.locator('button[type="submit"]').first.click()
    expect(page).to_have_url(re.compile(rf"{re.escape(base_url)}/cliente/painel(?:\?sec=overview)?/?$"))


def _regex_url_admin_cliente_pos_cadastro(base_url: str) -> re.Pattern[str]:
    return re.compile(
        rf"{re.escape(base_url)}/admin/clientes/\d+(?:/acesso-inicial)?/?(?:\?.*)?$"
    )


def _provisionar_cliente_via_admin(
    page: Page,
    *,
    base_url: str,
    nome: str,
    email: str,
    cnpj: str,
    segmento: str,
    cidade_estado: str,
    nome_responsavel: str,
    observacoes: str,
    plano: str = "Intermediario",
) -> str:
    page.goto(f"{base_url}/admin/novo-cliente", wait_until="domcontentloaded")
    page.locator('input[name="nome"]').fill(nome)
    page.locator('input[name="cnpj"]').fill(cnpj)
    page.locator('select[name="plano"]').select_option(plano)
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="segmento"]').fill(segmento)
    page.locator('input[name="cidade_estado"]').fill(cidade_estado)
    page.locator('input[name="nome_responsavel"]').fill(nome_responsavel)
    page.locator('textarea[name="observacoes"]').fill(observacoes)
    page.get_by_role("button", name="Criar empresa").click()

    expect(page).to_have_url(_regex_url_admin_cliente_pos_cadastro(base_url))
    return _extrair_senha_temporaria_da_pagina(page)


def _assert_controles_flutuantes_sem_sobreposicao(page: Page) -> None:
    ids = ["btn-ir-fim-chat", "btn-toggle-ui", "btn-shell-home", "btn-shell-profile", "btn-mesa-widget-toggle"]
    sobreposicoes = page.evaluate(
        """(ids) => {
            const visiveis = ids
                .map((id) => document.getElementById(id))
                .filter((el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                })
                .map((el) => ({ id: el.id, r: el.getBoundingClientRect() }));

            const overlap = (a, b) => {
                const x = Math.max(0, Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left));
                const y = Math.max(0, Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top));
                return (x * y) > 0;
            };

            const conflitos = [];
            for (let i = 0; i < visiveis.length; i++) {
                for (let j = i + 1; j < visiveis.length; j++) {
                    if (overlap(visiveis[i], visiveis[j])) {
                        conflitos.push([visiveis[i].id, visiveis[j].id]);
                    }
                }
            }
            return conflitos;
        }""",
        ids,
    )
    assert sobreposicoes == []


def test_e2e_inspetor_login_e_chat_inicial_carrega(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    expect(page.locator("#painel-chat")).to_have_attribute("data-workspace-stage", "assistant")
    page.wait_for_function(
        """() => {
            const painel = document.getElementById("painel-chat");
            return ["home", "workspace"].includes(painel?.dataset?.inspecaoUi || "");
        }""",
        timeout=10000,
    )
    modo_inicial = page.locator("#painel-chat").get_attribute("data-inspecao-ui")
    assert modo_inicial in {"home", "workspace"}
    if modo_inicial == "home":
        expect(page.locator("#tela-boas-vindas")).to_be_visible()
        expect(page.locator("#workspace-assistant-landing")).to_be_hidden()
        expect(page.locator("h1")).to_contain_text(re.compile(r"Portal do Inspetor", re.IGNORECASE))
    else:
        expect(page.locator("#workspace-assistant-landing")).to_be_visible()
        expect(page.locator("#tela-boas-vindas")).to_be_hidden()
        expect(page.locator("#workspace-headline")).to_have_text(re.compile(r"Novo Chat", re.IGNORECASE))
    expect(page.locator("[data-open-inspecao-modal]:visible").first).to_be_visible()


def test_e2e_inspetor_workspace_permite_nova_inspecao_com_laudo_ativo(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")

    expect(page.locator("#painel-chat")).to_have_attribute("data-inspecao-ui", "workspace")
    expect(page.locator("#workspace-titulo-laudo")).not_to_have_text(re.compile(r"Assistente Tariel IA", re.IGNORECASE))

    _abrir_modal_nova_inspecao(page)
    expect(page.locator("#modal-nova-inspecao")).to_be_visible()
    page.locator("#btn-cancelar-modal-inspecao").click()
    expect(page.locator("#modal-nova-inspecao")).to_be_hidden()


def test_e2e_css_versionado_e_tipografia_base_ativa(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    diagnostico = page.evaluate(
        """() => {
            const hrefs = [];
            const coletarHrefs = (sheet) => {
                if (!sheet) return;
                if (sheet.href) {
                    hrefs.push(sheet.href);
                }
                try {
                    for (const rule of Array.from(sheet.cssRules || [])) {
                        if (rule.type === CSSRule.IMPORT_RULE && rule.styleSheet) {
                            coletarHrefs(rule.styleSheet);
                        }
                    }
                } catch (erro) {
                    // Ignora folhas cross-origin (Google Fonts).
                }
            };

            for (const sheet of Array.from(document.styleSheets)) {
                coletarHrefs(sheet);
            }

            const layeredBootstrap = Array.from(document.querySelectorAll("style"))
                .map((el) => el.textContent || "")
                .find((text) => text.includes("@layer tariel.global")) || "";
            const bodyFont = getComputedStyle(document.body).fontFamily;
            const rootFontBase = getComputedStyle(document.documentElement)
                .getPropertyValue('--font-base')
                .trim();

            let possuiResetBodyComFontInherit = false;
            for (const sheet of Array.from(document.styleSheets)) {
                try {
                    for (const rule of Array.from(sheet.cssRules || [])) {
                        if (rule.selectorText === 'body, button, input, textarea, select') {
                            const font = (rule.style?.getPropertyValue('font') || '').trim();
                            const fontFamily = (rule.style?.getPropertyValue('font-family') || '').trim();
                            if (font === 'inherit' || fontFamily === 'inherit') {
                                possuiResetBodyComFontInherit = true;
                            }
                        }
                    }
                } catch (erro) {
                    // Ignora CSS cross-origin (Google Fonts).
                }
            }

            return {
                hrefs: Array.from(new Set(hrefs)),
                layeredBootstrap,
                possuiResetBodyComFontInherit,
            };
        }"""
    )

    assert any("/static/css/shared/global.css?v=" in href for href in diagnostico["hrefs"])
    assert any("/static/css/inspetor/tokens.generated.css?v=" in href for href in diagnostico["hrefs"])
    assert any("/static/css/inspetor/tokens.css?v=" in href for href in diagnostico["hrefs"])
    assert any("/static/css/shared/official_visual_system.css?v=" in href for href in diagnostico["hrefs"])
    assert any("/static/css/inspetor/workspace_history.css?v=" in href for href in diagnostico["hrefs"])
    assert any("/static/css/shared/app_shell.css?v=" in href for href in diagnostico["hrefs"])
    assert not any("/static/css/shared/layout.css?v=" in href for href in diagnostico["hrefs"])
    assert not any("/static/css/chat/chat_base.css?v=" in href for href in diagnostico["hrefs"])
    assert not any("/static/css/chat/chat_mobile.css?v=" in href for href in diagnostico["hrefs"])
    assert not any("/static/css/inspetor/workspace.css?v=" in href for href in diagnostico["hrefs"])
    assert "@layer tariel.global" in diagnostico["layeredBootstrap"]
    assert "layer(tariel.refinements)" in diagnostico["layeredBootstrap"]
    assert diagnostico["possuiResetBodyComFontInherit"] is False


def test_e2e_modal_nova_inspecao_abre_workspace_com_contexto_visual(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    contexto = _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    expect(page.locator("#workspace-titulo-laudo")).to_have_text(contexto["equipamento"])
    expect(page.locator("#rodape-contexto-titulo")).to_contain_text(re.compile(r"Inspeção Geral|Chat Livre", re.IGNORECASE))


def test_e2e_home_com_laudo_ativo_retorna_para_tela_inicial_sem_deslogar(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")

    status_antes = _api_fetch(
        page,
        path="/app/api/laudo/status",
        method="GET",
    )
    assert status_antes["status"] == 200
    assert status_antes["body"]["estado"] == "sem_relatorio"
    assert status_antes["body"]["laudo_id"] is None

    page.locator(".btn-home-cabecalho").click()
    expect(page).to_have_url(re.compile(rf"{re.escape(live_server_url)}/app/?(\?home=1)?$"))
    expect(page.locator("#tela-boas-vindas")).to_be_visible()
    expect(page.locator("#btn-abrir-modal-novo")).to_be_visible()

    status_depois = _api_fetch(
        page,
        path="/app/api/laudo/status",
        method="GET",
    )
    assert status_depois["status"] == 200

    page.goto(f"{live_server_url}/app/", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(rf"{re.escape(live_server_url)}/app/?(\?laudo=\d+)?$"))
    expect(page.locator("#painel-chat")).to_have_attribute("data-inspecao-ui", "workspace")
    expect(page.locator("#workspace-assistant-landing")).to_be_visible(timeout=10000)
    assert "/app/login" not in page.url


def test_e2e_acao_rapida_prefill_modal_e_preenche_composer(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    page.goto(f"{live_server_url}/app/?home=1", wait_until="domcontentloaded")
    expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=10000)

    botao = page.locator(".portal-model-card[data-tipo='nr12maquinas']").first
    expect(botao).to_be_visible()
    botao.click()

    expect(page.locator("#modal-nova-inspecao")).to_be_visible()
    expect(page.locator("#select-template-inspecao")).to_have_value("nr12maquinas")
    contexto = _preencher_modal_nova_inspecao(
        page,
        tipo_template=None,
        equipamento="Prensa Hidráulica 07",
        cliente="Metalúrgica Atlas",
        unidade="Linha 4",
    )
    _confirmar_modal_nova_inspecao(page, validar_contexto_visual=False, **contexto)
    expect(page.locator("#rodape-contexto-titulo")).to_contain_text(re.compile(r"NR-12", re.IGNORECASE))

    texto_composer = page.locator("#campo-mensagem").input_value()
    assert len(texto_composer.strip()) >= 20
    expect(page.locator("#btn-enviar")).to_be_enabled()


def test_e2e_modo_foco_mobile_expoe_chat_e_perfil_sem_cortes(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto = browser.new_context(viewport={"width": 390, "height": 844})
    try:
        page = contexto.new_page()
        _fazer_login(
            page,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        expect(page.locator("#btn-toggle-ui")).to_be_visible()
        page.locator("#btn-toggle-ui").click()

        expect(page.locator("#btn-shell-profile")).to_be_visible()

        metricas = page.evaluate(
            """() => {
                const card = document.getElementById("workspace-assistant-landing");
                if (!card) {
                    return { existe: false };
                }

                const style = window.getComputedStyle(card);
                return {
                    existe: true,
                    overflowY: style.overflowY,
                    clientHeight: card.clientHeight,
                    scrollHeight: card.scrollHeight
                };
            }"""
        )
        assert bool(metricas["existe"]) is True
        assert metricas["overflowY"] in {"visible", "clip"} or int(metricas["scrollHeight"]) <= int(metricas["clientHeight"]) + 2, str(metricas)

        page.locator("#btn-shell-profile").click()
        expect(page.locator("#modal-perfil-chat")).to_be_visible()
        expect(page.locator("#input-perfil-nome")).to_be_focused()
        page.locator("#btn-fechar-modal-perfil").click()

        page.locator("#btn-shell-home").click()
        expect(page.locator("#tela-boas-vindas")).to_be_visible()
    finally:
        contexto.close()


def test_e2e_perfil_restaura_foco_ao_fechar_no_modo_foco(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    page.locator("#btn-toggle-ui").click()
    expect(page.locator("#btn-shell-profile")).to_be_visible()

    page.locator("#btn-shell-profile").focus()
    expect(page.locator("#btn-shell-profile")).to_be_focused()

    page.locator("#btn-shell-profile").click()
    expect(page.locator("#modal-perfil-chat")).to_be_visible()
    expect(page.locator("#input-perfil-nome")).to_be_focused()

    page.keyboard.press("Escape")
    expect(page.locator("#modal-perfil-chat")).to_be_hidden()
    expect(page.locator("#btn-shell-profile")).to_be_focused()


def test_e2e_anexo_de_imagem_mantem_preview_unico(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    preview_item = page.locator("#preview-anexo .preview-item")
    page.wait_for_function("() => Boolean(window.TarielAPI?.prepararArquivoParaEnvio)")

    def _preparar_preview() -> None:
        page.evaluate(
            """(pngBase64) => {
                const bytes = Uint8Array.from(atob(pngBase64), (char) => char.charCodeAt(0));
                const arquivo = new File([bytes], "evidencia.png", { type: "image/png" });
                window.TarielAPI.prepararArquivoParaEnvio(arquivo);
            }""",
            PNG_1X1_TRANSPARENTE_B64,
        )

    _preparar_preview()
    page.wait_for_function("() => document.querySelectorAll('#preview-anexo .preview-item').length === 1")

    _preparar_preview()
    page.wait_for_function("() => document.querySelectorAll('#preview-anexo .preview-item').length === 1")

    page.locator("#preview-anexo .btn-remover-preview").click()
    expect(preview_item).to_have_count(0)


def test_e2e_finalizar_sem_evidencias_aciona_gate_qualidade(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    _forcar_estado_relatorio_workspace(page, laudo_id)
    _aceitar_proximo_dialogo(page)
    page.locator("[data-finalizar-inspecao]:visible").first.click()

    expect(page.locator("#modal-gate-qualidade")).to_be_visible(timeout=10000)
    expect(page.locator("#lista-gate-roteiro-template .item-gate-roteiro").first).to_be_visible()
    expect(page.locator("#lista-gate-faltantes .item-gate-qualidade").first).to_be_visible()


def test_e2e_estado_inspetor_converge_em_snapshot_canonico(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    laudo_id = _iniciar_inspecao_via_api(page, tipo_template="padrao")
    _carregar_laudo_no_inspetor(page, laudo_id)
    _forcar_estado_relatorio_workspace(page, laudo_id, estado="relatorio_ativo")
    _esperar_convergencia_estado_inspetor(
        page,
        laudo_id=laudo_id,
        estado="relatorio_ativo",
    )

    _forcar_estado_relatorio_workspace(page, laudo_id, estado="aguardando")
    _esperar_convergencia_estado_inspetor(
        page,
        laudo_id=laudo_id,
        estado="aguardando",
    )


def test_e2e_url_laudo_sobrepoe_force_home_landing_persistido(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    laudo_id = _iniciar_inspecao_via_api(page, tipo_template="padrao")
    _forcar_estado_relatorio_workspace(page, laudo_id, estado="relatorio_ativo")
    page.evaluate("""() => sessionStorage.setItem("tariel_force_home_landing", "1")""")

    page.goto(f"{live_server_url}/app/?laudo={laudo_id}&aba=conversa", wait_until="domcontentloaded")
    page.wait_for_function(
        """(payload) => {
            const snapshot = window.TarielInspectorState?.obterSnapshotEstadoInspectorAtual?.();
            const body = document.body?.dataset || {};
            return !!snapshot
                && Number(snapshot.laudoAtualId || 0) === payload.laudoId
                && String(snapshot.modoInspecaoUI || "") === "workspace"
                && String(snapshot.forceHomeLanding || false) === "false"
                && String(snapshot.inspectorBaseScreen || "") === "inspection_workspace"
                && String(body.laudoAtualId || "") === String(payload.laudoId)
                && String(body.forceHomeLanding || "") === "false"
                && String(body.inspectorBaseScreen || "") === "inspection_workspace";
        }""",
        arg={"laudoId": laudo_id},
        timeout=15000,
    )
    expect(page.locator("[data-finalizar-inspecao]:visible, #btn-finalizar-inspecao:visible").first).to_be_visible(timeout=10000)


def test_e2e_boot_frio_carrega_laudo_por_url_sem_depender_do_historico_lateral(
    page: Page,
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)

    contexto_frio = browser.new_context()
    pagina_fria = contexto_frio.new_page()
    try:
        _fazer_login(
            pagina_fria,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        pagina_fria.goto(
            f"{live_server_url}/app/?laudo={laudo_id}&aba=historico",
            wait_until="domcontentloaded",
        )
        _esperar_contexto_workspace_inspetor(
            pagina_fria,
            laudo_id=laudo_id,
            aba="historico",
            view="inspection_history",
        )
        expect(pagina_fria.locator("[data-workspace-history-root]")).to_be_visible(timeout=10000)
        expect(pagina_fria.locator(".thread-tab[data-tab=\"historico\"]")).to_have_attribute(
            "aria-selected",
            "true",
            timeout=10000,
        )
    finally:
        contexto_frio.close()


def test_e2e_boot_frio_conversa_carrega_laudo_por_url_e_permite_historico(
    page: Page,
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)

    page.locator("#campo-mensagem").fill("Mensagem inicial para validar conversa fria.")
    expect(page.locator("#btn-enviar")).to_be_enabled(timeout=10000)
    page.locator("#btn-enviar").click()
    expect(
        page.locator(".linha-mensagem.mensagem-inspetor .texto-msg", has_text="Mensagem inicial para validar conversa fria.").first
    ).to_be_visible(timeout=10000)

    contexto_frio = browser.new_context()
    pagina_fria = contexto_frio.new_page()
    try:
        _fazer_login(
            pagina_fria,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        pagina_fria.goto(
            f"{live_server_url}/app/?laudo={laudo_id}&aba=conversa",
            wait_until="domcontentloaded",
        )
        pagina_fria.wait_for_function(
            """(ctx) => {
                const snapshot = window.TarielInspectorState?.obterSnapshotEstadoInspectorAtual?.() || {};
                const body = document.body?.dataset || {};
                const composer = document.getElementById("campo-mensagem");
                const composerVisivel = Boolean(
                    composer
                    && !composer.hidden
                    && !composer.closest?.("[hidden], [inert]")
                    && composer.getClientRects?.().length
                );
                return (
                    Number(snapshot.laudoAtualId || body.laudoAtualId || 0) === Number(ctx.laudoId)
                    && String(snapshot.threadTab || body.threadTab || "").trim() === "conversa"
                    && composerVisivel
                );
            }""",
            arg={"laudoId": laudo_id},
            timeout=15000,
        )
        expect(pagina_fria.locator("#campo-mensagem")).to_be_visible(timeout=10000)

        pagina_fria.goto(
            f"{live_server_url}/app/?laudo={laudo_id}&aba=historico",
            wait_until="domcontentloaded",
        )
        _esperar_contexto_workspace_inspetor(
            pagina_fria,
            laudo_id=laudo_id,
            aba="historico",
            view="inspection_history",
        )
        expect(pagina_fria.locator("[data-workspace-history-root]")).to_be_visible(timeout=10000)
    finally:
        contexto_frio.close()


def test_e2e_thread_tabs_workspace_trocam_view_por_clique_real(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)

    page.goto(
        f"{live_server_url}/app/?laudo={laudo_id}&aba=conversa",
        wait_until="domcontentloaded",
    )
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="conversa",
        view="inspection_conversation",
    )
    expect(page.locator("#campo-mensagem")).to_be_visible(timeout=10000)

    _selecionar_thread_tab_workspace(page, "historico")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="historico",
        view="inspection_history",
    )
    expect(page.locator("[data-workspace-history-root]")).to_be_visible(timeout=10000)

    _selecionar_thread_tab_workspace(page, "anexos")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="anexos",
        view="inspection_record",
    )
    expect(page.locator("#workspace-anexos-panel")).to_be_visible(timeout=10000)

    _selecionar_thread_tab_workspace(page, "mesa")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="mesa",
        view="inspection_mesa",
    )
    expect(page.locator("#workspace-mesa-stage")).to_be_visible(timeout=10000)

    _selecionar_thread_tab_workspace(page, "conversa")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="conversa",
        view="inspection_conversation",
    )
    expect(page.locator("#campo-mensagem")).to_be_visible(timeout=10000)


def test_e2e_botao_enviar_habilita_com_texto_no_composer(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    campo = page.locator("#campo-mensagem")
    btn_enviar = page.locator("#btn-enviar")

    campo.fill("")
    expect(btn_enviar).to_be_disabled()
    campo.fill("   ")
    expect(btn_enviar).to_be_disabled()

    campo.fill("Observação de teste em campo.")
    expect(btn_enviar).to_be_enabled()

    campo.fill("")
    expect(btn_enviar).to_be_disabled()


def test_e2e_envio_chat_principal_via_ui_com_mock_da_ia(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto = browser.new_context(service_workers="block")
    try:
        page = contexto.new_page()
        _fazer_login(
            page,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        _iniciar_inspecao_via_modal(page, tipo_template="padrao")
        _mockar_resposta_chat_json(
            page,
            texto_resposta="Resposta simulada da IA para teste E2E.",
        )

        texto = f"Registro de inspeção E2E composer {uuid.uuid4().hex[:10]}"
        page.locator("#campo-mensagem").fill(texto)
        page.locator("#btn-enviar").click()

        expect(
            page.locator(
                ".linha-mensagem.mensagem-inspetor .texto-msg",
                has_text=texto,
            ).first
        ).to_be_visible(timeout=10000)
        expect(page.locator(".linha-mensagem.mensagem-ia").first).to_be_visible(timeout=10000)
        expect(
            page.locator(
                ".linha-mensagem.mensagem-ia .texto-msg",
                has_text="Resposta simulada da IA para teste E2E.",
            ).first
        ).to_be_visible(timeout=10000)
        expect(page.locator("#btn-enviar")).to_be_disabled()
    finally:
        contexto.close()


def test_e2e_conversa_workspace_mantem_scroll_da_thread_da_ia(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto = browser.new_context(service_workers="block")
    try:
        page = contexto.new_page()
        _fazer_login(
            page,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        _iniciar_inspecao_via_modal(page, tipo_template="padrao")
        page.evaluate(
            """() => {
                window.TarielInspectorState?.atualizarThreadWorkspace?.("conversa", {
                    persistirURL: false,
                });
            }"""
        )
        _esperar_contexto_workspace_inspetor(
            page,
            laudo_id=_obter_laudo_ativo(page),
            aba="conversa",
            view="inspection_conversation",
        )
        _mockar_resposta_chat_json(
            page,
            texto_resposta="Resposta simulada longa da IA para validar overflow e retorno ao fim da conversa. " * 6,
        )

        for indice in range(8):
            texto = f"Mensagem scroll E2E {indice} {uuid.uuid4().hex[:6]} " + ("detalhe " * 20)
            page.locator("#campo-mensagem").fill(texto)
            page.locator("#btn-enviar").click()
            expect(
                page.locator(
                    ".linha-mensagem.mensagem-inspetor .texto-msg",
                    has_text=texto,
                ).first
            ).to_be_visible(timeout=10000)
            page.wait_for_function(
                """(esperado) => {
                    return document.querySelectorAll("#area-mensagens .linha-mensagem.mensagem-ia").length >= esperado;
                }""",
                arg=indice + 1,
                timeout=10000,
            )

        page.wait_for_function(
            """() => {
                return String(document.body?.dataset?.workspaceView || "").trim() === "inspection_conversation";
            }""",
            timeout=10000,
        )

        metricas_scroll = page.evaluate(
            """() => {
                const resolverAlvoScroll = () => {
                    const candidatos = [
                        document.getElementById("area-mensagens"),
                        document.querySelector('.workspace-view-root--conversation[data-active="true"]'),
                        document.querySelector('.workspace-channel-stage--ia'),
                        document.querySelector('.chat-thread-surface'),
                    ].filter((node) =>
                        node instanceof HTMLElement &&
                        !node.hidden &&
                        !node.closest('[hidden], [inert]') &&
                        node.getClientRects().length > 0
                    );

                    const alvoLocal = candidatos
                        .map((node) => ({ node, score: node.scrollHeight - node.clientHeight }))
                        .sort((atual, proximo) => proximo.score - atual.score)
                        .find((item) => item.score > 16)?.node;

                    if (alvoLocal instanceof HTMLElement) {
                        return { alvo: alvoLocal, page: false };
                    }

                    const scrollPagina = document.scrollingElement;
                    if (
                        scrollPagina instanceof HTMLElement &&
                        (scrollPagina.scrollHeight - window.innerHeight) > 16
                    ) {
                        return { alvo: scrollPagina, page: true };
                    }

                    return { alvo: candidatos[0] || null, page: false };
                };

                const { alvo, page } = resolverAlvoScroll();

                if (!(alvo instanceof HTMLElement)) return null;
                const estilo = window.getComputedStyle(alvo);
                return {
                    overflowY: page ? "page" : estilo.overflowY,
                    clientHeight: page ? window.innerHeight : alvo.clientHeight,
                    scrollHeight: alvo.scrollHeight,
                    usesScrollButton: !page && alvo.id === "area-mensagens",
                };
            }"""
        )
        assert metricas_scroll is not None
        assert metricas_scroll["overflowY"] in {"auto", "scroll", "hidden", "page"}
        assert metricas_scroll["scrollHeight"] > metricas_scroll["clientHeight"] + 8

        page.evaluate(
            """() => {
                const resolverAlvoScroll = () => {
                    const candidatos = [
                        document.getElementById("area-mensagens"),
                        document.querySelector('.workspace-view-root--conversation[data-active="true"]'),
                        document.querySelector('.workspace-channel-stage--ia'),
                        document.querySelector('.chat-thread-surface'),
                    ].filter((node) =>
                        node instanceof HTMLElement &&
                        !node.hidden &&
                        !node.closest('[hidden], [inert]') &&
                        node.getClientRects().length > 0
                    );
                    const alvoLocal = candidatos
                        .map((node) => ({ node, score: node.scrollHeight - node.clientHeight }))
                        .sort((atual, proximo) => proximo.score - atual.score)
                        .find((item) => item.score > 16)?.node;
                    if (alvoLocal instanceof HTMLElement) return alvoLocal;
                    return document.scrollingElement instanceof HTMLElement
                        ? document.scrollingElement
                        : candidatos[0];
                };
                const alvo = resolverAlvoScroll();
                if (!(alvo instanceof HTMLElement)) return;
                alvo.scrollTop = 0;
                alvo.dispatchEvent(new Event("scroll", { bubbles: true }));
            }"""
        )
        if metricas_scroll["usesScrollButton"]:
            expect(page.locator("#btn-ir-fim-chat")).to_have_attribute("aria-hidden", "false", timeout=10000)
            assert "visivel" in (page.locator("#btn-ir-fim-chat").get_attribute("class") or "")

        page.evaluate(
            """() => {
                const resolverAlvoScroll = () => {
                    const candidatos = [
                        document.getElementById("area-mensagens"),
                        document.querySelector('.workspace-view-root--conversation[data-active="true"]'),
                        document.querySelector('.workspace-channel-stage--ia'),
                        document.querySelector('.chat-thread-surface'),
                    ].filter((node) =>
                        node instanceof HTMLElement &&
                        !node.hidden &&
                        !node.closest('[hidden], [inert]') &&
                        node.getClientRects().length > 0
                    );
                    const alvoLocal = candidatos
                        .map((node) => ({ node, score: node.scrollHeight - node.clientHeight }))
                        .sort((atual, proximo) => proximo.score - atual.score)
                        .find((item) => item.score > 16)?.node;
                    if (alvoLocal instanceof HTMLElement) return alvoLocal;
                    return document.scrollingElement instanceof HTMLElement
                        ? document.scrollingElement
                        : candidatos[0];
                };
                const alvo = resolverAlvoScroll();
                if (!(alvo instanceof HTMLElement)) return;
                alvo.scrollTop = alvo.scrollHeight;
                alvo.dispatchEvent(new Event("scroll", { bubbles: true }));
            }"""
        )
        page.wait_for_function(
            """() => {
                const resolverAlvoScroll = () => {
                    const candidatos = [
                        document.getElementById("area-mensagens"),
                        document.querySelector('.workspace-view-root--conversation[data-active="true"]'),
                        document.querySelector('.workspace-channel-stage--ia'),
                        document.querySelector('.chat-thread-surface'),
                    ].filter((node) =>
                        node instanceof HTMLElement &&
                        !node.hidden &&
                        !node.closest('[hidden], [inert]') &&
                        node.getClientRects().length > 0
                    );
                    const alvoLocal = candidatos
                        .map((node) => ({ node, score: node.scrollHeight - node.clientHeight }))
                        .sort((atual, proximo) => proximo.score - atual.score)
                        .find((item) => item.score > 16)?.node;
                    if (alvoLocal instanceof HTMLElement) return alvoLocal;
                    return document.scrollingElement instanceof HTMLElement
                        ? document.scrollingElement
                        : candidatos[0];
                };
                const alvo = resolverAlvoScroll();
                if (!(alvo instanceof HTMLElement)) return false;
                const clientHeight = alvo === document.scrollingElement
                    ? window.innerHeight
                    : alvo.clientHeight;
                const distancia = alvo.scrollHeight - clientHeight - alvo.scrollTop;
                return alvo.scrollTop > 0 && distancia <= 24;
            }""",
            timeout=10000,
        )
    finally:
        contexto.close()


def test_e2e_conversa_workspace_preserva_laudo_e_historico_no_reload(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="conversa",
        view="inspection_conversation",
    )

    page.locator("#campo-mensagem").fill("/resumo")
    page.locator("#btn-enviar").click()

    expect(
        page.locator(".linha-mensagem.mensagem-inspetor .texto-msg", has_text="/resumo").first
    ).to_be_visible(timeout=10000)
    expect(
        page.locator(".linha-mensagem.mensagem-ia .texto-msg", has_text="Resumo da Sessão").first
    ).to_be_visible(timeout=10000)
    historico = _api_fetch(
        page,
        path=f"/app/api/laudo/{laudo_id}/mensagens",
        method="GET",
    )
    assert historico["status"] == 200
    itens_historico = historico["body"]["itens"]
    assert any(item["papel"] == "usuario" and "/resumo" in item["texto"] for item in itens_historico)
    assert any(item["papel"] == "assistente" and "Resumo da Sessão" in item["texto"] for item in itens_historico)
    expect(page).to_have_url(
        re.compile(rf"{re.escape(live_server_url)}/app/\?laudo={laudo_id}&aba=conversa$")
    )

    page.reload(wait_until="domcontentloaded")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="conversa",
        view="inspection_conversation",
    )
    page.wait_for_function(
        """() => document.querySelectorAll("#area-mensagens .linha-mensagem").length >= 1""",
        timeout=10000,
    )
    expect(
        page.locator(".linha-mensagem.mensagem-ia .texto-msg", has_text="Resumo da Sessão").first
    ).to_be_visible(timeout=10000)


def test_e2e_sidebar_portal_preserva_laudo_ativo_apos_fluxo_conversa_mesa(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    laudos_fixados: list[int] = []
    for indice in range(3):
        resposta_inicio = _api_fetch(
            page,
            path="/app/api/laudo/iniciar",
            method="POST",
            form_body={
                "tipo_template": "padrao",
                "local_inspecao": f"Asset pinado {indice}",
                "cliente": "Petrobras",
                "unidade": f"Unidade {indice}",
                "objetivo": "Forcar laudos fixados no topo do portal.",
            },
        )
        assert resposta_inicio["status"] == 200
        laudo_id = int(resposta_inicio["body"]["laudo_id"])
        resposta_pin = _api_fetch(
            page,
            path=f"/app/api/laudo/{laudo_id}/pin",
            method="PATCH",
            json_body={"pinado": True},
        )
        assert resposta_pin["status"] == 200
        laudos_fixados.append(laudo_id)

    resposta_alvo = _api_fetch(
        page,
        path="/app/api/laudo/iniciar",
        method="POST",
        form_body={
            "tipo_template": "padrao",
            "local_inspecao": "Laudo alvo portal",
            "cliente": "Petrobras",
            "unidade": "Refinaria alvo",
            "objetivo": "Garantir retorno do card ao voltar para o portal.",
        },
    )
    assert resposta_alvo["status"] == 200
    laudo_alvo = int(resposta_alvo["body"]["laudo_id"])
    assert laudo_alvo not in laudos_fixados

    page.goto(
        f"{live_server_url}/app/?laudo={laudo_alvo}&aba=conversa",
        wait_until="domcontentloaded",
    )
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_alvo,
        aba="conversa",
        view="inspection_conversation",
    )

    expect(page.locator(".workspace-channel-stage--ia .workspace-channel-back")).to_be_visible(timeout=10000)
    item_sidebar_workspace = page.locator(f'#lista-historico .item-historico[data-laudo-id="{laudo_alvo}"]').first
    expect(item_sidebar_workspace).to_be_visible(timeout=10000)

    page.locator('.workspace-channel-stage--ia [data-workspace-channel-tab="mesa"]').click()
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_alvo,
        aba="mesa",
        view="inspection_mesa",
    )
    expect(page.locator(".workspace-channel-stage--mesa .workspace-channel-back")).to_be_visible(timeout=10000)
    page.locator(".workspace-channel-stage--mesa .workspace-channel-back").click()

    expect(page).to_have_url(re.compile(rf"{re.escape(live_server_url)}/app/\?home=1$"))
    expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=10000)
    expect(page.locator(f'#lista-historico .item-historico[data-laudo-id="{laudo_alvo}"]').first).to_be_visible(
        timeout=10000
    )
    assert page.locator("#lista-historico .item-historico[data-laudo-id]").count() >= 4


def test_e2e_isolamento_portal_inspetor_nao_acessa_revisao(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    page.goto(f"{live_server_url}/revisao/painel", wait_until="domcontentloaded")
    conteudo = page.content()
    assert "Mesa de Avaliação" not in conteudo
    assert "/revisao/login" in page.url or "/app/login" in page.url or "Acesso restrito" in conteudo or "Sessão expirada" in conteudo


def test_e2e_isolamento_portais_revisor_e_admin(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="revisao",
        email=credenciais_seed["revisor"]["email"],
        senha=credenciais_seed["revisor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
    )

    page.goto(f"{live_server_url}/app/", wait_until="domcontentloaded")
    assert "/revisao/painel" in page.url or "/app/login" in page.url

    page.goto(f"{live_server_url}/admin/painel", wait_until="domcontentloaded")
    assert "/admin/login" in page.url or "/revisao/painel" in page.url


def test_e2e_widget_mesa_so_abre_com_inspecao_ativa(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    painel_mesa = page.locator("#painel-mesa-widget")
    btn_toggle_mesa = page.locator("#btn-mesa-widget-toggle")

    expect(painel_mesa).to_be_hidden()
    expect(btn_toggle_mesa).to_be_hidden()

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    _carregar_laudo_no_inspetor(page, laudo_id)
    expect(btn_toggle_mesa).to_be_visible()
    btn_toggle_mesa.click()
    expect(painel_mesa).to_be_visible()
    expect(btn_toggle_mesa).to_have_attribute("aria-expanded", "true")
    expect(page.locator("#mesa-widget-input")).to_be_visible()


def test_e2e_widget_mesa_envia_mensagem_via_ui_e_persiste(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    _carregar_laudo_no_inspetor(page, laudo_id)

    expect(page.locator("#btn-mesa-widget-toggle")).to_be_visible(timeout=10000)
    page.locator("#btn-mesa-widget-toggle").click()
    expect(page.locator("#painel-mesa-widget")).to_be_visible()

    texto = f"Mensagem widget mesa E2E {uuid.uuid4().hex[:8]}"
    page.locator("#mesa-widget-input").fill(texto)
    page.locator("#mesa-widget-enviar").click()

    expect(page.locator("#workspace-mesa-card-status")).to_contain_text(re.compile(r"aguardando", re.IGNORECASE))
    expect(page.locator("#mesa-widget-resumo-titulo")).to_contain_text(re.compile(r"aguardando resposta da mesa", re.IGNORECASE))
    expect(page.locator("#mesa-widget-lista .mesa-widget-item .texto", has_text=texto).first).to_be_visible(timeout=10000)

    historico_mesa = _api_fetch(
        page,
        path=f"/app/api/laudo/{laudo_id}/mesa/mensagens",
        method="GET",
    )
    assert historico_mesa["status"] == 200
    itens = historico_mesa["body"]["itens"]
    assert any(item["tipo"] == "humano_insp" and texto in item["texto"] for item in itens)


def test_e2e_widget_mesa_fica_somente_leitura_fora_da_coleta(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    _carregar_laudo_no_inspetor(page, laudo_id)

    page.locator("#btn-mesa-widget-toggle").click()
    expect(page.locator("#painel-mesa-widget")).to_be_visible(timeout=10000)

    cenarios = [
        ("aguardando", re.compile(r"aguardando retorno da mesa", re.IGNORECASE)),
        ("ajustes", re.compile(r"reabra a inspe[cç][aã]o", re.IGNORECASE)),
        ("aprovado", re.compile(r"laudo aprovado", re.IGNORECASE)),
    ]

    for estado, placeholder in cenarios:
        _forcar_estado_relatorio_workspace(page, laudo_id, estado=estado)
        _esperar_convergencia_estado_inspetor(page, laudo_id=laudo_id, estado=estado)

        expect(page.locator("#aviso-laudo-bloqueado")).to_be_visible(timeout=10000)
        expect(page.locator("#mesa-widget-input")).to_be_disabled()
        expect(page.locator("#mesa-widget-enviar")).to_be_disabled()
        expect(page.locator("#btn-rail-finalizar-inspecao")).to_be_disabled()
        expect(page.locator("#mesa-widget-input")).to_have_attribute("placeholder", placeholder)


def test_e2e_inspetor_abas_workspace_preservam_url_reload_e_historico(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    _carregar_laudo_no_inspetor(page, laudo_id)

    page.goto(
        f"{live_server_url}/app/?laudo={laudo_id}&aba=historico",
        wait_until="domcontentloaded",
    )
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="historico",
        view="inspection_history",
    )
    expect(page.locator("[data-workspace-history-root]")).to_be_visible(timeout=10000)

    page.evaluate(
        """() => {
            window.TarielInspectorState?.atualizarThreadWorkspace?.("anexos", {
                persistirURL: true,
            });
        }"""
    )
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="anexos",
        view="inspection_record",
    )

    page.evaluate(
        """() => {
            window.TarielInspectorState?.atualizarThreadWorkspace?.("mesa", {
                persistirURL: true,
            });
        }"""
    )
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="mesa",
        view="inspection_mesa",
    )
    expect(page.locator("#workspace-mesa-stage #painel-mesa-widget")).to_be_visible(timeout=10000)

    page.reload(wait_until="domcontentloaded")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="mesa",
    )

    page.go_back(wait_until="domcontentloaded")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="anexos",
        view="inspection_record",
    )

    page.go_back(wait_until="domcontentloaded")
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="historico",
        view="inspection_history",
    )


def test_e2e_inspetor_historico_workspace_usa_payload_canonico_e_filtros(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    texto = f"Historico canônico E2E {uuid.uuid4().hex[:8]}"

    resposta_chat = _api_fetch(
        page,
        path="/app/api/chat",
        method="POST",
        json_body={
            "mensagem": texto,
            "dados_imagem": "",
            "setor": "geral",
            "historico": [],
            "modo": "detalhado",
            "texto_documento": "",
            "nome_documento": "",
            "laudo_id": laudo_id,
        },
    )
    assert resposta_chat["status"] == 200

    prazo_historico = time.time() + 10.0
    historico_disponivel = False
    while time.time() < prazo_historico:
        historico = _api_fetch(
            page,
            path=f"/app/api/laudo/{laudo_id}/mensagens",
            method="GET",
        )
        itens = historico.get("body", {}).get("itens") if isinstance(historico.get("body"), dict) else None
        if historico.get("status") == 200 and isinstance(itens, list) and len(itens) >= 1:
            historico_disponivel = True
            break
        page.wait_for_timeout(250)
    assert historico_disponivel, "Histórico canônico do laudo não ficou disponível a tempo."

    page.goto(
        f"{live_server_url}/app/?laudo={laudo_id}&aba=historico",
        wait_until="domcontentloaded",
    )
    _esperar_contexto_workspace_inspetor(
        page,
        laudo_id=laudo_id,
        aba="historico",
        view="inspection_history",
    )
    page.evaluate(
        """async (idLaudo) => {
            if (window.TarielAPI?.carregarLaudo) {
                await window.TarielAPI.carregarLaudo(idLaudo, {
                    forcar: true,
                    silencioso: true,
                });
            }
        }""",
        laudo_id,
    )
    expect(page.locator("[data-workspace-history-root]")).to_be_visible(timeout=10000)
    expect(page.locator(".workspace-history-card__text").first).to_be_visible(timeout=10000)

    page.locator('[data-chat-filter="ia"]').click(force=True)
    page.wait_for_function(
        """() => (
            document.body?.dataset?.threadTab === "historico"
            && document.querySelectorAll('.workspace-history-card[data-history-role="ia"]').length >= 1
        )""",
        timeout=10000,
    )
    assert page.locator('.workspace-history-card[data-history-role="ia"]').count() >= 1
    texto_historico_ia = page.locator(
        '.workspace-history-card[data-history-role="ia"] .workspace-history-card__text'
    ).first.inner_text().strip()

    token_busca = texto_historico_ia.rsplit(" ", 1)[-1]
    page.locator("#chat-thread-search").fill(token_busca)
    expect(
        page.locator(".workspace-history-card__text", has_text=texto_historico_ia).first
    ).to_be_visible(timeout=10000)

    page.locator('[data-history-type-filter="mensagens"]').click(force=True)
    expect(page.locator("#chat-thread-results")).to_contain_text(re.compile(r"registro", re.IGNORECASE))


def test_e2e_historico_pin_unpin_e_excluir_laudo(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    _iniciar_inspecao_via_modal(page, tipo_template="padrao")
    laudo_id = _obter_laudo_ativo(page)
    resposta_chat = _api_fetch(
        page,
        path="/app/api/chat",
        method="POST",
        json_body={
            "mensagem": "/pendencias",
            "dados_imagem": "",
            "setor": "geral",
            "historico": [],
            "modo": "detalhado",
            "texto_documento": "",
            "nome_documento": "",
            "laudo_id": laudo_id,
        },
    )
    assert resposta_chat["status"] == 200
    assert isinstance(resposta_chat["body"], dict)
    assert resposta_chat["body"].get("laudo_card", {}).get("id") == laudo_id

    page.locator(".btn-home-cabecalho").click()
    expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=10000)
    page.goto(f"{live_server_url}/app/?home=1", wait_until="domcontentloaded")
    expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=10000)
    item_alvo = page.locator(f'#lista-historico .item-historico[data-laudo-id="{laudo_id}"]').first
    expect(item_alvo).to_be_visible(timeout=10000)
    item_alvo.scroll_into_view_if_needed()
    laudo_alvo = str(laudo_id)

    botao_pin = item_alvo.locator('[data-acao-laudo="pin"]').first
    estado_inicial = botao_pin.get_attribute("aria-pressed")
    botao_pin.click(force=True)
    expect(botao_pin).not_to_have_attribute("aria-pressed", estado_inicial or "false")

    page.wait_for_function(
        """(laudoId) => {
            const item = document.querySelector(`.item-historico[data-laudo-id="${laudoId}"]`);
            const btn = item?.querySelector('[data-acao-laudo="pin"]');
            return item && (item.dataset.pinado === "true" || btn?.getAttribute("aria-pressed") === "true");
        }""",
        arg=laudo_alvo,
        timeout=10000,
    )
    page.evaluate(
        """(laudoId) => {
            const btn = document.querySelector(`.item-historico[data-laudo-id="${laudoId}"] [data-acao-laudo="pin"]`);
            btn?.click();
        }""",
        laudo_alvo,
    )

    _selecionar_aba_laudos_sidebar(page, "recentes")
    item_alvo = page.locator(f'.item-historico[data-laudo-id="{laudo_alvo}"]:visible').first
    expect(item_alvo).to_be_visible(timeout=10000)
    botao_pin = item_alvo.locator('[data-acao-laudo="pin"]').first
    expect(botao_pin).to_have_attribute("aria-pressed", estado_inicial or "false")

    resposta_desativar = _api_fetch(page, path="/app/api/laudo/desativar", method="POST")
    assert resposta_desativar["status"] == 200
    page.goto(f"{live_server_url}/app/?home=1", wait_until="domcontentloaded")
    expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=10000)

    item_alvo = page.locator(f'.item-historico[data-laudo-id="{laudo_alvo}"]:visible').first
    expect(item_alvo).to_be_visible(timeout=10000)
    item_alvo.scroll_into_view_if_needed()
    total_antes = page.locator(".item-historico[data-laudo-id]:visible").count()
    expect(item_alvo.locator('[data-acao-laudo="delete"]').first).to_have_count(1)
    resposta_excluir = _api_fetch(
        page,
        path=f"/app/api/laudo/{laudo_alvo}",
        method="DELETE",
    )
    assert resposta_excluir["status"] in {200, 204}
    page.goto(f"{live_server_url}/app/?home=1", wait_until="domcontentloaded")
    expect(page.locator(f'.item-historico[data-laudo-id="{laudo_alvo}"]:visible')).to_have_count(0)
    assert page.locator(".item-historico[data-laudo-id]:visible").count() == max(total_antes - 1, 0)


@pytest.mark.parametrize(
    ("largura", "altura"),
    [
        (1366, 768),
        (390, 844),
    ],
)
def test_e2e_responsivo_chat_sem_overflow_e_sem_sobreposicao(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
    largura: int,
    altura: int,
) -> None:
    contexto = browser.new_context(viewport={"width": largura, "height": altura})
    try:
        page = contexto.new_page()
        _fazer_login(
            page,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        _iniciar_inspecao_via_modal(page, tipo_template="padrao")
        laudo_id = _obter_laudo_ativo(page)
        _carregar_laudo_no_inspetor(page, laudo_id)
        _assert_sem_overflow_horizontal(page)
        _assert_controles_flutuantes_sem_sobreposicao(page)

        if largura <= 1199:
            expect(page.locator("#btn-mesa-widget-toggle")).to_be_hidden()
            expect(page.locator("#btn-toggle-humano")).to_be_hidden()
        else:
            expect(page.locator("#btn-mesa-widget-toggle")).to_be_visible(timeout=10000)
            page.locator("#btn-mesa-widget-toggle").click()
            expect(page.locator("#painel-mesa-widget")).to_be_visible()

            metricas_painel = page.evaluate(
                """() => {
                    const painel = document.getElementById("painel-mesa-widget");
                    const r = painel ? painel.getBoundingClientRect() : { left: 0, right: 0, top: 0, bottom: 0, width: 0, height: 0 };
                    return {
                        viewportW: window.innerWidth,
                        viewportH: window.innerHeight,
                        left: r.left,
                        right: r.right,
                        top: r.top,
                        bottom: r.bottom,
                        width: r.width,
                        height: r.height
                    };
                }"""
            )
            assert float(metricas_painel["width"]) > 180
            assert float(metricas_painel["height"]) > 180
            assert float(metricas_painel["left"]) >= -2
            assert float(metricas_painel["right"]) <= float(metricas_painel["viewportW"]) + 2
            assert float(metricas_painel["top"]) >= -2

        _assert_sem_overflow_horizontal(page)
    finally:
        contexto.close()


@pytest.mark.parametrize(
    ("largura", "altura"),
    [
        (1366, 768),
        (390, 844),
    ],
)
def test_e2e_responsivo_admin_sem_overflow_horizontal(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
    largura: int,
    altura: int,
) -> None:
    contexto = browser.new_context(viewport={"width": largura, "height": altura})
    try:
        page = contexto.new_page()
        _fazer_login(
            page,
            base_url=live_server_url,
            portal="admin",
            email=credenciais_seed["admin"]["email"],
            senha=credenciais_seed["admin"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/admin/painel/?$",
        )

        expect(page.locator(".btn-novo-cliente")).to_be_visible()
        page.locator(".btn-novo-cliente").scroll_into_view_if_needed()
        _assert_sem_overflow_horizontal(page)
    finally:
        contexto.close()


def test_e2e_admin_navegacao_basica_sem_redirecionar_para_login(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="admin",
        email=credenciais_seed["admin"]["email"],
        senha=credenciais_seed["admin"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/admin/painel/?$",
    )

    page.goto(f"{live_server_url}/admin/clientes", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(rf"{re.escape(live_server_url)}/admin/clientes/?"))

    page.reload(wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(rf"{re.escape(live_server_url)}/admin/clientes/?"))
    assert "/admin/login" not in page.url

    page.goto(f"{live_server_url}/admin/painel", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(rf"{re.escape(live_server_url)}/admin/painel/?$"))


def test_e2e_admin_provisiona_admin_cliente_e_portal_unificado_funciona(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_admin = browser.new_context()
    contexto_cliente = browser.new_context()

    try:
        page_admin = contexto_admin.new_page()
        _fazer_login(
            page_admin,
            base_url=live_server_url,
            portal="admin",
            email=credenciais_seed["admin"]["email"],
            senha=credenciais_seed["admin"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/admin/painel/?$",
        )

        sufixo = uuid.uuid4().hex[:8]
        email_cliente = f"cliente.{sufixo}@empresa.test"
        cnpj = f"{uuid.uuid4().int % 10**14:014d}"

        page_admin.goto(f"{live_server_url}/admin/novo-cliente", wait_until="domcontentloaded")
        page_admin.locator('input[name="nome"]').fill(f"Cliente E2E {sufixo}")
        page_admin.locator('input[name="cnpj"]').fill(cnpj)
        page_admin.locator('select[name="plano"]').select_option("Intermediario")
        page_admin.locator('input[name="email"]').fill(email_cliente)
        page_admin.locator('input[name="segmento"]').fill("Industrial")
        page_admin.locator('input[name="cidade_estado"]').fill("Goiânia/GO")
        page_admin.locator('input[name="nome_responsavel"]').fill("Responsável E2E")
        page_admin.locator('textarea[name="observacoes"]').fill("Provisionamento automatizado E2E.")
        page_admin.get_by_role("button", name="Criar empresa").click()

        expect(page_admin).to_have_url(_regex_url_admin_cliente_pos_cadastro(live_server_url))
        senha_temporaria = _extrair_senha_temporaria_da_pagina(page_admin)

        page_cliente = contexto_cliente.new_page()
        nova_senha_cliente = f"Nova@{sufixo}12345"
        _login_cliente_primeiro_acesso(
            page_cliente,
            base_url=live_server_url,
            email=email_cliente,
            senha_temporaria=senha_temporaria,
            nova_senha=nova_senha_cliente,
        )

        expect(page_cliente.locator("#hero-prioridades")).to_be_visible()
        expect(page_cliente.locator("#tab-admin")).to_be_visible()
        expect(page_cliente.locator("#tab-chat")).to_be_visible()
        expect(page_cliente.locator("#tab-mesa")).to_be_visible()
        page_cliente.locator("#admin-section-tab-team").click()
        expect(page_cliente.locator("#usuarios-busca")).to_be_visible()
        expect(page_cliente.locator("#lista-usuarios")).not_to_contain_text(email_cliente)
        expect(page_cliente.locator("#lista-usuarios")).not_to_contain_text("admin-cliente@tariel.ia")
        expect(page_cliente.locator("#lista-usuarios")).not_to_contain_text("inspetor@tariel.ia")
        expect(page_cliente.locator("#lista-usuarios")).not_to_contain_text("revisor@tariel.ia")

        resposta_plano = _api_fetch(
            page_cliente,
            path="/cliente/api/empresa/plano/interesse",
            method="POST",
            json_body={"plano": "Ilimitado", "origem": "admin"},
        )
        assert resposta_plano["status"] == 200
        page_cliente.reload(wait_until="domcontentloaded")
        page_cliente.locator("#admin-section-tab-capacity").click()
        expect(page_cliente.locator("#empresa-cards")).to_contain_text("Intermediario", timeout=10000)
        expect(page_cliente.locator("#admin-planos-historico")).to_contain_text("Ilimitado", timeout=10000)
        auditoria_plano = _api_fetch(page_cliente, path="/cliente/api/auditoria")
        assert auditoria_plano["status"] == 200
        assert any(item["acao"] == "plano_interesse_registrado" for item in auditoria_plano["body"]["itens"])

        email_inspetor = f"inspetor.{sufixo}@empresa.test"
        resposta_inspetor = _api_fetch(
            page_cliente,
            path="/cliente/api/usuarios",
            method="POST",
            json_body={
                "nome": "Inspetor Cliente",
                "email": email_inspetor,
                "nivel_acesso": "inspetor",
                "telefone": "62999990000",
                "crea": "",
            },
        )
        assert resposta_inspetor["status"] == 201
        assert resposta_inspetor["body"]["senha_temporaria"]
        page_cliente.reload(wait_until="domcontentloaded")
        page_cliente.locator("#admin-section-tab-team").click()
        expect(page_cliente.locator("#admin-onboarding-resumo")).to_be_visible()
        expect(page_cliente.locator("#lista-usuarios")).to_contain_text(email_inspetor, timeout=10000)
        page_cliente.get_by_role("button", name="Ver primeiros acessos").click()
        expect(page_cliente.locator("#usuarios-resumo")).to_contain_text("Filtro rapido: Primeiros acessos", timeout=10000)
        expect(page_cliente.locator("#lista-usuarios")).to_contain_text(email_inspetor, timeout=10000)
        page_cliente.locator("#admin-onboarding-lista").get_by_role("button", name="Gerar nova senha").first.click()
        expect(page_cliente.locator("#feedback")).to_contain_text("Senha temporaria:", timeout=10000)
        prioridade_primeiro_acesso = page_cliente.locator("#hero-prioridades .priority-item").filter(has_text="Primeiro acesso pendente")
        expect(prioridade_primeiro_acesso).to_be_visible(timeout=10000)
        prioridade_primeiro_acesso.get_by_role("button", name="Revisar equipe").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/painel(?:\?sec=team)?/?$"))
        expect(page_cliente.locator("#tab-admin")).to_have_attribute("aria-selected", "true")
        expect(page_cliente.locator("#admin-section-tab-team")).to_have_attribute("aria-selected", "true")
        expect(page_cliente.locator("#usuarios-busca")).to_have_value(email_inspetor)
        expect(page_cliente.locator(f'#lista-usuarios [data-user-row="{resposta_inspetor["body"]["usuario"]["id"]}"]')).to_have_class(
            re.compile(r"user-row-highlight"),
            timeout=10000,
        )
        auditoria_usuario = _api_fetch(page_cliente, path="/cliente/api/auditoria")
        assert auditoria_usuario["status"] == 200
        assert any(item["acao"] == "usuario_criado" for item in auditoria_usuario["body"]["itens"])

        email_revisor = f"mesa.{sufixo}@empresa.test"
        resposta_revisor = _api_fetch(
            page_cliente,
            path="/cliente/api/usuarios",
            method="POST",
            json_body={
                "nome": "Mesa Cliente",
                "email": email_revisor,
                "nivel_acesso": "revisor",
                "telefone": "62999991111",
                "crea": "123456/GO",
            },
        )
        assert resposta_revisor["status"] == 201
        assert resposta_revisor["body"]["senha_temporaria"]
        page_cliente.reload(wait_until="domcontentloaded")
        page_cliente.locator("#admin-section-tab-team").click()
        expect(page_cliente.locator("#lista-usuarios")).to_contain_text(email_revisor, timeout=10000)

        resposta_laudo = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/laudos",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        assert resposta_laudo["status"] == 200
        laudo_id = int(resposta_laudo["body"]["laudo_id"])

        texto_whisper = f"@mesa Revisar fluxo do admin-cliente {sufixo}"
        resposta_chat = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/mensagem",
            method="POST",
            json_body={
                "laudo_id": laudo_id,
                "mensagem": texto_whisper,
                "historico": [],
                "setor": "geral",
                "modo": "detalhado",
            },
        )
        assert resposta_chat["status"] == 200
        page_cliente.reload(wait_until="domcontentloaded")

        page_cliente.locator("#tab-chat").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat(?:\?sec=overview)?/?$"))
        expect(page_cliente.locator("#chat-triagem")).to_be_visible()
        expect(page_cliente.locator("#chat-movimentos")).to_be_visible()
        page_cliente.locator("#chat-section-tab-queue").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat\?sec=queue/?$"))
        expect(page_cliente.locator("#chat-busca-laudos")).to_be_visible()
        page_cliente.locator("#chat-section-tab-case").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat\?sec=case/?$"))
        expect(page_cliente.locator("#chat-contexto")).to_be_visible()
        expect(page_cliente.locator("#btn-chat-upload-doc")).to_be_visible()
        page_cliente.locator("#chat-section-tab-overview").click()
        page_cliente.get_by_role("button", name="Ver abertos").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat\?sec=queue/?$"))
        expect(page_cliente.locator("#chat-lista-resumo")).to_contain_text("Filtro rapido: Em operação", timeout=10000)
        expect(page_cliente.locator("#lista-chat-laudos")).to_contain_text("Aberto", timeout=10000)

        page_cliente.locator("#tab-mesa").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa(?:\?sec=overview)?/?$"))
        page_cliente.locator("#mesa-section-tab-pending").click()
        expect(page_cliente.locator("#mesa-triagem")).to_be_visible()
        expect(page_cliente.locator("#mesa-movimentos")).to_be_visible()
        page_cliente.locator("#mesa-triagem").get_by_role("button", name="Ver respostas novas").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa\?sec=queue/?$"))
        expect(page_cliente.locator("#mesa-lista-resumo")).to_contain_text("Filtro rapido: Respostas novas", timeout=10000)
        page_cliente.locator("#mesa-section-tab-pending").click()
        page_cliente.locator("#mesa-triagem").get_by_role("button", name="Limpar filtro rapido").click()
        page_cliente.wait_for_function(
            "() => !!document.querySelector('#lista-mesa-laudos [data-mesa]')",
            timeout=10000,
        )
        page_cliente.locator(f"#lista-mesa-laudos [data-mesa='{laudo_id}']").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa\?sec=reply/?$"))
        expect(page_cliente.locator("#mesa-busca-laudos")).not_to_be_visible()
        expect(page_cliente.locator("#mesa-contexto")).to_be_visible()
        expect(page_cliente.locator("#mesa-mensagens")).to_contain_text(
            re.compile(r"admin-cliente", re.IGNORECASE),
            timeout=10000,
        )

        texto_resposta = f"Retorno mesa cliente {sufixo}"
        page_cliente.locator("#mesa-resposta").fill(texto_resposta)
        page_cliente.locator("#form-mesa-msg button[type='submit']").click()
        expect(page_cliente.locator("#mesa-mensagens")).to_contain_text(texto_resposta, timeout=10000)
    finally:
        contexto_admin.close()
        contexto_cliente.close()


def test_e2e_admin_cliente_deep_links_por_secao_preservam_shell_e_historico(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_cliente = browser.new_context()

    try:
        page_cliente = contexto_cliente.new_page()
        _fazer_login(
            page_cliente,
            base_url=live_server_url,
            portal="cliente",
            email=credenciais_seed["admin_cliente"]["email"],
            senha=credenciais_seed["admin_cliente"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/cliente/painel(?:\?sec=overview)?/?$",
        )

        resposta_laudo = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/laudos",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        assert resposta_laudo["status"] == 200
        laudo_id = int(resposta_laudo["body"]["laudo_id"])

        resposta_chat = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/mensagem",
            method="POST",
            json_body={
                "laudo_id": laudo_id,
                "mensagem": f"Mensagem E2E portal cliente {uuid.uuid4().hex[:8]}",
                "historico": [],
                "setor": "geral",
                "modo": "detalhado",
            },
        )
        assert resposta_chat["status"] == 200

        page_cliente.goto(f"{live_server_url}/cliente/painel?sec=team", wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/painel\?sec=team$"))
        expect(page_cliente.locator("#tab-admin")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#admin-section-tab-team")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#admin-team")).to_be_visible()
        expect(page_cliente.locator("#admin-section-summary-title")).to_have_text("Equipe")
        expect(page_cliente.locator("#admin-section-count-team")).to_contain_text(re.compile(r"perfis operacionais", re.IGNORECASE))

        page_cliente.reload(wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/painel\?sec=team$"))
        expect(page_cliente.locator("#admin-section-tab-team")).to_have_attribute("aria-current", "page")

        page_cliente.locator("#admin-section-tab-capacity").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/painel\?sec=capacity$"))
        expect(page_cliente.locator("#admin-section-tab-capacity")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#admin-capacity")).to_be_visible()

        page_cliente.go_back()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/painel\?sec=team$"))
        expect(page_cliente.locator("#admin-section-tab-team")).to_have_attribute("aria-current", "page")

        page_cliente.goto(f"{live_server_url}/cliente/chat?sec=queue", wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat\?sec=queue$"))
        expect(page_cliente.locator("#tab-chat")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#chat-section-tab-queue")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#chat-queue")).to_be_visible()
        expect(page_cliente.locator("#chat-section-count-queue")).to_contain_text(re.compile(r"casos na fila", re.IGNORECASE))
        expect(page_cliente.locator(f'#lista-chat-laudos [data-chat="{laudo_id}"]')).to_be_visible(timeout=10000)

        page_cliente.locator(f'#lista-chat-laudos [data-chat="{laudo_id}"]').click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat\?sec=case$"))
        expect(page_cliente.locator("#chat-section-tab-case")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#chat-case")).to_be_visible()
        expect(page_cliente.locator("#chat-section-summary-title")).to_have_text("Caso ativo")

        page_cliente.go_back()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat\?sec=queue$"))
        expect(page_cliente.locator("#chat-section-tab-queue")).to_have_attribute("aria-current", "page")

        page_cliente.goto(f"{live_server_url}/cliente/mesa?sec=pending", wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa\?sec=pending$"))
        expect(page_cliente.locator("#tab-mesa")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#mesa-section-tab-pending")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#mesa-pending")).to_be_visible()
        expect(page_cliente.locator("#mesa-section-count-pending")).to_contain_text(re.compile(r"pendencias|whispers", re.IGNORECASE))

        page_cliente.locator("#mesa-section-tab-queue").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa\?sec=queue$"))
        expect(page_cliente.locator(f'#lista-mesa-laudos [data-mesa="{laudo_id}"]')).to_be_visible(timeout=10000)

        page_cliente.locator(f'#lista-mesa-laudos [data-mesa="{laudo_id}"]').click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa\?sec=reply$"))
        expect(page_cliente.locator("#mesa-section-tab-reply")).to_have_attribute("aria-current", "page")
        expect(page_cliente.locator("#mesa-reply")).to_be_visible()
        expect(page_cliente.locator("#mesa-section-summary-title")).to_have_text("Responder")

        page_cliente.go_back()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa\?sec=queue$"))
        expect(page_cliente.locator("#mesa-section-tab-queue")).to_have_attribute("aria-current", "page")
    finally:
        contexto_cliente.close()


def test_e2e_admin_ceo_cria_empresa_ilimitada_e_admin_cliente_consume_mesmo_tenant(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_admin = browser.new_context()
    contexto_cliente = browser.new_context()

    try:
        page_admin = contexto_admin.new_page()
        _fazer_login(
            page_admin,
            base_url=live_server_url,
            portal="admin",
            email=credenciais_seed["admin"]["email"],
            senha=credenciais_seed["admin"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/admin/painel/?$",
        )

        sufixo = uuid.uuid4().hex[:8]
        nome_empresa = f"Empresa Ilimitada {sufixo}"
        email_cliente = f"cliente.ilimitado.{sufixo}@empresa.test"
        senha_temporaria = _provisionar_cliente_via_admin(
            page_admin,
            base_url=live_server_url,
            nome=nome_empresa,
            email=email_cliente,
            cnpj=f"{uuid.uuid4().int % 10**14:014d}",
            segmento="Industrial Premium",
            cidade_estado="São Paulo/SP",
            nome_responsavel="Responsável Ilimitado",
            observacoes="Provisionamento E2E do tenant ilimitado via Admin-CEO.",
            plano="Ilimitado",
        )

        page_admin.goto(f"{live_server_url}/admin/clientes", wait_until="domcontentloaded")
        linha_cliente = page_admin.locator("tbody tr").filter(has_text=nome_empresa).first
        expect(linha_cliente).to_be_visible(timeout=10000)
        expect(linha_cliente).to_contain_text("Ilimitado")

        page_cliente = contexto_cliente.new_page()
        nova_senha_cliente = f"Cliente@{sufixo}12345"
        _login_cliente_primeiro_acesso(
            page_cliente,
            base_url=live_server_url,
            email=email_cliente,
            senha_temporaria=senha_temporaria,
            nova_senha=nova_senha_cliente,
        )

        expect(page_cliente.locator("#hero-prioridades")).to_be_visible(timeout=10000)
        expect(page_cliente.locator("#empresa-cards")).to_contain_text("Ilimitado", timeout=10000)
        expect(page_cliente.locator("#empresa-cards")).to_contain_text("Sem teto comercial neste contrato", timeout=10000)
        page_cliente.locator("#admin-section-tab-capacity").click()
        expect(page_cliente.locator("#empresa-resumo-detalhado")).to_contain_text("Limite mensal: sem teto", timeout=10000)
        expect(page_cliente.locator("#empresa-resumo-detalhado")).to_contain_text("Laudos restantes: sem teto", timeout=10000)
        expect(page_cliente.locator("#empresa-resumo-detalhado")).to_contain_text("Limite de usuarios: sem teto", timeout=10000)
        expect(page_cliente.locator("#empresa-resumo-detalhado")).to_contain_text("Vagas restantes: sem teto", timeout=10000)

        page_cliente.goto(f"{live_server_url}/cliente/chat", wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat(?:\?sec=overview)?/?$"))
        expect(page_cliente.locator("#tab-chat")).to_have_attribute("aria-selected", "true")
        page_cliente.locator("#chat-section-tab-queue").click()
        expect(page_cliente.locator("#chat-busca-laudos")).to_be_visible(timeout=10000)

        page_cliente.goto(f"{live_server_url}/cliente/mesa", wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa(?:\?sec=overview)?/?$"))
        expect(page_cliente.locator("#tab-mesa")).to_have_attribute("aria-selected", "true")
        page_cliente.locator("#mesa-section-tab-queue").click()
        expect(page_cliente.locator("#mesa-busca-laudos")).to_be_visible(timeout=10000)

        page_cliente.goto(f"{live_server_url}/cliente/painel", wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/painel(?:\?sec=overview)?/?$"))
        expect(page_cliente.locator("#tab-admin")).to_have_attribute("aria-selected", "true")

        resumo_inicial = _api_fetch(page_cliente, path="/cliente/api/empresa/resumo")
        assert resumo_inicial["status"] == 200
        assert isinstance(resumo_inicial["body"], dict)
        assert resumo_inicial["body"]["plano_ativo"] == "Ilimitado"
        assert resumo_inicial["body"]["usuarios_max"] is None
        assert resumo_inicial["body"]["laudos_mes_limite"] is None
        assert resumo_inicial["body"]["usuarios_restantes"] is None
        assert resumo_inicial["body"]["laudos_restantes"] is None
        assert resumo_inicial["body"]["uso_percentual"] is None

        email_inspetor = f"insp.ilimitado.{sufixo}@empresa.test"
        email_revisor = f"mesa.ilimitado.{sufixo}@empresa.test"
        resposta_inspetor = _api_fetch(
            page_cliente,
            path="/cliente/api/usuarios",
            method="POST",
            json_body={
                "nome": "Inspetor Ilimitado",
                "email": email_inspetor,
                "nivel_acesso": "inspetor",
                "telefone": "11999990001",
                "crea": "",
            },
        )
        resposta_revisor = _api_fetch(
            page_cliente,
            path="/cliente/api/usuarios",
            method="POST",
            json_body={
                "nome": "Mesa Ilimitada",
                "email": email_revisor,
                "nivel_acesso": "revisor",
                "telefone": "11999990002",
                "crea": "123456/SP",
            },
        )
        assert resposta_inspetor["status"] == 201
        assert resposta_revisor["status"] == 201

        resposta_laudo = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/laudos",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        assert resposta_laudo["status"] == 200
        laudo_id = int(resposta_laudo["body"]["laudo_id"])

        bootstrap = _api_fetch(page_cliente, path="/cliente/api/bootstrap")
        assert bootstrap["status"] == 200
        assert isinstance(bootstrap["body"], dict)
        emails_operacionais = {item["email"] for item in bootstrap["body"]["usuarios"]}
        assert email_cliente not in emails_operacionais
        assert email_inspetor in emails_operacionais
        assert email_revisor in emails_operacionais
        assert laudo_id in {int(item["id"]) for item in bootstrap["body"]["chat"]["laudos"]}

        page_cliente.reload(wait_until="domcontentloaded")
        page_cliente.locator("#admin-section-tab-team").click()
        expect(page_cliente.locator("#lista-usuarios")).not_to_contain_text(email_cliente)
        expect(page_cliente.locator("#lista-usuarios")).to_contain_text(email_inspetor, timeout=10000)
        expect(page_cliente.locator("#lista-usuarios")).to_contain_text(email_revisor, timeout=10000)
        page_cliente.locator("#admin-section-tab-overview").click()
        expect(page_cliente.locator("#empresa-cards")).to_contain_text("Sem teto comercial neste contrato", timeout=10000)

        resumo_final = _api_fetch(page_cliente, path="/cliente/api/empresa/resumo")
        assert resumo_final["status"] == 200
        assert isinstance(resumo_final["body"], dict)
        assert resumo_final["body"]["plano_ativo"] == "Ilimitado"
        assert resumo_final["body"]["usuarios_em_uso"] >= 3
        assert resumo_final["body"]["laudos_mes_atual"] >= 1
        assert resumo_final["body"]["usuarios_max"] is None
        assert resumo_final["body"]["laudos_mes_limite"] is None
        assert resumo_final["body"]["usuarios_restantes"] is None
        assert resumo_final["body"]["laudos_restantes"] is None
    finally:
        contexto_admin.close()
        contexto_cliente.close()


def test_e2e_admin_cliente_mesa_ignora_resposta_atrasada_ao_trocar_de_laudo(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_cliente = browser.new_context()

    try:
        page_cliente = contexto_cliente.new_page()
        _fazer_login(
            page_cliente,
            base_url=live_server_url,
            portal="cliente",
            email=credenciais_seed["admin_cliente"]["email"],
            senha=credenciais_seed["admin_cliente"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/cliente/painel(?:\?sec=overview)?/?$",
        )

        laudo_a = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/laudos",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        laudo_b = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/laudos",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        assert laudo_a["status"] == 200
        assert laudo_b["status"] == 200

        laudo_a_id = int(laudo_a["body"]["laudo_id"])
        laudo_b_id = int(laudo_b["body"]["laudo_id"])
        sufixo = uuid.uuid4().hex[:8]
        texto_a = f"Portal mesa corrida A {sufixo}"
        texto_b = f"Portal mesa corrida B {sufixo}"

        envio_a = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/mensagem",
            method="POST",
            json_body={
                "laudo_id": laudo_a_id,
                "mensagem": f"@mesa {texto_a}",
                "historico": [],
                "setor": "geral",
                "modo": "detalhado",
            },
        )
        envio_b = _api_fetch(
            page_cliente,
            path="/cliente/api/chat/mensagem",
            method="POST",
            json_body={
                "laudo_id": laudo_b_id,
                "mensagem": f"@mesa {texto_b}",
                "historico": [],
                "setor": "geral",
                "modo": "detalhado",
            },
        )
        assert envio_a["status"] == 200
        assert envio_b["status"] == 200

        page_cliente.reload(wait_until="domcontentloaded")
        page_cliente.locator("#tab-mesa").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa(?:\?sec=overview)?/?$"))
        page_cliente.locator("#mesa-section-tab-queue").click()
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/mesa\?sec=queue/?$"))
        page_cliente.wait_for_function(
            "() => !!document.querySelector('#lista-mesa-laudos [data-mesa]')",
            timeout=10000,
        )

        _atrasar_requisicoes(
            page_cliente,
            padroes=[f"**/cliente/api/mesa/laudos/{laudo_a_id}/*"],
            atraso_ms=900,
        )

        _disparar_click_mesa_lista(page_cliente, laudo_a_id)
        page_cliente.wait_for_timeout(80)
        _disparar_click_mesa_lista(page_cliente, laudo_b_id)

        expect(page_cliente.locator("#mesa-mensagens")).to_contain_text(texto_b, timeout=10000)
        page_cliente.wait_for_timeout(1200)
        expect(page_cliente.locator("#mesa-mensagens")).not_to_contain_text(texto_a)
    finally:
        contexto_cliente.close()


def test_e2e_admin_cliente_secao_novo_laudo_mantem_copy_sem_jargao_interno(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_cliente = browser.new_context()

    try:
        page_cliente = contexto_cliente.new_page()
        _fazer_login(
            page_cliente,
            base_url=live_server_url,
            portal="cliente",
            email=credenciais_seed["admin_cliente"]["email"],
            senha=credenciais_seed["admin_cliente"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/cliente/painel(?:\?sec=overview)?/?$",
        )

        page_cliente.goto(f"{live_server_url}/cliente/chat?sec=new", wait_until="domcontentloaded")
        expect(page_cliente).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat\?sec=new$"))
        expect(page_cliente.locator("#chat-new")).to_be_visible()
        expect(page_cliente.locator("#chat-new")).to_contain_text("Abertura guiada de laudo")
        expect(page_cliente.locator("#chat-new")).to_contain_text("Escolha um modelo liberado para a empresa")
        expect(page_cliente.locator("#chat-new")).to_contain_text("Modelo liberado")
        expect(page_cliente.locator("#chat-new")).not_to_contain_text(re.compile(r"tenant|master template|seed can[oô]nico", re.IGNORECASE))
        page_cliente.wait_for_function(
            "() => document.querySelectorAll('#chat-tipo-template option').length >= 1",
            timeout=10000,
        )
        expect(page_cliente.locator("#btn-chat-laudo-criar")).to_have_text("Criar laudo")
    finally:
        contexto_cliente.close()


def test_e2e_admin_cliente_isola_empresas_no_portal_unificado(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_admin = browser.new_context()
    contexto_cliente_a = browser.new_context()
    contexto_cliente_b = browser.new_context()

    try:
        page_admin = contexto_admin.new_page()
        _fazer_login(
            page_admin,
            base_url=live_server_url,
            portal="admin",
            email=credenciais_seed["admin"]["email"],
            senha=credenciais_seed["admin"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/admin/painel/?$",
        )

        sufixo = uuid.uuid4().hex[:8]
        email_cliente_a = f"cliente.a.{sufixo}@empresa.test"
        email_cliente_b = f"cliente.b.{sufixo}@empresa.test"

        senha_temp_a = _provisionar_cliente_via_admin(
            page_admin,
            base_url=live_server_url,
            nome=f"Cliente A {sufixo}",
            email=email_cliente_a,
            cnpj=f"{uuid.uuid4().int % 10**14:014d}",
            segmento="Industrial A",
            cidade_estado="Goiânia/GO",
            nome_responsavel="Responsável A",
            observacoes="Cliente A criado para validar isolamento multiempresa.",
            plano="Intermediario",
        )
        senha_temp_b = _provisionar_cliente_via_admin(
            page_admin,
            base_url=live_server_url,
            nome=f"Cliente B {sufixo}",
            email=email_cliente_b,
            cnpj=f"{uuid.uuid4().int % 10**14:014d}",
            segmento="Industrial B",
            cidade_estado="Anápolis/GO",
            nome_responsavel="Responsável B",
            observacoes="Cliente B criado para validar isolamento multiempresa.",
            plano="Intermediario",
        )

        page_cliente_a = contexto_cliente_a.new_page()
        page_cliente_b = contexto_cliente_b.new_page()
        _login_cliente_primeiro_acesso(
            page_cliente_a,
            base_url=live_server_url,
            email=email_cliente_a,
            senha_temporaria=senha_temp_a,
            nova_senha=f"NovaA@{sufixo}12345",
        )
        _login_cliente_primeiro_acesso(
            page_cliente_b,
            base_url=live_server_url,
            email=email_cliente_b,
            senha_temporaria=senha_temp_b,
            nova_senha=f"NovaB@{sufixo}12345",
        )

        resposta_plano_a = _api_fetch(
            page_cliente_a,
            path="/cliente/api/empresa/plano/interesse",
            method="POST",
            json_body={"plano": "Ilimitado", "origem": "admin"},
        )
        resposta_plano_b = _api_fetch(
            page_cliente_b,
            path="/cliente/api/empresa/plano/interesse",
            method="POST",
            json_body={"plano": "Ilimitado", "origem": "admin"},
        )
        assert resposta_plano_a["status"] == 200
        assert resposta_plano_b["status"] == 200

        email_inspetor_a = f"insp.a.{sufixo}@empresa.test"
        email_inspetor_b = f"insp.b.{sufixo}@empresa.test"

        resposta_inspetor_a = _api_fetch(
            page_cliente_a,
            path="/cliente/api/usuarios",
            method="POST",
            json_body={
                "nome": "Inspetor A",
                "email": email_inspetor_a,
                "nivel_acesso": "inspetor",
                "telefone": "62990000001",
                "crea": "",
            },
        )
        assert resposta_inspetor_a["status"] == 201

        resposta_inspetor_b = _api_fetch(
            page_cliente_b,
            path="/cliente/api/usuarios",
            method="POST",
            json_body={
                "nome": "Inspetor B",
                "email": email_inspetor_b,
                "nivel_acesso": "inspetor",
                "telefone": "62990000002",
                "crea": "",
            },
        )
        assert resposta_inspetor_b["status"] == 201

        resposta_laudo_a = _api_fetch(
            page_cliente_a,
            path="/cliente/api/chat/laudos",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        resposta_laudo_b = _api_fetch(
            page_cliente_b,
            path="/cliente/api/chat/laudos",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        assert resposta_laudo_a["status"] == 200
        assert resposta_laudo_b["status"] == 200
        laudo_id_a = int(resposta_laudo_a["body"]["laudo_id"])
        laudo_id_b = int(resposta_laudo_b["body"]["laudo_id"])

        bootstrap_a = _api_fetch(page_cliente_a, path="/cliente/api/bootstrap")
        bootstrap_b = _api_fetch(page_cliente_b, path="/cliente/api/bootstrap")
        assert bootstrap_a["status"] == 200
        assert bootstrap_b["status"] == 200

        emails_a = {item["email"] for item in bootstrap_a["body"]["usuarios"]}
        emails_b = {item["email"] for item in bootstrap_b["body"]["usuarios"]}
        assert email_cliente_a not in emails_a
        assert email_inspetor_a in emails_a
        assert email_cliente_b not in emails_a
        assert email_inspetor_b not in emails_a
        assert email_cliente_b not in emails_b
        assert email_inspetor_b in emails_b
        assert email_cliente_a not in emails_b
        assert email_inspetor_a not in emails_b

        ids_laudos_a = {int(item["id"]) for item in bootstrap_a["body"]["chat"]["laudos"]}
        ids_laudos_b = {int(item["id"]) for item in bootstrap_b["body"]["chat"]["laudos"]}
        assert laudo_id_a in ids_laudos_a
        assert laudo_id_b not in ids_laudos_a
        assert laudo_id_b in ids_laudos_b
        assert laudo_id_a not in ids_laudos_b

        acesso_cruzado_chat_a = _api_fetch(
            page_cliente_a,
            path=f"/cliente/api/chat/laudos/{laudo_id_b}/mensagens",
        )
        acesso_cruzado_chat_b = _api_fetch(
            page_cliente_b,
            path=f"/cliente/api/chat/laudos/{laudo_id_a}/mensagens",
        )
        acesso_cruzado_mesa_a = _api_fetch(
            page_cliente_a,
            path=f"/cliente/api/mesa/laudos/{laudo_id_b}/mensagens",
        )
        acesso_cruzado_mesa_b = _api_fetch(
            page_cliente_b,
            path=f"/cliente/api/mesa/laudos/{laudo_id_a}/mensagens",
        )
        assert acesso_cruzado_chat_a["status"] == 404
        assert acesso_cruzado_chat_b["status"] == 404
        assert acesso_cruzado_mesa_a["status"] == 404
        assert acesso_cruzado_mesa_b["status"] == 404

        page_cliente_a.reload(wait_until="domcontentloaded")
        page_cliente_b.reload(wait_until="domcontentloaded")

        page_cliente_a.locator("#admin-section-tab-team").click()
        page_cliente_b.locator("#admin-section-tab-team").click()
        expect(page_cliente_a.locator("#lista-usuarios")).not_to_contain_text(email_cliente_a)
        expect(page_cliente_a.locator("#lista-usuarios")).to_contain_text(email_inspetor_a)
        expect(page_cliente_a.locator("#lista-usuarios")).not_to_contain_text(email_cliente_b)
        expect(page_cliente_a.locator("#lista-usuarios")).not_to_contain_text(email_inspetor_b)

        expect(page_cliente_b.locator("#lista-usuarios")).not_to_contain_text(email_cliente_b)
        expect(page_cliente_b.locator("#lista-usuarios")).to_contain_text(email_inspetor_b)
        expect(page_cliente_b.locator("#lista-usuarios")).not_to_contain_text(email_cliente_a)
        expect(page_cliente_b.locator("#lista-usuarios")).not_to_contain_text(email_inspetor_a)

        page_cliente_a.locator("#tab-chat").click()
        page_cliente_b.locator("#tab-chat").click()
        expect(page_cliente_a).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat(?:\?sec=overview)?/?$"))
        expect(page_cliente_b).to_have_url(re.compile(rf"{re.escape(live_server_url)}/cliente/chat(?:\?sec=overview)?/?$"))
        page_cliente_a.locator("#chat-section-tab-queue").click()
        page_cliente_b.locator("#chat-section-tab-queue").click()
        expect(page_cliente_a.locator(f'#lista-chat-laudos [data-chat="{laudo_id_a}"]')).to_be_visible(timeout=10000)
        expect(page_cliente_a.locator(f'#lista-chat-laudos [data-chat="{laudo_id_b}"]')).to_have_count(0)
        expect(page_cliente_b.locator(f'#lista-chat-laudos [data-chat="{laudo_id_b}"]')).to_be_visible(timeout=10000)
        expect(page_cliente_b.locator(f'#lista-chat-laudos [data-chat="{laudo_id_a}"]')).to_have_count(0)
    finally:
        contexto_admin.close()
        contexto_cliente_a.close()
        contexto_cliente_b.close()


def test_e2e_fluxo_bilateral_inspetor_e_revisor_no_canal_mesa(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        iniciar = _api_fetch(
            page_inspetor,
            path="/app/api/laudo/iniciar",
            method="POST",
            form_body={"tipo_template": "padrao"},
        )
        assert iniciar["status"] == 200
        assert isinstance(iniciar["body"], dict)
        laudo_id = int(iniciar["body"]["laudo_id"])

        enviar_mesa = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": "Mesa, validar item da NR-12 no equipamento A."},
        )
        assert enviar_mesa["status"] == 201
        referencia_id = int(enviar_mesa["body"]["mensagem"]["id"])

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        resposta_revisor = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/responder",
            method="POST",
            json_body={
                "texto": "Mesa: ponto validado, incluir foto complementar do item.",
                "referencia_mensagem_id": referencia_id,
            },
        )
        assert resposta_revisor["status"] == 200
        assert resposta_revisor["body"]["success"] is True

        mesa_inspetor = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagens",
            method="GET",
        )
        assert mesa_inspetor["status"] == 200
        itens_mesa = mesa_inspetor["body"]["itens"]
        assert any(item["tipo"] == "humano_eng" and item.get("referencia_mensagem_id") == referencia_id for item in itens_mesa)

        chat_ia = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mensagens",
            method="GET",
        )
        assert chat_ia["status"] == 200
        tipos_chat = {item["tipo"] for item in chat_ia["body"]["itens"]}
        assert "humano_eng" not in tipos_chat
        assert "humano_insp" not in tipos_chat
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_revisor_ui_responde_e_inspetor_recebe(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        texto_inspecao = f"Solicitação para mesa em teste UI {uuid.uuid4().hex[:8]}"
        envio_inspetor = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": texto_inspecao},
        )
        assert envio_inspetor["status"] == 201

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        _abrir_laudo_no_revisor(page_revisor, laudo_id)
        _abrir_painel_decisao_mesa_no_revisor(page_revisor)
        expect(page_revisor.locator("#view-timeline")).to_contain_text(re.compile(r"teste UI", re.IGNORECASE))
        expect(page_revisor.locator("#mesa-operacao-painel .mesa-operacao-tag")).to_contain_text(re.compile(r"canal em triagem", re.IGNORECASE))

        texto_resposta = f"Retorno da mesa via UI {uuid.uuid4().hex[:8]}"
        page_revisor.locator("#input-resposta").fill(texto_resposta)
        page_revisor.locator("#btn-enviar-msg").click()

        expect(page_revisor.locator("#view-timeline .bolha.engenharia", has_text=texto_resposta).first).to_be_visible(timeout=10000)
        expect(page_revisor.locator("#mesa-operacao-painel .mesa-operacao-tag")).to_contain_text(re.compile(r"1 pend[êe]ncia aberta", re.IGNORECASE))

        historico_mesa = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagens",
            method="GET",
        )
        assert historico_mesa["status"] == 200
        assert any(item["tipo"] == "humano_eng" and texto_resposta in item["texto"] for item in historico_mesa["body"]["itens"])
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_inspetor_retorna_no_widget_e_revisor_reflete_no_timeline(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        texto_inicial = f"Solicitacao inicial para mesa UI {uuid.uuid4().hex[:8]}"
        envio_inspetor = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": texto_inicial},
        )
        assert envio_inspetor["status"] == 201

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        _abrir_laudo_no_revisor(page_revisor, laudo_id)
        expect(page_revisor.locator("#view-timeline")).to_contain_text(re.compile(r"solicitacao inicial", re.IGNORECASE))

        texto_resposta = f"Retorno da mesa UI {uuid.uuid4().hex[:8]}"
        page_revisor.locator("#input-resposta").fill(texto_resposta)
        page_revisor.locator("#btn-enviar-msg").click()
        expect(page_revisor.locator("#view-timeline .bolha.engenharia", has_text=texto_resposta).first).to_be_visible(timeout=10000)

        _carregar_laudo_no_inspetor(page_inspetor, laudo_id)
        page_inspetor.locator("#btn-mesa-widget-toggle").click()
        expect(page_inspetor.locator("#painel-mesa-widget")).to_be_visible(timeout=10000)
        expect(page_inspetor.locator("#mesa-widget-lista")).to_contain_text(texto_resposta, timeout=10000)

        followup_texto = f"Campo respondeu no widget UI {uuid.uuid4().hex[:8]}"
        page_inspetor.locator("#mesa-widget-input").fill(followup_texto)
        page_inspetor.locator("#mesa-widget-enviar").click()
        expect(page_inspetor.locator("#mesa-widget-lista .mesa-widget-item.saida", has_text=followup_texto).first).to_be_visible(timeout=10000)
        expect(page_revisor.locator("#view-timeline .bolha.inspetor", has_text=followup_texto).first).to_be_visible(timeout=10000)
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_inspetor_anexa_arquivo_no_widget_mesa_e_revisor_visualiza(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        _carregar_laudo_no_inspetor(page_inspetor, laudo_id)
        page_inspetor.locator("#btn-mesa-widget-toggle").click()
        expect(page_inspetor.locator("#painel-mesa-widget")).to_be_visible(timeout=10000)

        page_inspetor.locator("#mesa-widget-input-anexo").set_input_files(
            {
                "name": "mesa-evidencia.png",
                "mimeType": "image/png",
                "buffer": base64.b64decode(PNG_1X1_TRANSPARENTE_B64),
            }
        )
        expect(page_inspetor.locator("#mesa-widget-preview-anexo")).to_contain_text("mesa-evidencia.png")
        page_inspetor.locator("#mesa-widget-enviar").click()

        expect(page_inspetor.locator("#mesa-widget-lista .anexo-mesa-link", has_text="mesa-evidencia.png").first).to_be_visible(timeout=10000)

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        _abrir_laudo_no_revisor(page_revisor, laudo_id)
        expect(page_revisor.locator("#view-timeline .anexo-mensagem-link", has_text="mesa-evidencia.png").first).to_be_visible(timeout=10000)
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_revisor_anexa_arquivo_e_inspetor_visualiza_no_widget_mesa(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        envio_inspetor = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": f"Abrindo canal de anexo UI {uuid.uuid4().hex[:8]}"},
        )
        assert envio_inspetor["status"] == 201

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        _abrir_laudo_no_revisor(page_revisor, laudo_id)

        page_revisor.locator("#input-anexo-resposta").set_input_files(
            {
                "name": "retorno-mesa.png",
                "mimeType": "image/png",
                "buffer": base64.b64decode(PNG_1X1_TRANSPARENTE_B64),
            }
        )
        expect(page_revisor.locator("#preview-resposta-anexo")).to_contain_text("retorno-mesa.png", timeout=10000)
        page_revisor.locator("#input-resposta").fill("Segue anexo complementar da mesa.")
        page_revisor.locator("#btn-enviar-msg").click()

        expect(page_revisor.locator("#view-timeline .anexo-mensagem-link", has_text="retorno-mesa.png").first).to_be_visible(timeout=10000)

        _carregar_laudo_no_inspetor(page_inspetor, laudo_id)
        page_inspetor.locator("#btn-mesa-widget-toggle").click()
        expect(page_inspetor.locator("#painel-mesa-widget")).to_be_visible(timeout=10000)
        expect(page_inspetor.locator("#mesa-widget-resumo-titulo")).to_contain_text(
            re.compile(r"pend[êe]ncia aberta|mesa respondeu|[uú]ltimo retorno veio da mesa", re.IGNORECASE)
        )
        expect(
            page_inspetor.locator(
                "#mesa-widget-lista .mesa-widget-pill-operacao",
                has_text=re.compile(r"pend[êe]ncia aberta", re.IGNORECASE),
            ).first
        ).to_be_visible(timeout=10000)
        expect(page_inspetor.locator("#mesa-widget-lista .anexo-mesa-link", has_text="retorno-mesa.png").first).to_be_visible(timeout=10000)
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_revisor_exibe_painel_operacional_da_mesa(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        texto_inicial = f"Pendencia operacional mesa {uuid.uuid4().hex[:8]}"
        envio_inspetor = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": texto_inicial},
        )
        assert envio_inspetor["status"] == 201

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        _abrir_laudo_no_revisor(page_revisor, laudo_id)
        _abrir_painel_decisao_mesa_no_revisor(page_revisor)

        painel_operacao = page_revisor.locator("#mesa-operacao-painel")
        expect(painel_operacao).to_be_visible(timeout=10000)
        expect(painel_operacao).to_contain_text(re.compile(r"opera[cç][aã]o da mesa", re.IGNORECASE))
        expect(painel_operacao).to_contain_text(re.compile(r"pend[êe]ncias abertas", re.IGNORECASE))
        expect(painel_operacao.locator(".mesa-operacao-tag")).to_contain_text(re.compile(r"canal em triagem", re.IGNORECASE))

        texto_resposta = f"Abrir pendencia via painel {uuid.uuid4().hex[:8]}"
        page_revisor.locator("#input-resposta").fill(texto_resposta)
        page_revisor.locator("#btn-enviar-msg").click()

        item_pendencia = painel_operacao.locator(".mesa-operacao-item.aberta", has_text=texto_resposta).first
        expect(item_pendencia).to_be_visible(timeout=10000)
        expect(painel_operacao.locator(".mesa-operacao-tag")).to_contain_text(re.compile(r"1 pend[êe]ncia aberta", re.IGNORECASE))
        expect(item_pendencia.locator('[data-mesa-action="alternar-pendencia"]')).to_contain_text(re.compile(r"marcar resolvida", re.IGNORECASE))

        item_pendencia.locator('[data-mesa-action="responder-item"]').click()
        expect(page_revisor.locator("#ref-ativa-resposta")).to_be_visible(timeout=10000)
        expect(page_revisor.locator("#ref-ativa-texto")).to_contain_text(re.compile(r"Abrir pendencia via painel", re.IGNORECASE))

        item_pendencia.locator('[data-mesa-action="alternar-pendencia"]').click()
        item_resolvido = painel_operacao.locator(".mesa-operacao-item.resolvida", has_text=texto_resposta).first
        expect(item_resolvido).to_be_visible(timeout=10000)
        expect(item_resolvido).to_contain_text(re.compile(r"resolvida por", re.IGNORECASE))
        expect(item_resolvido.locator('[data-mesa-action="alternar-pendencia"]')).to_contain_text(re.compile(r"reabrir", re.IGNORECASE))

        item_resolvido.locator('[data-mesa-action="alternar-pendencia"]').click()
        item_reaberto = painel_operacao.locator(".mesa-operacao-item.aberta", has_text=texto_resposta).first
        expect(item_reaberto).to_be_visible(timeout=10000)
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_revisor_mesa_ignora_respostas_atrasadas_ao_trocar_de_laudo(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_a_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        laudo_b_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        sufixo = uuid.uuid4().hex[:8]
        texto_a = f"Revisor corrida A {sufixo}"
        texto_b = f"Revisor corrida B {sufixo}"

        envio_a = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_a_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": texto_a},
        )
        envio_b = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_b_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": texto_b},
        )
        assert envio_a["status"] == 201
        assert envio_b["status"] == 201

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        _atrasar_requisicoes(
            page_revisor,
            padroes=[
                f"**/revisao/api/laudo/{laudo_a_id}/mensagens*",
                f"**/revisao/api/laudo/{laudo_a_id}/pacote*",
            ],
            atraso_ms=900,
        )

        item_a = page_revisor.locator(f'.js-item-laudo[data-id="{laudo_a_id}"]').first
        item_b = page_revisor.locator(f'.js-item-laudo[data-id="{laudo_b_id}"]').first
        expect(item_a).to_be_visible(timeout=10000)
        expect(item_b).to_be_visible(timeout=10000)

        item_a.click()
        page_revisor.wait_for_timeout(80)
        item_b.click()

        expect(page_revisor.locator("#view-timeline")).to_contain_text(texto_b, timeout=10000)
        page_revisor.wait_for_timeout(1200)
        expect(page_revisor.locator("#view-timeline")).not_to_contain_text(texto_a)
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_revisor_biblioteca_templates_abre_preview_e_escolhe_modelo(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="revisao",
        email=credenciais_seed["revisor"]["email"],
        senha=credenciais_seed["revisor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
    )

    for versao, titulo, texto in (
        (1, "Template E2E v1", "Ponto A validado pelo inspetor."),
        (2, "Template E2E v2", "Ponto B validado pela mesa."),
    ):
        resposta_criar = _api_fetch(
            page,
            path="/revisao/api/templates-laudo/editor",
            method="POST",
            json_body={
                "nome": titulo,
                "codigo_template": "e2e_diff_templates",
                "versao": versao,
                "origem_modo": "a4",
            },
        )
        assert resposta_criar["status"] == 201, resposta_criar
        template_id = int(resposta_criar["body"]["id"])

        resposta_salvar = _api_fetch(
            page,
            path=f"/revisao/api/templates-laudo/editor/{template_id}",
            method="PUT",
            json_body={
                "documento_editor_json": {
                    "version": 1,
                    "doc": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "heading",
                                "attrs": {"level": 1},
                                "content": [{"type": "text", "text": titulo}],
                            },
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": texto}],
                            },
                        ],
                    },
                }
            },
        )
        assert resposta_salvar["status"] == 200, resposta_salvar

    page.goto(f"{live_server_url}/revisao/templates-laudo", wait_until="domcontentloaded")

    grupo = page.locator('[data-codigo-template="e2e_diff_templates"]').first
    expect(grupo).to_be_visible(timeout=10000)
    expect(grupo.locator(".js-open-preview")).to_be_visible(timeout=10000)

    grupo.locator(".js-open-preview").click()

    expect(page.locator("#template-preview-modal")).to_be_visible(timeout=10000)
    expect(page.locator("#preview-modal-title")).to_contain_text("Template E2E v2", timeout=10000)
    expect(page.locator("#preview-modal-fields")).to_contain_text(re.compile(r"Cliente|Equipamento|Inspeção", re.IGNORECASE), timeout=10000)
    page.wait_for_function(
        """() => {
            const frame = document.getElementById("preview-modal-frame");
            return !!frame && /^blob:/.test(String(frame.getAttribute("src") || ""));
        }""",
        timeout=30000,
    )

    page.locator("#btn-choose-preview-template").click()

    expect(page.locator("#selected-template-banner")).to_be_visible(timeout=10000)
    expect(page.locator("#selected-template-name")).to_contain_text("Template E2E v2", timeout=10000)
    expect(grupo).to_contain_text(re.compile(r"escolhido", re.IGNORECASE), timeout=10000)


def test_e2e_revisor_biblioteca_templates_escolhe_modelo_no_card_e_limpa_banner(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="revisao",
        email=credenciais_seed["revisor"]["email"],
        senha=credenciais_seed["revisor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
    )

    for versao, titulo, texto, ativo in (
        (1, "Template Base Auto v1", "Versão ativa recomendada pela heurística.", True),
        (2, "Template Base Fixa v2", "Versão manual para a mesa documental.", False),
    ):
        resposta_criar = _api_fetch(
            page,
            path="/revisao/api/templates-laudo/editor",
            method="POST",
            json_body={
                "nome": titulo,
                "codigo_template": "e2e_base_recomendada",
                "versao": versao,
                "origem_modo": "a4",
                "ativo": ativo,
            },
        )
        assert resposta_criar["status"] == 201, resposta_criar
        template_id = int(resposta_criar["body"]["id"])

        resposta_salvar = _api_fetch(
            page,
            path=f"/revisao/api/templates-laudo/editor/{template_id}",
            method="PUT",
            json_body={
                "documento_editor_json": {
                    "version": 1,
                    "doc": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "heading",
                                "attrs": {"level": 1},
                                "content": [{"type": "text", "text": titulo}],
                            },
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": texto}],
                            },
                        ],
                    },
                }
            },
        )
        assert resposta_salvar["status"] == 200, resposta_salvar

    page.goto(f"{live_server_url}/revisao/templates-laudo", wait_until="domcontentloaded")

    grupo = page.locator('[data-codigo-template="e2e_base_recomendada"]').first
    expect(grupo).to_be_visible(timeout=10000)
    expect(grupo.locator(".template-featured-body .template-title")).to_contain_text("Template Base Auto v1", timeout=10000)
    expect(grupo.locator(".js-select-model")).to_be_visible(timeout=10000)

    grupo.locator(".js-select-model").click()

    expect(page.locator("#status-lista")).to_contain_text("Modelo escolhido para a próxima leitura da mesa.", timeout=10000)
    expect(page.locator("#selected-template-banner")).to_be_visible(timeout=10000)
    expect(page.locator("#selected-template-name")).to_contain_text("Template Base Auto v1", timeout=10000)

    page.locator("#btn-clear-selected-template").click()

    expect(page.locator("#status-lista")).to_contain_text("Escolha do modelo removida.", timeout=10000)
    expect(page.locator("#selected-template-banner")).to_be_hidden(timeout=10000)


def test_e2e_revisor_editor_word_workspace_inspector_preview_e_comparacao(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="revisao",
        email=credenciais_seed["revisor"]["email"],
        senha=credenciais_seed["revisor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
    )

    codigo = f"e2e_editor_workspace_{uuid.uuid4().hex[:8]}"
    ids_templates: list[int] = []
    for versao, titulo, texto in (
        (1, "Workspace Editor v1", "Base original aprovada pela mesa."),
        (2, "Workspace Editor v2", "Base comparada com alteração estrutural."),
    ):
        resposta_criar = _api_fetch(
            page,
            path="/revisao/api/templates-laudo/editor",
            method="POST",
            json_body={
                "nome": titulo,
                "codigo_template": codigo,
                "versao": versao,
                "origem_modo": "a4",
            },
        )
        assert resposta_criar["status"] == 201, resposta_criar
        template_id = int(resposta_criar["body"]["id"])
        ids_templates.append(template_id)

        resposta_salvar = _api_fetch(
            page,
            path=f"/revisao/api/templates-laudo/editor/{template_id}",
            method="PUT",
            json_body={
                "nome": titulo,
                "documento_editor_json": {
                    "version": 1,
                    "doc": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "heading",
                                "attrs": {"level": 1},
                                "content": [{"type": "text", "text": titulo}],
                            },
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": texto}],
                            },
                        ],
                    },
                },
                "estilo_json": {
                    "pagina": {"size": "A4", "orientation": "portrait", "margens_mm": {"top": 18, "right": 14, "bottom": 18, "left": 14}},
                    "cabecalho_texto": f"Tariel • {titulo}",
                    "rodape_texto": "Documento E2E",
                    "marca_dagua": {"texto": "E2E", "opacity": 0.08},
                },
            },
        )
        assert resposta_salvar["status"] == 200, resposta_salvar

    page.goto(
        f"{live_server_url}/revisao/templates-laudo/editor?template_id={ids_templates[0]}",
        wait_until="domcontentloaded",
    )

    expect(page.locator("#card-editor-word")).to_be_visible(timeout=10000)
    expect(page.locator(".word-left-rail")).to_be_visible(timeout=10000)
    expect(page.locator(".word-tab.active")).to_contain_text("Modelo", timeout=10000)
    expect(page.locator("#editor-word-surface .ProseMirror")).to_be_visible(timeout=30000)
    _assert_sem_overflow_horizontal(page)

    page.locator('.word-tab[data-tab="layout"]').click()
    expect(page.locator('#editor-header')).to_be_visible(timeout=10000)

    page.locator('.word-tab[data-tab="preview"]').click()
    expect(page.locator('#editor-preview-dados')).to_be_visible(timeout=10000)
    page.locator("#btn-editor-preview").click()
    expect(page.locator("#status-editor-word")).to_contain_text(re.compile(r"visualiza[cç][aã]o do documento atualizada", re.IGNORECASE), timeout=30000)
    page.wait_for_function(
        """() => {
            const frame = document.getElementById("frame-editor-preview");
            return !!frame && /^blob:/.test(String(frame.getAttribute("src") || ""));
        }""",
        timeout=30000,
    )

    page.locator('.word-tab[data-tab="comparar"]').click()
    page.locator("#editor-compare-template-select").select_option(str(ids_templates[1]))
    page.locator("#btn-editor-compare").click()

    expect(page.locator("#editor-compare-summary")).to_be_visible(timeout=30000)
    expect(page.locator("#status-editor-compare")).to_have_class(re.compile(r".*\bok\b.*"), timeout=30000)
    expect(page.locator("#status-editor-compare")).not_to_be_empty(timeout=30000)
    expect(page.locator("#editor-compare-blocks")).to_contain_text("Base comparada com alteração estrutural.", timeout=30000)


def test_e2e_revisor_exporta_pacote_tecnico_da_mesa(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context(accept_downloads=True)
    contexto_revisor = browser.new_context(accept_downloads=True)

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        texto_inicial = f"Pacote tecnico mesa {uuid.uuid4().hex[:8]}"
        envio_inspetor = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": texto_inicial},
        )
        assert envio_inspetor["status"] == 201

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )

        _abrir_laudo_no_revisor(page_revisor, laudo_id)

        expect(page_revisor.locator(".js-btn-pacote-resumo")).to_be_visible(timeout=10000)
        expect(page_revisor.locator(".js-btn-pacote-json")).to_be_visible(timeout=10000)
        expect(page_revisor.locator(".js-btn-pacote-pdf")).to_be_visible(timeout=10000)

        page_revisor.locator(".js-btn-pacote-resumo").click()
        expect(page_revisor.locator("#modal-pacote")).to_be_visible(timeout=10000)
        expect(page_revisor.locator("#modal-pacote-conteudo")).to_contain_text(re.compile(r"Mensagens|Pend[êe]ncias Abertas|Whispers Recentes", re.IGNORECASE))
        page_revisor.locator("#btn-fechar-pacote").click()
        expect(page_revisor.locator("#modal-pacote")).to_be_hidden(timeout=10000)

        with page_revisor.expect_download(timeout=10000) as download_info:
            page_revisor.locator(".js-btn-pacote-json").click()
        download = download_info.value
        assert re.match(r"pacote_mesa_.+\.json$", download.suggested_filename), download.suggested_filename

        caminho_download = download.path()
        assert caminho_download, "Playwright não disponibilizou o arquivo JSON baixado."
        with open(caminho_download, encoding="utf-8") as arquivo_json:
            pacote = json.load(arquivo_json)

        assert int(pacote["laudo_id"]) == laudo_id
        assert isinstance(pacote.get("resumo_mensagens"), dict)
        assert isinstance(pacote.get("pendencias_abertas"), list)
        assert isinstance(pacote.get("whispers_recentes"), list)
        assert int(pacote["resumo_mensagens"].get("total") or 0) >= 1

        resposta_pdf = page_revisor.request.fetch(
            urljoin(page_revisor.url, f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf"),
            method="GET",
        )
        assert resposta_pdf.status == 200
        assert "application/pdf" in resposta_pdf.headers.get("content-type", "").lower()
        assert resposta_pdf.body().startswith(b"%PDF")
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()


def test_e2e_revisor_reemite_oficialmente_quando_pdf_diverge(
    browser: Browser,
    live_server_url: str,
    live_server_database_url: str | None,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_inspetor = browser.new_context()
    contexto_revisor = browser.new_context()

    try:
        page_inspetor = contexto_inspetor.new_page()
        _fazer_login(
            page_inspetor,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        laudo_id = _iniciar_inspecao_via_api(page_inspetor, tipo_template="padrao")
        texto_mesa = f"Governança documental E2E {uuid.uuid4().hex[:8]}"
        envio_inspetor = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagem",
            method="POST",
            json_body={"texto": texto_mesa},
        )
        assert envio_inspetor["status"] == 201
        _seed_gate_qualidade_minimo_e2e(
            live_server_database_url,
            laudo_id=laudo_id,
        )
        finalizacao = _api_fetch(
            page_inspetor,
            path=f"/app/api/laudo/{laudo_id}/finalizar",
            method="POST",
        )
        assert finalizacao["status"] == 200, finalizacao
        assert isinstance(finalizacao["body"], dict)
        assert finalizacao["body"]["success"] is True
        assert finalizacao["body"]["review_mode_final"] == "mesa_required"
        _seed_report_pack_pronto_para_emissao_e2e(
            live_server_database_url,
            laudo_id=laudo_id,
        )

        page_revisor = contexto_revisor.new_page()
        _fazer_login(
            page_revisor,
            base_url=live_server_url,
            portal="revisao",
            email=credenciais_seed["revisor"]["email"],
            senha=credenciais_seed["revisor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/revisao/painel/?$",
        )
        csrf_revisor = _csrf_token_from_session_cookie(page_revisor)

        aprovacao = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/avaliar",
            method="POST",
            form_body={"acao": "aprovar", "motivo": ""},
            csrf_token_override=csrf_revisor,
        )
        assert aprovacao["status"] == 200, aprovacao
        assert isinstance(aprovacao["body"], dict)
        assert str(aprovacao["body"]["status_revisao"]).strip().lower() == "aprovado"

        signatario = _seed_signatario_governado_e2e(
            live_server_database_url,
            laudo_id=laudo_id,
        )
        laudo_seed = _consultar_laudo_seed(live_server_database_url, laudo_id)
        pdf_v1 = _gerar_pdf_real_via_api(
            page_inspetor,
            laudo_id=laudo_id,
            tipo_template=str(laudo_seed["tipo_template"]),
            diagnostico="Documento emitido oficial E2E v1",
        )
        _seed_pdf_emitido_versionado_e2e(
            live_server_database_url,
            laudo_id=laudo_id,
            version_label="v0001",
            pdf_bytes=pdf_v1,
        )

        emissao_inicial_resposta = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
            method="POST",
            json_body={"signatory_id": signatario["id"]},
            csrf_token_override=csrf_revisor,
        )
        assert emissao_inicial_resposta["status"] == 200, emissao_inicial_resposta

        pacote_inicial = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/pacote",
            method="GET",
        )
        assert pacote_inicial["status"] == 200, pacote_inicial
        emissao_inicial = pacote_inicial["body"]["emissao_oficial"]
        issue_inicial = emissao_inicial["current_issue"]
        issue_inicial_id = int(issue_inicial["id"])
        issue_inicial_numero = str(issue_inicial["issue_number"])
        assert emissao_inicial["reissue_recommended"] is False
        assert issue_inicial["primary_pdf_diverged"] is False
        assert issue_inicial["primary_pdf_storage_version"] == "v0001"

        verificacao_inicial = _api_fetch(
            page_revisor,
            path=f"/app/public/laudo/verificar/{laudo_seed['codigo_hash']}?format=json",
            method="GET",
        )
        assert verificacao_inicial["status"] == 200, verificacao_inicial
        assert verificacao_inicial["body"]["official_issue_number"] == issue_inicial_numero
        assert verificacao_inicial["body"]["official_issue_primary_pdf_diverged"] is False

        pdf_v2 = _gerar_pdf_real_via_api(
            page_inspetor,
            laudo_id=laudo_id,
            tipo_template=str(laudo_seed["tipo_template"]),
            diagnostico="Documento emitido oficial E2E v2 com divergencia",
        )
        _seed_pdf_emitido_versionado_e2e(
            live_server_database_url,
            laudo_id=laudo_id,
            version_label="v0002",
            pdf_bytes=pdf_v2,
        )

        pacote_divergente = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/pacote",
            method="GET",
        )
        assert pacote_divergente["status"] == 200, pacote_divergente
        emissao_divergente = pacote_divergente["body"]["emissao_oficial"]
        assert emissao_divergente["reissue_recommended"] is True
        assert emissao_divergente["current_issue"]["issue_number"] == issue_inicial_numero
        assert emissao_divergente["current_issue"]["primary_pdf_diverged"] is True
        assert emissao_divergente["current_issue"]["current_primary_pdf_storage_version"] == "v0002"

        reemissao_resposta = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
            method="POST",
            json_body={
                "signatory_id": signatario["id"],
                "expected_current_issue_id": issue_inicial_id,
                "expected_current_issue_number": issue_inicial_numero,
            },
            csrf_token_override=csrf_revisor,
        )
        assert reemissao_resposta["status"] == 200, reemissao_resposta
        assert isinstance(reemissao_resposta["body"], dict)
        assert reemissao_resposta["body"]["reissued"] is True
        assert reemissao_resposta["body"]["superseded_issue_number"] == issue_inicial_numero

        pacote_alinhado = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/pacote",
            method="GET",
        )
        assert pacote_alinhado["status"] == 200, pacote_alinhado
        emissao_alinhada = pacote_alinhado["body"]["emissao_oficial"]
        issue_alinhada = emissao_alinhada["current_issue"]
        issue_alinhada_numero = str(issue_alinhada["issue_number"])
        assert emissao_alinhada["reissue_recommended"] is False
        assert issue_alinhada_numero != issue_inicial_numero
        assert issue_alinhada["reissue_of_issue_number"] == issue_inicial_numero
        assert "primary_pdf_diverged" in list(issue_alinhada["reissue_reason_codes"] or [])
        assert issue_alinhada["reissue_reason_summary"] == "Reemissão motivada por divergência do PDF principal."
        assert issue_alinhada["primary_pdf_diverged"] is False
        assert issue_alinhada["primary_pdf_storage_version"] == "v0002"

        conflito_reissue = _api_fetch(
            page_revisor,
            path=f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
            method="POST",
            json_body={
                "signatory_id": signatario["id"],
                "expected_current_issue_id": issue_inicial_id,
                "expected_current_issue_number": issue_inicial_numero,
            },
            csrf_token_override=csrf_revisor,
        )
        assert conflito_reissue["status"] == 409, conflito_reissue
        assert isinstance(conflito_reissue["body"], dict)
        assert "emissão oficial" in str(conflito_reissue["body"]["detail"]).lower()

        verificacao_alinhada = _api_fetch(
            page_revisor,
            path=f"/app/public/laudo/verificar/{laudo_seed['codigo_hash']}?format=json",
            method="GET",
        )
        assert verificacao_alinhada["status"] == 200, verificacao_alinhada
        payload_verificacao = verificacao_alinhada["body"]
        assert payload_verificacao["official_issue_number"] == issue_alinhada_numero
        assert payload_verificacao["official_issue_primary_pdf_diverged"] is False
        assert payload_verificacao["official_issue_current_pdf_storage_version"] == "v0002"
        assert payload_verificacao["official_issue_reissue_of_issue_number"] == issue_inicial_numero
        assert payload_verificacao["official_issue_reissue_reason_summary"] == "Reemissão motivada por divergência do PDF principal."

        page_revisor.goto(
            f"{live_server_url}/app/public/laudo/verificar/{laudo_seed['codigo_hash']}",
            wait_until="domcontentloaded",
        )
        expect(page_revisor.locator("body")).to_contain_text(issue_alinhada_numero, timeout=10000)
        expect(page_revisor.locator("body")).to_contain_text(issue_inicial_numero, timeout=10000)
        expect(page_revisor.locator("body")).to_contain_text("Linhagem da emissão", timeout=10000)
        expect(page_revisor.locator("body")).to_contain_text(
            "Reemissão motivada por divergência do PDF principal.",
            timeout=10000,
        )
    finally:
        contexto_inspetor.close()
        contexto_revisor.close()
