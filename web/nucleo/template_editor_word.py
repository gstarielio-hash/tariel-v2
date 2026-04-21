from __future__ import annotations

import base64
import html
import io
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from pypdf import PdfReader

from app.domains.chat.catalog_document_view_model import build_catalog_document_view_model
from app.core.perf_support import medir_operacao, medir_operacao_async
from app.shared.public_verification import build_public_verification_qr_png_bytes
from nucleo.template_laudos import normalizar_codigo_template, salvar_pdf_template_base

logger = logging.getLogger(__name__)

MODO_EDITOR_LEGADO = "legado_pdf"
MODO_EDITOR_RICO = "editor_rico"

MAX_NODES_DOCUMENTO = 5_000
MAX_PROFUNDIDADE_DOCUMENTO = 45
MAX_ASSET_BYTES = 5 * 1024 * 1024
MAX_PLACEHOLDER_CHARS = 120

REGEX_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_.:\-]{1,120})\s*\}\}")
REGEX_PLACEHOLDER_SINGLE = re.compile(r"\{([a-zA-Z0-9_.:\-]{1,120})\}")
REGEX_TOKEN_SEGMENTO = re.compile(r"^[a-zA-Z0-9_.\-]{1,120}$")

MIME_IMAGEM_PERMITIDO = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

_DIR_EDITOR_ASSETS = Path(
    os.getenv(
        "DIR_EDITOR_TEMPLATES_ASSETS",
        str(Path(tempfile.gettempdir()) / "tariel_templates_editor_assets"),
    )
).resolve()


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalizar_modo_editor(valor: str | None) -> str:
    modo = str(valor or "").strip().lower()
    if modo == MODO_EDITOR_RICO:
        return MODO_EDITOR_RICO
    return MODO_EDITOR_LEGADO


def documento_editor_padrao() -> dict[str, Any]:
    return {
        "version": 1,
        "doc": {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Template Técnico Tariel.ia"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Use {{json_path:informacoes_gerais.local_inspecao}} e {{token:cliente_nome}} para preencher automaticamente.",
                        }
                    ],
                },
            ],
        },
    }


def estilo_editor_padrao() -> dict[str, Any]:
    return {
        "pagina": {
            "size": "A4",
            "orientation": "portrait",
            "margens_mm": {"top": 18, "right": 14, "bottom": 18, "left": 14},
        },
        "tipografia": {
            "font_family": "Inter, 'Segoe UI', Arial, sans-serif",
            "font_size_px": 12,
            "line_height": 1.45,
        },
        "tema": {
            "primaria": "#17324d",
            "secundaria": "#55697a",
            "acento": "#b6813a",
            "suave": "#eef3f7",
            "borda": "#c5d2dc",
        },
        "cabecalho_texto": "",
        "rodape_texto": "",
        "marca_dagua": {"texto": "", "opacity": 0.08, "font_size_px": 72, "rotate_deg": -32},
    }


def _contar_nodes(node: Any, profundidade: int = 0) -> int:
    if profundidade > MAX_PROFUNDIDADE_DOCUMENTO:
        return MAX_NODES_DOCUMENTO + 1
    if isinstance(node, dict):
        total = 1
        content = node.get("content")
        if isinstance(content, list):
            for child in content:
                total += _contar_nodes(child, profundidade + 1)
                if total > MAX_NODES_DOCUMENTO:
                    return total
        return total
    if isinstance(node, list):
        total = 0
        for child in node:
            total += _contar_nodes(child, profundidade + 1)
            if total > MAX_NODES_DOCUMENTO:
                return total
        return total
    return 1


def normalizar_documento_editor(payload: dict[str, Any] | None) -> dict[str, Any]:
    base = documento_editor_padrao()
    if not isinstance(payload, dict):
        return base

    doc = payload.get("doc")
    if not isinstance(doc, dict) or str(doc.get("type") or "").strip().lower() != "doc":
        return base
    if _contar_nodes(doc) > MAX_NODES_DOCUMENTO:
        raise ValueError("Documento do editor excede o limite de complexidade.")

    return {
        "version": int(payload.get("version") or 1),
        "doc": doc,
    }


def normalizar_estilo_editor(payload: dict[str, Any] | None) -> dict[str, Any]:
    base = estilo_editor_padrao()
    if not isinstance(payload, dict):
        return base

    pagina_bruta = payload.get("pagina")
    if isinstance(pagina_bruta, dict):
        orientation = str(pagina_bruta.get("orientation") or "portrait").strip().lower()
        if orientation not in {"portrait", "landscape"}:
            orientation = "portrait"
        margens = pagina_bruta.get("margens_mm")
        if not isinstance(margens, dict):
            margens = {}
        base["pagina"] = {
            "size": "A4",
            "orientation": orientation,
            "margens_mm": {
                "top": max(5, min(40, int(margens.get("top", 18) or 18))),
                "right": max(5, min(40, int(margens.get("right", 14) or 14))),
                "bottom": max(5, min(40, int(margens.get("bottom", 18) or 18))),
                "left": max(5, min(40, int(margens.get("left", 14) or 14))),
            },
        }

    tipografia = payload.get("tipografia")
    if isinstance(tipografia, dict):
        base["tipografia"] = {
            "font_family": str(tipografia.get("font_family") or base["tipografia"]["font_family"])[:120],
            "font_size_px": max(10, min(18, int(tipografia.get("font_size_px", 12) or 12))),
            "line_height": max(1.2, min(2.0, float(tipografia.get("line_height", 1.45) or 1.45))),
        }

    tema = payload.get("tema")
    if isinstance(tema, dict):
        base["tema"] = {
            "primaria": _normalizar_cor_tema(tema.get("primaria"), fallback=base["tema"]["primaria"]),
            "secundaria": _normalizar_cor_tema(tema.get("secundaria"), fallback=base["tema"]["secundaria"]),
            "acento": _normalizar_cor_tema(tema.get("acento"), fallback=base["tema"]["acento"]),
            "suave": _normalizar_cor_tema(tema.get("suave"), fallback=base["tema"]["suave"]),
            "borda": _normalizar_cor_tema(tema.get("borda"), fallback=base["tema"]["borda"]),
        }

    base["cabecalho_texto"] = str(payload.get("cabecalho_texto") or "").strip()[:200]
    base["rodape_texto"] = str(payload.get("rodape_texto") or "").strip()[:200]

    marca_dagua = payload.get("marca_dagua")
    if isinstance(marca_dagua, dict):
        base["marca_dagua"] = {
            "texto": str(marca_dagua.get("texto") or "").strip()[:120],
            "opacity": max(0.02, min(0.35, float(marca_dagua.get("opacity", 0.08) or 0.08))),
            "font_size_px": max(24, min(160, int(marca_dagua.get("font_size_px", 72) or 72))),
            "rotate_deg": max(-70, min(70, int(marca_dagua.get("rotate_deg", -32) or -32))),
        }
    return base


def _normalizar_assets(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    saida: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        asset_id = str(item.get("id") or "").strip()[:40]
        path = str(item.get("path") or "").strip()
        mime = str(item.get("mime_type") or "").strip().lower()
        if not asset_id or not path or mime not in MIME_IMAGEM_PERMITIDO:
            continue
        saida.append(
            {
                "id": asset_id,
                "filename": str(item.get("filename") or "imagem"),
                "mime_type": mime,
                "path": path,
                "size_bytes": int(item.get("size_bytes") or 0),
                "created_em": str(item.get("created_em") or ""),
            }
        )
    return saida


def _obter_valor_por_caminho(payload: dict[str, Any], caminho: str) -> Any:
    atual: Any = payload
    for parte in str(caminho or "").split("."):
        chave = parte.strip()
        if not chave:
            continue
        if isinstance(atual, dict):
            atual = atual.get(chave)
        else:
            return None
    return atual


def _resolver_placeholder(raw: str, dados_formulario: dict[str, Any]) -> str:
    bruto = str(raw or "").strip()
    if not bruto:
        return ""

    modo = "token"
    chave = bruto
    if ":" in bruto:
        candidato_modo, candidato_chave = bruto.split(":", 1)
        candidato_modo = str(candidato_modo or "").strip().lower()
        candidato_chave = str(candidato_chave or "").strip()
        if candidato_modo in {"json_path", "token"} and candidato_chave:
            modo = candidato_modo
            chave = candidato_chave

    if not REGEX_TOKEN_SEGMENTO.match(chave):
        return ""

    if modo == "json_path" or "." in chave:
        valor = _obter_valor_por_caminho(dados_formulario, chave)
    else:
        tokens = dados_formulario.get("tokens") if isinstance(dados_formulario.get("tokens"), dict) else {}
        valor = tokens.get(chave)
        if valor is None:
            valor = dados_formulario.get(chave)

    if valor is None:
        return ""
    if isinstance(valor, (dict, list)):
        return html.escape(str(valor), quote=True)
    return html.escape(str(valor), quote=True)


def _substituir_placeholders_texto(texto: str, dados_formulario: dict[str, Any]) -> str:
    texto_bruto = str(texto or "")

    def _replace(match: re.Match[str]) -> str:
        chave = str(match.group(1) or "").strip()[:MAX_PLACEHOLDER_CHARS]
        return _resolver_placeholder(chave, dados_formulario)

    resolvido = REGEX_PLACEHOLDER.sub(_replace, texto_bruto)
    resolvido = REGEX_PLACEHOLDER_SINGLE.sub(_replace, resolvido)
    return html.escape(resolvido, quote=True).replace("\n", "<br>")


def _css_cor_segura(valor: Any) -> str:
    cor = str(valor or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", cor):
        return cor
    if re.fullmatch(r"rgba?\([0-9,\s.]+\)", cor):
        return cor
    return ""


def _css_fonte_segura(valor: Any) -> str:
    fonte = str(valor or "").strip()[:80]
    if not fonte:
        return ""
    if re.fullmatch(r"[A-Za-z0-9 ,.'\"_-]{1,80}", fonte):
        return fonte
    return ""


def _css_tamanho_seguro(valor: Any) -> str:
    tamanho = str(valor or "").strip().lower()
    if re.fullmatch(r"\d{1,2}px", tamanho):
        return tamanho
    return ""


def _css_alinhamento_seguro(valor: Any) -> str:
    alinhamento = str(valor or "").strip().lower()
    if alinhamento in {"left", "center", "right", "justify"}:
        return alinhamento
    return ""


def _normalizar_cor_tema(valor: Any, *, fallback: str) -> str:
    cor = str(valor or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", cor):
        return cor
    if re.fullmatch(r"rgba?\([0-9,\s.]+\)", cor):
        return cor
    return fallback


def _css_classes_seguras(valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    classes: list[str] = []
    vistos: set[str] = set()
    for token in texto.split():
        classe = token.strip()[:40]
        if not classe or classe in vistos:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", classe):
            continue
        vistos.add(classe)
        classes.append(classe)
    return " ".join(classes[:8])


def _style_inline(attrs: dict[str, Any]) -> str:
    fragmentos: list[str] = []
    classes = _css_classes_seguras(attrs.get("className"))
    if classes:
        fragmentos.append(f'class="{html.escape(classes, quote=True)}"')

    estilos: list[str] = []
    alinhamento = _css_alinhamento_seguro(attrs.get("textAlign"))
    if alinhamento:
        estilos.append(f"text-align:{alinhamento}")
    if estilos:
        fragmentos.append(f'style="{"; ".join(estilos)}"')
    return f" {' '.join(fragmentos)}" if fragmentos else ""


def _aplicar_marks(texto_html: str, marks: list[dict[str, Any]] | None) -> str:
    resultado = texto_html
    for mark in marks or []:
        tipo = str((mark or {}).get("type") or "").strip().lower()
        attrs = (mark or {}).get("attrs") if isinstance(mark, dict) else {}
        if tipo == "bold":
            resultado = f"<strong>{resultado}</strong>"
        elif tipo == "italic":
            resultado = f"<em>{resultado}</em>"
        elif tipo == "underline":
            resultado = f"<u>{resultado}</u>"
        elif tipo == "strike":
            resultado = f"<s>{resultado}</s>"
        elif tipo == "highlight":
            cor = _css_cor_segura(attrs.get("color") if isinstance(attrs, dict) else "")
            style = f' style="background-color:{cor};"' if cor else ""
            resultado = f"<mark{style}>{resultado}</mark>"
        elif tipo == "textstyle":
            estilos: list[str] = []
            if isinstance(attrs, dict):
                cor = _css_cor_segura(attrs.get("color"))
                if cor:
                    estilos.append(f"color:{cor}")
                fonte = _css_fonte_segura(attrs.get("fontFamily"))
                if fonte:
                    estilos.append(f"font-family:{fonte}")
                tamanho = _css_tamanho_seguro(attrs.get("fontSize"))
                if tamanho:
                    estilos.append(f"font-size:{tamanho}")
            if estilos:
                resultado = f'<span style="{"; ".join(estilos)}">{resultado}</span>'
        elif tipo == "link":
            href = ""
            if isinstance(attrs, dict):
                href = str(attrs.get("href") or "").strip()
            if href.startswith("http://") or href.startswith("https://"):
                href_seguro = html.escape(href, quote=True)
                resultado = f'<a href="{href_seguro}" target="_blank" rel="noopener noreferrer">{resultado}</a>'
    return resultado


def _asset_para_data_uri(asset: dict[str, Any]) -> str:
    caminho = Path(str(asset.get("path") or "")).resolve()
    if not caminho.exists() or not caminho.is_file():
        return ""
    mime = str(asset.get("mime_type") or "").strip().lower()
    if mime not in MIME_IMAGEM_PERMITIDO:
        return ""
    conteudo = caminho.read_bytes()
    if len(conteudo) > MAX_ASSET_BYTES:
        return ""
    base = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{base}"


def _render_nodes_html(
    nodes: list[dict[str, Any]],
    *,
    dados_formulario: dict[str, Any],
    assets_map: dict[str, dict[str, Any]],
) -> str:
    partes: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        tipo = str(node.get("type") or "").strip()
        content = node.get("content")
        filhos = content if isinstance(content, list) else []
        attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}

        if tipo == "text":
            texto = _substituir_placeholders_texto(str(node.get("text") or ""), dados_formulario)
            partes.append(_aplicar_marks(texto, node.get("marks") if isinstance(node.get("marks"), list) else []))
            continue

        if tipo == "hardBreak":
            partes.append("<br>")
            continue

        if tipo == "placeholder":
            raw = str(attrs.get("raw") or "").strip()
            if not raw:
                mode = str(attrs.get("mode") or "token").strip().lower()
                key = str(attrs.get("key") or "").strip()
                raw = f"{mode}:{key}" if key else ""
            partes.append(_resolver_placeholder(raw, dados_formulario))
            continue

        if tipo == "section":
            partes.append(
                f"<section{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</section>"
            )
            continue

        if tipo == "panel":
            partes.append(
                f"<div{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</div>"
            )
            continue

        if tipo == "spacer":
            partes.append(f"<div{_style_inline(attrs)}></div>")
            continue

        if tipo == "paragraph":
            partes.append(f"<p{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</p>")
            continue

        if tipo == "heading":
            nivel = int(attrs.get("level") or 2)
            nivel = max(1, min(4, nivel))
            partes.append(f"<h{nivel}{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</h{nivel}>")
            continue

        if tipo == "bulletList":
            partes.append(
                f"<ul{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</ul>"
            )
            continue

        if tipo == "orderedList":
            partes.append(
                f"<ol{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</ol>"
            )
            continue

        if tipo == "listItem":
            partes.append(
                f"<li{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</li>"
            )
            continue

        if tipo == "table":
            partes.append(
                f"<table{_style_inline(attrs)}><tbody>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</tbody></table>"
            )
            continue

        if tipo == "tableRow":
            partes.append(
                f"<tr{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</tr>"
            )
            continue

        if tipo in {"tableCell", "tableHeader"}:
            tag = "th" if tipo == "tableHeader" else "td"
            partes.append(
                f"<{tag}{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</{tag}>"
            )
            continue

        if tipo == "blockquote":
            partes.append(
                f"<blockquote{_style_inline(attrs)}>{_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map)}</blockquote>"
            )
            continue

        if tipo == "horizontalRule":
            partes.append(f"<hr{_style_inline(attrs)}>")
            continue

        if tipo == "image":
            src = str(attrs.get("src") or "").strip()
            asset_id = str(attrs.get("asset_id") or "").strip()
            if src.startswith("asset://") and not asset_id:
                asset_id = src.split("asset://", 1)[1].strip()
            src_final = ""
            if asset_id:
                asset = assets_map.get(asset_id)
                if asset:
                    src_final = _asset_para_data_uri(asset)
            elif src.startswith("data:image/"):
                src_final = src

            if src_final:
                alt = html.escape(str(attrs.get("alt") or ""), quote=True)[:180]
                width = attrs.get("width")
                largura_style = ""
                if isinstance(width, (int, float)) and 40 <= float(width) <= 1200:
                    largura_style = f' style="max-width:{int(width)}px;"'
                partes.append(
                    f'<p{_style_inline(attrs)}><img src="{html.escape(src_final, quote=True)}" alt="{alt}"{largura_style}></p>'
                )
            continue

        partes.append(_render_nodes_html(filhos, dados_formulario=dados_formulario, assets_map=assets_map))
    return "".join(partes)


def montar_html_documento_editor(
    *,
    documento_editor_json: dict[str, Any] | None,
    estilo_json: dict[str, Any] | None,
    assets_json: Any,
    dados_formulario: dict[str, Any] | None,
    public_verification: dict[str, Any] | None = None,
) -> str:
    doc_payload = normalizar_documento_editor(documento_editor_json)
    estilo = normalizar_estilo_editor(estilo_json)
    dados = dados_formulario if isinstance(dados_formulario, dict) else {}
    assets = _normalizar_assets(assets_json)
    assets_map = {item["id"]: item for item in assets}

    doc = doc_payload.get("doc") if isinstance(doc_payload.get("doc"), dict) else documento_editor_padrao()["doc"]
    conteudo = doc.get("content") if isinstance(doc.get("content"), list) else []
    body_html = _render_nodes_html(conteudo, dados_formulario=dados, assets_map=assets_map)

    pagina = estilo["pagina"]
    margens = pagina["margens_mm"]
    tipografia = estilo["tipografia"]
    tema = estilo.get("tema") if isinstance(estilo.get("tema"), dict) else estilo_editor_padrao()["tema"]
    cabecalho = _substituir_placeholders_texto(str(estilo.get("cabecalho_texto") or ""), dados)
    rodape = _substituir_placeholders_texto(str(estilo.get("rodape_texto") or ""), dados)
    watermark = estilo.get("marca_dagua") if isinstance(estilo.get("marca_dagua"), dict) else {}
    watermark_texto = html.escape(str(watermark.get("texto") or ""), quote=True)
    watermark_opacidade = float(watermark.get("opacity", 0.08) or 0.08)
    watermark_fonte = int(watermark.get("font_size_px", 72) or 72)
    watermark_rotate = int(watermark.get("rotate_deg", -32) or -32)

    watermark_html = ""
    if watermark_texto:
        watermark_html = '<div class="tariel-watermark">' + watermark_texto + "</div>"

    verification = public_verification if isinstance(public_verification, dict) else {}
    verification_url = html.escape(str(verification.get("verification_url") or ""), quote=True)
    verification_hash = html.escape(str(verification.get("codigo_hash") or ""), quote=True)
    verification_qr = html.escape(str(verification.get("qr_image_data_uri") or ""), quote=True)
    verification_html = ""
    if verification_url and verification_hash:
        verification_html = f"""
    <section class="tariel-verification-block">
      <div class="tariel-verification-copy">
        <div class="tariel-verification-eyebrow">Verificacao Publica</div>
        <h2>Hash e QR Code do documento emitido</h2>
        <p>Use o QR Code ou a URL para conferir a autenticidade do laudo no endpoint publico da Tariel.</p>
        <div class="tariel-verification-meta">
          <strong>Hash</strong>
          <span>{verification_hash}</span>
        </div>
        <div class="tariel-verification-meta">
          <strong>URL</strong>
          <span>{verification_url}</span>
        </div>
      </div>
      {f'<img class="tariel-verification-qr" src="{verification_qr}" alt="QR Code de verificacao publica do laudo">' if verification_qr else ''}
    </section>
"""

    html_doc = f"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    @page {{
      size: A4 {"landscape" if pagina["orientation"] == "landscape" else "portrait"};
      margin: {margens["top"]}mm {margens["right"]}mm {margens["bottom"]}mm {margens["left"]}mm;
    }}
    html, body {{
      margin: 0;
      padding: 0;
      color: #18232d;
      font-family: {tipografia["font_family"]};
      font-size: {tipografia["font_size_px"]}px;
      line-height: {tipografia["line_height"]};
      background: #fff;
    }}
    body {{
      counter-reset: section;
    }}
    :root {{
      --tariel-primary: {tema["primaria"]};
      --tariel-secondary: {tema["secundaria"]};
      --tariel-accent: {tema["acento"]};
      --tariel-soft: {tema["suave"]};
      --tariel-border: {tema["borda"]};
    }}
    .tariel-doc {{
      position: relative;
      min-height: 100%;
      padding-top: 18mm;
      padding-bottom: 14mm;
    }}
    .tariel-header {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 14mm;
      font-size: 10px;
      border-bottom: 1px solid var(--tariel-border);
      color: var(--tariel-secondary);
      padding: 2mm 4mm;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      background: #fff;
    }}
    .tariel-footer {{
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: 10mm;
      font-size: 10px;
      border-top: 1px solid var(--tariel-border);
      color: var(--tariel-secondary);
      padding: 2mm 4mm;
      background: #fff;
    }}
    .tariel-body p {{
      margin: 0 0 10px;
    }}
    .tariel-body h1, .tariel-body h2, .tariel-body h3, .tariel-body h4 {{
      margin: 0 0 10px;
      line-height: 1.2;
    }}
    .tariel-body h1 {{
      color: var(--tariel-primary);
      font-size: 26px;
      letter-spacing: 0.01em;
      margin-bottom: 8px;
    }}
    .tariel-body h2 {{
      color: var(--tariel-primary);
      font-size: 16px;
      margin-top: 18px;
      padding-bottom: 4px;
      border-bottom: 2px solid var(--tariel-border);
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }}
    .tariel-body h3 {{
      color: var(--tariel-secondary);
      font-size: 14px;
      margin-top: 14px;
    }}
    .tariel-body ul, .tariel-body ol {{
      margin: 0 0 10px 22px;
    }}
    .tariel-body table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0 0 12px;
      page-break-inside: avoid;
      table-layout: fixed;
    }}
    .tariel-body td, .tariel-body th {{
      border: 1px solid var(--tariel-border);
      padding: 7px 8px;
      vertical-align: top;
    }}
    .tariel-body th {{
      background: var(--tariel-soft);
      color: var(--tariel-primary);
      font-weight: 700;
      text-align: left;
    }}
    .tariel-body img {{
      max-width: 100%;
      height: auto;
      display: inline-block;
    }}
    .tariel-body blockquote {{
      margin: 0 0 10px;
      padding: 10px 14px;
      border-left: 4px solid var(--tariel-primary);
      background: var(--tariel-soft);
      color: var(--tariel-primary);
    }}
    .tariel-body hr {{
      margin: 14px 0;
      border: 0;
      border-top: 1px solid var(--tariel-border);
    }}
    .tariel-body mark {{
      padding: 0 .08em;
      border-radius: 3px;
    }}
    .tariel-watermark {{
      position: fixed;
      inset: 45% 0 auto 0;
      text-align: center;
      font-size: {watermark_fonte}px;
      opacity: {watermark_opacidade};
      color: #666;
      transform: rotate({watermark_rotate}deg);
      pointer-events: none;
      z-index: 0;
      font-weight: 700;
      user-select: none;
    }}
    .tariel-body {{
      position: relative;
      z-index: 2;
    }}
    .tariel-body .doc-kicker {{
      margin-bottom: 6px;
      color: var(--tariel-accent);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-lead {{
      margin-bottom: 14px;
      padding: 10px 12px;
      border-left: 4px solid var(--tariel-primary);
      background: var(--tariel-soft);
      color: #24323f;
    }}
    .tariel-body .doc-meta {{
      color: var(--tariel-secondary);
      font-size: 10px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }}
    .tariel-body .doc-note {{
      margin: 12px 0;
      padding: 8px 10px;
      border: 1px solid var(--tariel-border);
      background: #f8fafb;
      color: #34424f;
      font-size: 11px;
    }}
    .tariel-body .doc-small {{
      color: var(--tariel-secondary);
      font-size: 11px;
    }}
    .tariel-body .doc-divider {{
      margin-top: 10px;
      margin-bottom: 16px;
    }}
    .tariel-body .doc-cover td:first-child,
    .tariel-body .doc-conclusion td:first-child {{
      width: 34%;
      color: var(--tariel-primary);
      font-weight: 700;
      background: #fbfcfd;
    }}
    .tariel-body .doc-compact th,
    .tariel-body .doc-compact td {{
      padding-top: 5px;
      padding-bottom: 5px;
    }}
    .tariel-body .doc-matrix th,
    .tariel-body .doc-matrix td,
    .tariel-body .doc-evidence-matrix th,
    .tariel-body .doc-evidence-matrix td,
    .tariel-body .doc-action-plan th,
    .tariel-body .doc-action-plan td {{
      font-size: 10.5px;
    }}
    .tariel-verification-block {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 132px;
      gap: 14px;
      align-items: center;
      margin-top: 22px;
      padding: 14px;
      border: 1px solid var(--tariel-border);
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(23, 50, 77, 0.05), rgba(182, 129, 58, 0.08));
      page-break-inside: avoid;
    }}
    .tariel-verification-copy {{
      display: grid;
      gap: 8px;
    }}
    .tariel-verification-eyebrow {{
      color: var(--tariel-accent);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .tariel-verification-block h2 {{
      margin: 0;
      border: 0;
      padding: 0;
      font-size: 14px;
      text-transform: none;
      letter-spacing: 0;
    }}
    .tariel-verification-block p {{
      margin: 0;
      color: var(--tariel-secondary);
      font-size: 11px;
    }}
    .tariel-verification-meta {{
      display: grid;
      gap: 2px;
      word-break: break-word;
    }}
    .tariel-verification-meta strong {{
      color: var(--tariel-primary);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .tariel-verification-meta span {{
      color: #22303d;
      font-size: 11px;
    }}
    .tariel-verification-qr {{
      width: 132px;
      height: 132px;
      object-fit: contain;
      border-radius: 18px;
      border: 1px solid var(--tariel-border);
      background: #fff;
      padding: 10px;
      justify-self: end;
    }}
    .tariel-body .doc-cover-shell,
    .tariel-body .doc-section,
    .tariel-body .doc-opening-panel,
    .tariel-body .doc-conclusion-panel,
    .tariel-body .doc-signature-grid,
    .tariel-body .doc-table,
    .tariel-body .doc-kv-grid {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .tariel-body .doc-cover-shell {{
      display: grid;
      gap: 10px;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(23, 50, 77, 0.12);
    }}
    .tariel-body .doc-title {{
      margin-bottom: 0;
      font-size: 29px;
      line-height: 1.08;
      letter-spacing: 0.005em;
    }}
    .tariel-body .doc-subtitle {{
      margin: 0;
      color: var(--tariel-secondary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-identity-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 2px 0 4px;
    }}
    .tariel-body .doc-chip {{
      margin: 0;
      padding: 5px 10px;
      border: 1px solid rgba(23, 50, 77, 0.12);
      border-radius: 999px;
      background: #fff;
      color: var(--tariel-secondary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-opening-panel {{
      padding: 16px 18px;
      border: 1px solid rgba(23, 50, 77, 0.12);
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(23, 50, 77, 0.04), rgba(23, 50, 77, 0.01)),
        #fff;
    }}
    .tariel-body .doc-opening-copy {{
      margin: 0;
      color: #273545;
      font-size: 13px;
      line-height: 1.65;
    }}
    .tariel-body .doc-section {{
      display: grid;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .tariel-body .doc-section-heading {{
      margin: 0;
      padding: 0 0 7px;
      border-bottom: 1px solid rgba(23, 50, 77, 0.14);
      font-size: 16px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-section-intro {{
      margin: 0;
      color: var(--tariel-secondary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 11px;
      line-height: 1.6;
    }}
    .tariel-body .doc-spacer {{
      height: 6px;
    }}
    .tariel-body .doc-kv-grid {{
      border-collapse: separate;
      border-spacing: 0;
      border: 1px solid rgba(23, 50, 77, 0.10);
      border-radius: 16px;
      overflow: hidden;
      background: #fff;
    }}
    .tariel-body .doc-kv-grid td {{
      border: 0;
      border-top: 1px solid rgba(23, 50, 77, 0.08);
      padding: 11px 12px;
      vertical-align: top;
    }}
    .tariel-body .doc-kv-grid tr:first-child td {{
      border-top: 0;
    }}
    .tariel-body .doc-kv-label {{
      width: 31%;
      background: #fafcfd;
    }}
    .tariel-body .doc-kv-label-copy {{
      margin: 0;
      color: var(--tariel-secondary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-kv-value {{
      background: #fff;
    }}
    .tariel-body .doc-kv-value-copy {{
      margin: 0;
      color: #21303e;
      font-size: 12px;
      line-height: 1.6;
    }}
    .tariel-body .doc-kv-value-copy--multiline {{
      min-height: 42px;
    }}
    .tariel-body .doc-kv-value--blank {{
      background:
        linear-gradient(180deg, rgba(23, 50, 77, 0.02), rgba(23, 50, 77, 0.00)),
        #fff;
    }}
    .tariel-body .doc-blank-field,
    .tariel-body .doc-blank-multiline-field,
    .tariel-body .doc-sign-line {{
      display: block;
      width: 100%;
      margin: 0;
    }}
    .tariel-body .doc-blank-field {{
      min-height: 18px;
      border-bottom: 1px solid rgba(23, 50, 77, 0.18);
    }}
    .tariel-body .doc-blank-multiline-field {{
      min-height: 82px;
      border: 1px solid rgba(23, 50, 77, 0.12);
      border-radius: 14px;
      background:
        linear-gradient(180deg, rgba(23, 50, 77, 0.02), rgba(23, 50, 77, 0.00)),
        #fff;
    }}
    .tariel-body .doc-table {{
      border-collapse: separate;
      border-spacing: 0;
      border: 1px solid rgba(23, 50, 77, 0.10);
      border-radius: 18px;
      overflow: hidden;
      background: #fff;
    }}
    .tariel-body .doc-table th,
    .tariel-body .doc-table td {{
      border: 0;
      border-top: 1px solid rgba(23, 50, 77, 0.08);
      padding: 10px 11px;
      vertical-align: top;
    }}
    .tariel-body .doc-table tr:first-child th {{
      border-top: 0;
    }}
    .tariel-body .doc-table-head {{
      background: linear-gradient(180deg, rgba(23, 50, 77, 0.08), rgba(23, 50, 77, 0.04));
    }}
    .tariel-body .doc-table-head-copy {{
      margin: 0;
      color: var(--tariel-primary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-table-cell-copy {{
      margin: 0;
      color: #22303c;
      font-size: 11px;
      line-height: 1.55;
    }}
    .tariel-body .doc-table-cell--blank {{
      background: rgba(23, 50, 77, 0.015);
    }}
    .tariel-body .doc-table--evidence td:nth-child(4),
    .tariel-body .doc-table--measurement td:nth-child(3),
    .tariel-body .doc-table--findings td:nth-child(3),
    .tariel-body .doc-table--findings td:nth-child(4) {{
      min-height: 42px;
    }}
    .tariel-body .doc-narrative {{
      padding: 14px 16px;
      border: 1px solid rgba(23, 50, 77, 0.10);
      border-radius: 16px;
      background: #fbfcfd;
    }}
    .tariel-body .doc-narrative-copy {{
      margin: 0;
      color: #243240;
      font-size: 12px;
      line-height: 1.7;
    }}
    .tariel-body .doc-conclusion-panel {{
      display: grid;
      gap: 10px;
      padding: 16px;
      border: 1px solid rgba(23, 50, 77, 0.14);
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(23, 50, 77, 0.05), rgba(23, 50, 77, 0.01)),
        #fff;
    }}
    .tariel-body .doc-status-chip {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: fit-content;
      margin: 0;
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(159, 111, 47, 0.12);
      color: var(--tariel-primary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-status-chip--blank {{
      min-width: 120px;
      min-height: 14px;
      background: rgba(23, 50, 77, 0.05);
    }}
    .tariel-body .doc-conclusion-card {{
      padding: 12px 14px;
      border: 1px solid rgba(23, 50, 77, 0.10);
      border-radius: 14px;
      background: #fff;
    }}
    .tariel-body .doc-panel-title {{
      margin: 0 0 8px;
      color: var(--tariel-secondary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-panel-copy {{
      margin: 0;
      color: #22303c;
      font-size: 12px;
      line-height: 1.65;
    }}
    .tariel-body .doc-signature-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .tariel-body .doc-signature-card {{
      padding: 14px 14px 12px;
      border: 1px solid rgba(23, 50, 77, 0.10);
      border-radius: 16px;
      background: #fff;
    }}
    .tariel-body .doc-sign-role {{
      margin: 0 0 10px;
      color: var(--tariel-secondary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .tariel-body .doc-sign-line {{
      min-height: 18px;
      margin-bottom: 7px;
      border-bottom: 1px solid rgba(23, 50, 77, 0.26);
    }}
    .tariel-body .doc-sign-name {{
      margin: 0;
      color: #22303c;
      font-size: 12px;
      min-height: 18px;
    }}
    .tariel-body .doc-sign-detail {{
      margin: 6px 0 0;
      color: var(--tariel-secondary);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 10px;
      line-height: 1.5;
      min-height: 14px;
    }}
    @media print {{
      .tariel-body .doc-signature-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
  </style>
</head>
<body>
  <div class="tariel-header">{cabecalho}</div>
  <div class="tariel-footer">{rodape}</div>
  {watermark_html}
  <main class="tariel-doc">
    <section class="tariel-body">{body_html}{verification_html}</section>
  </main>
</body>
</html>
"""
    return html_doc


def _texto_plano_doc(node: Any, dados_formulario: dict[str, Any]) -> str:
    if isinstance(node, dict):
        tipo = str(node.get("type") or "")
        if tipo == "text":
            return REGEX_PLACEHOLDER.sub(
                lambda m: _resolver_placeholder(str(m.group(1) or ""), dados_formulario),
                str(node.get("text") or ""),
            )
        if tipo == "placeholder":
            attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
            raw = str(attrs.get("raw") or "")
            if not raw:
                raw = f"{attrs.get('mode') or 'token'}:{attrs.get('key') or ''}"
            return _resolver_placeholder(raw, dados_formulario)
        content = node.get("content")
        if isinstance(content, list):
            return " ".join(_texto_plano_doc(item, dados_formulario) for item in content)
        return ""
    if isinstance(node, list):
        return " ".join(_texto_plano_doc(item, dados_formulario) for item in node)
    return ""


def _latin1_text(value: Any) -> str:
    return str(value or "").encode("latin-1", errors="replace").decode("latin-1")


def _render_fpdf_table(
    pdf: FPDF,
    *,
    rows: list[list[str]],
    headers: list[str] | None = None,
    col_widths: tuple[float, ...] | None = None,
) -> None:
    if not rows and not headers:
        return

    first_row = rows[0] if rows else []
    column_count = len(headers if headers is not None else first_row)
    if column_count <= 0:
        return
    if col_widths is None:
        base_width = pdf.epw / max(1, column_count)
        col_widths = tuple(base_width for _ in range(column_count))

    with pdf.table(
        width=pdf.epw,
        col_widths=col_widths,
        line_height=6,
        first_row_as_headings=bool(headers),
        text_align="LEFT",
        v_align="TOP",
    ) as table:
        if headers:
            heading_row = table.row()
            for header in headers:
                heading_row.cell(_latin1_text(header))
        for row in rows:
            table_row = table.row()
            for cell in row:
                table_row.cell(_latin1_text(cell or ""))


def _render_fpdf_narrative_panel(
    pdf: FPDF,
    *,
    text: str,
    blank: bool = False,
) -> None:
    pdf.set_fill_color(248, 250, 251)
    pdf.set_draw_color(204, 214, 222)
    pdf.set_text_color(36, 50, 63)
    pdf.set_font("helvetica", "", 10)
    content = _latin1_text(text if not blank else "")
    if blank:
        content = "\n\n\n"
    pdf.multi_cell(
        0,
        6,
        content,
        border=1,
        fill=True,
        padding=3,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )


def _render_fpdf_signature_block(
    pdf: FPDF,
    *,
    items: list[dict[str, Any]],
) -> None:
    for item in items:
        pdf.set_draw_color(204, 214, 222)
        pdf.set_text_color(96, 114, 132)
        pdf.set_font("helvetica", "B", 10)
        pdf.multi_cell(
            0,
            5,
            _latin1_text(str(item.get("role") or "")),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        x_inicio = pdf.get_x()
        y_inicio = pdf.get_y() + 8
        pdf.line(x_inicio, y_inicio, x_inicio + pdf.epw * 0.48, y_inicio)
        pdf.ln(10)
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(33, 48, 60)
        pdf.multi_cell(
            0,
            5,
            _latin1_text(str(item.get("name") or "")),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        details = " | ".join(
            part
            for part in [
                str(item.get("detail") or "").strip(),
                str(item.get("date") or "").strip(),
            ]
            if part
        )
        pdf.set_text_color(96, 114, 132)
        pdf.set_font("helvetica", "", 9)
        pdf.multi_cell(
            0,
            5,
            _latin1_text(details),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(4)


def _render_fpdf_document_block(pdf: FPDF, block: dict[str, Any]) -> None:
    block_type = str(block.get("type") or "").strip()
    if block_type == "kv_grid":
        rows = [
            [str(row.get("label") or ""), str(row.get("value") or "")]
            for row in list(block.get("rows") or [])
        ]
        _render_fpdf_table(
            pdf,
            rows=rows,
            headers=None,
            col_widths=(pdf.epw * 0.34, pdf.epw * 0.66),
        )
        return
    if block_type == "table":
        rows = [
            [str(cell.get("text") or "") for cell in list(row or [])]
            for row in list(block.get("rows") or [])
        ]
        _render_fpdf_table(
            pdf,
            rows=rows,
            headers=[str(label or "") for label in list(block.get("headers") or [])],
        )
        return
    if block_type == "narrative":
        _render_fpdf_narrative_panel(
            pdf,
            text=str(block.get("text") or ""),
            blank=bool(block.get("blank")),
        )
        return
    if block_type == "conclusion_panel":
        rows = list(block.get("rows") or [])
        status_row = next(
            (row for row in rows if str(row.get("label") or "").lower().startswith("status")),
            None,
        )
        if status_row is not None:
            pdf.set_fill_color(243, 246, 248)
            pdf.set_text_color(23, 50, 77)
            pdf.set_font("helvetica", "B", 10)
            pdf.multi_cell(
                0,
                6,
                _latin1_text(str(status_row.get("value") or "") or "Status tecnico"),
                border=1,
                fill=True,
                padding=2,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.ln(2)
        for row in rows:
            if row is status_row:
                continue
            pdf.set_text_color(96, 114, 132)
            pdf.set_font("helvetica", "B", 9)
            pdf.multi_cell(
                0,
                5,
                _latin1_text(str(row.get("label") or "")),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            _render_fpdf_narrative_panel(
                pdf,
                text=str(row.get("value") or ""),
                blank=bool(row.get("blank")),
            )
            pdf.ln(2)
        return
    if block_type == "signature_block":
        _render_fpdf_signature_block(
            pdf,
            items=list(block.get("items") or []),
        )


def _gerar_pdf_fallback_documental(
    *,
    payload: dict[str, Any],
    public_verification: dict[str, Any] | None = None,
) -> bytes:
    projection = payload.get("document_projection") if isinstance(payload.get("document_projection"), dict) else {}
    view_model = build_catalog_document_view_model(
        payload,
        audience=str(projection.get("audience") or "client"),
        render_mode=str(payload.get("render_mode") or projection.get("render_mode") or ""),
    )
    if not bool(view_model.get("modeled")):
        raise ValueError("Payload insuficiente para fallback documental estruturado.")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(_latin1_text(view_model.get("title") or "Laudo Tecnico Tariel"))
    pdf.set_author("Tariel.ia")
    pdf.add_page()

    pdf.set_draw_color(204, 214, 222)
    pdf.set_fill_color(243, 246, 248)
    pdf.set_text_color(96, 114, 132)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(
        0,
        7,
        _latin1_text(view_model.get("eyebrow") or "Tariel | Documento Tecnico"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(1)

    pdf.set_text_color(23, 50, 77)
    pdf.set_font("helvetica", "B", 18)
    pdf.multi_cell(
        0,
        9,
        _latin1_text(view_model.get("title") or "Laudo Tecnico Tariel"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    subtitle = str(view_model.get("subtitle") or "").strip()
    if subtitle:
        pdf.set_text_color(96, 114, 132)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(
            0,
            6,
            _latin1_text(subtitle),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    identity_items = [str(item or "").strip() for item in list(view_model.get("identity_items") or []) if str(item or "").strip()]
    if identity_items:
        pdf.ln(2)
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(96, 114, 132)
        pdf.multi_cell(
            0,
            5,
            _latin1_text(" | ".join(identity_items)),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    opening_text = str(view_model.get("opening_text") or "").strip()
    if opening_text:
        pdf.ln(3)
        _render_fpdf_narrative_panel(pdf, text=opening_text, blank=False)

    for section in list(view_model.get("sections") or []):
        pdf.ln(4)
        pdf.set_text_color(23, 50, 77)
        pdf.set_font("helvetica", "B", 12)
        pdf.multi_cell(
            0,
            7,
            _latin1_text(str(section.get("title") or "Secao Tecnica")),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        intro = str(section.get("intro") or "").strip()
        if intro:
            pdf.set_text_color(96, 114, 132)
            pdf.set_font("helvetica", "", 9)
            pdf.multi_cell(
                0,
                5,
                _latin1_text(intro),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        for block in list(section.get("blocks") or []):
            pdf.set_font("helvetica", "", 10)
            pdf.set_text_color(36, 50, 63)
            _render_fpdf_document_block(pdf, block)
            pdf.ln(2)

    verification = public_verification if isinstance(public_verification, dict) else {}
    verification_url = str(verification.get("verification_url") or "").strip()
    verification_hash = str(verification.get("codigo_hash") or "").strip()
    qr_temp_path: str | None = None
    if verification_url and verification_hash:
        pdf.ln(6)
        pdf.set_text_color(23, 50, 77)
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 7, "Verificacao Publica", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(
            0,
            6,
            _latin1_text(f"Hash: {verification_hash}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.multi_cell(
            0,
            6,
            _latin1_text(f"URL: {verification_url}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        qr_bytes = build_public_verification_qr_png_bytes(
            str(verification.get("qr_payload") or verification_url)
        )
        if qr_bytes:
            qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            qr_temp.write(qr_bytes)
            qr_temp.flush()
            qr_temp.close()
            qr_temp_path = qr_temp.name
            pdf.ln(2)
            pdf.image(qr_temp_path, w=34, h=34)

    raw = pdf.output()
    if qr_temp_path:
        try:
            os.remove(qr_temp_path)
        except OSError:
            logger.debug("Falha ao remover QR temporario do fallback PDF.", exc_info=True)
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, bytearray):
        return bytes(raw)
    return str(raw).encode("latin-1", errors="replace")


def _gerar_pdf_fallback_texto(
    *,
    documento_editor_json: dict[str, Any] | None,
    dados_formulario: dict[str, Any] | None,
    public_verification: dict[str, Any] | None = None,
) -> bytes:
    doc_payload = normalizar_documento_editor(documento_editor_json)
    dados = dados_formulario if isinstance(dados_formulario, dict) else {}
    view_model = build_catalog_document_view_model(dados, audience="client")
    if bool(view_model.get("modeled")):
        try:
            return _gerar_pdf_fallback_documental(
                payload=dados,
                public_verification=public_verification,
            )
        except Exception:
            logger.warning(
                "Falha ao montar fallback documental estruturado. Aplicando fallback textual simples.",
                exc_info=True,
            )

    doc = doc_payload.get("doc") if isinstance(doc_payload.get("doc"), dict) else {}
    texto = _texto_plano_doc(doc, dados).strip() or "Template sem conteúdo renderizável."

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 8, "Documento Tecnico Tariel", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 6, _latin1_text(texto))
    verification = public_verification if isinstance(public_verification, dict) else {}
    verification_url = str(verification.get("verification_url") or "").strip()
    verification_hash = str(verification.get("codigo_hash") or "").strip()
    qr_temp_path: str | None = None
    if verification_url and verification_hash:
        pdf.ln(6)
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 7, "Verificacao Publica", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(
            0,
            6,
            _latin1_text(f"Hash: {verification_hash}"),
        )
        pdf.multi_cell(
            0,
            6,
            _latin1_text(f"URL: {verification_url}"),
        )
        qr_bytes = build_public_verification_qr_png_bytes(
            str(verification.get("qr_payload") or verification_url)
        )
        if qr_bytes:
            qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            qr_temp.write(qr_bytes)
            qr_temp.flush()
            qr_temp.close()
            qr_temp_path = qr_temp.name
            pdf.ln(2)
            pdf.image(qr_temp_path, w=34, h=34)
    raw = pdf.output()
    if qr_temp_path:
        try:
            os.remove(qr_temp_path)
        except OSError:
            logger.debug("Falha ao remover QR temporario do fallback PDF.", exc_info=True)
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, bytearray):
        return bytes(raw)
    return str(raw).encode("latin-1", errors="replace")


async def gerar_pdf_html_playwright(
    *,
    html_documento: str,
    orientation: str = "portrait",
    margens_mm: dict[str, int] | None = None,
) -> bytes:
    from playwright.async_api import async_playwright

    margens = margens_mm or {"top": 18, "right": 14, "bottom": 18, "left": 14}
    async with medir_operacao_async(
        "pdf",
        "template_editor_word.gerar_pdf_html_playwright",
        detail={
            "orientation": str(orientation or "portrait").lower(),
            "html_chars": len(html_documento or ""),
        },
    ):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                pagina = await browser.new_page()
                await pagina.set_content(html_documento, wait_until="networkidle")
                pdf_bytes = await pagina.pdf(
                    format="A4",
                    landscape=str(orientation or "").lower() == "landscape",
                    print_background=True,
                    prefer_css_page_size=True,
                    margin={
                        "top": f"{int(margens.get('top', 18))}mm",
                        "right": f"{int(margens.get('right', 14))}mm",
                        "bottom": f"{int(margens.get('bottom', 18))}mm",
                        "left": f"{int(margens.get('left', 14))}mm",
                    },
                )
                return pdf_bytes
            finally:
                await browser.close()


async def gerar_pdf_editor_rico_bytes(
    *,
    documento_editor_json: dict[str, Any] | None,
    estilo_json: dict[str, Any] | None,
    assets_json: Any,
    dados_formulario: dict[str, Any] | None,
    public_verification: dict[str, Any] | None = None,
) -> bytes:
    async with medir_operacao_async(
        "template",
        "template_editor_word.gerar_pdf_editor_rico_bytes",
        detail={
            "assets_count": len(assets_json) if isinstance(assets_json, list) else 0,
            "dados_formulario_keys": len(dados_formulario or {}),
        },
    ):
        estilo = normalizar_estilo_editor(estilo_json)
        html_doc = montar_html_documento_editor(
            documento_editor_json=documento_editor_json,
            estilo_json=estilo,
            assets_json=assets_json,
            dados_formulario=dados_formulario,
            public_verification=public_verification,
        )
        try:
            return await gerar_pdf_html_playwright(
                html_documento=html_doc,
                orientation=str(estilo["pagina"]["orientation"]),
                margens_mm=estilo["pagina"]["margens_mm"],
            )
        except Exception:
            logger.warning(
                "Falha no Playwright para editor rico. Aplicando fallback textual.",
                exc_info=True,
            )
            return _gerar_pdf_fallback_texto(
                documento_editor_json=documento_editor_json,
                dados_formulario=dados_formulario,
                public_verification=public_verification,
            )


def gerar_pdf_base_placeholder_editor(
    *,
    empresa_id: int,
    codigo_template: str,
    versao: int,
    titulo: str = "Template A4 em branco",
) -> str:
    with medir_operacao(
        "pdf",
        "template_editor_word.gerar_pdf_base_placeholder_editor",
        detail={
            "empresa_id": int(empresa_id),
            "codigo_template": normalizar_codigo_template(codigo_template),
            "versao": int(versao),
        },
    ):
        pdf = FPDF(unit="mm", format="A4")
        pdf.add_page()
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(
            0,
            10,
            titulo[:120].encode("latin-1", errors="replace").decode("latin-1"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(
            0,
            6,
            "Base inicial do editor rico Tariel.ia. Este PDF sera substituido por snapshot na publicacao.",
        )
        raw = pdf.output()
        if isinstance(raw, bytes):
            conteudo = raw
        elif isinstance(raw, bytearray):
            conteudo = bytes(raw)
        else:
            conteudo = str(raw).encode("latin-1", errors="replace")
        return salvar_pdf_template_base(
            conteudo,
            empresa_id=empresa_id,
            codigo_template=normalizar_codigo_template(codigo_template),
            versao=versao,
        )


def salvar_snapshot_editor_como_pdf_base(
    *,
    pdf_bytes: bytes,
    empresa_id: int,
    codigo_template: str,
    versao: int,
) -> str:
    if not pdf_bytes:
        raise ValueError("Snapshot PDF vazio.")
    _ = PdfReader(io.BytesIO(pdf_bytes))
    return salvar_pdf_template_base(
        pdf_bytes,
        empresa_id=empresa_id,
        codigo_template=normalizar_codigo_template(codigo_template),
        versao=versao,
    )


def salvar_asset_editor_template(
    *,
    empresa_id: int,
    template_id: int,
    filename: str,
    mime_type: str,
    conteudo: bytes,
) -> dict[str, Any]:
    with medir_operacao(
        "template",
        "template_editor_word.salvar_asset_editor_template",
        detail={
            "empresa_id": int(empresa_id),
            "template_id": int(template_id),
            "mime_type": str(mime_type or "").strip().lower(),
            "bytes": len(conteudo or b""),
        },
    ):
        mime = str(mime_type or "").strip().lower()
        if mime not in MIME_IMAGEM_PERMITIDO:
            raise ValueError("Formato de imagem não suportado. Use PNG, JPG ou WEBP.")
        if not conteudo:
            raise ValueError("Arquivo de imagem vazio.")
        if len(conteudo) > MAX_ASSET_BYTES:
            raise ValueError("Imagem excede o limite de 5 MB.")

        pasta = (_DIR_EDITOR_ASSETS / f"empresa_{int(empresa_id)}" / f"template_{int(template_id)}").resolve()
        pasta.mkdir(parents=True, exist_ok=True)

        asset_id = os.urandom(8).hex()
        ext = MIME_IMAGEM_PERMITIDO[mime]
        nome_limpo = re.sub(r"[^A-Za-z0-9._\- ]+", "_", Path(filename or "imagem").name)[:120] or "imagem"
        caminho = (pasta / f"{asset_id}{ext}").resolve()
        caminho.write_bytes(conteudo)

        return {
            "id": asset_id,
            "filename": nome_limpo,
            "mime_type": mime,
            "path": str(caminho),
            "size_bytes": len(conteudo),
            "created_em": _agora_iso(),
        }


def obter_asset_editor_por_id(assets_json: Any, asset_id: str) -> dict[str, Any] | None:
    asset_id_limpo = str(asset_id or "").strip()
    for item in _normalizar_assets(assets_json):
        if item["id"] == asset_id_limpo:
            return item
    return None


__all__ = [
    "MODO_EDITOR_LEGADO",
    "MODO_EDITOR_RICO",
    "documento_editor_padrao",
    "estilo_editor_padrao",
    "normalizar_modo_editor",
    "normalizar_documento_editor",
    "normalizar_estilo_editor",
    "montar_html_documento_editor",
    "gerar_pdf_editor_rico_bytes",
    "gerar_pdf_base_placeholder_editor",
    "salvar_snapshot_editor_como_pdf_base",
    "salvar_asset_editor_template",
    "obter_asset_editor_por_id",
]
