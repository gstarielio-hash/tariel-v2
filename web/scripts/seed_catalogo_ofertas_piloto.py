from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Final

DIR_PROJETO = Path(__file__).resolve().parents[1]
if str(DIR_PROJETO) not in sys.path:
    sys.path.insert(0, str(DIR_PROJETO))

from sqlalchemy import select  # noqa: E402

from app.domains.admin.services import (  # noqa: E402
    importar_familia_canonica_para_catalogo,
    upsert_oferta_comercial_familia,
)
from app.shared.database import NivelAcesso, SessaoLocal, Usuario, inicializar_banco  # noqa: E402


@dataclass(frozen=True)
class OfertaPiloto:
    family_key: str
    nome_oferta: str
    descricao_comercial: str
    pacote_comercial: str
    prazo_padrao_dias: int
    material_real_status: str
    escopo_comercial: tuple[str, ...]
    insumos_minimos: tuple[str, ...]
    exclusoes: tuple[str, ...]
    variantes: tuple[dict[str, str], ...]


OFERTAS_PILOTO: Final[tuple[OfertaPiloto, ...]] = (
    OfertaPiloto(
        family_key="nr13_inspecao_vaso_pressao",
        nome_oferta="NR13 · Vaso de Pressao Premium",
        descricao_comercial=(
            "Oferta piloto para inspeção de vasos de pressão com leitura executiva do ativo, "
            "consolidação de evidências, parecer técnico auditável e emissão final versionada."
        ),
        pacote_comercial="premium_ativos_pressurizados",
        prazo_padrao_dias=5,
        material_real_status="parcial",
        escopo_comercial=(
            "Inspecao tecnica do vaso com rastreabilidade do ativo e do escopo contratado.",
            "Consolidacao de evidencias fotograficas, documentais e apontamentos da Mesa.",
            "Emissao do documento final versionado com conclusao tecnica e historico de aprovacao.",
        ),
        insumos_minimos=(
            "Prontuario ou documentos basicos do vaso disponiveis para confronto.",
            "Acesso operacional ao equipamento e acompanhamento do responsavel local.",
            "Identificacao do ativo, placa e condicoes de seguranca para a coleta.",
        ),
        exclusoes=(
            "Nao inclui reparo mecanico, END complementar ou adequacao fisica do equipamento.",
            "Nao inclui reconstituicao completa de prontuario fora do escopo contratado.",
        ),
        variantes=(
            {
                "variant_key": "inicial",
                "nome_exibicao": "Inspecao inicial",
                "uso_recomendado": "Primeira liberacao tecnica do ativo ou entrada do equipamento no controle Tariel.",
            },
            {
                "variant_key": "periodica",
                "nome_exibicao": "Inspecao periodica",
                "uso_recomendado": "Ciclo recorrente com comparacao historica e manutencao do prontuario do ativo.",
            },
            {
                "variant_key": "extraordinaria",
                "nome_exibicao": "Inspecao extraordinaria",
                "uso_recomendado": "Evento fora da rotina, parada, ocorrencia ou mudanca relevante de condicao operacional.",
            },
            {
                "variant_key": "documental",
                "nome_exibicao": "Revisao documental",
                "uso_recomendado": "Quando o foco for acervo, prontuario, pendencias documentais e trilha de regularizacao.",
            },
        ),
    ),
    OfertaPiloto(
        family_key="nr13_inspecao_caldeira",
        nome_oferta="NR13 · Caldeira Premium",
        descricao_comercial=(
            "Pacote comercial para inspeção de caldeiras com leitura operacional do conjunto, "
            "priorização de riscos de operação e emissão final preparada para rito interno e comercial."
        ),
        pacote_comercial="premium_caldeiras_nr13",
        prazo_padrao_dias=7,
        material_real_status="parcial",
        escopo_comercial=(
            "Inspecao da caldeira, entorno operacional e dispositivos de seguranca dentro do recorte contratado.",
            "Consolidacao de memoria tecnica, evidencias obrigatorias e parecer da Mesa para emissao.",
            "Versao final do laudo com estrutura premium para cliente, revisor e acervo institucional.",
        ),
        insumos_minimos=(
            "Dados basicos do equipamento e documentos disponiveis para conferência.",
            "Acesso ao local com condicoes seguras para coleta e registro.",
            "Contato do responsavel operacional para alinhamento de escopo, pendencias e devolutiva.",
        ),
        exclusoes=(
            "Nao inclui projeto de adequacao, reforma estrutural ou ensaio adicional nao contratado.",
            "Nao inclui treinamento operacional ou reconstituicao integral de documentacao legada.",
        ),
        variantes=(
            {
                "variant_key": "inicial",
                "nome_exibicao": "Inspecao inicial",
                "uso_recomendado": "Entrada da caldeira na biblioteca premium com baseline tecnico e operacional.",
            },
            {
                "variant_key": "periodica",
                "nome_exibicao": "Inspecao periodica",
                "uso_recomendado": "Rotina recorrente de manutencao da conformidade e rastreabilidade da operacao.",
            },
            {
                "variant_key": "extraordinaria",
                "nome_exibicao": "Inspecao extraordinaria",
                "uso_recomendado": "Eventos anormais, alteracoes de processo, paradas ou ocorrencias relevantes.",
            },
            {
                "variant_key": "prontuario",
                "nome_exibicao": "Refino de prontuario",
                "uso_recomendado": "Quando o cliente precisa tratar pendencias documentais antes da emissao plena.",
            },
        ),
    ),
    OfertaPiloto(
        family_key="nr10_inspecao_instalacoes_eletricas",
        nome_oferta="NR10 · Instalacoes Eletricas Executivo",
        descricao_comercial=(
            "Oferta comercial de entrada para inspeções NR10 com foco em clareza de escopo, "
            "leitura executiva das inconformidades e documento final pronto para apresentação ao cliente."
        ),
        pacote_comercial="executivo_nr10",
        prazo_padrao_dias=6,
        material_real_status="sintetico",
        escopo_comercial=(
            "Inspecao tecnica das instalacoes eletricas dentro do recorte acordado com o cliente.",
            "Levantamento de evidencias criticas, inconformidades e registros de risco prioritario.",
            "Emissao de laudo final com conclusao tecnica objetiva e orientacao de priorizacao.",
        ),
        insumos_minimos=(
            "Escopo eletrico delimitado antes da visita ou da revisao documental.",
            "Acesso aos quadros, identificacoes e documentos minimos disponiveis.",
            "Responsavel local para validar os limites da coleta e do parecer final.",
        ),
        exclusoes=(
            "Nao inclui projeto eletrico, adequacao de instalacoes ou execucao de correcoes.",
            "Nao inclui medições ou ensaios complementares fora do pacote contratado.",
        ),
        variantes=(
            {
                "variant_key": "campo",
                "nome_exibicao": "Inspecao de campo",
                "uso_recomendado": "Levantamento presencial de instalacoes, quadros e condicoes aparentes.",
            },
            {
                "variant_key": "documental",
                "nome_exibicao": "Revisao documental",
                "uso_recomendado": "Quando o cliente precisa revisar acervo tecnico e alinhamento do recorte regulatorio.",
            },
            {
                "variant_key": "priorizacao",
                "nome_exibicao": "Leitura executiva",
                "uso_recomendado": "Sintese comercial para cliente que precisa enxergar o que corrige primeiro.",
            },
        ),
    ),
)


def _resolver_admin_id(banco) -> int | None:
    admin = banco.scalar(
        select(Usuario)
        .where(Usuario.nivel_acesso == int(NivelAcesso.DIRETORIA))
        .order_by(Usuario.id.asc())
    )
    return int(admin.id) if admin is not None else None


def _texto_linhas(itens: tuple[str, ...]) -> str:
    return "\n".join(itens)


def main() -> int:
    inicializar_banco()

    with SessaoLocal() as banco:
        admin_id = _resolver_admin_id(banco)

        for oferta in OFERTAS_PILOTO:
            importar_familia_canonica_para_catalogo(
                banco,
                family_key=oferta.family_key,
                status_catalogo="publicado",
                criado_por_id=admin_id,
            )
            upsert_oferta_comercial_familia(
                banco,
                family_key=oferta.family_key,
                nome_oferta=oferta.nome_oferta,
                descricao_comercial=oferta.descricao_comercial,
                pacote_comercial=oferta.pacote_comercial,
                prazo_padrao_dias=oferta.prazo_padrao_dias,
                ativo_comercial=True,
                versao_oferta=1,
                material_real_status=oferta.material_real_status,
                escopo_comercial_text=_texto_linhas(oferta.escopo_comercial),
                insumos_minimos_text=_texto_linhas(oferta.insumos_minimos),
                exclusoes_text=_texto_linhas(oferta.exclusoes),
                variantes_comerciais_text=json.dumps(list(oferta.variantes), ensure_ascii=False),
                criado_por_id=admin_id,
            )

        banco.commit()

    print("Ofertas piloto do catalogo comercial atualizadas.")
    for oferta in OFERTAS_PILOTO:
        print(f"- {oferta.family_key} -> {oferta.nome_oferta} [{oferta.pacote_comercial}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
