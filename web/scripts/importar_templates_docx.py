from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DIR_PROJETO = Path(__file__).resolve().parents[1]
if str(DIR_PROJETO) not in sys.path:
    sys.path.insert(0, str(DIR_PROJETO))

from sqlalchemy import func  # noqa: E402

from app.domains.revisor.templates_laudo_support import (  # noqa: E402
    STATUS_TEMPLATE_ARQUIVADO,
    STATUS_TEMPLATE_ATIVO,
    STATUS_TEMPLATE_EM_TESTE,
    STATUS_TEMPLATE_LEGADO,
    STATUS_TEMPLATE_RASCUNHO,
    label_status_template,
    payload_template_auditoria,
    rebaixar_templates_ativos_mesmo_codigo,
    registrar_auditoria_templates,
    resolver_status_template_ativo,
)
from app.shared.database import SessaoLocal, TemplateLaudo, Usuario, inicializar_banco  # noqa: E402
from nucleo.template_editor_word import (  # noqa: E402
    MODO_EDITOR_RICO,
    estilo_editor_padrao,
    gerar_pdf_base_placeholder_editor,
    importar_docx_para_documento_editor,
    salvar_fonte_docx_template,
)
from nucleo.template_laudos import normalizar_codigo_template  # noqa: E402


STATUSS_VALIDOS = {
    STATUS_TEMPLATE_RASCUNHO,
    STATUS_TEMPLATE_EM_TESTE,
    STATUS_TEMPLATE_ATIVO,
    STATUS_TEMPLATE_LEGADO,
    STATUS_TEMPLATE_ARQUIVADO,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa arquivos DOCX existentes para a biblioteca de templates Word da mesa avaliadora.",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="E-mail do revisor dono da importação.",
    )
    parser.add_argument(
        "--status",
        default=STATUS_TEMPLATE_RASCUNHO,
        choices=sorted(STATUSS_VALIDOS),
        help="Ciclo inicial do template. Padrão: rascunho.",
    )
    parser.add_argument(
        "--ativo",
        action="store_true",
        help="Marca cada template importado como ativo no respectivo código.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma a operação sem prompt interativo.",
    )
    parser.add_argument(
        "arquivos",
        nargs="+",
        help="Caminhos dos arquivos .docx a importar.",
    )
    return parser


def _resolver_usuario(email: str) -> Usuario | None:
    with SessaoLocal() as banco:
        return banco.query(Usuario).filter(Usuario.email == str(email or "").strip().lower()).first()


def _normalizar_nome_template(caminho: Path) -> str:
    base = re.sub(r"(?i)[ _-]*editavel$", "", caminho.stem).strip(" _-")
    base = re.sub(r"[_-]+", " ", base).strip()
    return base[:180] or caminho.stem[:180] or "Template importado"


def _normalizar_codigo_arquivo(caminho: Path) -> str:
    base = re.sub(r"(?i)[ _-]*editavel$", "", caminho.stem).strip(" _-")
    return normalizar_codigo_template(base)


def _proxima_versao(banco, *, empresa_id: int, codigo_template: str) -> int:
    maior = (
        banco.query(func.max(TemplateLaudo.versao))
        .filter(
            TemplateLaudo.empresa_id == int(empresa_id),
            TemplateLaudo.codigo_template == str(codigo_template or ""),
        )
        .scalar()
    )
    return int(maior or 0) + 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    email = str(args.email or "").strip().lower()
    if not email:
        parser.error("Informe --email.")

    arquivos = [Path(item).expanduser().resolve() for item in args.arquivos]
    for caminho in arquivos:
        if not caminho.exists() or not caminho.is_file():
            print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
            return 1
        if caminho.suffix.lower() != ".docx":
            print(f"Arquivo inválido (use .docx): {caminho}", file=sys.stderr)
            return 1

    usuario = _resolver_usuario(email)
    if usuario is None:
        print(f"Revisor não encontrado: {email}", file=sys.stderr)
        return 1

    status_template, ativo_template = resolver_status_template_ativo(
        args.status,
        ativo=bool(args.ativo),
    )

    if not args.yes:
        confirmacao = input(
            f"Importar {len(arquivos)} DOCX(s) para a biblioteca da empresa {usuario.empresa_id} usando {email}? [y/N]: "
        ).strip().lower()
        if confirmacao not in {"y", "yes", "s", "sim"}:
            print("Operação cancelada.")
            return 1

    inicializar_banco()

    with SessaoLocal() as banco:
        usuario_db = banco.get(Usuario, int(usuario.id))
        if usuario_db is None:
            print("Usuário não encontrado no momento da importação.", file=sys.stderr)
            return 1

        importados: list[tuple[str, int, int]] = []
        for caminho in arquivos:
            nome_template = _normalizar_nome_template(caminho)
            codigo_template = _normalizar_codigo_arquivo(caminho)
            versao = _proxima_versao(
                banco,
                empresa_id=int(usuario_db.empresa_id),
                codigo_template=codigo_template,
            )

            if ativo_template:
                rebaixar_templates_ativos_mesmo_codigo(
                    banco,
                    empresa_id=int(usuario_db.empresa_id),
                    codigo_template=codigo_template,
                )

            conteudo = caminho.read_bytes()
            documento_editor = importar_docx_para_documento_editor(conteudo)
            arquivo_fonte = salvar_fonte_docx_template(
                empresa_id=int(usuario_db.empresa_id),
                codigo_template=codigo_template,
                versao=versao,
                filename=caminho.name,
                conteudo=conteudo,
            )
            caminho_pdf_base = gerar_pdf_base_placeholder_editor(
                empresa_id=int(usuario_db.empresa_id),
                codigo_template=codigo_template,
                versao=versao,
                titulo=nome_template,
            )

            template = TemplateLaudo(
                empresa_id=int(usuario_db.empresa_id),
                criado_por_id=int(usuario_db.id),
                nome=nome_template,
                codigo_template=codigo_template,
                versao=versao,
                ativo=ativo_template,
                modo_editor=MODO_EDITOR_RICO,
                status_template=status_template,
                arquivo_pdf_base=caminho_pdf_base,
                mapeamento_campos_json={},
                documento_editor_json=documento_editor,
                assets_json=[arquivo_fonte],
                estilo_json=estilo_editor_padrao(),
                observacoes=f"Importado de {caminho}",
            )
            banco.add(template)
            banco.flush()
            registrar_auditoria_templates(
                banco,
                usuario=usuario_db,
                acao="template_importado_docx_cli",
                resumo=f"Template DOCX {template.codigo_template} v{template.versao} importado via terminal.",
                detalhe=(
                    f"{template.nome} entrou como {label_status_template(template.status_template).lower()} "
                    "a partir de um DOCX existente."
                ),
                payload={
                    **payload_template_auditoria(template),
                    "origem": "importar_templates_docx.py",
                    "arquivo": str(caminho),
                },
            )
            importados.append((template.codigo_template, int(template.versao), int(template.id)))

        banco.commit()

    print("Importação concluída.")
    for codigo, versao, template_id in importados:
        print(f"- template_id={template_id} codigo={codigo} versao={versao}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
