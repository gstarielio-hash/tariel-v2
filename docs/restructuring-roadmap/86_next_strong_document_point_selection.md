# Seleção formal do próximo ponto documental forte após congelar `review_reject` e `report_finalize_stream`

## Objetivo

Escolher, com base em código real, documentação canônica, artefatos acumulados de 10A até 10H e validações já existentes, qual deve ser a próxima frente ativa do roadmap documental V2.

## Pré-checagem consolidada

- workspace:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- pontos já cobertos:
  - `report_finalize`
    - validado no 10B
  - `review_approve`
    - validado no 10C
- pontos explicitamente fora do foco ativo agora:
  - `review_reject`
    - permanece no máximo como telemetria `shadow_only`
    - decisão consolidada:
      - `deprecate_review_reject_as_enforce_candidate`
  - `report_finalize_stream`
    - permanece `shadow_only` como slice observado
    - decisão consolidada:
      - `retire_from_active_focus_and_keep_as_observed_slice`

## Candidatos fortes auditados

### 1. `template_publish_activate`

- rotas:
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
  - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- serviço:
  - [templates_laudo_management_routes.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/domains/revisor/templates_laudo_management_routes.py)
- `operation_kind` provável:
  - `template_publish_activate`
- semântica:
  - `publicar`

Leitura:

- promove uma versão de template a ativa;
- rebaixa versões ativas anteriores do mesmo código;
- no editor rico, gera snapshot PDF base antes da publicação;
- registra auditoria durável em `RegistroAuditoriaEmpresa`;
- afeta a versão operacional do template para o tenant.

### 2. `report_reopen`

- rotas:
  - `POST /app/api/laudo/{laudo_id}/reabrir`
  - `POST /cliente/api/chat/laudos/{laudo_id}/reabrir`
- serviço:
  - [laudo_service.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/domains/chat/laudo_service.py)
- `operation_kind` provável:
  - `report_reopen`
- semântica:
  - `reabrir`

Leitura:

- move o laudo de volta para `Rascunho`;
- limpa `reabertura_pendente_em`;
- reabre o fluxo operacional para edição;
- atravessa inspetor e admin-cliente.

### 3. `template_status_transition`

- rota:
  - `PATCH /revisao/api/templates-laudo/{template_id}/status`
- serviço:
  - [templates_laudo_management_routes.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/domains/revisor/templates_laudo_management_routes.py)
- `operation_kind` provável:
  - `template_status_transition`
- semântica:
  - `outra`

Leitura:

- altera genericamente o ciclo do template entre `rascunho`, `em_teste`, `ativo`, `legado` e `arquivado`;
- tem auditoria durável, mas o recorte é menos nítido do que o endpoint explícito de publicação.

### 4. `template_library_batch_mutation`

- rotas:
  - `POST /revisao/api/templates-laudo/lote/status`
  - `POST /revisao/api/templates-laudo/lote/excluir`
- serviço:
  - [templates_laudo_management_routes.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/domains/revisor/templates_laudo_management_routes.py)
- `operation_kind` provável:
  - `template_library_batch_mutation`
- semântica:
  - `outra`

Leitura:

- faz mutação em lote e exclusão de biblioteca;
- o blast radius é o pior do grupo;
- o rollback operacional também é o pior do grupo.

## Operações auditadas e descartadas

- `POST /app/api/laudo/{laudo_id}/finalizar`
  - já coberta no 10B
- `POST /cliente/api/chat/laudos/{laudo_id}/finalizar`
  - reaproveita o mesmo serviço do 10B
- `POST /revisao/api/templates-laudo/{template_id}/base-recomendada`
  - importante para curadoria, mas ainda mais indireto do que publicar a versão ativa
- `review_issue`
  - existe no contrato do soft gate, mas não há rota mutável real encontrada

## Ranqueamento comparativo

### 1. `template_publish_activate` - melhor

Motivos:

- é o ponto restante com semântica mais forte de governança documental;
- fica no domínio canônico dono de `Template / Documento`;
- é mais isolado do que o endpoint genérico de chat;
- já possui observabilidade durável por tenant:
  - `GET /revisao/api/templates-laudo/auditoria`
  - `RegistroAuditoriaEmpresa`
  - testes cobrindo `template_publicado`
- se alinha ao rollout por `tenant` ou `template` previsto nos docs canônicos.

Limites:

- o blast radius continua alto dentro do tenant;
- os blockers atuais do hard gate são majoritariamente case-level e não sustentam `enforce` aqui sem adaptação semântica;
- o primeiro passo neste ponto ainda precisa ser observação controlada.

Conclusão:

- melhor próximo candidato real;
- deve abrir primeiro em `shadow_only`.

### 2. `report_reopen` - aceitável com restrições

Motivos:

- é uma transição documental real;
- tem menor blast radius que mutação em lote.

Problemas:

- continua sendo caminho corretivo;
- cruza dois portais;
- os blockers atuais continuam fracos para qualquer `enforce` semântico nesse ponto.

Conclusão:

- fica em segundo lugar;
- só faria sentido se a frente de template fosse descartada.

### 3. `template_status_transition` - segurar

Problemas:

- mistura muitas transições num único endpoint;
- não oferece um recorte forte tão claro quanto publicar a versão ativa;
- tende a diluir observação e semântica logo na primeira abertura.

### 4. `template_library_batch_mutation` - não abrir agora

Problemas:

- mutação em lote e exclusão;
- blast radius muito alto;
- rollback mais frágil;
- baixa adequação para primeira frente forte pós-10H.

## Candidato escolhido

- rota principal:
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
- rota equivalente:
  - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- serviço:
  - [templates_laudo_management_routes.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/domains/revisor/templates_laudo_management_routes.py)
- `operation_kind` recomendado:
  - `template_publish_activate`
- semântica:
  - `publicar`

## Por que foi escolhido

- é a melhor combinação entre:
  - semântica documental forte;
  - domínio mais isolado;
  - observabilidade já durável;
  - scoping viável por tenant e por template.

Em comparação:

- é superior a `report_reopen` porque não é um caminho corretivo multiportal;
- é superior a `template_status_transition` porque o recorte é mais claro;
- é superior a mutações em lote porque o blast radius e o rollback são melhores.

## Modo de abertura recomendado

- `shadow_only`

## Blockers recomendados

### Em `enforce` na abertura

- nenhum

Racional:

- o hard gate atual ainda é dominado por sinais de materialização/emissão case-level;
- publicar template precisa primeiro provar sua própria semântica em observação controlada.

### Em `shadow` na abertura

- `template_source_unknown`
- `template_not_bound`

Observação:

- esses são os sinais reutilizáveis mais próximos do recorte atual;
- qualquer discussão futura de `enforce` exigirá família própria de blockers de governança de template, não apenas reaproveitamento automático dos blockers case-level.

## Decisão formal

- `approved_for_shadow_first_only`

## Rationale curto

Depois de congelar os dois slices observados, o próximo investimento forte não deve voltar para caminhos corretivos nem para o endpoint genérico de chat. A publicação da versão ativa de template é o melhor candidato porque pertence diretamente ao domínio `Template / Documento`, tem efeito operacional real, já possui auditoria durável por tenant e é estruturalmente mais isolada do que `report_finalize_stream`. Ainda assim, deve começar apenas em `shadow_only`, porque os blockers atuais ainda não sustentam `enforce` sem adaptação semântica.

## Condições para a próxima implementação

- criar `operation_kind` dedicado para `template_publish_activate`;
- manter rollout local/controlado, tenant allowlisted e, idealmente, template/code allowlisted;
- preservar boot/import check e smoke;
- exportar artifacts por execução e indexar a trilha da auditoria de templates;
- não tentar `shadow_plus_enforce_controlled` antes de provar a semântica própria desse ponto.

## Validações rerodadas nesta seleção

- `AMBIENTE=dev python3 -c "import sys; sys.path.insert(0, 'web'); import main; app = main.create_app(); print('boot_import_ok')"` -> `boot_import_ok`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py` -> `4 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10d.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10g.py` -> `2 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`

## Artefatos desta fase

- `artifacts/document_next_strong_point_selection/20260327_225320/candidate_matrix.json`
- `artifacts/document_next_strong_point_selection/20260327_225320/candidate_ranking.md`
- `artifacts/document_next_strong_point_selection/20260327_225320/selection_decision.txt`
- `artifacts/document_next_strong_point_selection/20260327_225320/source_evidence_index.txt`

## Próximo passo recomendado

Epic 10I - abertura controlada de `template_publish_activate` em `shadow_only`
