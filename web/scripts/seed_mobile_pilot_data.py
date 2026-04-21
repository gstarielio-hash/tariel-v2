from __future__ import annotations

import argparse
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
from app.shared.database import (  # noqa: E402
    Empresa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from app.v2.mobile_organic_validation import (  # noqa: E402
    resolve_demo_mobile_organic_validation_targets,
)


_PREVIEW = "Mobile pilot V2 target"
_THREAD_MESSAGE = "Mensagem segura da mesa para o piloto mobile V2."


def _resolve_inspector(banco, email: str) -> Usuario:
    usuario = banco.scalar(
        select(Usuario).where(
            Usuario.email == email,
            Usuario.ativo.is_(True),
        )
    )
    if usuario is None:
        raise RuntimeError(f"Inspetor do piloto nao encontrado: {email}")
    if int(usuario.nivel_acesso or 0) != int(NivelAcesso.INSPETOR):
        raise RuntimeError(f"Usuario informado nao e inspetor: {email}")
    return usuario


def _resolve_reviewer(banco, *, tenant_id: int, preferred_email: str | None) -> Usuario:
    if preferred_email:
        usuario = banco.scalar(
            select(Usuario).where(
                Usuario.email == preferred_email,
                Usuario.empresa_id == tenant_id,
                Usuario.ativo.is_(True),
            )
        )
        if usuario is not None and int(usuario.nivel_acesso or 0) == int(NivelAcesso.REVISOR):
            return usuario

    usuario = banco.scalar(
        select(Usuario)
        .where(
            Usuario.empresa_id == tenant_id,
            Usuario.nivel_acesso == int(NivelAcesso.REVISOR),
            Usuario.ativo.is_(True),
        )
        .order_by(Usuario.id.asc())
        .limit(1)
    )
    if usuario is None:
        raise RuntimeError(f"Revisor do tenant demo nao encontrado: empresa_id={tenant_id}")
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
    if laudo is not None:
        laudo.status_revisao = StatusRevisao.AGUARDANDO.value
        return laudo

    laudo = Laudo(
        empresa_id=inspector.empresa_id,
        usuario_id=inspector.id,
        setor_industrial="Mobile Pilot V2",
        tipo_template="padrao",
        status_revisao=StatusRevisao.AGUARDANDO.value,
        codigo_hash=uuid.uuid4().hex,
        primeira_mensagem=_PREVIEW,
        parecer_ia="Laudo seed local para smoke mobile controlado.",
        modo_resposta="detalhado",
        custo_api_reais=Decimal("0.0000"),
    )
    banco.add(laudo)
    banco.flush()
    return laudo


def _ensure_thread_message(banco, *, laudo: Laudo, reviewer: Usuario) -> MensagemLaudo:
    mensagem = banco.scalar(
        select(MensagemLaudo)
        .where(
            MensagemLaudo.laudo_id == laudo.id,
            MensagemLaudo.tipo == TipoMensagem.HUMANO_ENG.value,
        )
        .order_by(MensagemLaudo.id.asc())
    )
    if mensagem is not None:
        if not str(mensagem.conteudo or "").strip():
            mensagem.conteudo = _THREAD_MESSAGE
        return mensagem

    mensagem = MensagemLaudo(
        laudo_id=laudo.id,
        remetente_id=reviewer.id,
        tipo=TipoMensagem.HUMANO_ENG.value,
        conteudo=_THREAD_MESSAGE,
        lida=False,
        custo_api_reais=Decimal("0.0000"),
    )
    banco.add(mensagem)
    banco.flush()
    return mensagem


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Garante dados minimos oficiais do piloto mobile V2 no tenant demo local."
    )
    parser.add_argument("--inspetor-email", default="inspetor@tariel.ia")
    parser.add_argument("--revisor-email", default="revisor@tariel.ia")
    args = parser.parse_args()

    with banco_dados.SessaoLocal() as banco:
        inspetor = _resolve_inspector(banco, args.inspetor_email)
        revisor = _resolve_reviewer(
            banco,
            tenant_id=int(inspetor.empresa_id),
            preferred_email=args.revisor_email,
        )
        empresa = _ensure_demo_company_shape(banco, tenant_id=int(inspetor.empresa_id))
        laudo = _ensure_seed_laudo(banco, inspector=inspetor)
        mensagem = _ensure_thread_message(banco, laudo=laudo, reviewer=revisor)
        banco.commit()

    targets = resolve_demo_mobile_organic_validation_targets(
        tenant_key=str(inspetor.empresa_id),
    )
    payload = {
        "ok": True,
        "tenant_id": int(inspetor.empresa_id),
        "tenant_label": str(getattr(empresa, "nome_fantasia", "") or "").strip() or None,
        "inspetor_email": inspetor.email,
        "revisor_email": revisor.email,
        "laudo_id": int(laudo.id),
        "mensagem_id": int(mensagem.id),
        "resolved_targets": {
            surface: [int(item) for item in items]
            for surface, items in targets.items()
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
