# 27. Historical Docs Cleanup

## Data da execucao

- 2026-04-05

## Objetivo da fase

- limpar docs auxiliares que ainda descreviam o pipeline visual antigo como ativo
- preservar rastreabilidade nas auditorias e journals sem confundir runtime atual com estado passado

## Artefato desta fase

- `artifacts/final_visual_post_removal/20260405_074453/docs_cleanup_report.md`

## Docs auxiliares atualizados

- `web/PROJECT_MAP.md`
- `web/docs/frontend_mapa.md`
- `web/docs/inspector-understanding-packet/README.md`
- `web/docs/inspector-understanding-packet/02_runtime_entrypoints.md`
- `web/docs/inspector-understanding-packet/05_template_js_css_map.md`
- `web/docs/inspector-understanding-packet/11_file_index.md`
- `docs/full-system-audit/06_frontend_architecture.md`
- `docs/full-system-audit/11_file_index.md`
- `docs/full-system-audit/12_FOR_CHATGPT.md`
- `docs/full-system-audit/README.md`
- `docs/full-system-audit/13_OPEN_QUESTIONS.md`
- `docs/tariel_visual_system.md`
- `AGENTS.md`

## Limpeza aplicada

- `web/templates/base.html` deixou de aparecer como shell operacional vivo
- os bundles removidos passaram a ser descritos como removidos fisicamente, nao como arquivos ainda presentes
- o packet do inspetor foi reancorado no pipeline canonico real: `official_visual_system.css`, `reboot.css` e `workspace_{chrome,history,rail,states}.css`
- `docs/tariel_visual_system.md` foi rebaixado para historico e redirecionado para as fontes canônicas atuais
- `AGENTS.md` deixou de instruir leitura por arquivos que já não existem

## Referencias historicas mantidas por rastreabilidade

Mantidas como histórico útil, sem serem reclassificadas como documentação operacional:

- `docs/final-project-audit/13_visual_system_audit.md`
- `docs/final-project-audit/14_visual_system_canonic.md`
- `docs/final-project-audit/15_visual_standardization_rollout.md`
- `docs/final-project-audit/16_visual_hotspots_refactor.md`
- `docs/final-project-audit/17_visual_legacy_reduction.md`
- `docs/final-project-audit/18_visual_component_slices.md`
- `docs/final-project-audit/19_app_and_mesa_componentization.md`
- `docs/final-project-audit/20_inspector_history_componentization.md`
- `docs/final-project-audit/21_non_runtime_legacy_deactivation.md`
- `docs/final-project-audit/22_legacy_entrypoint_retirement.md`
- `docs/final-project-audit/23_final_visual_legacy_removal.md`
- `docs/final-project-audit/24_final_visual_runtime.md`
- `docs/final-project-audit/25_physical_legacy_removal.md`
- `docs/restructuring-roadmap/99_execution_journal.md`
- `web/docs/inspector-chat-audit.md`
- `web/docs/refatoracao_frontend_inspetor.md`

## Resultado final

- os mapas auxiliares agora descrevem o runtime final correto
- as auditorias anteriores continuam preservadas como trilha historica
- a chance de outra IA ou engenheiro reabrir o pipeline antigo por leitura errada caiu de forma objetiva
