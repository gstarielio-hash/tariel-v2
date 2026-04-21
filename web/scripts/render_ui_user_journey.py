from __future__ import annotations

import argparse
import base64
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    expect,
    sync_playwright,
)

from app.domains.admin.mfa import current_totp


PNG_1X1_TRANSPARENTE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0X8AAAAASUVORK5CYII="
)
DEFAULT_BASE_URL = "https://tariel-web-free.onrender.com"
DEFAULT_RENDER_CACHE = Path.home() / ".cache" / "tariel_render_free_deploy.json"
DEFAULT_ARTIFACT_ROOT = (
    Path("/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado")
    / "artifacts"
    / "render_ui_user_journey"
)


@dataclass
class StepRecord:
    name: str
    status: str
    details: str
    screenshot: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsoleRecord:
    page: str
    level: str
    text: str


@dataclass
class RunReport:
    base_url: str
    run_id: str
    run_error: str | None = None
    company: dict[str, Any] = field(default_factory=dict)
    users: dict[str, Any] = field(default_factory=dict)
    steps: list[StepRecord] = field(default_factory=list)
    ok_items: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    false_positive_items: list[str] = field(default_factory=list)
    visual_notes: list[str] = field(default_factory=list)
    console_issues: list[ConsoleRecord] = field(default_factory=list)
    page_errors: list[ConsoleRecord] = field(default_factory=list)
    generated_files: list[str] = field(default_factory=list)


class JourneyRunner:
    def __init__(
        self,
        *,
        base_url: str,
        artifact_root: Path,
        render_cache_path: Path,
        headless: bool = True,
        slow_mo_ms: int = 140,
        pause_scale: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.run_id = time.strftime("%Y%m%d_%H%M%S")
        self.artifact_dir = artifact_root / self.run_id
        self.screenshots_dir = self.artifact_dir / "screenshots"
        self.downloads_dir = self.artifact_dir / "downloads"
        self.report = RunReport(base_url=self.base_url, run_id=self.run_id)
        self.render_cache_path = render_cache_path
        self._admin_totp_secret: str | None = None
        self.headless = bool(headless)
        self.slow_mo_ms = max(int(slow_mo_ms), 0)
        self.pause_scale = max(float(pause_scale), 0.1)

        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        self._evidence_png = self.artifact_dir / "campo_evidencia.png"
        self._review_png = self.artifact_dir / "mesa_retorno.png"
        self._write_binary_file(self._evidence_png, base64.b64decode(PNG_1X1_TRANSPARENTE_B64))
        self._write_binary_file(self._review_png, base64.b64decode(PNG_1X1_TRANSPARENTE_B64))

    @staticmethod
    def _write_binary_file(path: Path, payload: bytes) -> None:
        path.write_bytes(payload)

    def log(self, message: str) -> None:
        print(f"[journey] {message}", flush=True)

    def add_step(
        self,
        name: str,
        status: str,
        details: str,
        *,
        screenshot: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.report.steps.append(
            StepRecord(
                name=name,
                status=status,
                details=details,
                screenshot=screenshot,
                extra=extra or {},
            )
        )
        self.log(f"{status.upper()}: {name} :: {details}")

    def add_ok(self, text: str) -> None:
        if text not in self.report.ok_items:
            self.report.ok_items.append(text)

    def add_missing(self, text: str) -> None:
        if text not in self.report.missing_items:
            self.report.missing_items.append(text)

    def add_false_positive(self, text: str) -> None:
        if text not in self.report.false_positive_items:
            self.report.false_positive_items.append(text)

    def add_visual_note(self, text: str) -> None:
        if text not in self.report.visual_notes:
            self.report.visual_notes.append(text)

    def mask_email(self, email: str) -> str:
        if "@" not in email:
            return email
        prefix, domain = email.split("@", 1)
        if len(prefix) <= 2:
            return f"{prefix[0]}***@{domain}"
        return f"{prefix[:2]}***@{domain}"

    def screenshot(self, page: Page, name: str, *, full_page: bool = True) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name.strip()) or "shot"
        filename = f"{safe_name}.png"
        path = self.screenshots_dir / filename
        page.screenshot(path=str(path), full_page=full_page)
        rel = str(path.relative_to(self.artifact_dir))
        self.report.generated_files.append(rel)
        return rel

    def write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.report.generated_files.append(str(path.relative_to(self.artifact_dir)))

    def write_markdown(self, path: Path, body: str) -> None:
        path.write_text(body, encoding="utf-8")
        self.report.generated_files.append(str(path.relative_to(self.artifact_dir)))

    def wire_page(self, page: Page, name: str) -> None:
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(90000)

        def _on_console(msg: Any) -> None:
            if msg.type not in {"warning", "error"}:
                return
            self.report.console_issues.append(
                ConsoleRecord(page=name, level=msg.type, text=msg.text)
            )

        def _on_page_error(err: Exception) -> None:
            self.report.page_errors.append(
                ConsoleRecord(page=name, level="pageerror", text=str(err))
            )

        page.on("console", _on_console)
        page.on("pageerror", _on_page_error)

    def human_pause(self, page: Page, ms: int = 350) -> None:
        page.wait_for_timeout(int(max(ms, 0) * self.pause_scale))

    def human_scroll(self, page: Page) -> None:
        page.mouse.wheel(0, 700)
        self.human_pause(page, 250)
        page.mouse.wheel(0, -500)
        self.human_pause(page, 250)

    def collect_visual_metrics(self, page: Page, label: str) -> None:
        metrics = page.evaluate(
            """() => {
                const innerWidth = window.innerWidth;
                const scrollWidth = document.documentElement.scrollWidth;
                const xBefore = window.scrollX;
                window.scrollTo({ left: 99999, top: window.scrollY, behavior: "instant" });
                const xAfter = window.scrollX;
                window.scrollTo({ left: xBefore, top: window.scrollY, behavior: "instant" });
                const offenders = Array.from(document.querySelectorAll("body *"))
                    .map((el) => {
                        const style = window.getComputedStyle(el);
                        if (style.display === "none" || style.visibility === "hidden") return null;
                        const rect = el.getBoundingClientRect();
                        if (rect.width <= 0 || rect.height <= 0) return null;
                        if (rect.right <= innerWidth + 2) return null;
                        return {
                            tag: el.tagName.toLowerCase(),
                            id: el.id || "",
                            right: Math.round(rect.right),
                            width: Math.round(rect.width),
                        };
                    })
                    .filter(Boolean)
                    .slice(0, 6);
                return {
                    innerWidth,
                    scrollWidth,
                    xAfter,
                    offenders,
                };
            }"""
        )
        ok = int(metrics["xAfter"]) <= 2 or int(metrics["scrollWidth"]) <= int(metrics["innerWidth"]) + 2
        if ok and not metrics["offenders"]:
            self.add_visual_note(f"{label}: sem overflow horizontal relevante.")
            return
        self.add_missing(f"{label}: overflow horizontal ou elemento excedendo viewport: {metrics}")

    @staticmethod
    def _extract_admin_totp_secret(page: Page) -> str:
        html = page.content()
        match_uri = re.search(r"secret=([A-Z2-7]+)", html)
        if match_uri:
            return match_uri.group(1)

        match_code = re.search(r"Segredo TOTP:\s*<code>([A-Z2-7 ]+)</code>", html)
        if match_code:
            return re.sub(r"\s+", "", match_code.group(1))

        text = page.locator("body").inner_text()
        match_text = re.search(r"Segredo TOTP:\s*([A-Z2-7 ]+)", text)
        if match_text:
            return re.sub(r"\s+", "", match_text.group(1))

        raise RuntimeError("Nao foi possivel extrair o segredo TOTP do admin.")

    def _recover_admin_totp_secret_from_pending_session(self, page: Page) -> str:
        response = page.request.fetch(
            f"{self.base_url}/admin/mfa/setup",
            method="POST",
            form={"codigo": "", "csrf_token": ""},
        )
        html = response.text()
        match_uri = re.search(r"secret=([A-Z2-7]+)", html)
        if match_uri:
            self.add_missing(
                "Sessao pendente de MFA do admin expôs o segredo TOTP ao aceitar POST invalido em /admin/mfa/setup."
            )
            return match_uri.group(1)

        match_code = re.search(r"Segredo TOTP:\s*<code>([A-Z2-7 ]+)</code>", html)
        if match_code:
            self.add_missing(
                "Sessao pendente de MFA do admin expôs o segredo TOTP ao aceitar POST invalido em /admin/mfa/setup."
            )
            return re.sub(r"\s+", "", match_code.group(1))

        raise RuntimeError("Nao foi possivel recuperar o segredo TOTP do admin na sessao pendente.")

    def _complete_admin_mfa(self, page: Page) -> None:
        if re.search(r"/admin/mfa/setup/?$", page.url):
            self._admin_totp_secret = self._extract_admin_totp_secret(page)
            page.locator('input[name="codigo"]').fill(current_totp(self._admin_totp_secret))
            self.human_pause(page, 250)
            page.locator('button[type="submit"]').click()
            return

        if re.search(r"/admin/mfa/challenge/?$", page.url):
            if not self._admin_totp_secret:
                self._admin_totp_secret = self._recover_admin_totp_secret_from_pending_session(page)
            page.locator('input[name="codigo"]').fill(current_totp(self._admin_totp_secret))
            self.human_pause(page, 250)
            page.locator('button[type="submit"]').click()

    def login_admin(self, page: Page, *, email: str, password: str) -> None:
        self.log("login admin")
        page.goto(f"{self.base_url}/admin/login", wait_until="domcontentloaded")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="senha"]').fill(password)
        self.human_pause(page, 300)
        page.locator('button[type="submit"]').click()

        if re.search(r"/admin/mfa/(setup|challenge)/?$", page.url):
            self._complete_admin_mfa(page)

        expect(page).to_have_url(
            re.compile(
                rf"{re.escape(self.base_url)}/admin/(painel|dashboard|clientes|novo-cliente|auditoria|configuracoes).*"
            )
        )

    def login_first_access(
        self,
        page: Page,
        *,
        portal: str,
        email: str,
        temp_password: str,
        new_password: str,
        success_regex: str,
    ) -> None:
        page.goto(f"{self.base_url}/{portal}/login", wait_until="domcontentloaded")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="senha"]').fill(temp_password)
        self.human_pause(page, 250)
        page.locator('button[type="submit"]').first.click()
        expect(page).to_have_url(re.compile(rf"{re.escape(self.base_url)}/{portal}/trocar-senha/?$"))

        page.locator('input[name="senha_atual"]').fill(temp_password)
        page.locator('input[name="nova_senha"]').fill(new_password)
        page.locator('input[name="confirmar_senha"]').fill(new_password)
        self.human_pause(page, 250)
        page.locator('button[type="submit"]').first.click()
        expect(page).to_have_url(re.compile(success_regex))
        if portal == "app":
            self.wait_for_inspector_runtime(page)

    def login_standard(
        self,
        page: Page,
        *,
        portal: str,
        email: str,
        password: str,
        success_regex: str,
    ) -> None:
        page.goto(f"{self.base_url}/{portal}/login", wait_until="domcontentloaded")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="senha"]').fill(password)
        self.human_pause(page, 250)
        page.locator('button[type="submit"]').first.click()
        expect(page).to_have_url(re.compile(success_regex))
        if portal == "app":
            self.wait_for_inspector_runtime(page)

    def wait_for_inspector_runtime(self, page: Page) -> None:
        page.wait_for_function(
            """() => Boolean(
                document.getElementById("painel-chat") &&
                window.TarielInspetorRuntime &&
                typeof window.TarielInspetorRuntime.actions?.abrirModalNovaInspecao === "function"
            )""",
            timeout=30000,
        )

    @staticmethod
    def extract_flash_temp_password(body_text: str) -> str:
        match = re.search(
            r"Senha tempor[áa]ria para .*?:\s*(.+?)\.\s*Compartilhe",
            body_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            raise RuntimeError("Nao foi possivel extrair senha temporaria da tela.")
        return match.group(1).strip()

    @staticmethod
    def extract_initial_access_temp_password(page: Page) -> str | None:
        campo_senha = page.locator('input[id^="credencial-senha-"]').first
        if campo_senha.count() == 0:
            return None
        try:
            valor = campo_senha.input_value()
        except Exception:
            valor = campo_senha.get_attribute("value")
        senha = str(valor or "").strip()
        return senha or None

    @staticmethod
    def extract_feedback_temp_password(feedback_text: str) -> str:
        match = re.search(
            r"Senha tempor[áa]ria:\s*(.+)$",
            feedback_text.strip(),
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            raise RuntimeError(f"Senha temporaria nao encontrada no feedback: {feedback_text!r}")
        return match.group(1).strip()

    def _obter_csrf_token(self, page: Page) -> str:
        csrf_meta = page.locator('meta[name="csrf-token"]').first
        if csrf_meta.count():
            valor = csrf_meta.get_attribute("content")
            if valor:
                return str(valor).strip()

        token_input = page.locator('input[name="csrf_token"]').first
        if token_input.count():
            try:
                valor = token_input.input_value()
            except Exception:
                valor = token_input.get_attribute("value")
            if valor:
                return str(valor).strip()

        return ""

    def _api_fetch_json(
        self,
        page: Page,
        *,
        path: str,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        csrf_token = self._obter_csrf_token(page)
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

        resposta = page.request.fetch(f"{self.base_url}{path}", **kwargs)
        bruto = resposta.text()
        try:
            corpo = resposta.json()
        except Exception:
            corpo = None

        return {
            "status": resposta.status,
            "ok": resposta.ok,
            "url": resposta.url,
            "body": corpo,
            "raw": bruto,
        }

    def wait_feedback(
        self,
        page: Page,
        pattern: str | re.Pattern[str],
        *,
        timeout: int = 20000,
        previous_text: str | None = None,
    ) -> str:
        feedback = page.locator("#feedback")
        if isinstance(pattern, str):
            regex = re.compile(re.escape(pattern), re.IGNORECASE)
        else:
            regex = pattern
        deadline = time.time() + (timeout / 1000.0)
        texto_anterior = str(previous_text or "").strip()
        ultimo_texto = ""
        ultimo_visible = ""
        while time.time() < deadline:
            try:
                ultimo_texto = feedback.inner_text().strip()
            except Exception:
                ultimo_texto = ""
            try:
                ultimo_visible = str(feedback.get_attribute("data-visible") or "").strip().lower()
            except Exception:
                ultimo_visible = ""

            texto_mudou = bool(ultimo_texto) and ultimo_texto != texto_anterior
            if regex.search(ultimo_texto) and (texto_mudou or ultimo_visible == "true"):
                return ultimo_texto
            page.wait_for_timeout(250)
        raise RuntimeError(
            f"Feedback nao correspondeu ao padrao esperado: {regex.pattern} | visible={ultimo_visible or 'false'} | texto={ultimo_texto!r}"
        )

    def _wait_for_user_row_visible(self, page: Page, *, email: str, timeout: int = 20000) -> Any:
        row = self.user_row(page, email)
        expect(row).to_be_visible(timeout=timeout)
        return row

    def _extract_user_id_from_row(self, row: Any) -> int | None:
        if row.count() == 0:
            return None
        valor = row.get_attribute("data-user-row")
        try:
            user_id = int(valor or 0)
        except Exception:
            return None
        return user_id if user_id > 0 else None

    def _reset_client_user_password_via_api(self, page: Page, *, user_id: int) -> str:
        resposta = self._api_fetch_json(
            page,
            path=f"/cliente/api/usuarios/{int(user_id)}/resetar-senha",
            method="POST",
        )
        if int(resposta["status"]) != 200 or not isinstance(resposta.get("body"), dict):
            raise RuntimeError(
                f"Falha ao resetar senha do usuario {user_id} via API: status={resposta['status']} body={resposta.get('raw')!r}"
            )
        senha = str(resposta["body"].get("senha_temporaria") or "").strip()
        if not senha:
            raise RuntimeError(f"Resposta de reset sem senha temporaria para usuario {user_id}.")
        return senha

    def _create_client_user_via_api(
        self,
        page: Page,
        *,
        role: str,
        name: str,
        email: str,
        phone: str = "",
        crea: str = "",
    ) -> dict[str, Any]:
        resposta = self._api_fetch_json(
            page,
            path="/cliente/api/usuarios",
            method="POST",
            json_body={
                "nome": name,
                "email": email,
                "nivel_acesso": role,
                "telefone": phone,
                "crea": crea,
                "allowed_portals": [role],
            },
        )
        if int(resposta["status"]) not in {200, 201} or not isinstance(resposta.get("body"), dict):
            raise RuntimeError(
                f"Falha ao criar usuario {email} via API autenticada: status={resposta['status']} body={resposta.get('raw')!r}"
            )
        corpo = dict(resposta["body"])
        usuario_payload = dict(corpo.get("usuario") or {}) if isinstance(corpo.get("usuario"), dict) else {}
        try:
            user_id = int(usuario_payload.get("id") or 0) or None
        except (TypeError, ValueError):
            user_id = None
        senha = str(corpo.get("senha_temporaria") or "").strip()
        if not senha:
            raise RuntimeError(f"Resposta de criacao sem senha temporaria para {email}.")
        return {
            "user_id": user_id,
            "temp_password": senha,
            "detail": str(corpo.get("detail") or "").strip(),
        }

    def _reload_client_team_and_wait_for_user_row(
        self,
        page: Page,
        *,
        email: str,
        timeout: int = 20000,
    ) -> Any:
        page.goto(f"{self.base_url}/cliente/equipe", wait_until="domcontentloaded")
        self.open_client_team(page)
        row = self.user_row(page, email)
        expect(row).to_be_visible(timeout=timeout)
        return row

    def create_company_via_admin(self, page: Page, *, company_name: str, cnpj: str, email: str) -> tuple[int, str]:
        page.goto(f"{self.base_url}/admin/novo-cliente", wait_until="domcontentloaded")
        expect(page.locator('input[name="nome"]')).to_be_visible()
        self.human_scroll(page)
        page.locator('input[name="nome"]').fill(company_name)
        page.locator('input[name="cnpj"]').fill(cnpj)
        page.locator('select[name="plano"]').select_option("Intermediario")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="segmento"]').fill("Industrial")
        page.locator('input[name="cidade_estado"]').fill("Sao Paulo/SP")
        page.locator('input[name="nome_responsavel"]').fill("Responsavel UI")
        page.locator('textarea[name="observacoes"]').fill("Tenant criado por auditoria UI real no Render.")
        shot_before = self.screenshot(page, "admin_novo_cliente_preenchido")
        self.add_step("admin_form_novo_cliente", "ok", "Formulario de novo cliente preenchido.", screenshot=shot_before)
        self.human_pause(page, 300)
        page.get_by_role("button", name="Criar empresa").click()
        expect(page).to_have_url(
            re.compile(
                rf"{re.escape(self.base_url)}/admin/clientes/\d+(?:/acesso-inicial)?/?(?:\?.*)?$"
            )
        )
        company_id = int(re.search(r"/admin/clientes/(\d+)", page.url).group(1))
        temp_password = (
            self.extract_initial_access_temp_password(page)
            or self.extract_flash_temp_password(page.locator("body").inner_text())
        )
        shot_after = self.screenshot(page, "admin_cliente_pos_criacao")
        self.add_step(
            "admin_create_company",
            "ok",
            f"Empresa criada no admin com id {company_id}.",
            screenshot=shot_after,
            extra={"company_id": company_id},
        )
        self.collect_visual_metrics(page, "admin/cliente_detalhe")
        return company_id, temp_password

    def wait_for_client_portal_ready(self, page: Page, *, timeout: int = 30000) -> None:
        deadline = time.time() + (timeout / 1000.0)
        last_status = ""
        while time.time() < deadline:
            try:
                payload = page.evaluate(
                    """() => ({
                        bootStatus: String(window.__TARIEL_CLIENTE_PORTAL_WIRED__?.status || "").trim(),
                        hasTabAdmin: Boolean(document.getElementById("tab-admin")),
                    })"""
                )
            except Exception:
                payload = {}
            last_status = str(payload.get("bootStatus") or "").strip()
            if last_status == "ready" and bool(payload.get("hasTabAdmin")):
                self.human_pause(page, 250)
                return
            page.wait_for_timeout(250)
        raise RuntimeError(
            f"Portal cliente nao estabilizou o boot a tempo. status_final={last_status or 'indisponivel'}"
        )

    def open_client_team(self, page: Page) -> None:
        page.goto(f"{self.base_url}/cliente/equipe", wait_until="domcontentloaded")
        self.wait_for_client_portal_ready(page)
        expect(page.locator("#tab-admin")).to_be_visible()
        if page.locator("#admin-section-tab-team").count() and page.locator("#admin-section-tab-team").is_visible():
            page.locator("#admin-section-tab-team").click()
        expect(page.locator("#admin-team")).to_be_visible(timeout=20000)
        self.human_scroll(page)

    def create_client_user(
        self,
        page: Page,
        *,
        role: str,
        name: str,
        email: str,
        phone: str = "",
        crea: str = "",
    ) -> str:
        self.open_client_team(page)
        page.locator("#usuario-nome").fill(name)
        page.locator("#usuario-email").fill(email)
        page.locator("#usuario-papel").select_option(role)
        page.locator("#usuario-telefone").fill(phone)
        page.locator("#usuario-crea").fill(crea)
        feedback_antes = page.locator("#feedback").inner_text().strip() if page.locator("#feedback").count() else ""
        botao_criar = page.locator("#btn-usuario-criar")
        if botao_criar.count() and botao_criar.is_disabled():
            nota = page.locator("#usuario-capacidade-nota").inner_text().strip() if page.locator("#usuario-capacidade-nota").count() else ""
            raise RuntimeError(f"Botao de criar usuario indisponivel: {nota or 'sem detalhe adicional'}")
        self.human_pause(page, 250)
        api_temp_password = ""
        api_user_id: int | None = None
        api_success = False
        api_detail = ""
        try:
            with page.expect_response(
                lambda response: (
                    response.request.method.upper() == "POST"
                    and response.url == f"{self.base_url}/cliente/api/usuarios"
                ),
                timeout=15000,
            ) as response_info:
                botao_criar.click()
            create_response = response_info.value
            response_raw = create_response.text()
            response_body = create_response.json() if response_raw else {}
            if int(create_response.status) >= 400:
                detalhe = (
                    str(response_body.get("detail") or "").strip()
                    if isinstance(response_body, dict)
                    else ""
                )
                raise RuntimeError(
                    f"Criacao de usuario respondeu {create_response.status}: {detalhe or response_raw[:400]}"
                )
            if isinstance(response_body, dict):
                api_success = bool(response_body.get("success"))
                api_temp_password = str(response_body.get("senha_temporaria") or "").strip()
                usuario_payload = (
                    dict(response_body.get("usuario") or {})
                    if isinstance(response_body.get("usuario"), dict)
                    else {}
                )
                try:
                    api_user_id = int(usuario_payload.get("id") or 0) or None
                except (TypeError, ValueError):
                    api_user_id = None
                api_detail = (
                    str(response_body.get("detail") or "").strip()
                    or str(usuario_payload.get("email") or "").strip()
                )
        except PlaywrightTimeoutError:
            api_success = False

        row = self.user_row(page, email)
        feedback_regex = re.compile(r"Senha tempor", re.IGNORECASE)

        try:
            feedback_text = self.wait_feedback(
                page,
                feedback_regex,
                previous_text=feedback_antes,
                timeout=12000,
            )
            temp_password = self.extract_feedback_temp_password(feedback_text)
            self._wait_for_user_row_visible(page, email=email, timeout=20000)
            try:
                self._reload_client_team_and_wait_for_user_row(page, email=email, timeout=20000)
            except Exception:
                pass
            return temp_password
        except Exception:
            if not api_success:
                try:
                    fallback = self._create_client_user_via_api(
                        page,
                        role=role,
                        name=name,
                        email=email,
                        phone=phone,
                        crea=crea,
                    )
                except Exception:
                    fallback = None
                if fallback:
                    api_success = True
                    api_user_id = fallback.get("user_id")
                    api_temp_password = str(fallback.get("temp_password") or "").strip()
                    api_detail = str(fallback.get("detail") or "").strip()
                    self.add_false_positive(
                        "Formulario de criacao do portal cliente nao acionou "
                        f"submit estavel para {email}; o roteiro usou a API "
                        "autenticada para continuar a validacao hospedada."
                    )

            if api_success:
                try:
                    self._reload_client_team_and_wait_for_user_row(page, email=email, timeout=20000)
                except Exception:
                    pass
                else:
                    if api_temp_password:
                        self.add_false_positive(
                            f"Cadastro de {email} concluiu no backend do "
                            "portal cliente, mas a UI precisou de recarga "
                            "completa para refletir a equipe atualizada."
                        )
                        return api_temp_password

            try:
                row = self._wait_for_user_row_visible(page, email=email, timeout=20000)
            except Exception:
                if api_success and api_user_id:
                    temp_password = api_temp_password or self._reset_client_user_password_via_api(
                        page,
                        user_id=api_user_id,
                    )
                    self.add_false_positive(
                        f"Cadastro de {email} concluiu no backend "
                        f"({api_detail or 'sem detalhe adicional'}), mas a "
                        "tabela da equipe nao refletiu o novo usuario de "
                        "forma estavel."
                    )
                    return temp_password
                raise

            user_id = self._extract_user_id_from_row(row) or api_user_id
            if not user_id:
                raise
            temp_password = api_temp_password or self._reset_client_user_password_via_api(page, user_id=user_id)
            try:
                self._reload_client_team_and_wait_for_user_row(page, email=email, timeout=20000)
            except Exception:
                pass
            self.add_false_positive(
                f"Cadastro de {email} apareceu na equipe sem feedback visual estável de senha temporária; o roteiro recuperou a senha por backend autenticado."
            )
            return temp_password

    def user_row(self, page: Page, email: str) -> Any:
        return page.locator("#lista-usuarios tr", has_text=email).first

    def edit_client_user(self, page: Page, *, email: str, phone: str = "", crea: str = "") -> None:
        row = self.user_row(page, email)
        expect(row).to_be_visible(timeout=20000)
        row.locator("summary.user-editor-toggle").click()
        if phone:
            row.locator('[data-field="telefone"]').fill(phone)
        if crea and row.locator('[data-field="crea"]').count():
            row.locator('[data-field="crea"]').fill(crea)
        feedback_antes = page.locator("#feedback").inner_text().strip() if page.locator("#feedback").count() else ""
        self.human_pause(page, 250)
        row.locator('button[data-act="save-user"]').click()
        self.wait_feedback(
            page,
            re.compile(r"Cadastro do usuario atualizado", re.IGNORECASE),
            previous_text=feedback_antes,
        )

    def toggle_client_user(self, page: Page, *, email: str, expected_button_text: str) -> None:
        row = self.user_row(page, email)
        expect(row).to_be_visible(timeout=20000)
        feedback_antes = page.locator("#feedback").inner_text().strip() if page.locator("#feedback").count() else ""
        row.locator('button[data-act="toggle-user"]').click()
        self.wait_feedback(
            page,
            re.compile(r"Status do usuario atualizado", re.IGNORECASE),
            previous_text=feedback_antes,
        )
        expect(self.user_row(page, email).locator('button[data-act="toggle-user"]')).to_contain_text(expected_button_text)

    def reset_client_user_password(self, page: Page, *, email: str) -> str:
        row = self.user_row(page, email)
        expect(row).to_be_visible(timeout=20000)
        feedback_antes = page.locator("#feedback").inner_text().strip() if page.locator("#feedback").count() else ""
        row.locator('button[data-act="reset-user"]').click()
        try:
            feedback_text = self.wait_feedback(
                page,
                re.compile(r"Senha tempor", re.IGNORECASE),
                previous_text=feedback_antes,
                timeout=12000,
            )
            return self.extract_feedback_temp_password(feedback_text)
        except Exception:
            user_id = self._extract_user_id_from_row(row)
            if not user_id:
                raise
            self.add_false_positive(
                f"Reset de senha de {email} concluiu sem feedback visual estável; o roteiro recuperou a senha por API autenticada."
            )
            return self._reset_client_user_password_via_api(page, user_id=user_id)

    def ensure_client_user_temp_password_via_api(self, page: Page, *, email: str) -> str:
        self.open_client_team(page)
        row = self.user_row(page, email)
        expect(row).to_be_visible(timeout=20000)
        user_id = self._extract_user_id_from_row(row)
        if not user_id:
            raise RuntimeError(f"Nao foi possivel localizar o id do usuario {email} para reset autenticado.")
        return self._reset_client_user_password_via_api(page, user_id=user_id)

    def delete_client_user(self, page: Page, *, email: str) -> None:
        row = self.user_row(page, email)
        expect(row).to_be_visible(timeout=20000)
        feedback_antes = page.locator("#feedback").inner_text().strip() if page.locator("#feedback").count() else ""
        page.once("dialog", lambda dialog: dialog.accept())
        row.locator('button[data-act="delete-user"]').click()
        self.wait_feedback(
            page,
            re.compile(r"Cadastro operacional excluido", re.IGNORECASE),
            previous_text=feedback_antes,
        )
        expect(self.user_row(page, email)).to_have_count(0, timeout=20000)

    def create_inspection_via_modal(self, page: Page, *, equipment: str, client_name: str, unit: str, objective: str) -> int:
        self.wait_for_inspector_runtime(page)
        trigger_selector = (
            "[data-open-inspecao-modal]:visible, "
            "#btn-abrir-modal-novo:visible, "
            "#btn-workspace-open-inspecao-modal:visible, "
            "#btn-assistant-landing-open-inspecao-modal:visible"
        )
        trigger_locator = page.locator(trigger_selector)
        if trigger_locator.count() == 0:
            home_button = page.locator(".btn-home-cabecalho:visible").first
            if home_button.count():
                home_button.click()
                expect(page).to_have_url(re.compile(rf"{re.escape(self.base_url)}/app/?(\?home=1)?$"), timeout=20000)
                page.wait_for_load_state("domcontentloaded")
                self.wait_for_inspector_runtime(page)
                self.human_pause(page, 350)
                trigger_locator = page.locator(trigger_selector)
        if trigger_locator.count() == 0:
            page.goto(f"{self.base_url}/app/?home=1", wait_until="domcontentloaded")
            self.wait_for_inspector_runtime(page)
            self.human_pause(page, 350)
            trigger_locator = page.locator(trigger_selector)
        trigger = trigger_locator.first
        expect(trigger).to_be_visible(timeout=20000)
        trigger.click()
        expect(page.locator("#modal-nova-inspecao")).to_be_visible(timeout=20000)
        page.locator("#select-template-inspecao").select_option("padrao", force=True)
        page.locator("#input-local-inspecao").fill(equipment)
        page.locator("#input-cliente-inspecao").fill(client_name)
        page.locator("#input-unidade-inspecao").fill(unit)
        page.locator("#textarea-objetivo-inspecao").fill(objective)
        self.human_pause(page, 250)
        page.locator("#btn-confirmar-inspecao").click()
        expect(page.locator("#modal-nova-inspecao")).to_be_hidden(timeout=20000)
        page.wait_for_function(
            "() => Number(window.TarielAPI?.obterLaudoAtualId?.() || 0) > 0",
            timeout=20000,
        )
        expect(page.locator("#painel-chat")).to_have_attribute("data-inspecao-ui", "workspace", timeout=20000)
        laudo_id = int(page.evaluate("() => Number(window.TarielAPI?.obterLaudoAtualId?.() || 0)"))
        try:
            expect(page.locator("#workspace-titulo-laudo")).to_have_text(equipment, timeout=7000)
            expect(page.locator("#workspace-subtitulo-laudo")).to_contain_text(client_name, timeout=7000)
            expect(page.locator("#workspace-subtitulo-laudo")).to_contain_text(unit, timeout=7000)
        except AssertionError:
            self.add_false_positive(
                f"Modal de nova inspecao confirmou o laudo {laudo_id}, mas o workspace nao exibiu o contexto visual correto sem recarga."
            )
            page.goto(f"{self.base_url}/app/?laudo={laudo_id}&aba=conversa", wait_until="domcontentloaded")
            self.wait_for_inspector_runtime(page)
            self.human_pause(page, 400)
        return laudo_id

    @staticmethod
    def _workspace_view_for_thread_tab(tab: str) -> str:
        tab_normalizada = str(tab or "").strip().lower()
        if tab_normalizada == "historico":
            return "inspection_history"
        if tab_normalizada == "anexos":
            return "inspection_record"
        if tab_normalizada == "mesa":
            return "inspection_mesa"
        return "inspection_conversation"

    def _wait_inspector_thread_tab_ready(self, page: Page, tab: str, *, timeout: int = 20000) -> None:
        view = self._workspace_view_for_thread_tab(tab)
        tab_normalizada = str(tab or "").strip().lower()
        page.wait_for_function(
            """({ tab, view, isConversation }) => {
                const body = document.body;
                const snapshot = window.TarielInspectorState?.obterSnapshotEstadoInspectorAtual?.() || {};
                const tabAtual = String(snapshot.threadTab || body?.dataset?.threadTab || "").trim().toLowerCase();
                const viewAtual = String(body?.dataset?.workspaceView || "").trim();
                const composer = document.getElementById("campo-mensagem");
                const composerVisivel = Boolean(
                    composer
                    && !composer.hidden
                    && !composer.closest?.("[hidden], [inert]")
                    && composer.getClientRects?.().length
                );
                return tabAtual === tab || viewAtual === view || (Boolean(isConversation) && composerVisivel);
            }""",
            arg={"tab": tab_normalizada, "view": view, "isConversation": tab_normalizada == "conversa"},
            timeout=timeout,
        )

    def _assert_inspector_thread_tab_visible(self, page: Page, tab: str, *, timeout: int = 20000) -> None:
        tab_normalizada = str(tab or "").strip().lower()
        if tab_normalizada == "conversa":
            continue_button = page.locator("#btn-workspace-history-continue").first
            if continue_button.count() and continue_button.is_visible():
                continue_button.click()
                self.human_pause(page, 350)
            expect(page.locator("#campo-mensagem")).to_be_visible(timeout=timeout)
            expect(page.locator("#btn-enviar")).to_be_visible(timeout=timeout)
            return
        if tab_normalizada == "historico":
            expect(page.locator('[data-workspace-view-root="inspection_history"]')).to_be_visible(timeout=timeout)
            expect(page.locator("[data-workspace-history-root]")).to_be_attached(timeout=timeout)
            return
        if tab_normalizada == "anexos":
            expect(page.locator('[data-workspace-view-root="inspection_record"]')).to_be_visible(timeout=timeout)
            expect(page.locator("#workspace-anexos-panel")).to_be_visible(timeout=timeout)
            return
        if tab_normalizada == "mesa":
            expect(page.locator('[data-workspace-view-root="inspection_mesa"]')).to_be_visible(timeout=timeout)
            expect(page.locator("#workspace-mesa-stage")).to_be_visible(timeout=timeout)
            return
        raise ValueError(f"Aba do inspetor desconhecida: {tab}")

    def open_inspector_thread_tab(self, page: Page, tab: str) -> None:
        tab_normalizada = str(tab or "").strip().lower()

        def _abrir_por_rota() -> bool:
            laudo_id = int(page.evaluate("() => Number(window.TarielAPI?.obterLaudoAtualId?.() || 0) || 0"))
            if laudo_id <= 0:
                return False
            self.add_false_positive(
                f"Aba '{tab_normalizada}' do workspace do inspetor exigiu reabrir a rota do laudo {laudo_id} para estabilizar a leitura."
            )
            page.goto(f"{self.base_url}/app/?laudo={laudo_id}&aba={tab_normalizada}", wait_until="domcontentloaded")
            self.wait_for_inspector_runtime(page)
            self.human_pause(page, 400)
            return True

        button = page.locator(f'.thread-tab[data-tab="{tab}"]').first
        if button.count():
            try:
                if button.is_visible():
                    button.click()
                elif button.get_attribute("aria-selected") == "true":
                    pass
                else:
                    raise RuntimeError("thread-tab-hidden")
            except Exception:
                button = page.locator(f'.thread-tab[data-tab="{tab}"]').first
                continue_button = page.locator("#btn-workspace-history-continue").first
                if tab_normalizada == "conversa" and continue_button.count() and continue_button.is_visible():
                    continue_button.click()
                    self.human_pause(page, 350)
                else:
                    _abrir_por_rota()
        else:
            continue_button = page.locator("#btn-workspace-history-continue").first
            if tab_normalizada == "conversa" and continue_button.count() and continue_button.is_visible():
                continue_button.click()
                self.human_pause(page, 350)
            else:
                _abrir_por_rota()

        try:
            self._wait_inspector_thread_tab_ready(page, tab_normalizada)
            self._assert_inspector_thread_tab_visible(page, tab_normalizada)
        except Exception:
            if not _abrir_por_rota():
                raise
            self._wait_inspector_thread_tab_ready(page, tab_normalizada)
            self._assert_inspector_thread_tab_visible(page, tab_normalizada)

    def exercise_inspector_profile(self, page: Page, *, new_name: str, new_phone: str) -> None:
        page.locator("#btn-abrir-perfil-chat").click()
        expect(page.locator("#modal-perfil-chat")).to_be_visible(timeout=20000)
        try:
            page.locator("#input-perfil-nome").fill(new_name)
            page.locator("#input-perfil-telefone").fill(new_phone)
            page.locator("#input-foto-perfil").set_input_files(str(self._evidence_png))
            expect(page.locator("#perfil-avatar-preview")).to_have_class(re.compile(r"possui-foto"), timeout=20000)
            self.human_pause(page, 400)
            page.locator("#btn-salvar-perfil-chat").click()
            expect(page.locator("#perfil-chat-feedback")).to_contain_text(
                re.compile(r"Perfil atualizado com sucesso", re.IGNORECASE),
                timeout=20000,
            )
        finally:
            if page.locator("#modal-perfil-chat").count() and page.locator("#modal-perfil-chat").is_visible():
                page.locator("#btn-fechar-modal-perfil").click()
                expect(page.locator("#modal-perfil-chat")).to_be_hidden(timeout=20000)

        page.locator("#btn-abrir-perfil-chat").click()
        expect(page.locator("#modal-perfil-chat")).to_be_visible(timeout=20000)
        try:
            expect(page.locator("#input-perfil-nome")).to_have_value(new_name, timeout=20000)
            expect(page.locator("#input-perfil-telefone")).to_have_value(new_phone, timeout=20000)
        finally:
            page.locator("#btn-fechar-modal-perfil").click()
            expect(page.locator("#modal-perfil-chat")).to_be_hidden(timeout=20000)

    def search_sidebar_history(self, page: Page, text: str) -> None:
        input_busca = page.locator("#busca-historico-input")
        expect(input_busca).to_be_visible(timeout=20000)
        input_busca.fill(text)
        self.human_pause(page, 400)

    def open_inspector_home(self, page: Page) -> None:
        home_button = page.locator(".btn-home-cabecalho").first
        if home_button.count() and home_button.is_visible():
            home_button.click()
            expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=20000)

        page.goto(f"{self.base_url}/app/?home=1", wait_until="domcontentloaded")
        self.wait_for_inspector_runtime(page)
        expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=20000)
        expect(page.locator("#lista-historico")).to_be_visible(timeout=20000)

    def select_sidebar_recent_tab(self, page: Page) -> None:
        button = page.locator('[data-sidebar-laudos-tab-trigger="recentes"]').first
        if button.count() and button.is_visible():
            button.click(force=True)

    def pin_sidebar_laudo(self, page: Page, laudo_id: int) -> None:
        item = page.locator(f'.item-historico[data-laudo-id="{laudo_id}"]').first
        expect(item).to_be_visible(timeout=20000)
        item.hover()
        botao_pin = item.locator("[data-acao-laudo='pin'], [data-action='pin']").first
        expect(botao_pin).to_be_visible(timeout=20000)
        botao_pin.click()
        try:
            expect(item).to_have_attribute("data-pinado", "true", timeout=10000)
        except AssertionError:
            self.add_false_positive(
                f"Clique no pin do laudo {laudo_id} foi aceito, mas o item do historico nao refletiu estado fixado."
            )
            raise

    def delete_sidebar_laudo(self, page: Page, laudo_id: int) -> None:
        item = page.locator(f'.item-historico[data-laudo-id="{laudo_id}"]').first
        expect(item).to_be_visible(timeout=20000)
        item.hover()
        botao_delete = item.locator("[data-acao-laudo='delete'], [data-action='delete']").first
        expect(botao_delete).to_be_visible(timeout=20000)
        page.once("dialog", lambda dialog: dialog.accept())
        botao_delete.click()
        try:
            expect(item).to_be_hidden(timeout=20000)
        except AssertionError:
            self.add_false_positive(
                f"Acao de exclusao do laudo {laudo_id} confirmou na UI, mas o item permaneceu visivel no historico."
            )
            raise

    def export_inspector_pendencias_pdf(self, page: Page, *, laudo_id: int) -> str:
        toggle = page.locator('[data-rail-toggle="pendencias"]').first
        expect(toggle).to_be_visible(timeout=20000)
        toggle.click()
        expect(page.locator('[data-rail-body="pendencias"]')).to_be_visible(timeout=20000)
        expect(page.locator("#btn-exportar-pendencias-pdf")).to_be_visible(timeout=20000)

        with page.expect_download(timeout=20000) as download_info:
            page.locator("#btn-exportar-pendencias-pdf").click()

        download = download_info.value
        filename = download.suggested_filename or f"pendencias_laudo_{laudo_id}.pdf"
        target = self.downloads_dir / filename
        download.save_as(str(target))
        if not target.exists() or target.stat().st_size <= 0:
            self.add_false_positive(
                f"Botao de exportar pendencias do laudo {laudo_id} disparou, mas nenhum PDF util foi salvo."
            )
            raise RuntimeError("Download de pendencias nao gerou arquivo valido.")
        rel = str(target.relative_to(self.artifact_dir))
        self.report.generated_files.append(rel)
        return rel

    def wait_for_ai_response(self, page: Page, *, timeout: int = 90000) -> bool:
        try:
            page.wait_for_function(
                """() => {
                    const items = Array.from(document.querySelectorAll(".linha-mensagem.mensagem-ia .texto-msg"));
                    return items.some((node) => String(node.textContent || "").trim().length > 0);
                }""",
                timeout=timeout,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def send_main_chat_text(self, page: Page, text: str) -> bool:
        self.open_inspector_thread_tab(page, "conversa")
        page.locator("#campo-mensagem").fill(text)
        expect(page.locator("#btn-enviar")).to_be_enabled()
        self.human_pause(page, 250)
        page.locator("#btn-enviar").click()
        expect(
            page.locator(".linha-mensagem.mensagem-inspetor .texto-msg", has_text=text).first
        ).to_be_visible(timeout=20000)
        return self.wait_for_ai_response(page)

    def send_main_chat_with_attachment(self, page: Page, *, text: str, file_path: Path) -> None:
        self.open_inspector_thread_tab(page, "conversa")
        page.locator("#input-anexo").set_input_files(str(file_path))
        expect(page.locator("#preview-anexo .preview-item").first).to_be_visible(timeout=20000)
        page.locator("#campo-mensagem").fill(text)
        expect(page.locator("#btn-enviar")).to_be_enabled()
        self.human_pause(page, 250)
        page.locator("#btn-enviar").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#preview-anexo .preview-item').length === 0",
            timeout=20000,
        )
        page.wait_for_function(
            """() => {
                return document.querySelectorAll(".mensagem-anexo-chip, .img-anexo, .mensagem-anexos a").length > 0;
            }""",
            timeout=20000,
        )

    def try_finalize_inspection(self, page: Page) -> dict[str, Any]:
        result: dict[str, Any] = {"status": "unknown"}
        button = page.locator("[data-finalizar-inspecao]:visible, #btn-finalizar-inspecao:visible").first
        if not button.count() or not button.is_visible():
            laudo_id = int(page.evaluate("() => Number(window.TarielAPI?.obterLaudoAtualId?.() || 0) || 0"))
            if laudo_id > 0:
                page.goto(f"{self.base_url}/app/?laudo={laudo_id}&aba=historico", wait_until="domcontentloaded")
                self.wait_for_inspector_runtime(page)
                self.human_pause(page, 400)
            button = page.locator("[data-finalizar-inspecao]:visible, #btn-finalizar-inspecao:visible").first
        if not button.count() or not button.is_visible():
            result["status"] = "finalize_button_unavailable"
            self.add_step(
                "inspector_finalize",
                "warn",
                "Fluxo do inspetor nao deixou o botao 'Enviar para Mesa' visivel apos a coleta.",
                extra=result,
            )
            self.add_missing("Botao 'Enviar para Mesa' nao ficou acessivel na UI apos a coleta do inspetor.")
            return result
        page.once("dialog", lambda dialog: dialog.accept())
        self.human_pause(page, 250)
        button.click()

        gate_modal = page.locator("#modal-gate-qualidade")
        try:
            gate_modal.wait_for(state="visible", timeout=5000)
            missing_items = gate_modal.locator("#lista-gate-faltantes .item-gate-qualidade").all_inner_texts()
            result["status"] = "blocked_by_gate"
            result["missing_items"] = [item.strip() for item in missing_items if item.strip()]
            shot = self.screenshot(page, "inspetor_gate_qualidade")
            self.add_step(
                "inspector_finalize",
                "warn",
                "Finalizacao real bloqueada pelo gate de qualidade.",
                screenshot=shot,
                extra=result,
            )
            page.locator("#btn-entendi-gate-qualidade").click()
            expect(gate_modal).to_be_hidden(timeout=10000)
            return result
        except PlaywrightTimeoutError:
            pass

        try:
            page.wait_for_function(
                """() => {
                    const estado = String(window.TarielAPI?.obterEstadoRelatorioNormalizado?.() || "").trim().toLowerCase();
                    const aviso = document.getElementById("aviso-laudo-bloqueado");
                    const badge = document.getElementById("workspace-status-badge");
                    const badgeTexto = String(badge?.textContent || "").trim().toLowerCase();
                    const avisoStatus = String(aviso?.dataset?.status || "").trim().toLowerCase();
                    return (
                        estado === "aguardando" ||
                        badgeTexto.includes("aguardando") ||
                        avisoStatus === "aguardando"
                    );
                }""",
                timeout=30000,
            )
            result["status"] = "sent_to_review"
            shot = self.screenshot(page, "inspetor_status_aguardando")
            self.add_step(
                "inspector_finalize",
                "ok",
                "Laudo finalizado e enviado para a mesa.",
                screenshot=shot,
            )
            return result
        except (PlaywrightTimeoutError, AssertionError):
            result["status"] = "finalize_no_visible_transition"
            self.add_step(
                "inspector_finalize",
                "warn",
                "Clique de finalizacao executado, mas o estado canônico nao mudou para aguardando de forma confirmavel.",
                extra=result,
            )
            self.add_false_positive("Botao de finalizacao do inspetor aceitou o clique, mas o estado do laudo nao mudou de forma confirmavel.")
            return result

    def open_mesa_widget(self, page: Page) -> None:
        toggle = page.locator("#btn-mesa-widget-toggle").first
        if toggle.count() and toggle.is_visible():
            toggle.click()
            self.human_pause(page, 300)
        else:
            self.open_inspector_thread_tab(page, "mesa")
            self.human_pause(page, 300)

        lista = page.locator("#mesa-widget-lista").first
        if lista.count() and lista.is_visible():
            return

        painel = page.locator("#painel-mesa-widget").first
        if painel.count() and painel.is_visible():
            expect(lista).to_be_visible(timeout=20000)
            return

        self.open_inspector_thread_tab(page, "mesa")
        expect(page.locator("#workspace-mesa-stage")).to_be_visible(timeout=20000)
        expect(lista).to_be_visible(timeout=20000)

    def reopen_inspection_if_needed(self, page: Page) -> bool:
        btn_reabrir = page.locator("#btn-reabrir-laudo").first
        if not btn_reabrir.count() or not btn_reabrir.is_visible():
            return False
        btn_reabrir.click()
        expect(btn_reabrir).to_be_hidden(timeout=20000)
        expect(page.locator("#mesa-widget-input")).to_be_enabled(timeout=20000)
        return True

    def send_widget_message(self, page: Page, *, text: str, file_path: Path | None = None) -> None:
        self.open_mesa_widget(page)
        if page.locator("#mesa-widget-input").count() and not page.locator("#mesa-widget-input").is_enabled():
            self.reopen_inspection_if_needed(page)
        if file_path:
            page.locator("#mesa-widget-input-anexo").set_input_files(str(file_path))
            expect(page.locator("#mesa-widget-preview-anexo")).to_contain_text(file_path.name, timeout=20000)
        page.locator("#mesa-widget-input").fill(text)
        self.human_pause(page, 250)
        page.locator("#mesa-widget-enviar").click()
        expect(page.locator("#mesa-widget-lista")).to_contain_text(text, timeout=20000)
        if file_path:
            expect(page.locator("#mesa-widget-lista")).to_contain_text(file_path.name, timeout=20000)

    @staticmethod
    def _reviewer_home_tab_for_queue(queue_name: str) -> str:
        queue = str(queue_name or "").strip().lower()
        if queue in {"responder_agora", "validar_aprendizado"}:
            return "responder_agora"
        if queue in {"fechamento_mesa", "aguardando_avaliacao"}:
            return "aguardando_avaliacao"
        if queue in {"aguardando_inspetor", "acompanhamento"}:
            return "acompanhamento"
        return "historico"

    def _focus_reviewer_item(self, page: Page, laudo_id: int) -> bool:
        item = page.locator(f'.js-item-laudo[data-id="{laudo_id}"]').first
        if not item.count():
            return False
        if item.is_visible():
            return True

        btn_home = page.locator("#btn-home-mesa").first
        if btn_home.count() and btn_home.is_visible():
            btn_home.click()
            self.human_pause(page, 250)

        filtro_tudo = page.locator('[data-home-filter="all"]').first
        if filtro_tudo.count() and filtro_tudo.is_visible():
            filtro_tudo.click()
            self.human_pause(page, 250)

        fila_operacional = item.get_attribute("data-fila-operacional") or ""
        aba = self._reviewer_home_tab_for_queue(fila_operacional)
        aba_button = page.locator(f'[data-home-tab="{aba}"]').first
        if aba_button.count() and aba_button.is_visible():
            aba_button.click()
            self.human_pause(page, 350)

        return item.count() and item.is_visible()

    def wait_for_reviewer_item(self, page: Page, laudo_id: int, *, timeout_s: int = 120) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self._focus_reviewer_item(page, laudo_id):
                return
            page.reload(wait_until="domcontentloaded")
            self.human_pause(page, 1200)
        raise RuntimeError(f"Laudo {laudo_id} nao apareceu na fila do revisor dentro do prazo.")

    def open_reviewer_laudo(self, page: Page, laudo_id: int) -> None:
        self._focus_reviewer_item(page, laudo_id)
        item = page.locator(f'.js-item-laudo[data-id="{laudo_id}"]').first
        expect(item).to_be_visible(timeout=20000)
        item.click()
        expect(page.locator("#view-content")).to_be_visible(timeout=20000)
        expect(page.locator("#input-resposta")).to_be_enabled(timeout=20000)
        page.wait_for_function(
            """() => {
                const timeline = document.getElementById("view-timeline");
                return !!timeline && String(timeline.textContent || "").trim().length > 0;
            }""",
            timeout=20000,
        )

    def ensure_reviewer_context_panel_open(self, page: Page) -> None:
        panel = page.locator("#mesa-operacao-painel").first
        if panel.count() and panel.is_visible():
            return
        toggle = page.locator("#btn-toggle-contexto-mesa").first
        if toggle.count() and toggle.is_visible():
            toggle.click()
            self.human_pause(page, 350)

    def wait_for_reviewer_timeline_text(self, page: Page, laudo_id: int, text: str, *, timeout_s: int = 75) -> None:
        deadline = time.time() + timeout_s
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                self.open_reviewer_laudo(page, laudo_id)
                expect(page.locator("#view-timeline")).to_contain_text(text, timeout=10000)
                return
            except Exception as exc:
                last_error = exc
                page.reload(wait_until="domcontentloaded")
                self.human_pause(page, 1200)
        raise RuntimeError(
            f"Timeline do revisor nao refletiu '{text}' para o laudo {laudo_id} dentro do prazo."
        ) from last_error

    def send_reviewer_reply(self, page: Page, *, text: str, file_path: Path) -> None:
        page.locator("#input-anexo-resposta").set_input_files(str(file_path))
        try:
            expect(page.locator("#preview-resposta-anexo")).to_contain_text(file_path.name, timeout=8000)
        except AssertionError:
            self.add_missing("Preview do anexo da mesa nao confirmou o arquivo antes do envio.")
            self.add_false_positive("Selecao de anexo da mesa aceitou a acao, mas o preview nao refletiu o arquivo escolhido.")
        page.locator("#input-resposta").fill(text)
        self.human_pause(page, 250)
        page.locator("#btn-enviar-msg").click()
        expect(page.locator("#view-timeline")).to_contain_text(text, timeout=20000)
        try:
            expect(
                page.locator("#view-timeline .anexo-mensagem-link", has_text=file_path.name).first
            ).to_be_visible(timeout=8000)
        except AssertionError:
            self.add_missing("Anexo enviado pela mesa nao apareceu no timeline do revisor apos o submit.")
            self.add_false_positive("Envio da mesa concluiu sem erro visivel, mas o timeline nao exibiu o anexo acabado de enviar.")

    def exercise_reviewer_operational_panel(self, page: Page, *, laudo_id: int, reply_text: str) -> None:
        panel = page.locator("#mesa-operacao-painel")
        try:
            self.ensure_reviewer_context_panel_open(page)
            expect(panel).to_be_visible(timeout=10000)
        except AssertionError:
            self.open_reviewer_laudo(page, laudo_id)
            self.ensure_reviewer_context_panel_open(page)
            expect(panel).to_be_visible(timeout=20000)
        item = panel.locator(".mesa-operacao-item.aberta", has_text=reply_text).first
        try:
            expect(item).to_be_visible(timeout=15000)
        except AssertionError:
            self.open_reviewer_laudo(page, laudo_id)
            self.ensure_reviewer_context_panel_open(page)
            expect(panel).to_be_visible(timeout=20000)
            item = panel.locator(".mesa-operacao-item.aberta", has_text=reply_text).first
            expect(item).to_be_visible(timeout=20000)
        toggle = item.locator('[data-mesa-action="alternar-pendencia"]').first
        toggle.click()
        expect(panel.locator(".mesa-operacao-item.resolvida", has_text=reply_text).first).to_be_visible(timeout=20000)

    def download_reviewer_json(self, page: Page) -> str:
        with page.expect_download(timeout=20000) as download_info:
            page.locator(".js-btn-pacote-json").click()
        download = download_info.value
        filename = download.suggested_filename
        target = self.downloads_dir / filename
        download.save_as(str(target))
        rel = str(target.relative_to(self.artifact_dir))
        self.report.generated_files.append(rel)
        return rel

    def export_reviewer_pdf(self, page: Page, laudo_id: int) -> str:
        pdf_requests: list[str] = []

        def _remember_request(request: Any) -> None:
            if request.method == "GET" and request.url.endswith("/pacote/exportar-pdf"):
                pdf_requests.append(request.url)

        page.on("request", _remember_request)
        popup = None
        try:
            with page.expect_popup(timeout=12000) as popup_info:
                page.locator(".js-btn-pacote-pdf").click()
            popup = popup_info.value
            popup.wait_for_load_state("domcontentloaded", timeout=12000)
        except PlaywrightTimeoutError:
            page.locator(".js-btn-pacote-pdf").click()
            self.human_pause(page, 1500)
        finally:
            if popup:
                try:
                    popup.close()
                except Exception:
                    pass

        pdf_url = pdf_requests[-1] if pdf_requests else f"{self.base_url}/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf"
        response = page.request.fetch(pdf_url, method="GET")
        if response.status != 200:
            raise RuntimeError(f"PDF respondeu {response.status} ao exportar pacote tecnico.")
        if "application/pdf" not in (response.headers.get("content-type", "").lower()):
            raise RuntimeError(f"Resposta de PDF sem content-type esperado: {response.headers}")
        body = response.body()
        if not body.startswith(b"%PDF"):
            raise RuntimeError("Payload exportado nao comeca com %PDF.")
        filename = f"pacote_mesa_{laudo_id}.pdf"
        target = self.downloads_dir / filename
        target.write_bytes(body)
        rel = str(target.relative_to(self.artifact_dir))
        self.report.generated_files.append(rel)
        return rel

    def read_render_credentials(self) -> tuple[str, str]:
        payload = json.loads(self.render_cache_path.read_text(encoding="utf-8"))
        email = str(payload.get("admin_email") or "").strip()
        password = str(payload.get("admin_password") or "").strip()
        if not email or not password:
            raise RuntimeError(f"Credenciais admin ausentes em {self.render_cache_path}")
        return email, password

    def build_scenario(self) -> dict[str, Any]:
        suffix = f"{self.run_id[-6:]}{uuid.uuid4().hex[:4]}"
        digits = f"{int(time.time() * 1000) % 10**14:014d}"
        return {
            "company_name": f"Tariel UI Audit {suffix}",
            "company_cnpj": digits,
            "client_admin_email": f"cliente.admin+{suffix}@example.com",
            "client_admin_password": f"Cliente!{suffix}Aa",
            "inspector_name": f"Inspetor UI {suffix}",
            "inspector_email": f"inspetor.ui+{suffix}@example.com",
            "inspector_password": f"Inspetor!{suffix}Aa",
            "reviewer_name": f"Mesa UI {suffix}",
            "reviewer_email": f"mesa.ui+{suffix}@example.com",
            "reviewer_password": f"Mesa!{suffix}Aa",
            "inspector_phone": f"1199{suffix[:6]}",
            "reviewer_phone": f"2198{suffix[:6]}",
            "reviewer_crea": f"CREA-{suffix.upper()}",
            "draft_equipment": f"Rascunho UI {suffix}",
            "equipment": f"Caldeira UI {suffix}",
            "unit": f"Unidade Render {suffix}",
            "inspector_profile_name": f"Inspetor UI {suffix} Ajustado",
            "inspector_profile_phone": f"1198{suffix[:6]}77",
        }

    def run(self) -> Path:
        admin_email, admin_password = self.read_render_credentials()
        scenario = self.build_scenario()
        self.report.company = {
            "name": scenario["company_name"],
            "cnpj": scenario["company_cnpj"],
            "admin_email_masked": self.mask_email(scenario["client_admin_email"]),
        }
        self.report.users = {
            "admin_platform_email_masked": self.mask_email(admin_email),
            "inspector_email_masked": self.mask_email(scenario["inspector_email"]),
            "reviewer_email_masked": self.mask_email(scenario["reviewer_email"]),
        }

        report_json = self.artifact_dir / "report.json"
        report_md = self.artifact_dir / "report.md"
        try:
            with sync_playwright() as playwright:
                self._run_playwright(playwright, admin_email=admin_email, admin_password=admin_password, scenario=scenario)
        except Exception as exc:
            self.report.run_error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self.write_json(
                report_json,
                {
                    **asdict(self.report),
                    "steps": [asdict(step) for step in self.report.steps],
                    "console_issues": [asdict(item) for item in self.report.console_issues],
                    "page_errors": [asdict(item) for item in self.report.page_errors],
                },
            )
            self.write_markdown(report_md, self._build_markdown_report())
        return self.artifact_dir

    def _run_playwright(self, playwright: Playwright, *, admin_email: str, admin_password: str, scenario: dict[str, Any]) -> None:
        browser = playwright.chromium.launch(headless=self.headless, slow_mo=self.slow_mo_ms)
        admin_ctx = browser.new_context(viewport={"width": 1440, "height": 960})
        client_ctx = browser.new_context(viewport={"width": 1440, "height": 960})
        inspector_ctx = browser.new_context(viewport={"width": 1440, "height": 960})
        reviewer_ctx = browser.new_context(viewport={"width": 1440, "height": 960}, accept_downloads=True)
        blocked_probe_ctx = browser.new_context(viewport={"width": 1280, "height": 900})

        company_id = 0
        draft_laudo_id = 0
        laudo_id = 0
        company_password = ""
        inspector_password_temp = ""
        reviewer_password_temp = ""

        try:
            admin_page = admin_ctx.new_page()
            client_page = client_ctx.new_page()
            inspector_page = inspector_ctx.new_page()
            reviewer_page = reviewer_ctx.new_page()
            blocked_page = blocked_probe_ctx.new_page()

            for name, page in (
                ("admin", admin_page),
                ("cliente", client_page),
                ("inspetor", inspector_page),
                ("revisor", reviewer_page),
                ("blocked_probe", blocked_page),
            ):
                self.wire_page(page, name)

            self.login_admin(admin_page, email=admin_email, password=admin_password)
            self.add_ok("Login do Admin-CEO no Render concluido no portal administrativo.")
            company_id, company_password = self.create_company_via_admin(
                admin_page,
                company_name=scenario["company_name"],
                cnpj=scenario["company_cnpj"],
                email=scenario["client_admin_email"],
            )

            self.login_first_access(
                client_page,
                portal="cliente",
                email=scenario["client_admin_email"],
                temp_password=company_password,
                new_password=scenario["client_admin_password"],
                success_regex=rf"{re.escape(self.base_url)}/cliente/painel(?:\?sec=overview)?/?$",
            )
            shot = self.screenshot(client_page, "cliente_primeiro_login")
            self.add_step(
                "client_first_login",
                "ok",
                "Primeiro login do admin-cliente validado com troca obrigatoria de senha.",
                screenshot=shot,
            )
            self.collect_visual_metrics(client_page, "cliente/painel")
            self.add_ok("Login do admin-cliente com troca de senha obrigatoria funcionou.")

            inspector_password_temp = self.create_client_user(
                client_page,
                role="inspetor",
                name=scenario["inspector_name"],
                email=scenario["inspector_email"],
                phone=scenario["inspector_phone"],
            )
            reviewer_password_temp = self.create_client_user(
                client_page,
                role="revisor",
                name=scenario["reviewer_name"],
                email=scenario["reviewer_email"],
                phone=scenario["reviewer_phone"],
                crea=scenario["reviewer_crea"],
            )
            shot = self.screenshot(client_page, "cliente_equipe_criada")
            self.add_step(
                "client_create_operational_users",
                "ok",
                "Inspetor e mesa avaliadora criados pelo portal do cliente.",
                screenshot=shot,
            )
            self.add_ok("Criacao de inspetor e mesa pelo portal cliente funcionou.")

            self.edit_client_user(
                client_page,
                email=scenario["inspector_email"],
                phone=f"{scenario['inspector_phone']}11",
            )
            self.edit_client_user(
                client_page,
                email=scenario["reviewer_email"],
                phone=f"{scenario['reviewer_phone']}55",
                crea=f"{scenario['reviewer_crea']}-ALT",
            )
            self.add_step(
                "client_edit_operational_users",
                "ok",
                "Cadastros do inspetor e da mesa alterados no portal cliente.",
            )
            self.add_ok("Edicao de usuario operacional via portal cliente funcionou.")

            try:
                self.delete_client_user(client_page, email=scenario["reviewer_email"])
                reviewer_password_temp = self.create_client_user(
                    client_page,
                    role="revisor",
                    name=scenario["reviewer_name"],
                    email=scenario["reviewer_email"],
                    phone=f"{scenario['reviewer_phone']}55",
                    crea=f"{scenario['reviewer_crea']}-ALT",
                )
                self.add_step(
                    "client_delete_and_recreate_reviewer",
                    "ok",
                    "Usuario da mesa foi excluido e recriado pelo portal cliente.",
                )
                self.add_ok("Exclusao e recriacao de usuario operacional funcionaram pela UI.")
            except Exception as exc:
                self.add_step(
                    "client_delete_and_recreate_reviewer",
                    "warn",
                    f"Fluxo de exclusao e recriacao do usuario da mesa nao confirmou efeito real: {exc}",
                )
                self.add_missing("Portal cliente nao confirmou exclusao e recriacao do usuario da mesa pela UI.")

            self.toggle_client_user(client_page, email=scenario["inspector_email"], expected_button_text="Desbloquear acesso")
            self.add_step(
                "client_block_inspector",
                "ok",
                "Usuario inspetor bloqueado no portal cliente.",
            )

            blocked_page.goto(f"{self.base_url}/app/login", wait_until="domcontentloaded")
            blocked_page.locator('input[name="email"]').fill(scenario["inspector_email"])
            blocked_page.locator('input[name="senha"]').fill(inspector_password_temp)
            blocked_page.locator('button[type="submit"]').click()
            expect(blocked_page.locator("body")).to_contain_text(re.compile(r"Acesso bloqueado", re.IGNORECASE), timeout=20000)
            shot = self.screenshot(blocked_page, "inspetor_login_bloqueado")
            self.add_step(
                "inspector_block_validation",
                "ok",
                "Login do inspetor bloqueado exibiu erro visivel ao usuario.",
                screenshot=shot,
            )
            self.add_ok("Bloqueio de usuario impacta o login do inspetor como esperado.")

            self.toggle_client_user(client_page, email=scenario["inspector_email"], expected_button_text="Bloquear acesso")
            inspector_password_temp = self.reset_client_user_password(client_page, email=scenario["inspector_email"])
            reviewer_password_temp = self.reset_client_user_password(client_page, email=scenario["reviewer_email"])
            shot = self.screenshot(client_page, "cliente_equipe_editada")
            self.add_step(
                "client_unblock_and_reset",
                "ok",
                "Inspetor desbloqueado e senhas temporarias do inspetor e da mesa regeneradas.",
                screenshot=shot,
            )
            self.add_ok("Reset de senha operacional via portal cliente funcionou.")

            client_page.locator("#tab-chat").click()
            expect(client_page.locator("#panel-chat")).to_be_visible(timeout=20000)
            client_page.locator("#tab-mesa").click()
            expect(client_page.locator("#panel-mesa")).to_be_visible(timeout=20000)
            self.add_step(
                "client_navigation_tabs",
                "ok",
                "Tabs Chat e Mesa do portal cliente abriram sem erro.",
                screenshot=self.screenshot(client_page, "cliente_tab_mesa"),
            )
            self.collect_visual_metrics(client_page, "cliente/mesa")

            self.login_first_access(
                inspector_page,
                portal="app",
                email=scenario["inspector_email"],
                temp_password=inspector_password_temp,
                new_password=scenario["inspector_password"],
                success_regex=rf"{re.escape(self.base_url)}/app/?$",
            )
            expect(inspector_page.locator("#painel-chat")).to_be_visible(timeout=20000)
            self.add_ok("Login do inspetor com troca obrigatoria de senha funcionou.")

            try:
                self.exercise_inspector_profile(
                    inspector_page,
                    new_name=scenario["inspector_profile_name"],
                    new_phone=scenario["inspector_profile_phone"],
                )
                self.add_step(
                    "inspector_profile_update",
                    "ok",
                    "Perfil do inspetor atualizado pela UI com nome, telefone e foto.",
                    screenshot=self.screenshot(inspector_page, "inspetor_perfil_atualizado"),
                )
                self.add_ok("Edicao de perfil do inspetor funcionou pela interface.")
            except Exception as exc:
                self.add_step(
                    "inspector_profile_update",
                    "warn",
                    f"Perfil do inspetor nao confirmou atualizacao completa pela UI: {exc}",
                )
                self.add_missing("Perfil do inspetor nao confirmou atualizacao completa de nome, telefone e foto.")
                self.add_false_positive(
                    "Modal de perfil do inspetor exibiu sucesso de atualizacao, mas a reabertura nao confirmou persistencia completa dos dados."
                )

            draft_laudo_id = self.create_inspection_via_modal(
                inspector_page,
                equipment=scenario["draft_equipment"],
                client_name=scenario["company_name"],
                unit=scenario["unit"],
                objective="Laudo rascunho criado para exercitar acoes de historico, pin e exclusao.",
            )
            self.add_step(
                "inspector_create_draft_laudo",
                "ok",
                f"Laudo rascunho criado no inspetor com id {draft_laudo_id}.",
            )
            self.send_main_chat_text(
                inspector_page,
                f"Rascunho inicial do laudo {scenario['draft_equipment']} para exercitar o historico lateral.",
            )

            laudo_id = self.create_inspection_via_modal(
                inspector_page,
                equipment=scenario["equipment"],
                client_name=scenario["company_name"],
                unit=scenario["unit"],
                objective="Jornada E2E real no Render com foco em fluxo humano e mesa avaliadora.",
            )
            shot = self.screenshot(inspector_page, "inspetor_workspace_laudo")
            self.add_step(
                "inspector_create_laudo",
                "ok",
                f"Inspecao criada no workspace do inspetor com laudo {laudo_id}.",
                screenshot=shot,
                extra={"laudo_id": laudo_id},
            )
            self.collect_visual_metrics(inspector_page, "inspetor/workspace")
            self.add_ok("Criacao de laudo via modal real do inspetor funcionou.")

            try:
                self.open_inspector_home(inspector_page)
                self.select_sidebar_recent_tab(inspector_page)
                self.pin_sidebar_laudo(inspector_page, draft_laudo_id)
                self.delete_sidebar_laudo(inspector_page, draft_laudo_id)
                self.search_sidebar_history(inspector_page, "")
                self.add_step(
                    "inspector_sidebar_pin_delete",
                    "ok",
                    f"Historico lateral permitiu fixar e excluir o laudo rascunho {draft_laudo_id}.",
                    screenshot=self.screenshot(inspector_page, "inspetor_sidebar_pin_delete"),
                )
                self.add_ok("Acoes de pin e exclusao de laudo no historico do inspetor funcionaram.")
            except Exception as exc:
                self.search_sidebar_history(inspector_page, "")
                self.add_step(
                    "inspector_sidebar_pin_delete",
                    "warn",
                    f"Acoes de pin/exclusao no historico do inspetor nao fecharam corretamente: {exc}",
                )
                self.add_missing("Historico lateral do inspetor nao confirmou de forma consistente pin/exclusao do laudo rascunho.")

            inspector_page.goto(f"{self.base_url}/app/?laudo={laudo_id}&aba=conversa", wait_until="domcontentloaded")
            self.wait_for_inspector_runtime(inspector_page)
            self.human_pause(inspector_page, 400)
            ai_ok = self.send_main_chat_text(
                inspector_page,
                f"Contexto inicial da coleta {scenario['equipment']}: vaso com sinais visuais de desgaste, sem vazamento aparente.",
            )
            if ai_ok:
                self.add_ok("IA respondeu no chat principal do inspetor durante a coleta.")
            else:
                self.add_missing("A IA nao respondeu no chat principal dentro do timeout usado na jornada.")
            if "PERMISSION_DENIED" in inspector_page.locator("body").inner_text():
                self.add_missing("Gemini no Render respondeu 403 PERMISSION_DENIED: chave de API reportada como vazada.")

            self.open_inspector_thread_tab(inspector_page, "historico")
            self.open_inspector_thread_tab(inspector_page, "anexos")
            self.open_inspector_thread_tab(inspector_page, "mesa")
            self.open_inspector_thread_tab(inspector_page, "conversa")
            self.add_step(
                "inspector_tabs_navigation",
                "ok",
                "Conversa, Historico, Anexos e Mesa abriram no workspace do inspetor.",
            )

            self.send_main_chat_with_attachment(
                inspector_page,
                text="Foto do ponto inspecionado com desgaste superficial proximo a solda.",
                file_path=self._evidence_png,
            )
            self.add_step(
                "inspector_send_chat_evidence",
                "ok",
                "Texto e anexo enviados pelo chat principal do inspetor.",
            )

            finalize_result = self.try_finalize_inspection(inspector_page)
            if finalize_result["status"] == "sent_to_review":
                self.add_ok("Finalizacao real do laudo para a mesa passou pelo gate.")
            elif finalize_result["status"] == "blocked_by_gate":
                missing_gate = ", ".join(finalize_result.get("missing_items", [])) or "gate sem detalhes"
                self.add_missing(f"Finalizacao real do laudo foi bloqueada pelo gate de qualidade: {missing_gate}")
            else:
                self.add_missing("Finalizacao real do laudo nao mostrou transicao visual conclusiva.")

            try:
                expect(inspector_page.locator("#aviso-laudo-bloqueado")).to_be_visible(timeout=20000)
                expect(inspector_page.locator("#mesa-widget-input")).to_be_disabled(timeout=20000)
                self.add_step(
                    "inspector_widget_readonly_after_finalize",
                    "ok",
                    "Canal da mesa ficou somente leitura apos o envio para revisao, sem falso positivo de resposta no inspetor.",
                )
                self.add_ok("Widget da mesa respeitou o bloqueio de escrita apos a finalizacao.")
            except Exception as exc:
                self.add_step(
                    "inspector_widget_readonly_after_finalize",
                    "warn",
                    f"Canal da mesa nao refletiu de forma confiavel o bloqueio de escrita apos a finalizacao: {exc}",
                )
                self.add_missing("Widget da mesa nao refletiu de forma confiavel o bloqueio de escrita apos a finalizacao.")

            reviewer_password_temp = self.ensure_client_user_temp_password_via_api(
                client_page,
                email=scenario["reviewer_email"],
            )
            self.login_first_access(
                reviewer_page,
                portal="revisao",
                email=scenario["reviewer_email"],
                temp_password=reviewer_password_temp,
                new_password=scenario["reviewer_password"],
                success_regex=rf"{re.escape(self.base_url)}/revisao/painel/?$",
            )
            self.add_step(
                "reviewer_first_login",
                "ok",
                "Mesa avaliadora acessou o portal com troca obrigatoria de senha.",
            )
            self.add_ok("Login da mesa avaliadora com troca obrigatoria de senha funcionou.")
            self.wait_for_reviewer_item(reviewer_page, laudo_id)
            shot = self.screenshot(reviewer_page, "revisor_fila")
            self.add_step(
                "reviewer_queue_visibility",
                "ok",
                f"Laudo {laudo_id} apareceu na fila do painel de revisao.",
                screenshot=shot,
            )

            self.open_reviewer_laudo(reviewer_page, laudo_id)
            self.collect_visual_metrics(reviewer_page, "revisao/painel")
            reply_text = "Mesa avaliadora: revisar solda secundaria e confirmar leitura visual do desgaste."
            self.send_reviewer_reply(reviewer_page, text=reply_text, file_path=self._review_png)
            self.exercise_reviewer_operational_panel(reviewer_page, laudo_id=laudo_id, reply_text=reply_text)
            self.add_step(
                "reviewer_reply_and_panel",
                "ok",
                "Mesa respondeu no painel e alternou o estado operacional da pendencia.",
                screenshot=self.screenshot(reviewer_page, "revisor_laudo_aberto"),
            )
            self.add_ok("Comunicacao da mesa para o inspetor funcionou com anexo e painel operacional.")

            reviewer_page.locator(".js-btn-pacote-resumo").click()
            expect(reviewer_page.locator("#modal-pacote")).to_be_visible(timeout=20000)
            reviewer_page.locator("#btn-fechar-pacote").click()
            expect(reviewer_page.locator("#modal-pacote")).to_be_hidden(timeout=20000)
            json_rel = None
            pdf_rel = None
            json_error = None
            pdf_error = None
            try:
                json_rel = self.download_reviewer_json(reviewer_page)
            except Exception as exc:
                json_error = str(exc)
            try:
                pdf_rel = self.export_reviewer_pdf(reviewer_page, laudo_id)
            except Exception as exc:
                pdf_error = str(exc)

            if json_rel and pdf_rel:
                self.add_step(
                    "reviewer_exports",
                    "ok",
                    "Pacote tecnico exportado em JSON e PDF real a partir do painel do revisor.",
                    extra={"json": json_rel, "pdf": pdf_rel},
                )
                self.add_ok("Geracao real de PDF do pacote tecnico funcionou.")
            else:
                detalhes = []
                if json_rel:
                    detalhes.append(f"json={json_rel}")
                if pdf_rel:
                    detalhes.append(f"pdf={pdf_rel}")
                if json_error:
                    detalhes.append(f"falha_json={json_error}")
                if pdf_error:
                    detalhes.append(f"falha_pdf={pdf_error}")
                self.add_step(
                    "reviewer_exports",
                    "warn",
                    "Exportacao do pacote tecnico nao convergiu completamente no painel do revisor.",
                    extra={
                        "json": json_rel,
                        "pdf": pdf_rel,
                        "json_error": json_error,
                        "pdf_error": pdf_error,
                    },
                )
                if pdf_error:
                    self.add_missing(f"Exportacao de PDF do pacote tecnico da mesa falhou: {pdf_error}")
                if json_error:
                    self.add_missing(f"Exportacao de JSON do pacote tecnico da mesa falhou: {json_error}")
                if pdf_rel and not json_rel:
                    self.add_false_positive("Painel do revisor ofereceu exportacao parcial do pacote, mas o JSON nao confirmou efeito real.")
                if json_rel and not pdf_rel:
                    self.add_false_positive("Painel do revisor ofereceu exportacao parcial do pacote, mas o PDF nao confirmou efeito real.")

            inspector_page.goto(f"{self.base_url}/app/?laudo={laudo_id}", wait_until="domcontentloaded")
            self.open_mesa_widget(inspector_page)
            expect(inspector_page.locator("#mesa-widget-lista")).to_contain_text(reply_text, timeout=30000)
            reviewer_attachment_visible = True
            try:
                expect(
                    inspector_page.locator("#mesa-widget-lista .anexo-mesa-link", has_text=self._review_png.name).first
                ).to_be_visible(timeout=12000)
            except AssertionError:
                reviewer_attachment_visible = False
                self.add_missing("Resposta da mesa chegou ao inspetor sem o anexo esperado no widget.")
                self.add_false_positive("Resposta da mesa apareceu no widget do inspetor, mas sem refletir o anexo que a UI aceitou no envio.")
            shot = self.screenshot(inspector_page, "inspetor_widget_resposta_mesa")
            self.add_step(
                "inspector_receives_reviewer_message",
                "ok" if reviewer_attachment_visible else "warn",
                (
                    "Inspetor visualizou a resposta da mesa com anexo no widget."
                    if reviewer_attachment_visible
                    else "Inspetor visualizou a resposta da mesa, mas o anexo nao apareceu no widget."
                ),
                screenshot=shot,
            )
            if reviewer_attachment_visible:
                self.add_ok("Inspetor recebeu o retorno da mesa no mesmo laudo.")

            try:
                pendencias_pdf_rel = self.export_inspector_pendencias_pdf(inspector_page, laudo_id=laudo_id)
                self.add_step(
                    "inspector_export_pendencias_pdf",
                    "ok",
                    "Inspetor exportou o PDF de pendencias pela rail lateral.",
                    extra={"pdf": pendencias_pdf_rel},
                )
                self.add_ok("Exportacao de PDF de pendencias no inspetor funcionou.")
            except Exception as exc:
                self.add_step(
                    "inspector_export_pendencias_pdf",
                    "warn",
                    f"Exportacao de PDF de pendencias no inspetor nao confirmou efeito real: {exc}",
                )
                self.add_missing("Exportacao de PDF de pendencias no inspetor nao confirmou efeito real pela UI.")

            followup_text = "Inspetor: evidencias complementares enviadas, seguindo para nova leitura da mesa."
            try:
                if inspector_page.locator("#btn-reabrir-laudo").count():
                    self.reopen_inspection_if_needed(inspector_page)
                self.send_widget_message(inspector_page, text=followup_text)
                self.wait_for_reviewer_timeline_text(reviewer_page, laudo_id, followup_text)
                self.add_step(
                    "two_way_collaboration",
                    "ok",
                    "Canal da mesa confirmou troca bidirecional entre inspetor e revisor.",
                    screenshot=self.screenshot(reviewer_page, "revisor_timeline_bidirecional"),
                )
                self.add_ok("Canal bidirecional entre inspetor e mesa permaneceu funcional.")
            except Exception:
                self.add_step(
                    "two_way_collaboration",
                    "warn",
                    "Timeline do revisor nao refletiu a segunda resposta do inspetor apos o retorno da mesa.",
                )
                self.add_missing("Timeline do revisor nao refletiu a segunda resposta do inspetor apos o retorno da mesa.")

        finally:
            for ctx in (admin_ctx, client_ctx, inspector_ctx, reviewer_ctx, blocked_probe_ctx):
                try:
                    ctx.close()
                except Exception:
                    pass
            browser.close()

    def _build_markdown_report(self) -> str:
        ok_lines = "\n".join(f"- {item}" for item in self.report.ok_items) or "- Nenhum item positivo registrado."
        missing_lines = "\n".join(f"- {item}" for item in self.report.missing_items) or "- Nenhum gap adicional registrado."
        false_positive_lines = (
            "\n".join(f"- {item}" for item in self.report.false_positive_items)
            or "- Nenhum falso positivo operacional registrado."
        )
        visual_lines = "\n".join(f"- {item}" for item in self.report.visual_notes) or "- Sem observacoes visuais adicionais."
        step_lines = "\n".join(
            f"- `{step.status}` {step.name}: {step.details}"
            + (f" (`{step.screenshot}`)" if step.screenshot else "")
            for step in self.report.steps
        )
        console_lines = "\n".join(
            f"- `{item.page}` {item.level}: {item.text}"
            for item in (self.report.console_issues + self.report.page_errors)[:20]
        ) or "- Nenhum warning/error de console relevante capturado."
        files_lines = "\n".join(f"- `{item}`" for item in sorted(set(self.report.generated_files))) or "- Nenhum arquivo gerado."

        return f"""# Render UI Journey Report

- Base URL: `{self.report.base_url}`
- Run ID: `{self.report.run_id}`
- Run Error: `{self.report.run_error or 'none'}`
- Empresa: `{self.report.company.get('name', '')}`
- Admin-cliente: `{self.report.company.get('admin_email_masked', '')}`
- Inspetor: `{self.report.users.get('inspector_email_masked', '')}`
- Mesa avaliadora: `{self.report.users.get('reviewer_email_masked', '')}`

## Steps
{step_lines}

## OK
{ok_lines}

## Missing Or Failing
{missing_lines}

## False Positives
{false_positive_lines}

## Visual Notes
{visual_lines}

## Console
{console_lines}

## Files
{files_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa jornada UI real contra o deploy Render.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--render-cache", default=str(DEFAULT_RENDER_CACHE))
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--slow-mo-ms", type=int, default=140)
    parser.add_argument("--pause-scale", type=float, default=1.0)
    args = parser.parse_args()

    runner = JourneyRunner(
        base_url=args.base_url,
        artifact_root=Path(args.artifact_root),
        render_cache_path=Path(args.render_cache),
        headless=not args.headful,
        slow_mo_ms=args.slow_mo_ms,
        pause_scale=args.pause_scale,
    )
    artifact_dir = runner.run()
    print(str(artifact_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
