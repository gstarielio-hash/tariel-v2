from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.shared.database as banco_dados  # noqa: E402
from app.domains.chat.report_pack_helpers import atualizar_report_pack_draft_laudo  # noqa: E402
from app.shared.database import (  # noqa: E402
    AprendizadoVisualIa,
    Empresa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)

_PREVIEW = "Pré-laudo canônico mobile"
_SETOR = "NR35 Linha de Vida"
_FAMILY_KEY = "nr35_inspecao_linha_de_vida"
_TEMPLATE_KEY = "nr35_linha_vida"
_STARTED_AT = "2026-04-13T21:30:00-03:00"
_CAPTURED_AT = "2026-04-13T21:32:00-03:00"
_EXAMPLE_PATH = (
    ROOT
    / "canonical_docs"
    / "family_schemas"
    / f"{_FAMILY_KEY}.laudo_output_exemplo.json"
)
_FIXTURE_DIR = (
    ROOT
    / ".."
    / ".tmp_online"
    / "vision-fixtures"
    / "industrial_inspection_2026_04_13"
    / "nr35"
).resolve()
_NR35_FIXTURES = (
    (
        "nr35_01_visao_geral.jpg",
        "Vista geral da linha de vida",
        "Vista geral do ativo inspecionado.",
    ),
    (
        "nr35_02_ponto_superior_corrosao.jpg",
        "Ponto superior com corrosão inicial",
        "Corrosão inicial localizada no ponto superior do cabo de aço.",
    ),
    (
        "nr35_03_ponto_inferior_terminal.jpg",
        "Ponto inferior / terminal",
        "Terminal inferior e conjunto de fixação inferior sem deformação aparente.",
    ),
)


def _nr35_guided_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": "identificacao_laudo",
            "title": "Identificação do ativo e do laudo",
            "prompt": "Registre unidade, local, laudo e referência do fabricante.",
            "evidence_hint": "Unidade, local, laudo e fabricante.",
        },
        {
            "id": "contexto_vistoria",
            "title": "Contexto da vistoria",
            "prompt": "Confirme responsáveis, data e contexto operacional da inspeção.",
            "evidence_hint": "Responsáveis, data e objetivo da vistoria.",
        },
        {
            "id": "objeto_inspecao",
            "title": "Objeto da inspeção",
            "prompt": "Descreva a linha de vida e o escopo da vistoria.",
            "evidence_hint": "Tipo de sistema e escopo resumido.",
        },
        {
            "id": "componentes_inspecionados",
            "title": "Componentes inspecionados",
            "prompt": "Marque C, NC ou N/A para os componentes normativos.",
            "evidence_hint": "Fixação, cabo, esticador, sapatilha, olhal e grampos.",
        },
        {
            "id": "registros_fotograficos",
            "title": "Registros fotográficos",
            "prompt": "Anexe vista geral, ponto superior e ponto inferior.",
            "evidence_hint": "Vista geral, corrosão no topo e terminal inferior.",
        },
        {
            "id": "conclusao",
            "title": "Conclusão e próxima inspeção",
            "prompt": "Defina o status final e o encaminhamento técnico.",
            "evidence_hint": "Status final, justificativa e próxima ação.",
        },
    ]


def _resolve_inspector(banco, email: str) -> Usuario:
    usuario = banco.scalar(
        select(Usuario).where(
            Usuario.email == email,
            Usuario.ativo.is_(True),
        )
    )
    if usuario is None:
        raise RuntimeError(f"Inspetor do seed canônico nao encontrado: {email}")
    if int(usuario.nivel_acesso or 0) != int(NivelAcesso.INSPETOR):
        raise RuntimeError(f"Usuario informado nao e inspetor: {email}")
    return usuario


def _ensure_demo_company_shape(banco, *, tenant_id: int) -> Empresa | None:
    empresa = banco.get(Empresa, tenant_id)
    if empresa is None:
        return None
    if not str(empresa.nome_fantasia or "").strip():
        empresa.nome_fantasia = "Empresa Demo (DEV)"
    if not str(empresa.cnpj or "").strip():
        empresa.cnpj = "00000000000000"
    return empresa


def _load_structured_payload() -> dict[str, object]:
    payload = json.loads(_EXAMPLE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("O exemplo canônico NR35 nao possui payload JSON valido.")
    return copy.deepcopy(payload)


def _ensure_seed_laudo(banco, *, inspector: Usuario) -> Laudo:
    laudo = banco.scalar(
        select(Laudo)
        .where(
            Laudo.usuario_id == inspector.id,
            Laudo.empresa_id == inspector.empresa_id,
            Laudo.primeira_mensagem == _PREVIEW,
        )
        .order_by(Laudo.id.asc())
    )
    if laudo is None:
        laudo = Laudo(
            empresa_id=inspector.empresa_id,
            usuario_id=inspector.id,
            setor_industrial=_SETOR,
            tipo_template=_TEMPLATE_KEY,
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem=_PREVIEW,
            parecer_ia="Caso seed local para smoke mobile do pré-laudo canônico.",
            modo_resposta="detalhado",
            custo_api_reais=Decimal("0.0000"),
        )
        banco.add(laudo)
        banco.flush()

    laudo.usuario_id = inspector.id
    laudo.empresa_id = inspector.empresa_id
    laudo.setor_industrial = _SETOR
    laudo.tipo_template = _TEMPLATE_KEY
    laudo.catalog_family_key = _FAMILY_KEY
    laudo.catalog_family_label = "NR-35 Inspeção de Linha de Vida"
    laudo.status_revisao = StatusRevisao.RASCUNHO.value
    laudo.primeira_mensagem = _PREVIEW
    laudo.parecer_ia = "Caso seed local para smoke mobile do pré-laudo canônico."
    laudo.modo_resposta = "detalhado"
    laudo.revisado_por = None
    laudo.motivo_rejeicao = None
    laudo.encerrado_pelo_inspetor_em = None
    laudo.reabertura_pendente_em = None
    laudo.reaberto_em = None
    laudo.entry_mode_preference = "auto_recommended"
    laudo.entry_mode_effective = "chat_first"
    laudo.entry_mode_reason = "default_product_fallback"
    laudo.dados_formulario = _load_structured_payload()
    laudo.guided_inspection_draft_json = None
    laudo.report_pack_draft_json = None
    return laudo


def _reset_case_thread(
    banco,
    *,
    laudo: Laudo,
    inspector: Usuario,
) -> dict[str, object]:
    banco.query(AprendizadoVisualIa).filter(
        AprendizadoVisualIa.laudo_id == int(laudo.id)
    ).delete(synchronize_session=False)
    banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == int(laudo.id)).delete(
        synchronize_session=False
    )
    banco.flush()

    def add_message(tipo: str, conteudo: str) -> MensagemLaudo:
        mensagem = MensagemLaudo(
            laudo_id=int(laudo.id),
            remetente_id=int(inspector.id)
            if tipo == TipoMensagem.HUMANO_INSP.value
            else None,
            tipo=tipo,
            conteudo=conteudo,
            lida=False,
            custo_api_reais=Decimal("0.0000"),
        )
        banco.add(mensagem)
        banco.flush()
        return mensagem

    msg_identificacao = add_message(
        TipoMensagem.HUMANO_INSP.value,
        "Unidade: Usina Orizona; Local: Orizona - GO | Escada de acesso ao elevador 01; "
        "Laudo inspecao: AT-IN-OZ-001-01-26; Fabricante: MC-CRMR-0032.",
    )
    msg_contexto = add_message(
        TipoMensagem.HUMANO_INSP.value,
        "Contratante: Caramuru Alimentos S/A; Contratada: ATY Service LTDA; "
        "Engenheiro: Gabriel Santos; Inspetor: inspetor@tariel.ia; Data: 2026-01-29. "
        "Inspeção periódica da linha de vida vertical LV-12 na moega 02.",
    )
    msg_objeto = add_message(
        TipoMensagem.HUMANO_INSP.value,
        "Linha de vida vertical da escada de acesso ao elevador 01. "
        "Escopo da inspeção: diagnóstico visual e funcional do sistema com foco em integridade e rastreabilidade.",
    )
    msg_componentes = add_message(
        TipoMensagem.HUMANO_INSP.value,
        "fixacao dos pontos: C; cabo de aco: NC; esticador: C; sapatilha: C; olhal: C; grampos: C. "
        "Detalhe: corrosao inicial no cabo de aco proximo ao ponto superior.",
    )
    image_messages = [
        add_message(TipoMensagem.HUMANO_INSP.value, "[imagem]"),
        add_message(TipoMensagem.HUMANO_INSP.value, "[imagem]"),
        add_message(TipoMensagem.HUMANO_INSP.value, "[imagem]"),
    ]
    msg_conclusao = add_message(
        TipoMensagem.HUMANO_INSP.value,
        "Status: Reprovado. Observacoes finais: linha de vida com corrosao inicial no cabo de aco "
        "proximo ao ponto superior. Bloquear o sistema ate substituicao do trecho comprometido e reinspecao.",
    )
    msg_ia = add_message(
        TipoMensagem.IA.value,
        "Pré-laudo canônico materializado para revisão no mobile com base no template NR35 e nas evidências do caso.",
    )

    return {
        "identificacao": msg_identificacao,
        "contexto": msg_contexto,
        "objeto": msg_objeto,
        "componentes": msg_componentes,
        "conclusao": msg_conclusao,
        "images": image_messages,
        "ia": msg_ia,
    }


def _register_visual_fixtures(
    banco,
    *,
    laudo: Laudo,
    inspector: Usuario,
    image_messages: list[MensagemLaudo],
) -> None:
    if len(image_messages) != len(_NR35_FIXTURES):
        raise RuntimeError("Quantidade de mensagens de imagem divergente do bundle NR35.")

    for message, (filename, title, summary) in zip(image_messages, _NR35_FIXTURES, strict=True):
        file_path = (_FIXTURE_DIR / filename).resolve()
        if not file_path.is_file():
            raise RuntimeError(f"Fixture visual NR35 nao encontrada: {file_path}")
        image_bytes = file_path.read_bytes()
        banco.add(
            AprendizadoVisualIa(
                empresa_id=int(inspector.empresa_id),
                laudo_id=int(laudo.id),
                mensagem_referencia_id=int(message.id),
                criado_por_id=int(inspector.id),
                setor_industrial=_SETOR,
                resumo=title,
                descricao_contexto=summary,
                correcao_inspetor="Registro fotográfico canônico validado para smoke mobile.",
                imagem_url=(
                    f"/static/uploads/aprendizados_ia/{int(inspector.empresa_id)}/"
                    f"{int(laudo.id)}/{filename}"
                ),
                imagem_nome_original=filename,
                imagem_mime_type="image/jpeg",
                imagem_sha256=hashlib.sha256(image_bytes).hexdigest(),
                caminho_arquivo=str(file_path),
            )
        )
    banco.flush()


def _build_guided_draft(case_messages: dict[str, object]) -> dict[str, object]:
    checklist = _nr35_guided_checklist()
    image_messages = [
        item for item in list(case_messages.get("images") or []) if isinstance(item, MensagemLaudo)
    ]
    msg_identificacao = case_messages["identificacao"]
    msg_contexto = case_messages["contexto"]
    msg_objeto = case_messages["objeto"]
    msg_componentes = case_messages["componentes"]
    msg_conclusao = case_messages["conclusao"]
    evidence_refs = [
        {
            "message_id": int(msg_identificacao.id),
            "step_id": "identificacao_laudo",
            "step_title": "Identificação do ativo e do laudo",
            "captured_at": msg_identificacao.criado_em.isoformat(),
            "evidence_kind": "chat_message",
            "attachment_kind": "none",
        },
        {
            "message_id": int(msg_contexto.id),
            "step_id": "contexto_vistoria",
            "step_title": "Contexto da vistoria",
            "captured_at": msg_contexto.criado_em.isoformat(),
            "evidence_kind": "chat_message",
            "attachment_kind": "none",
        },
        {
            "message_id": int(msg_objeto.id),
            "step_id": "objeto_inspecao",
            "step_title": "Objeto da inspeção",
            "captured_at": msg_objeto.criado_em.isoformat(),
            "evidence_kind": "chat_message",
            "attachment_kind": "none",
        },
        {
            "message_id": int(msg_componentes.id),
            "step_id": "componentes_inspecionados",
            "step_title": "Componentes inspecionados",
            "captured_at": msg_componentes.criado_em.isoformat(),
            "evidence_kind": "chat_message",
            "attachment_kind": "none",
        },
        {
            "message_id": int(image_messages[0].id),
            "step_id": "registros_fotograficos",
            "step_title": "Vista geral da linha de vida",
            "captured_at": _CAPTURED_AT,
            "evidence_kind": "chat_message",
            "attachment_kind": "image",
        },
        {
            "message_id": int(image_messages[1].id),
            "step_id": "registros_fotograficos",
            "step_title": "Ponto superior com corrosão inicial",
            "captured_at": _CAPTURED_AT,
            "evidence_kind": "chat_message",
            "attachment_kind": "image",
        },
        {
            "message_id": int(image_messages[2].id),
            "step_id": "registros_fotograficos",
            "step_title": "Ponto inferior / terminal",
            "captured_at": _CAPTURED_AT,
            "evidence_kind": "chat_message",
            "attachment_kind": "image",
        },
        {
            "message_id": int(msg_conclusao.id),
            "step_id": "conclusao",
            "step_title": "Conclusão e próxima inspeção",
            "captured_at": msg_conclusao.criado_em.isoformat(),
            "evidence_kind": "chat_message",
            "attachment_kind": "none",
        },
    ]
    return {
        "template_key": _TEMPLATE_KEY,
        "template_label": "NR-35 Linha de Vida",
        "started_at": _STARTED_AT,
        "current_step_index": len(checklist) - 1,
        "completed_step_ids": [item["id"] for item in checklist],
        "checklist": checklist,
        "evidence_bundle_kind": "case_thread",
        "evidence_refs": evidence_refs,
        "mesa_handoff": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Garante um caso NR35 com pré-laudo canônico materializado para smoke mobile."
    )
    parser.add_argument("--inspetor-email", default="inspetor@tariel.ia")
    args = parser.parse_args()

    with banco_dados.SessaoLocal() as banco:
        inspetor = _resolve_inspector(banco, args.inspetor_email)
        empresa = _ensure_demo_company_shape(banco, tenant_id=int(inspetor.empresa_id))
        laudo = _ensure_seed_laudo(banco, inspector=inspetor)
        case_messages = _reset_case_thread(banco, laudo=laudo, inspector=inspetor)
        _register_visual_fixtures(
            banco,
            laudo=laudo,
            inspector=inspetor,
            image_messages=list(case_messages["images"]),
        )
        laudo.guided_inspection_draft_json = _build_guided_draft(case_messages)
        payload = atualizar_report_pack_draft_laudo(banco=banco, laudo=laudo) or {}
        banco.commit()

    pre_laudo_document = payload.get("pre_laudo_document") if isinstance(payload, dict) else {}
    pre_laudo_summary = payload.get("pre_laudo_summary") if isinstance(payload, dict) else {}
    output = {
        "ok": True,
        "tenant_id": int(inspetor.empresa_id),
        "tenant_label": str(getattr(empresa, "nome_fantasia", "") or "").strip() or None,
        "inspetor_email": inspetor.email,
        "laudo_id": int(laudo.id),
        "preview": _PREVIEW,
        "template_key": _TEMPLATE_KEY,
        "family_key": _FAMILY_KEY,
        "case_lifecycle_hint": "laudo_em_coleta",
        "next_questions": list((pre_laudo_summary or {}).get("next_questions") or []),
        "document_sections": len(list((pre_laudo_document or {}).get("document_sections") or [])),
        "required_slots": len(list((pre_laudo_document or {}).get("required_slots") or [])),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
