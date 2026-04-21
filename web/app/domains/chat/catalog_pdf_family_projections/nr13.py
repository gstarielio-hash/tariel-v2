from __future__ import annotations

from typing import Any

from app.domains.chat.catalog_pdf_templates import (
    _build_document_summary,
    _coerce_bool,
    _infer_nonconformity_flag,
    _normalize_operation_state,
    _pick_first_text,
    _pick_text_by_paths,
    _pick_value_by_paths,
    _resolve_conclusion_status,
    _set_block_fields_if_blank,
    _set_path_if_blank,
)
from app.shared.database import Laudo


def apply_nr13_projection(
    *,
    payload: dict[str, Any],
    existing_payload: dict[str, Any] | None,
    family_key: str,
    laudo: Laudo | None,
    location_hint: str | None,
    summary_hint: str | None,
    recommendation_hint: str | None,
    title_hint: str | None,
) -> None:
    if family_key not in {"nr13_inspecao_vaso_pressao", "nr13_inspecao_caldeira"}:
        return

    equipment_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.identificacao_do_vaso",
                "identificacao.identificacao_da_caldeira",
                "identificacao.identificacao_do_equipamento",
                "objeto_inspecao.identificacao",
                "nome_equipamento",
                "equipamento",
                "nome_inspecao",
                "informacoes_gerais.nome_equipamento",
                "informacoes_gerais.equipamento",
            ],
        ),
        title_hint,
        getattr(laudo, "primeira_mensagem", None),
    )
    tag_hint = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.tag_patrimonial", "tag_patrimonial", "codigo_tag", "equipamento_tag", "tag", "asset_tag"],
    )
    placa_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.placa_identificacao.descricao", "placa_identificacao", "placa", "identificacao_placa"],
    )
    placa_refs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.placa_identificacao.referencias_texto", "placa_identificacao_refs", "placa_identificacao_referencias", "placa_refs"],
    )
    vista_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "caracterizacao_do_equipamento.vista_geral_equipamento.descricao",
            "caracterizacao_do_equipamento.vista_geral_caldeira.descricao",
            "vista_geral_equipamento",
            "vista_geral_caldeira",
            "vista_geral",
        ],
    )
    vista_refs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "caracterizacao_do_equipamento.vista_geral_equipamento.referencias_texto",
            "caracterizacao_do_equipamento.vista_geral_caldeira.referencias_texto",
            "vista_geral_refs",
            "vista_geral_referencias",
        ],
    )
    descricao_sumaria = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["caracterizacao_do_equipamento.descricao_sumaria", "descricao_sumaria", "descricao_equipamento", "resumo_equipamento"],
        ),
        summary_hint,
    )
    condicao_operacao = _normalize_operation_state(
        _pick_value_by_paths(
            existing_payload,
            payload,
            paths=[
                "caracterizacao_do_equipamento.condicao_de_operacao_no_momento",
                "condicao_de_operacao_no_momento",
                "condicao_operacao",
                "status_operacao",
                "equipamento_em_operacao",
                "em_operacao",
            ],
        )
    )
    condicao_geral = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["inspecao_visual.condicao_geral", "condicao_geral", "condicoes_gerais"]),
        summary_hint,
    )
    integridade_aparente = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["inspecao_visual.integridade_aparente", "integridade_aparente", "integridade"]),
        summary_hint,
    )
    acessibilidade = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "inspecao_visual.acessibilidade_para_inspecao",
            "acessibilidade_para_inspecao",
            "acessibilidade_inspecao",
            "acesso_inspecao",
            "acesso_equipamento",
        ],
    )
    area_desc = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["inspecao_visual.area_instalacao.descricao", "area_instalacao"]),
        location_hint,
    )
    area_refs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["inspecao_visual.area_instalacao.referencias_texto", "area_instalacao_refs", "area_instalacao_referencias"],
    )

    prontuario_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["documentacao_e_registros.prontuario.referencias_texto", "prontuario", "prontuario_ref", "prontuario_referencias"],
    )
    prontuario_obs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["documentacao_e_registros.prontuario.observacao", "observacao_prontuario"],
    )
    certificado_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["documentacao_e_registros.certificado.referencias_texto", "certificado", "certificado_ref", "certificado_referencias"],
    )
    certificado_obs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["documentacao_e_registros.certificado.observacao", "observacao_certificado"],
    )
    relatorio_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["documentacao_e_registros.relatorio_anterior.referencias_texto", "relatorio_anterior", "historico_relatorio", "relatorio_anterior_ref"],
    )
    relatorio_obs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["documentacao_e_registros.relatorio_anterior.observacao", "observacao_relatorio_anterior"],
    )
    document_summary = _build_document_summary(
        prontuario_text=prontuario_text,
        certificado_text=certificado_text,
        relatorio_text=relatorio_text,
    )

    if family_key == "nr13_inspecao_vaso_pressao":
        identification_path = "identificacao.identificacao_do_vaso"
        vista_path = "caracterizacao_do_equipamento.vista_geral_equipamento"
        issue_desc = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["inspecao_visual.pontos_de_corrosao.descricao", "pontos_de_corrosao", "corrosao", "descricao_corrosao"],
        )
        issue_path = "inspecao_visual.pontos_de_corrosao"
        secondary_visual_blocks = [
            ("inspecao_visual.vazamentos", _pick_text_by_paths(existing_payload, payload, paths=["inspecao_visual.vazamentos.descricao", "vazamentos"])),
            (
                "inspecao_visual.isolamento_termico",
                _pick_text_by_paths(existing_payload, payload, paths=["inspecao_visual.isolamento_termico.descricao", "isolamento_termico"]),
            ),
        ]
        device_blocks = [
            (
                "dispositivos_e_acessorios.dispositivos_de_seguranca",
                _pick_text_by_paths(
                    existing_payload, payload, paths=["dispositivos_e_acessorios.dispositivos_de_seguranca.descricao", "dispositivos_de_seguranca"]
                ),
            ),
            (
                "dispositivos_e_acessorios.manometro",
                _pick_text_by_paths(existing_payload, payload, paths=["dispositivos_e_acessorios.manometro.descricao", "manometro"]),
            ),
            (
                "dispositivos_e_acessorios.valvula_seguranca_detalhe",
                _pick_text_by_paths(existing_payload, payload, paths=["dispositivos_e_acessorios.valvula_seguranca_detalhe.descricao", "valvula_seguranca"]),
            ),
            (
                "dispositivos_e_acessorios.suportes_e_fixacao",
                _pick_text_by_paths(
                    existing_payload, payload, paths=["dispositivos_e_acessorios.suportes_e_fixacao.descricao", "suportes_e_fixacao", "suportes"]
                ),
            ),
        ]
        leitura_dispositivos = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["dispositivos_e_acessorios.leitura_dos_dispositivos_de_seguranca", "leitura_dos_dispositivos_de_seguranca"],
        )
    else:
        identification_path = "identificacao.identificacao_da_caldeira"
        vista_path = "caracterizacao_do_equipamento.vista_geral_caldeira"
        issue_desc = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["inspecao_visual.pontos_de_vazamento_ou_fuligem.descricao", "pontos_de_vazamento_ou_fuligem", "pontos_fuligem", "fuligem", "vazamentos"],
        )
        issue_path = "inspecao_visual.pontos_de_vazamento_ou_fuligem"
        secondary_visual_blocks = [
            (
                "inspecao_visual.isolamento_termico",
                _pick_text_by_paths(existing_payload, payload, paths=["inspecao_visual.isolamento_termico.descricao", "isolamento_termico"]),
            ),
            (
                "inspecao_visual.chamine_ou_exaustao",
                _pick_text_by_paths(
                    existing_payload, payload, paths=["inspecao_visual.chamine_ou_exaustao.descricao", "chamine_ou_exaustao", "exaustao", "chamine"]
                ),
            ),
        ]
        device_blocks = [
            (
                "dispositivos_e_controles.dispositivos_de_seguranca",
                _pick_text_by_paths(
                    existing_payload, payload, paths=["dispositivos_e_controles.dispositivos_de_seguranca.descricao", "dispositivos_de_seguranca"]
                ),
            ),
            (
                "dispositivos_e_controles.painel_e_comandos",
                _pick_text_by_paths(
                    existing_payload, payload, paths=["dispositivos_e_controles.painel_e_comandos.descricao", "painel_e_comandos", "painel_comandos"]
                ),
            ),
            (
                "dispositivos_e_controles.manometro",
                _pick_text_by_paths(existing_payload, payload, paths=["dispositivos_e_controles.manometro.descricao", "manometro"]),
            ),
            (
                "dispositivos_e_controles.indicador_nivel",
                _pick_text_by_paths(existing_payload, payload, paths=["dispositivos_e_controles.indicador_nivel.descricao", "indicador_nivel"]),
            ),
            (
                "dispositivos_e_controles.queimador_ou_sistema_termico",
                _pick_text_by_paths(
                    existing_payload,
                    payload,
                    paths=["dispositivos_e_controles.queimador_ou_sistema_termico.descricao", "queimador_ou_sistema_termico", "queimador"],
                ),
            ),
        ]
        leitura_dispositivos = _pick_first_text(
            _pick_text_by_paths(
                existing_payload, payload, paths=["dispositivos_e_controles.leitura_dos_dispositivos_de_seguranca", "leitura_dos_dispositivos_de_seguranca"]
            ),
            _pick_text_by_paths(
                existing_payload, payload, paths=["dispositivos_e_controles.leitura_dos_comandos_e_indicadores", "leitura_dos_comandos_e_indicadores"]
            ),
        )
        _set_path_if_blank(
            payload,
            "dispositivos_e_controles.leitura_dos_comandos_e_indicadores",
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=[
                    "dispositivos_e_controles.leitura_dos_comandos_e_indicadores",
                    "leitura_dos_comandos_e_indicadores",
                    "painel_e_comandos",
                    "painel_comandos",
                ],
            ),
        )

    explicit_nc = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=["nao_conformidades.ha_nao_conformidades", "ha_nao_conformidades", "possui_nao_conformidades"],
    )
    nc_description = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["nao_conformidades.descricao", "descricao_nao_conformidades", "nao_conformidades"]),
        issue_desc,
    )
    has_nonconformity = _infer_nonconformity_flag(explicit_nc, nc_description, recommendation_hint)

    _set_path_if_blank(payload, identification_path, equipment_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", location_hint)
    _set_path_if_blank(payload, "identificacao.tag_patrimonial", tag_hint)
    _set_block_fields_if_blank(
        payload,
        block_path="identificacao.placa_identificacao",
        description=placa_desc,
        references_text=placa_refs,
        available=_coerce_bool(placa_desc) if _coerce_bool(placa_desc) is not None else bool(placa_desc or placa_refs),
    )
    _set_block_fields_if_blank(
        payload,
        block_path=vista_path,
        description=vista_desc,
        references_text=vista_refs,
        available=bool(vista_desc or vista_refs),
    )
    _set_path_if_blank(payload, "caracterizacao_do_equipamento.descricao_sumaria", descricao_sumaria)
    _set_path_if_blank(payload, "caracterizacao_do_equipamento.condicao_de_operacao_no_momento", condicao_operacao)

    _set_path_if_blank(payload, "inspecao_visual.condicao_geral", condicao_geral)
    _set_path_if_blank(payload, "inspecao_visual.integridade_aparente", integridade_aparente)
    _set_path_if_blank(payload, "inspecao_visual.acessibilidade_para_inspecao", acessibilidade)
    _set_block_fields_if_blank(
        payload,
        block_path="inspecao_visual.area_instalacao",
        description=area_desc,
        references_text=area_refs,
        available=bool(area_desc or area_refs),
    )
    _set_block_fields_if_blank(payload, block_path=issue_path, description=issue_desc, available=bool(issue_desc))
    for block_path, description in secondary_visual_blocks:
        _set_block_fields_if_blank(payload, block_path=block_path, description=description, available=bool(description))

    for block_path, description in device_blocks:
        _set_block_fields_if_blank(payload, block_path=block_path, description=description, available=bool(description))
    device_reading_path = (
        "dispositivos_e_acessorios.leitura_dos_dispositivos_de_seguranca"
        if family_key == "nr13_inspecao_vaso_pressao"
        else "dispositivos_e_controles.leitura_dos_dispositivos_de_seguranca"
    )
    _set_path_if_blank(payload, device_reading_path, leitura_dispositivos)

    _set_block_fields_if_blank(
        payload,
        block_path="documentacao_e_registros.prontuario",
        references_text=prontuario_text,
        observation=prontuario_obs,
        available=_coerce_bool(prontuario_text) if _coerce_bool(prontuario_text) is not None else bool(prontuario_text),
    )
    _set_block_fields_if_blank(
        payload,
        block_path="documentacao_e_registros.certificado",
        references_text=certificado_text,
        observation=certificado_obs,
        available=_coerce_bool(certificado_text) if _coerce_bool(certificado_text) is not None else bool(certificado_text),
    )
    _set_block_fields_if_blank(
        payload,
        block_path="documentacao_e_registros.relatorio_anterior",
        references_text=relatorio_text,
        observation=relatorio_obs,
        available=_coerce_bool(relatorio_text) if _coerce_bool(relatorio_text) is not None else bool(relatorio_text),
    )
    _set_path_if_blank(payload, "documentacao_e_registros.registros_disponiveis_no_local", document_summary)

    _set_path_if_blank(payload, "nao_conformidades.ha_nao_conformidades", has_nonconformity)
    _set_path_if_blank(
        payload,
        "nao_conformidades.ha_nao_conformidades_texto",
        "Sim" if has_nonconformity is True else "Nao" if has_nonconformity is False else None,
    )
    _set_path_if_blank(payload, "nao_conformidades.descricao", nc_description)
    _set_block_fields_if_blank(payload, block_path="nao_conformidades.evidencias", description=issue_desc, available=bool(issue_desc))

    _set_path_if_blank(
        payload,
        "mesa_review.pendencias_resolvidas_texto",
        f"Base documental considerada na emissao: {document_summary}" if document_summary else None,
    )
    _set_path_if_blank(
        payload,
        "conclusao.status",
        _resolve_conclusion_status(getattr(laudo, "status_revisao", None), has_nonconformity=has_nonconformity),
    )


__all__ = ["apply_nr13_projection"]
