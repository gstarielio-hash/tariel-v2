# PLANS

Arquivo de trabalho para tarefas longas, confusas ou multissuperfície.

Atualizado em `2026-04-16`.

## Quando usar

- tarefa com mais de `30 min`;
- tarefa com impacto em mais de um workspace;
- investigação com muitos blockers;
- refatoração estrutural;
- correção crítica com risco de regressão.

## Estado atual

### `PKT-POST-MOBILE-02` - Polimento visual de Finalizar, Histórico e Configurações no Android

- `status`: concluído em `2026-04-16`; `Finalizar` ganhou agrupamento visual explícito entre ações, radar de emissão e pontos críticos, `Histórico` passou a expor radar operacional e cards de retomada mais legíveis, e `Configurações` ganhou topo com sinais rápidos de workspace, ambiente e contato sem reabrir a navegação principal

### Objetivo

- limpar a hierarquia visual das superfícies secundárias mais densas do app do inspetor
- reduzir sensação de painel genérico em `Finalizar`, `Histórico` e `Configurações`
- preservar contratos de navegação, testes e automação já estabelecidos

### Escopo

- entra reforço visual do topo de `Configurações` com sinais operacionais rápidos
- entra radar resumido de casos e item de retomada mais legível no `Histórico`
- entra separação explícita entre ações, resumo e pontos críticos em `Finalizar`
- nao entra redesenho estrutural do shell autenticado nem mudança de contrato da thread

### Criterio de pronto

- `Finalizar` deixa claro o que é ação imediata, o que é radar de emissão e o que é detalhe crítico
- `Histórico` permite leitura mais rápida de fila, mesa e retomada sem abrir cada caso
- `Configurações` expõe no topo os sinais principais da sessão atual sem depender da rolagem longa
- bateria focal de componentes do Android segue verde após o polimento

### `PKT-POST-ADMIN-CEO-01` - Polimento UX do catálogo de laudos

- `status`: concluído em `2026-04-09`; home em largura total com `drawer` para criação/bootstrap, detalhe de família com `abas` reais em `SSR` via `?tab=`, header compacto, formulários recolhidos por padrão, `advanced mode` explícito para JSON cru e leitura reforçada de releases/histórico

### Objetivo

- transformar o catálogo de laudos em painel executivo mais denso e menos parecido com cadastro operacional comprido
- preservar a separação já existente entre `family`, `mode`, `offer`, `calibration` e `tenant release`
- melhorar foco visual, hierarquia e legibilidade sem mexer no contrato principal do backend além do necessário para URL-first e retorno consistente

### Escopo

- entra remoção do formulário fixo de `Nova família` da home em favor de `drawer`
- entram `abas` reais no detalhe com apenas a aba ativa renderizada em `SSR`
- entram listas/estado atual antes dos formulários, formulários recolhidos e `advanced mode` para JSON cru
- entram header compacto, cards/KPIs menores, overflow de ações secundárias e timeline mais legível
- nao entra remodular o catálogo, reabrir migrações ou misturar oferta comercial com modo técnico

### Criterio de pronto

- a home prioriza portfólio, filtros, status e ação rápida em `1366x768`, sem coluna fixa de cadastro
- o detalhe da família deixa de ser uma página longa e passa a navegar por `?tab=` e `#hash`
- JSON cru e blocos vazios deixam de dominar a UX principal
- testes focais do catálogo no `admin` seguem verdes no recorte alterado

### `PKT-CATALOGO-TEMPLATES-01` - Runtime canônico de templates por família

- `status`: em andamento em `2026-04-09`; foco em ligar catálogo governado, `template_master_seed` e geração real de PDF por família sem reabrir modelagem principal; frente atual já cobre resolução catalog-aware de template no `/app/api/gerar_pdf`, priorização de template específico da família quando existir, fallback para seed canônico da família quando não existir template tenant salvo, preservação do legado apenas quando não houver artefato canônico operacional, materialização do `laudo_output` canônico para `NR13` (`vaso de pressão` e `caldeira`), `NR10` (`instalações elétricas` e agora também `prontuário de instalações elétricas`), `NR12` (`máquina e equipamento` e `apreciação de risco`), `NR20` (`inspeção de instalações inflamáveis` e `prontuário de instalações inflamáveis`), `NR33` (`avaliação de espaço confinado` e `permissão de entrada`) e `NR35` (`linha de vida` e `ponto de ancoragem`) a partir do payload atual do caso, início da `wave_2` com `NR18` (`canteiro de obra` e `frente de construção`), `NR22` (`área de mineração` e `instalação mineira`), `NR29` (`operação portuária`), `NR30` (`trabalho aquaviário`), `NR31` (`frente rural`), `NR32` (`inspeção em serviço de saúde` e `plano de risco biológico`), `NR34` (`inspeção frente naval`) e agora também `NR36` (`unidade de abate e processamento`), `NR37` (`plataforma de petróleo`) e `NR38` (`limpeza urbana e manejo de resíduos`), fechando a cobertura de runtime da `wave_2`, extensão da malha catalogada para a `wave_3` completa com `NR01`, `NR04`, `NR05`, `NR06`, `NR07`, `NR08`, `NR09`, `NR11`, `NR14`, `NR15`, `NR16`, `NR17`, `NR19`, `NR21`, `NR23`, `NR24`, `NR25` e `NR26`, persistência desse payload canônico no ciclo de finalização HTTP/SSE antes da etapa de PDF, leitura da Mesa/revisor por blocos canônicos com resumo operacional por seção no pacote técnico e painel inline do caso aberto para revisão sem depender do modal, uma suíte de regressão por fixtures canônicas da `onda_1` para impedir drift entre os artefatos oficiais e o runtime, smoke de emissão PDF por fixture oficial para validar seleção de template canônico e materialização final por família, um runner único de homologação completa da `onda_1` com gate de testes, provisão operacional e relatório consolidado em `.test-artifacts/homologacao/wave_1`, já fechado em `12` famílias homologadas sem pendências remanescentes dentro da onda, um runner equivalente da `wave_2` em `.test-artifacts/homologacao/wave_2`, fechado em `13` famílias homologadas com `13` demos emitidas no tenant piloto, a homologação completa da `wave_3` em `.test-artifacts/homologacao/wave_3`, fechada em `22` famílias homologadas com `22` demos emitidas no tenant piloto, o fechamento automatizado da `wave_4` em `.test-artifacts/homologacao/wave_4`, validando `NR02`, `NR03`, `NR27` e `NR28` como exceções de catálogo sem `family_schema` vendável nem provisão de templates, e agora também contrato documental oficial com `templates mestres`, `document_control`, `tenant_branding` e compatibilidade de placeholders de cabeçalho/rodapé para personalização do PDF por empresa cliente

### Objetivo

- fazer o catálogo de famílias deixar de ser só governança e passar a participar da emissão real do PDF
- garantir que famílias catalogadas possam gerar documento próprio com template dedicado, mesmo antes de uma biblioteca tenant totalmente curada
- manter compatibilidade com templates legacy existentes e com o renderer atual do `editor_rico`

### Escopo

- entra resolução de template por `catalog_family_key`, `release default`, `offer default` e artefato canônico da família
- entra fallback para `template_master_seed` e `laudo_output_seed` no runtime de PDF quando não houver template ativo salvo
- entra priorização de template específico da família sobre runtime genérico do tipo `nr13`
- nao entra modelar de uma vez todos os `report packs` semânticos por família
- nao entra reabrir migrations ou alterar o contrato principal de início/finalização do caso

### Criterio de pronto

- um laudo governado por catálogo consegue sair com PDF da família sem depender de template tenant já salvo
- um template ativo específico da família continua prevalecendo quando existir
- o fallback legado segue intacto para famílias sem artefato canônico operacional

### `PKT-LAUDOS-01` - Espinha semantica para preenchimento correto de laudos oficiais

- `status`: em andamento em `2026-04-06`; `Fase A`, `Fase B` e `Fase C` da entrada configuravel ja implementadas; `Fase D` fechada no fluxo atual com retomada/alternancia do mesmo caso, persistencia canonica do draft guiado por `laudo`, round-trip em `status/mensagens`, sync mobile, `evidence_refs` ligados a `message_id` da thread e `mesa_handoff` no draft canonico; `Fase E` e `Fase F` agora estao implementadas para as familias modeladas `nr35_linha_vida` e `cbmgo`, com `report_pack_draft_json`, `image_slots`, faltas de evidencia, candidato estruturado incremental, gates semanticos e liberacao `mobile_autonomous` allowlisted na finalizacao quando o caso fecha completo, sem nao conformidade impeditiva e sem conflito relevante; `Fase G` tambem entrou no backend com allowlist por template/tenant e agregacao operacional local de rollout, cobrindo preferencia do usuario x modo efetivo, troca de modo, gaps de evidencia e divergencia IA-humano; isso conclui o `full automatico` das familias modeladas atuais, nao a liberacao ampla para todas as familias; ponto de retomada em `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`; proximo slice passa para expansao segura de familias/modelagem e eventual superficie de consulta operacional; plano executivo em `docs/restructuring-roadmap/127_semantic_report_pack_execution_plan.md`, governanca normativa em `docs/restructuring-roadmap/128_normative_override_and_learning_governance.md`, entrada configuravel em `docs/restructuring-roadmap/129_dual_entry_configurable_inspection_roadmap.md` e checklist em `docs/restructuring-roadmap/130_dual_entry_implementation_checklist.md`

### Objetivo

- transformar o preenchimento de laudos oficiais no fluxo central do produto, acima da conversa isolada com a IA
- unificar `Templates/`, `editor_rico` da Mesa e finalizacao da IA em uma espinha unica baseada em `report packs`
- fazer a IA preencher `JSON canonico` por familia documental, com texto, checklist, fotos e gates de validacao
- permitir `chat-first` ou `evidence-first` como entradas configuraveis do mesmo caso tecnico, com preferencia definida pelo usuario e restricoes por politica

### Escopo

- entra catalogo de familias documentais oficiais e congelamento de `family/version/policy`
- entra contrato de `report pack` com `schema`, `image_slots`, `evidence_policy` e `validation_policy`
- entra `evidence bundle` do caso inteiro, em vez de depender apenas do payload corrente da interacao
- entra evolucao do renderer para texto, `checkbox` e imagem
- entra integracao semantica do `editor_rico` da Mesa como autoria de template
- entra politica dupla `mesa_required` e `mobile_autonomous`, com hard gates para autonomia
- entra separacao entre `aprovacao operacional`, `verdade normativa` e `elegibilidade para aprendizado`
- entra politica de `entrada configuravel` com `entry_mode_preference`, `entry_mode_effective` e `entry_mode_reason`
- nao entra liberacao ampla e imediata de autonomia mobile para todas as familias
- nao entra tratar PDF travado como fonte primaria de inteligencia do processo

### Criterio de pronto

- ao menos uma familia oficial opera ponta a ponta via `report pack` versionado, `evidence bundle`, `JSON canonico` e renderer com texto, `checkbox` e imagem
- a politica `mesa_required` funciona com medicao explicita de divergencia entre prefill da IA e decisao final humana
- override humano pode aprovar emissao sem transformar conflito normativo em aprendizado automatico
- o usuario consegue iniciar por conversa ou evidencias sem criar pipeline tecnico paralelo ou perder rastreabilidade do caso
- a autonomia mobile so existe onde houver allowlist, gates fortes e rollback simples para `mesa_required`

### `PKT-POST-ADMIN-CLIENTE-01` - Fechamento do portal Admin-Cliente

- `status`: concluído em `2026-03-31`; checklist pratico em `docs/restructuring-roadmap/122_admin_cliente_implementation_checklist.md` e fechamento em `docs/restructuring-roadmap/123_admin_cliente_surface_closure.md`

### Objetivo

- fechar o portal `admin-cliente` como superficie canonica da empresa cliente
- retirar mutacao comercial direta e autoprovisionamento ambiguo no mesmo nivel administrativo
- limpar stubs de auth, semantica residual de `admin-geral` e compatibilidade excessiva do boot

### Escopo

- entra governanca de plano por `interesse/solicitacao`, nao por mutacao direta
- entra foco de usuarios em `inspetor` e `revisor`, com `decision gate` explicito sobre multiplos `admin_cliente`
- entra honestidade de produto no login cliente
- entra limpeza semantica do bootstrap e reducao do `temporaryCompat` no portal cliente
- entra simplificacao de UX e isolamento visual do auth cliente
- nao entra `modo suporte` do `admin-geral`
- nao entra redesign premium amplo de todo o portal

### Criterio de pronto

- o portal cliente nao conclui troca comercial de plano nem se autoprovisiona como governanca superior por padrao
- login e UX do portal cliente so anunciam capacidades reais do produto
- residuos de `Admin-CEO` deixam de contaminar a experiencia principal do tenant
- `pytest` focal de `cliente`, `tenant boundary`, `session/auth/audit`, `smoke` e bootstrap `v2` permanece verde

### `PKT-POST-ADMIN-CLIENTE-02` - Fechamento operacional de visibilidade, suporte e auditoria

- `status`: concluido em `2026-04-01`; follow-up registrado em `docs/restructuring-roadmap/124_admin_cliente_policy_completion.md`

### Objetivo

- fechar o residual funcional do `admin-cliente` deixado apos o encerramento estrutural
- materializar a politica final de visibilidade do tenant no contrato administrativo
- governar suporte excepcional por tenant sem abrir um "modo suporte" navegavel dentro do `/cliente`
- classificar a auditoria do tenant por escopo e categoria, com timeline explicita

### Escopo

- entra derivacao da `visibility_policy` a partir da politica real da plataforma
- entra abertura e encerramento auditavel de suporte excepcional no `admin-geral`, com `step-up`, justificativa e referencia de aprovacao
- entra resumo e filtro de auditoria por `admin`, `chat`, `mesa` e `support` no portal cliente
- entra reflexo dessas politicas no diagnostico do tenant e no detalhe administrativo do `Admin-CEO`
- nao entra `admin-geral` navegando por dentro do tenant
- nao entra redesign premium amplo

### Criterio de pronto

- `admin-cliente` deixa de depender de placeholder para visibilidade, suporte e auditoria
- o suporte excepcional fica formalmente governado fora do `/cliente`, com trilha duravel por tenant
- bootstrap, API, diagnostico e telas administrativas convergem para a mesma leitura de politica
- rodada ampla de regressao do dominio cliente/admin permanece verde

### `PKT-POST-ADMIN-CLIENTE-03` - Checkpoint de UX premium local do portal

- `status`: concluido em `2026-04-01`; fechamento em `docs/restructuring-roadmap/125_admin_cliente_premium_ux_checkpoint.md`

### Objetivo

- fechar o acabamento premium local do `admin-cliente` depois do encerramento estrutural e funcional
- elevar leitura executiva, hierarquia visual e exploracao da timeline sem reabrir backend sensivel
- endurecer deep link, reload e historico das subabas do tenant com UX mais madura

### Escopo

- entra hero executivo, CTA dominante e KPIs na shell do portal cliente
- entram briefs por secao, cards mais hierarquicos e subnavegacao premium no `admin`
- entram politica de suporte mais visivel, protocolo recente, filtros e busca na auditoria
- entram fallbacks SSR mais fortes em `chat` e `mesa` para `?sec=`
- entra endurecimento URL-first da navegacao do `admin` para preservar historico
- nao entra redesign premium amplo do produto inteiro
- nao entram mudancas de auth, sessao, contratos do chat ou ACL do tenant

### Criterio de pronto

- o `admin-cliente` passa a ter leitura premium local verificavel sem perder estabilidade
- deep link, reload e back/forward seguem verdes nas superficies do portal cliente
- suporte e auditoria deixam de ser apenas blocos basicos e passam a ter leitura exploravel
- checks de JS, testes focais do portal e recorte Playwright permanecem verdes

### `PKT-POST-INSPETOR-01` - Hardening URL-first do workspace e historico canonico

- `status`: concluido em `2026-04-01`; fechamento em `docs/restructuring-roadmap/126_inspetor_workspace_history_hardening.md`

### Objetivo

- fechar o residual do workspace focado do `inspetor` depois da reorganizacao estrutural
- transformar `Conversa | Historico | Anexos | Mesa` em abas recuperaveis por URL e `history.state`
- trocar a timeline do `Historico` para leitura canonica do payload do laudo com fallback apenas para transientes locais

### Escopo

- entram helpers explicitos de `?aba=` no core do chat
- entram boot, `popstate` e selecao de laudo preservando a aba ativa do workspace
- entra priorizacao de `?aba=` no resolvedor do `inspetor` sem misturar autoridade de negocio com navegacao
- entra timeline de historico alimentada pelo payload canonico e pelo evento `tariel:historico-laudo-renderizado`
- entram testes browser para deep link, reload, back/forward e leitura do historico tecnico
- nao entra redesign premium amplo do `inspetor`
- nao entra API nova dedicada so para timeline tecnica

### Criterio de pronto

- `?aba=` passa a reabrir `historico`, `anexos` e `mesa` sem depender de estado efemero do runtime
- reload e back/forward preservam a aba ativa do workspace do `inspetor`
- o modo `Historico` deixa de depender apenas do DOM corrente e passa a consumir o payload canonico do laudo quando ele existe
- smoke, testes focais do `inspetor` e recorte Playwright especifico permanecem verdes

### `PKT-POST-PLAN-01` — Alinhamento técnico pós-plano

- `status`: executado em `2026-03-31`; próximos passos deixaram de ser limpeza estrutural ampla e passaram a ser slices dependentes de decisão

### Objetivo

- fechar os resíduos técnicos pós-plano em `P1` a `P8` sem reabrir o plano mestre
- transformar o que ainda era `shadow`, compatibilidade ou observação em contrato explícito quando isso pudesse ser feito sem ambiguidade
- sair do modo “hotspot estrutural” para um checkpoint orientado por decisão e governança

### Escopo

- entra convergência do estado do Inspetor
- entra enforcement documental por tenant
- entra colaboração canônica da Mesa em `frontend paralelo da Mesa`, Android, shell legada e realtime do revisor
- entra política explícita de visibilidade administrativa
- entram contrato explícito de anexos/sync móvel, governança documental, benchmarks pós-plano e alinhamento visual seguro do shell principal do Inspetor
- não entra redefinição jurídica final de IA, catálogo comercial fino nem redesign premium amplo de UX

### Critério de pronto

- `make contract-check`, `make verify`, `make v2-acceptance` e `make post-plan-benchmarks` verdes na mesma rodada
- resíduos estruturais concentrados apenas no que depende de decisão de produto/comercial/jurídico
- checkpoint documentado em `Tarie 2/docs/migration/79_post_plan_execution_closure.md`

### `PKT-F12-01` — Fechamento da Fase 12 Evolução estrutural V2

- `status`: concluído em `2026-03-31`; próximo passo direto é encerrar o plano mestre atual e tratar novas frentes como evolução pós-plano

### Objetivo

- promover a espinha estrutural do `V2` no sistema vivo sem reescrita big bang
- consolidar a ordem `envelopes -> ACL -> projeções -> provenance -> policy engine -> facade -> adapter`
- institucionalizar um runner oficial de aceite da fase

### Escopo

- entram envelopes, ACL, projeções do inspetor e da mesa, provenance, `policy engine`, facade documental e adapter Android
- entram projeções administrativas e `metering` explícito sem leitura técnica bruta
- entra `make v2-acceptance` com artifact autoritativo em `artifacts/v2_phase_acceptance/20260331_071151/`
- não entra uma nova fase posterior dentro do plano mestre atual

### Critério de pronto

- a ordem estrutural do `V2` fica materializada em código versionado e coberta por testes focais
- o pacote administrativo deixa de depender de lógica implícita de billing/consumo embutida em projeções
- `make v2-acceptance`, `make contract-check` e `make verify` passam na rodada final da fase

### `PKT-F11-01` — Fechamento da Fase 11 Higiene permanente e governança

- `status`: concluído em `2026-03-31`; próximo passo direto é `Fase 12 - Evolução estrutural V2`

### Objetivo

- institucionalizar política de `artifacts/`, `gitignore` por workspace e governança local mínima
- tirar `PLANS.md` e `git worktree` da memória informal
- reduzir a chance de outputs locais dominarem `git status`

### Escopo

- entra policy versionada de hygiene local
- entram `.gitignore` revistos por workspace
- entram `make hygiene-check` e `make hygiene-acceptance`
- entra endurecimento do `clean-generated`
- não entra reescrita histórica de artifacts já antigos/versionados

### Critério de pronto

- policy de `artifacts/` fica explícita e versionada
- `PLANS.md` e `git worktree` ficam institucionalizados como regra operacional
- `make hygiene-acceptance`, `make contract-check` e `make verify` passam na rodada final da fase

### `PKT-F10-01` — Fechamento da Fase 10 Observabilidade, operação e segurança

- `status`: concluído em `2026-03-30`; próximo passo direto é `Fase 11 - Higiene permanente e governança`

### Objetivo

- promover a `Fase 10` sem deixar tracing, erro, retenção e governança dependerem de memória informal
- unificar `correlation_id` e `traceparent` entre backend, `frontend paralelo da Mesa` e mobile
- institucionalizar um runner oficial de aceite da fase

### Escopo

- entra `OpenTelemetry` opcional no backend
- entra `Sentry` opcional com scrubbing
- entra política explícita de analytics/replay/LGPD/retenção
- entra summary administrativo em `/admin/api/observability/summary`
- entra `make observability-acceptance`
- não entra enforcement remoto de branch protection no GitHub via API

### Critério de pronto

- `correlation_id` e `traceparent` cruzam backend, `frontend paralelo da Mesa` e mobile sem dialetos paralelos
- logs e medições pesadas ficam observáveis sem depender de grep manual em payload bruto
- retenção, mascaramento e replay deixam de ser implícitos
- `make observability-acceptance`, `make contract-check` e `make verify` passam na rodada final da fase

### `PKT-F09-01` — Fechamento da Fase 09 Documento, template e IA

- `status`: concluído em `2026-03-30`; próximo passo direto é `Fase 10 - Observabilidade, operação e segurança`

### Objetivo

- promover a `Fase 09 - Documento, template e IA` sem deixar o ciclo documental depender do legado invisível
- fechar lifecycle de template, preview/publicação/rollback, provenance IA/humana e medição operacional de `OCR`/custos
- institucionalizar um runner oficial de aceite da fase

### Escopo

- entra lifecycle completo de template no `frontend paralelo da Mesa`, com `publish`, status, base recomendada, clone, preview e arquivo-base
- entra provenance IA/humana explícita no shell oficial do caso sem quebrar o fold principal validado por snapshot
- entra agregação administrativa de operações pesadas em `/admin/api/document-operations/summary`
- entra `make document-acceptance` com artifact autoritativo em `artifacts/document_phase_acceptance/20260330_213625/`
- não entra observabilidade distribuída ampla nem policy global de rollout/segurança

### Critério de pronto

- template, preview, publicação e rollback deixam de divergir entre shell oficial e fonte de verdade
- provenance IA/humana fica explícita e auditável no detalhe do caso
- `OCR`, geração documental e custos pesados ficam agregados em leitura administrativa explícita
- `make document-acceptance`, `make verify` e `make contract-check` passam na rodada final da fase

### `PKT-F08-01` — Fechamento da Fase 08 Mobile

- `status`: concluído em `2026-03-30`; próximo passo direto é `Fase 09 - Documento, template e IA`

### Objetivo

- promover a `Fase 08 - Mobile` sem depender de login/manual smoke improvisado para validar a APK
- fechar build local, push operacional e smoke real controlado do app Android
- manter separada a trilha de validação orgânica/humana do tenant demo para qualquer discussão futura de tenant real

### Escopo

- entra endurecimento do login mobile com timeout real, persistência local não-bloqueante e probe de automação
- entra registro operacional de dispositivo/push no backend e no app
- entra institucionalização de `make mobile-baseline`, `make mobile-preview` e `make smoke-mobile`
- entra artifact autoritativo do runner oficial em `artifacts/mobile_pilot_run/20260330_203601/`
- não entra promoção de tenant real

### Critério de pronto

- a APK preview sobe, autentica e alcança o shell autenticado no emulador de forma reproduzível
- histórico, seleção de laudo, central de atividade e thread da Mesa passam no runner oficial
- o build/smoke do mobile ficam amarrados em entrypoints oficiais do repositório
- a trilha orgânica/humana continua separada como guard-rail operacional e não como smoke improvisado

### `PKT-F07-01` — Fechamento da Fase 07 de Cliente/Admin

- `status`: concluído em `2026-03-30`; próximo passo direto é `Fase 08 - Mobile`

### Objetivo

- promover a `Fase 07 - Cliente e admin` sem trilha administrativa oculta
- fechar auditoria visível do `admin-geral`
- fechar suporte e diagnóstico explícitos do portal `admin-cliente`

### Escopo

- entra auditoria HTML/JSON do `admin-geral`
- entra diagnóstico exportável por tenant no detalhe administrativo
- entra diagnóstico exportável e relato de suporte no portal cliente
- entra a manutenção do `RBAC`, `CSRF` e da fronteira explícita entre `cliente`, `admin`, `chat` e `mesa`
- não entra redesign estrutural amplo dos portais

### Critério de pronto

- `/admin/auditoria` existe como leitura explícita da trilha crítica do `admin-geral`
- `/admin/clientes/{empresa_id}/diagnostico` exporta o tenant sem depender de console ou script manual
- `/cliente/api/diagnostico` e `/cliente/api/suporte/report` ficam operacionais e auditáveis
- a bateria focal de `cliente/admin`, tenant boundary, sessão/auth/auditoria e smoke parcial fica verde

### `PKT-F06-01` — frontend paralelo da Mesa oficial, FE-V10 e fechamento da Fase 06

- `status`: concluído em `2026-03-30` e supersedido em `2026-04-04` pela consolidação da Mesa oficial no `SSR`; próximo passo direto continua `Fase 07 - Cliente e admin`

### Objetivo

- promover a `frontend paralelo da Mesa` como superfície oficial da Mesa sem quebrar auth/sessão do legado
- materializar rollout, rollback e aceite final da Mesa em artifact reproduzível
- integrar o smoke oficial da Mesa ao gate local do repositório

### Escopo

- entra o bridge de rollout em `web/app/domains/revisor`
- entra a preservação da cookie/sessão real no BFF do `frontend paralelo da Mesa`
- entra o runner read-only de paridade/aceite FE-V10
- entra o gate local `mesa-smoke` em `make verify`
- não entra automação cega de mutação real em dados do revisor

### Critério de pronto

- `/revisao/painel` redireciona oficialmente para `frontend paralelo da Mesa` com rollback explícito por `?surface=ssr`
- a fila real do `frontend paralelo da Mesa` continua lendo a fonte legacy sem recursão
- `make mesa-smoke` fica verde e passa a compor `make verify`
- o artifact de aceite FE-V10 fica verde com paridade real e sem divergências na fila

### Observação posterior

- em `2026-04-04`, a iniciativa `frontend paralelo da Mesa` foi arquivada para eliminar a duplicação da Mesa; a superfície oficial voltou a ser exclusivamente o `SSR` em `web/`, com limpeza de scripts, workflows e docs operacionais associados ao frontend paralelo

### `PKT-E02-01` — Mapeamento legado do Technical Case

- `status`: concluído em `2026-03-30`; próximo pacote direto é `PKT-E02-02`

### Objetivo

- congelar o mapa `Laudo -> case_id/thread_id/document_id/document_version`
- explicitar quais superfícies leem e escrevem o caso hoje
- deixar a ACL do caso pronta para implementação sem depender de memória informal

### Escopo

- entra o legado vivo em `web/app/domains/chat`, `web/app/domains/revisor`, `web/app/domains/cliente`, `web/app/domains/admin` e `web/app/shared`
- entra o alinhamento com os contratos canônicos do workspace V2 em `/home/gabriel/Área de trabalho/Tarie 2`
- não entra mudança funcional no backend do legado
- não entra troca de payload em produção

### Passos

1. inventariar `Laudo`, `MensagemLaudo`, `LaudoRevisao`, `AnexoMesa` e `PacoteMesaLaudo`
2. congelar a tradução de estado legado para estado canônico
3. mapear entrypoints de inspetor/chat web, mesa web, admin-cliente web, admin geral web e Android mobile
4. registrar o pacote documental em `/home/gabriel/Área de trabalho/Tarie 2/scaffolding/backend/domains/technical_case/legacy_mapping/README.md`

### Critério de pronto

- tabela `legado -> caso técnico` publicada
- assimetria entre `Admin Cliente`, `Admin Geral`, chat e mesa explicitada
- próximo passo `PKT-E02-02` identificado sem ambiguidade

### `PKT-E02-02` — ACL de leitura do caso

- `status`: concluído em `2026-03-30`; próximo pacote direto é `PKT-E02-03`

### Objetivo

- transformar o mapeamento legado em snapshot canônico executável do caso
- materializar `case_id`, `thread_id`, `document_id` e `document_version` sem depender do payload bruto do portal
- expor a leitura canônica em `shadow mode` em caminhos reais de inspetor e mesa

### Escopo

- entra a ACL incremental em `web/app/v2/acl`
- entra integração leve via `request.state` nos reads de status do inspetor e pacote da mesa
- entra cobertura de teste da nova tradução
- não entra troca do payload público em produção

### Passos

1. criar `technical_case_snapshot.py` com estado, refs legadas, visibilidade e sensibilidade
2. conectar o snapshot rico ao read de status do inspetor
3. conectar o snapshot rico ao read de pacote da mesa
4. validar com `pytest` focado e manter payload público intacto

### Critério de pronto

- snapshot canônico rico executável publicado em `web/app/v2/acl/technical_case_snapshot.py`
- `request.state` expõe o snapshot rico nos caminhos de leitura conectados
- `pytest` focal da ACL, inspetor e mesa verde
- próximo passo `PKT-E02-03` identificado sem ambiguidade

### `PKT-E02-03` — Consumo piloto da facade

- `status`: concluído em `2026-03-30`; próximo pacote direto é `PKT-E03-01`

### Objetivo

- usar a leitura canônica do caso em um consumer controlado, sem trocar o fluxo público inteiro
- validar a assimetria do `admin-cliente` sobre chat web e mesa web sem promover acesso administrativo cruzado
- comparar o piloto com o bootstrap legado e manter rollback por `feature flag`

### Escopo

- entra o bootstrap do `admin-cliente` em `web/app/domains/cliente`
- entra projeção canônica incremental para visão administrativa do tenant em `web/app/v2/contracts` e `web/app/v2/adapters`
- entra `shadow mode` por `request.state` e `feature flag`
- não entra troca do payload público do endpoint
- não entra exposição de superfícies administrativas para chat web ou mesa web

### Passos

1. criar a projeção incremental do `tenant admin`
2. adaptar o bootstrap legado para gerar a projeção em `shadow mode`
3. validar compatibilidade com o payload atual e divergências mínimas
4. cobrir o piloto com teste focado sem alterar a resposta pública

### Critério de pronto

- o bootstrap do `admin-cliente` registra a projeção canônica em `shadow mode`
- o payload público permanece inalterado com a `feature flag` ligada
- `pytest` focal do piloto, da ACL e das projeções correlatas verde
- próximo passo `PKT-E03-01` identificado sem ambiguidade

### `MP-003` — Projeção administrativa do Admin Geral

- `status`: concluído em `2026-03-30`; próximo passo direto é fechar a matriz contratual multiportal e revisar `RBAC` por ação

### Objetivo

- projetar uma visão administrativa agregada para o `admin-geral`, sem conteúdo técnico bruto por padrão
- validar a singularidade entre `Admin Geral` e `Admin Cliente`
- conectar a projeção em `shadow mode` no painel legado sem trocar o HTML público

### Escopo

- entra contrato incremental em `web/app/v2/contracts/platform_admin.py`
- entra adapter de shadow do painel em `web/app/v2/adapters/platform_admin_dashboard.py`
- entra integração leve em `web/app/domains/admin/routes.py`
- entra cobertura de teste focada para shape e rota
- não entra leitura técnica integral de tenant

### Passos

1. materializar a projeção canônica `platform_admin_view`
2. adaptar o dashboard legado para emitir a projeção em `request.state`
3. comparar contagens agregadas com o payload administrativo atual
4. validar que o HTML público do painel não muda com a `feature flag`

### Critério de pronto

- o painel do `admin-geral` registra a projeção agregada em `shadow mode`
- a visão continua sem conteúdo técnico bruto por padrão
- o HTML público do painel permanece inalterado com a `feature flag` ligada
- `pytest` focal da nova projeção e das projeções correlatas verde

### `MP-004` — Matriz de RBAC por ação

- `status`: concluído em `2026-03-30`; próximo passo direto é revisar isolamento de tenant por ação crítica

### Objetivo

- explicitar `RBAC` por ação nas superfícies críticas com base nos guards reais do sistema vivo
- remover o atalho que deixava `Admin Geral` entrar na superfície bruta da `Mesa`
- travar em teste as fronteiras entre `Inspetor`, `Revisor`, `Admin Cliente`, `Admin Geral` e `Android`

### Escopo

- entra a revisão de guards em `web/app/shared/security.py`
- entra a matriz operacional em `/home/gabriel/Área de trabalho/Tarie 2/contracts/api/multiportal_rbac_action_matrix_v1.md`
- entra teste focal de fronteira entre superfícies em `web/tests/test_rbac_action_matrix.py`
- não entra política fina de acesso excepcional

### Passos

1. mapear endpoints críticos por superfície e papel permitido
2. alinhar o guard da `Mesa` com a singularidade entre `Revisor` e `Admin Geral`
3. registrar a matriz multiportal com leitura e escrita representativas
4. validar com suites focais e suites amplas dos portais afetados

### Critério de pronto

- `Admin Geral` deixa de acessar endpoints brutos da `Mesa`
- `Admin Cliente` continua consumindo recortes próprios de chat e mesa sem usar endpoints brutos
- a matriz de `RBAC` por ação fica publicada e referenciada no pacote multiportal
- `pytest` focal de `RBAC`, portais, cliente, admin e projeções verde

### `MP-005` — Matriz de tenant boundary

- `status`: concluído em `2026-03-30`; próximo passo direto é consolidar sessão, auth e trilha de auditoria

### Objetivo

- explicitar o isolamento de tenant por superfície crítica no sistema vivo
- provar em teste que `inspetor`, `mesa`, `admin-cliente` e `mobile` não atravessam tenant por acidente
- garantir que `admin-geral` só governa tenant por alvo explícito e não por herança do `empresa_id` administrativo

### Escopo

- entra a revisão do estado de sessão por portal em `web/app/shared/security_portal_state.py`
- entra a matriz operacional em `/home/gabriel/Área de trabalho/Tarie 2/contracts/api/multiportal_tenant_boundary_matrix_v1.md`
- entra a suíte focal em `web/tests/test_tenant_boundary_matrix.py`
- não entra política detalhada de auditoria nem correlação distribuída

### Passos

1. mapear as rotas críticas com tenant implícito e tenant explícito
2. fechar qualquer compatibilidade de sessão que misture portal administrativo com mesa
3. registrar a matriz multiportal com semântica de `404`, bootstrap e alvo explícito
4. validar com suites focais e suites amplas dos portais afetados

### Critério de pronto

- `inspetor web`, `mobile`, `mesa` e `admin-cliente` mantêm isolamento de tenant em teste
- `admin-geral` governa tenant por `empresa_id` explícito sem prender a plataforma ao próprio tenant do usuário
- a matriz de `tenant boundary` fica publicada e referenciada no pacote multiportal
- `pytest` focal de tenant, portais, cliente, admin e `RBAC` verde

### `MP-006` — Sessão, auth e trilha de auditoria

- `status`: concluído em `2026-03-30`; próximo passo direto é fechar a verdade única do laudo ativo no inspetor

### Objetivo

- consolidar o contrato de sessão por portal nas superfícies web
- impedir que logout de um portal derrube outro portal no mesmo browser por acidente
- persistir trilha durável mínima das ações críticas do `admin-geral` sobre tenant

### Escopo

- entra a unificação do `admin` no contrato `portal-aware` de sessão
- entra o logout seletivo do `admin-cliente`
- entra auditoria durável das mutações críticas do `admin-geral` em tenant
- entra a matriz operacional em `/home/gabriel/Área de trabalho/Tarie 2/contracts/api/multiportal_session_auth_audit_matrix_v1.md`
- não entra auditoria durável completa do `inspetor` nem do `Android`

### Passos

1. mapear auth mode, sessão e CSRF por superfície
2. remover atalho de sessão global bruta do `admin`
3. tornar seletivo o encerramento de sessão do `admin-cliente`
4. registrar auditoria durável do `admin-geral` nas ações críticas sobre tenant
5. validar com suites focais e suites amplas do legado

### Critério de pronto

- `admin` e `admin-cliente` conseguem coexistir no mesmo browser sem logout cruzado acidental
- `admin-geral` grava auditoria durável nas mutações críticas de tenant
- a matriz de sessão/auth/auditoria fica publicada e referenciada no pacote multiportal
- `pytest` focal de sessão, portais, cliente, admin e regressão ampla verde

### `MP-007` — Verdade única do laudo ativo no inspetor

- `status`: concluído em `2026-03-30`; próximo passo direto volta para fechar os contratos críticos multiportal e promover a `Fase 03`

### Objetivo

- explicitar quem manda no `laudo ativo` entre sessão, SSR, `?laudo=`, `?home=1`, sidebar e espelhos locais
- impedir que `URL` ou `localStorage` sequestrem o contexto técnico depois que o backend já materializou o estado principal

### Escopo

- entra um resolvedor backend único do contexto principal do inspetor
- entra helper único de limpeza do contexto do laudo ativo
- entra redução da autoridade contínua de `URL/localStorage` no boot do inspetor
- entra a matriz operacional em `/home/gabriel/Área de trabalho/Tarie 2/contracts/api/inspector_active_report_authority_v1.md`
- não entra revisão completa de `sidebar`, filtros, tabs ou layout do inspetor

### Passos

1. mapear como sessão, `?laudo=`, `?home=1` e storage competem hoje
2. consumir `?laudo=` no backend como ingresso explícito e refletir isso no SSR
3. centralizar a limpeza do contexto do laudo ativo
4. remover `URL/localStorage` da escolha autoritativa contínua no boot do inspetor
5. validar com `pytest` focal, regressão ampla de portais e `Playwright` específico

### Critério de pronto

- `?laudo=` válido promove o mesmo laudo para sessão e SSR no mesmo request
- `?home=1` só força landing visual e não limpa o laudo ativo por acidente
- `URL/localStorage` não sobrepõem o `laudo ativo` depois que o backend já materializou o estado
- a matriz de autoridade do `laudo ativo` fica publicada e referenciada no pacote multiportal
- `pytest` focal + regressão ampla de portais + `Playwright` específico ficam verdes

### `MP-008` — Bootstraps multiportal explícitos

- `status`: concluído em `2026-03-30`; próximo passo direto é fechar a fila especializada da mesa, `template publish` e as lacunas administrativas restantes do pacote multiportal

### Objetivo

- congelar os contratos mínimos de bootstrap/transporte que ainda estavam implícitos no inspetor, na mesa `SSR` e no Android
- reduzir a matriz multiportal às lacunas reais, sem confundir shell/boot com contrato acidental
- travar esses shapes com testes próprios no sistema vivo

### Escopo

- entra o bootstrap SSR do inspetor via `#tariel-boot`
- entra o front contract mínimo da mesa `SSR` via `#revisor-front-contract`
- entra o envelope legado de `login/bootstrap` do Android
- entra documentação canônica no workspace V2 e suíte focal no legado
- não entra fila especializada da mesa
- não entra `template publish`
- não entra fechamento dos contratos administrativos de billing/saúde operacional

### Passos

1. mapear os blocos mínimos de bootstrap por superfície
2. publicar os contratos canônicos e schemas aplicáveis no workspace V2
3. travar os shapes mínimos com `pytest` focal no sistema vivo
4. reduzir a matriz multiportal para exibir apenas as lacunas ainda abertas de verdade

### Critério de pronto

- `inspetor/chat web` tem contrato explícito para `meta csrf` e `#tariel-boot`
- `mesa avaliadora web` tem contrato explícito para shell `SSR` e `#revisor-front-contract`
- `Android mobile` tem envelope explícito para `login` e `bootstrap`
- a matriz multiportal deixa de listar bootstrap/sessão dessas superfícies como lacuna aberta
- `pytest` focal dos contratos + regressões correlatas ficam verdes

### `MP-009` — Template publish explícito da Mesa

- `status`: concluído em `2026-03-30`; próximo passo direto é congelar a projeção especializada de fila da mesa antes de atacar as lacunas administrativas restantes

### Objetivo

- tornar explícito o contrato de publicação de template da mesa
- garantir que a rota clássica e a rota do editor rico devolvam o mesmo envelope mínimo
- travar a geração de auditoria e a semântica de ativação no sistema vivo

### Escopo

- entra o par de rotas `POST /revisao/api/templates-laudo/{id}/publicar` e `POST /revisao/api/templates-laudo/editor/{id}/publicar`
- entra schema do envelope mínimo de resposta no workspace V2
- entra suíte focal de contrato no legado
- não entra preview, diff, lote, base recomendada nem fila da mesa

### Passos

1. ler o payload público atual das rotas de publicação
2. publicar contrato canônico único para as duas rotas
3. validar equivalência de envelope e efeitos mínimos em teste
4. reduzir a matriz multiportal para remover `template publish` da lista de lacunas

### Critério de pronto

- as duas rotas devolvem o mesmo envelope mínimo `{ok, template_id, status}`
- a publicação continua rebaixando ativos anteriores do mesmo código
- a ação continua gerando auditoria `template_publicado`
- a matriz multiportal deixa de listar `template publish` como lacuna aberta da mesa
- `pytest` focal do contrato + regressão ampla correlata ficam verdes

### `MP-010` — Projecao especializada de fila da Mesa

- `status`: concluido em `2026-03-30`; proximo passo direto e voltar a reduzir as lacunas contratuais de `inspetor`, `Android`, `admin-cliente` e `admin-geral`

### Objetivo

- congelar a linguagem da fila especializada da mesa fora do HTML do painel
- registrar a projecao canônica em `shadow mode` no `painel_revisor`
- permitir convergencia futura entre `SSR` e `frontend paralelo da Mesa` sem depender de estrutura incidental do template

### Escopo

- entra projecao canonica da fila da mesa em `web/app/v2/contracts/review_queue.py`
- entra adapter de comparacao em `web/app/v2/adapters/review_queue_dashboard.py`
- entra integracao em `shadow mode` no `web/app/domains/revisor/panel.py`
- entra schema e contrato no workspace V2
- nao entra mudanca do HTML publico
- nao entra troca da superficie oficial da mesa

### Passos

1. mapear o shape real das secoes, totais, filtros e resumo de templates do painel
2. publicar a projecao canônica especializada da fila
3. comparar a projecao com o contexto legado do painel em `request.state`
4. validar que o HTML publico nao muda quando a flag esta ligada

### Criterio de pronto

- a fila da mesa tem projecao canônica propria, separada do `reviewer_case_view`
- o `painel_revisor` registra o resultado da projecao em `shadow mode`
- a matriz multiportal deixa de listar a fila especializada como lacuna contratual da mesa
- `pytest` focal da fila + regressao ampla correlata ficam verdes

### `MP-011` — Visao documental propria do inspetor

- `status`: concluido em `2026-03-30`; proximo passo direto e voltar a reduzir as lacunas contratuais de `Android`, `admin-cliente` e `admin-geral`

### Objetivo

- congelar o recorte documental do `inspetor/chat web` fora do payload legado de status
- registrar uma projecao documental dedicada em `shadow mode`, derivada da `document_facade`
- fechar a lacuna contratual do inspetor sem transformar preview, policy ou facade interna em contrato acidental

### Escopo

- entra projecao canonica em `web/app/v2/contracts/inspector_document.py`
- entra integracao em `shadow mode` no `web/app/domains/chat/laudo_service.py`
- entra schema e contrato no workspace V2
- nao entra mudanca do JSON publico de `/app/api/laudo/status`
- nao entra rota nova de preview ou emissao

### Passos

1. mapear o recorte documental ja calculado pela `document_facade` no fluxo do inspetor
2. publicar a projecao documental dedicada para a superficie `inspetor/chat web`
3. registrar o resultado em `request.state` sem alterar o payload legado
4. reduzir a matriz multiportal para remover a lacuna documental do inspetor

### Criterio de pronto

- o inspetor tem projecao documental propria separada do `inspector_case_view`
- `obter_status_relatorio_resposta` registra essa projecao em `shadow mode`
- a matriz multiportal deixa de listar lacuna contratual critica para a superficie do inspetor
- `pytest` focal documental do inspetor + regressao ampla correlata ficam verdes

### `MP-012` — Sync offline observavel do Android

- `status`: concluido em `2026-03-30`; proximo passo direto e fechar a politica final do feedback da mesa no mobile antes de tentar promover a `Fase 03`

### Objetivo

- congelar a linguagem observavel da fila offline do Android fora de strings do modal
- compartilhar um snapshot unico entre agregados do app e diagnostico exportavel
- reduzir a lacuna contratual do Android sem acoplar o mobile a payload incidental do backend

### Escopo

- entra builder puro de snapshot em `android/src/features/offline/offlineSyncObservability.ts`
- entra consumo no diagnostico exportado em `android/src/features/settings/useSettingsOperationsActions.ts`
- entra alinhamento dos agregados de fila em `android/src/features/common/buildInspectorBaseDerivedStateSections.ts`
- entra contrato e schema no workspace V2
- nao entra troca do payload HTTP publico do backend
- nao entra decisao final da politica de feedback da mesa no mobile

### Passos

1. mapear a fila offline real do app e os helpers de retry/backoff ja vivos
2. publicar snapshot observavel unico com totais, blocker, atividade e itens
3. usar o snapshot no diagnostico local sem depender de texto de UI
4. reduzir a matriz multiportal para deixar aberta apenas a politica de feedback da mesa

### Criterio de pronto

- a fila offline do Android tem snapshot observavel proprio e testado
- o diagnostico exportado inclui estado, capacidade e atividade da fila offline
- a matriz multiportal deixa de listar `sync offline observavel` como lacuna do Android
- `jest` focal do mobile, `typecheck` e `make contract-check` ficam verdes

### `MP-013` — Politica final do feedback da Mesa no Android

- `status`: concluido em `2026-03-30`; proximo passo direto e fechar as lacunas contratuais administrativas remanescentes para tentar promover a `Fase 03`

### Objetivo

- congelar quanto feedback da mesa o Android pode ver sem transformar o app em cliente da superficie de revisao
- tornar a politica movel explicita em backend, contrato publico V2 e parser do app
- impedir leak de contador, ponteiro temporal ou corpo de mensagem quando o feedback da mesa estiver oculto

### Escopo

- entra contrato publico explicito em `web/app/v2/contracts/mobile.py`
- entra enforcement de visibilidade nos adapters moveis do backend
- entra parser e validacao de consistencia no app Android
- entra contrato operacional e schema alinhado no workspace V2
- nao entra colaboracao quase completa da mesa no mobile
- nao entra billing/admin nem promocao automatica da `Fase 03`

### Passos

1. transformar `android_feedback_sync_policy` em contrato explicito de leitura publica
2. filtrar mensagens, contadores e ponteiros da mesa quando a politica ficar em modo `hidden`
3. validar no parser do app que backend e politica permanecem coerentes
4. reduzir a matriz multiportal para remover a ultima lacuna contratual do Android nesta fase

### Criterio de pronto

- o contrato publico V2 do mobile expõe `feedback_policy` explicita
- `hidden` remove corpo de mensagem, contadores e ponteiros da mesa do payload movel
- `jest` focal do app e `pytest` focal do backend ficam verdes
- a matriz multiportal deixa de listar o Android como lacuna contratual critica da `Fase 03`

### `MP-014` — Matriz inicial de hotspots e ownership

- `status`: iniciado em `2026-03-30`; proximo passo direto e atacar `InspectorMobileApp.tsx` como primeiro hotspot estrutural da `Fase 04`

### Objetivo

- promover a `Fase 03` sem entrar na `Fase 04` de forma cega
- registrar quais arquivos grandes e sensiveis concentram risco real de acoplamento
- definir ownership alvo e primeiro corte recomendado antes de qualquer quebra estrutural

### Escopo

- entra inventario de hotspots confirmado por auditoria e tamanho real de arquivo
- entra doc operacional no workspace V2
- entra backlog minimo da `Fase 04`
- nao entra refatoracao estrutural ainda
- nao entra redesign de superficie

### Passos

1. cruzar hotspots confirmados pela auditoria com os arquivos vivos mais concentrados
2. publicar matriz com ownership alvo e primeiro corte por hotspot
3. promover a fase nos artefatos operacionais
4. apontar o primeiro hotspot a ser quebrado na sequencia automatica

### Criterio de pronto

- a `Fase 04` passa a ter um mapa inicial de hotspots com ownership claro
- backlog e plano mestre deixam explicito o primeiro alvo estrutural
- a sequencia automatica passa a seguir `InspectorMobileApp.tsx` antes dos demais hotspots

### `MP-015` — Primeiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair estado e efeitos transversais de runtime/configuracao do app raiz

### Objetivo

- iniciar a drenagem real do hotspot mais evidente do mobile sem mexer no comportamento publico
- tirar do app raiz o bloco de automacao do piloto que mistura diagnostico de historico, markers de probe e acks de render humano
- manter a baseline movel inteira verde depois da extracao

### Escopo

- entra novo controller em `android/src/features/common/usePilotAutomationController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o controller extraido
- nao entra redesign de tela
- nao entra troca de payload, bootstrap ou contrato publico

### Passos

1. extrair wrapper de selecao de historico com diagnostico para hook dedicado
2. mover markers/probe e acks de render humano para o mesmo controller
3. reconnectar o app raiz so com a interface do novo controller
4. validar com `jest` focal, `typecheck` e baseline movel completa

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar a logica de automacao do piloto
- o novo controller fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-016` — Segundo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair shell lateral, teclado e apresentacao transitoria do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem mudar a superficie publica
- tirar do app raiz o pacote de runtime/configuracao que ainda misturava observabilidade, crash reports, runtime de voz e aviso de IA
- manter a baseline movel completa verde apos o segundo corte

### Escopo

- entra novo controller em `android/src/features/common/useInspectorRuntimeController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para runtime/configuracao
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. extrair runtime instalado, politica de anexos e config de IA para hook dedicado
2. mover observabilidade, crash reports e runtime de voz para o mesmo controller
3. reconnectar o app raiz usando apenas a saida do novo hook
4. validar com `jest` focal e `npm run quality:baseline`

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar runtime/configuracao transversal
- o novo controller fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-017` — Terceiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e consolidar o mapping massivo de `settingsState` e aliases/setters fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem tocar no comportamento publico
- tirar do app raiz o shell lateral, o ciclo de teclado e a apresentacao transitoria ligada a drawers e modais
- manter a baseline movel completa verde apos o terceiro corte

### Escopo

- entra novo controller em `android/src/features/common/useInspectorShellController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para shell/transitorio
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. extrair estado local de historico, drawers, preview, intro e teclado para hook dedicado
2. mover efeitos de reset transitorio de bloqueio/sessao e scroll condicionado pelo teclado
3. reconnectar o app raiz ao novo controller e manter `useSidePanelsController` encapsulado
4. validar com `jest` focal e `npm run quality:baseline`

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar shell lateral, teclado e apresentacao transitoria
- o novo controller fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-018` — Quarto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a montagem de `buildAuthenticatedLayoutInput` e `buildLoginScreenProps` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o mapping massivo de `settingsState`, aliases e setters acoplados
- manter a baseline movel completa verde apos o quarto corte

### Escopo

- entra novo binding em `android/src/features/settings/useInspectorSettingsBindings.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o binding de settings
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular o mapping de `settingsState` e `settingsActions` em binding dedicado por dominio
2. reconnectar o app raiz por destructuring do binding, preservando os nomes consumidos
3. validar setters acoplados de fala, notificacao e seguranca em teste focal
4. validar com `npm run quality:baseline`

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar o mapping massivo de settings
- o novo binding fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-019` — Quinto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a montagem de `buildInspectorSettingsDrawerInput` e `buildInspectorSessionModalsInput` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a montagem pesada dos props de layout autenticado e da tela de login
- manter a baseline movel completa verde apos o quinto corte

### Escopo

- entra novo builder em `android/src/features/common/buildInspectorScreenProps.ts`
- entra export de tipo em `android/src/features/auth/buildLoginScreenProps.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o builder de props de tela
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de props do layout autenticado em builder puro que consome `inspectorBaseDerivedState` e `threadContextState`
2. encapsular a composicao de props da tela de login em builder puro compartilhado
3. reconnectar o app raiz por blocos `baseState`, `shellState`, `threadState`, `composerState` e `authState`
4. limpar destructuring residual para manter `lint` limpo
5. validar com `npm run quality:baseline`

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline os props do layout autenticado e da tela de login
- o builder novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-020` — Sexto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a montagem de `buildInspectorSettingsDrawerInput` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a montagem inline dos `session modals` usando o estado derivado ja consolidado
- manter a baseline movel completa verde apos o sexto corte

### Escopo

- entra novo builder em `android/src/features/common/buildInspectorRootChromeProps.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o builder de `session modals`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao dos `session modals` em builder puro que consome `inspectorBaseDerivedState`
2. reconnectar o app raiz por blocos `activityAndLockState`, `attachmentState`, `offlineQueueState` e `settingsState`
3. limpar destructuring residual para manter `lint` limpo
4. validar com `npm run quality:baseline`

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline os `session modals`
- o builder novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-021` — Setimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a montagem de `buildSettingsSheetBodyRenderer` e `buildSettingsSheetConfirmAction` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a montagem inline do `settings drawer`, fazendo o shell consumir `baseState` e grupos especificos de settings
- manter a baseline movel completa verde apos o setimo corte

### Escopo

- entra novo builder em `android/src/features/settings/buildInspectorRootSettingsDrawerProps.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o builder do `settings drawer`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao do `settings drawer` em builder puro que consome `inspectorBaseDerivedState`
2. reconnectar o app raiz por blocos `accountState`, `experienceState`, `navigationState`, `securityState` e `supportAndSystemState`
3. limpar destructuring residual para manter `lint` limpo
4. validar com `npm run quality:baseline`

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o `settings drawer`
- o builder novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-022` — Oitavo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `buildSettingsConfirmAndExportActions` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a montagem inline do trilho de `settings sheet`, incluindo `body renderer` e `confirm action`
- manter a baseline movel completa verde apos o oitavo corte

### Escopo

- entra novo builder em `android/src/features/settings/buildInspectorRootSettingsSheetProps.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o builder do `settings sheet`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `buildSettingsSheetBodyRenderer` e `buildSettingsSheetConfirmAction` em builder puro que consome `inspectorBaseDerivedState`
2. reconnectar o app raiz por blocos `accountState`, `actionsState`, `appState`, `backendState`, `baseState`, `draftState` e `settersState`
3. limpar destructuring residual para manter `lint` limpo
4. validar com `npm run quality:baseline`

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de `settings sheet`
- o builder novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-023` — Nono corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useSettingsToggleActions` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de `confirm/export` das configuracoes
- manter a baseline movel completa verde apos o nono corte

### Escopo

- entra novo builder em `android/src/features/settings/buildInspectorRootSettingsConfirmExportActions.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o builder do trilho de `confirm/export`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `buildSettingsConfirmAndExportActions` em builder puro com grupos explicitos de estado e callbacks
2. reconnectar o app raiz por blocos `accountState`, `actionState`, `collectionState`, `draftState`, `preferenceState` e `settersState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de `confirm/export`
- o builder novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-024` — Decimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useSettingsSecurityActions` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de `toggle` das configuracoes
- manter a baseline movel completa verde apos o decimo corte

### Escopo

- entra novo wrapper em `android/src/features/settings/useInspectorRootSettingsToggleActions.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de `toggle`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useSettingsToggleActions` em wrapper de root com grupos explicitos de estado e callbacks
2. reconnectar o app raiz por blocos `actionState`, `cacheState`, `permissionState`, `setterState` e `voiceState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de `toggle`
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-025` — Decimo primeiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useSettingsEntryActions` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de seguranca das configuracoes
- manter a baseline movel completa verde apos o decimo primeiro corte

### Escopo

- entra novo wrapper em `android/src/features/settings/useInspectorRootSettingsSecurityActions.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de seguranca
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useSettingsSecurityActions` em wrapper de root com grupos explicitos de conta, auth, colecoes, setters e callbacks
2. reconnectar o app raiz por blocos `accountState`, `actionState`, `authState`, `collectionState` e `setterState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de seguranca
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-026` — Decimo segundo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useSettingsReauthActions` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de entrada/navegacao das configuracoes
- manter a baseline movel completa verde apos o decimo segundo corte

### Escopo

- entra novo wrapper em `android/src/features/settings/useInspectorRootSettingsEntryActions.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de entrada
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useSettingsEntryActions` em wrapper de root com grupos explicitos de conta, callbacks e setters
2. reconnectar o app raiz por blocos `accountState`, `actionState` e `setterState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de entrada
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-027` — Decimo terceiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useSettingsOperationsActions` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de reautenticacao das configuracoes
- manter a baseline movel completa verde apos o decimo terceiro corte

### Escopo

- entra novo wrapper em `android/src/features/settings/useInspectorRootSettingsReauthActions.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de reautenticacao
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useSettingsReauthActions` em wrapper de root com grupos explicitos de callbacks, estado transitório e setters
2. reconnectar o app raiz por blocos `actionState`, `draftState` e `setterState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de reautenticacao
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-028` — Decimo quarto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useAttachmentController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho operacional de settings
- manter a baseline movel completa verde apos o decimo quarto corte

### Escopo

- entra novo wrapper em `android/src/features/settings/useInspectorRootSettingsOperationsActions.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho operacional
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useSettingsOperationsActions` em wrapper de root com grupos explicitos de callbacks, colecoes, identidade, permissoes, runtime e setters
2. reconnectar o app raiz por blocos `actionState`, `collectionState`, `identityState`, `permissionState`, `runtimeState` e `setterState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho operacional de settings
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-029` — Decimo quinto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useInspectorSession` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de anexos do chat
- manter a baseline movel completa verde apos o decimo quinto corte

### Escopo

- entra novo wrapper em `android/src/features/chat/useInspectorRootAttachmentController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de anexos
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useAttachmentController` em wrapper de root com grupos explicitos de acesso, politica, builders e setters
2. reconnectar o app raiz por blocos `accessState`, `policyState`, `builderState` e `setterState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de anexos
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-030` — Decimo sexto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useHistoryController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de sessao/bootstrap do inspetor
- manter a baseline movel completa verde apos o decimo sexto corte

### Escopo

- entra novo wrapper em `android/src/features/session/useInspectorRootSession.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de sessao
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useInspectorSession` em wrapper de root com grupos explicitos de bootstrap, setters e callbacks
2. reconnectar o app raiz por blocos `bootstrapState`, `setterState` e `callbackState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de sessao
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-031` — Decimo setimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useVoiceInputController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de historico
- manter a baseline movel completa verde apos o decimo setimo corte

### Escopo

- entra novo wrapper em `android/src/features/history/useInspectorRootHistoryController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de historico
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useHistoryController` em wrapper de root com grupos explicitos de estado, callbacks e setters
2. reconnectar o app raiz por blocos `state`, `actionState` e `setterState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de historico
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-032` — Decimo oitavo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useOfflineQueueController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de voz/ditado
- manter a baseline movel completa verde apos o decimo oitavo corte

### Escopo

- entra novo wrapper em `android/src/features/chat/useInspectorRootVoiceInputController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de voz
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useVoiceInputController` em wrapper de root com grupos explicitos de capacidade, vozes e callbacks
2. reconnectar o app raiz por blocos `capabilityState`, `voiceState` e `actionState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de voz
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-033` — Decimo nono corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useActivityCenterController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho de fila offline
- manter a baseline movel completa verde apos o decimo nono corte

### Escopo

- entra novo wrapper em `android/src/features/offline/useInspectorRootOfflineQueueController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do trilho de fila offline
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useOfflineQueueController` em wrapper de root com grupos explicitos de estado, callbacks e setters
2. reconnectar o app raiz por blocos `state`, `actionState` e `setterState`
3. validar com teste focal, `typecheck` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho de fila offline
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-034` — Vigesimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useMesaController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline da central de atividade
- manter a baseline movel completa verde apos o vigesimo corte

### Escopo

- entra novo wrapper em `android/src/features/activity/useInspectorRootActivityCenterController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper da central de atividade
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useActivityCenterController` em wrapper de root com grupos explicitos de estado, callbacks, setters e limites
2. reconnectar o app raiz por blocos `state`, `actionState`, `setterState` e `limitsState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline a central de atividade
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-035` — Vigesimo primeiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useInspectorChatController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do trilho da mesa
- manter a baseline movel completa verde apos o vigesimo primeiro corte

### Escopo

- entra novo wrapper em `android/src/features/mesa/useInspectorRootMesaController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper da mesa
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useMesaController` em wrapper de root com grupos explicitos de estado, refs, cache, callbacks e setters
2. reconnectar o app raiz por blocos `state`, `refState`, `cacheState`, `actionState` e `setterState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o trilho da mesa
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-036` — Vigesimo segundo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de `useAppLockController` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do controller principal do chat
- manter a baseline movel completa verde apos o vigesimo segundo corte

### Escopo

- entra novo wrapper em `android/src/features/chat/useInspectorRootChatController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper do chat
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useInspectorChatController` em wrapper de root com grupos explicitos de sessao, conversa, mesa, setters e callbacks de dominio
2. reconnectar o app raiz por blocos `sessionState`, `conversationState`, `mesaState`, `setterState` e `actionState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o controller principal do chat
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-037` — Vigesimo terceiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a montagem de `buildInspectorBaseDerivedStateInput` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline do controller de bloqueio do app
- manter a baseline movel completa verde apos o vigesimo terceiro corte

### Escopo

- entra novo wrapper em `android/src/features/security/useInspectorRootAppLockController.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o wrapper de app lock
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a composicao de `useAppLockController` em wrapper de root com grupos explicitos de sessao, permissoes, setters e callbacks de seguranca
2. reconnectar o app raiz por blocos `sessionState`, `permissionState`, `setterState` e `actionState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o controller de bloqueio do app
- o wrapper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-038` — Vigesimo quarto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a montagem de `buildInspectorAuthenticatedLayoutScreenProps` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a montagem inline do input base do estado derivado compartilhado
- manter a baseline movel completa verde apos o vigesimo quarto corte

### Escopo

- entra novo helper em `android/src/features/common/buildInspectorRootBaseDerivedStateInput.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o helper root do estado derivado
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a montagem de `buildInspectorBaseDerivedStateInput` em helper root com grupos explicitos de shell, chat, historico/offline, configuracoes e helpers
2. reconnectar o app raiz por blocos `shellState`, `chatState`, `historyAndOfflineState`, `settingsState` e `helperState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o input base do estado derivado
- o helper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-039` — Vigesimo quinto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a montagem de `buildInspectorLoginScreenProps` para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a montagem inline dos props do branch autenticado
- manter a baseline movel completa verde apos o vigesimo quinto corte

### Escopo

- entra novo helper em `android/src/features/common/buildInspectorRootScreenProps.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o helper root de props do layout autenticado
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a montagem de `buildInspectorAuthenticatedLayoutScreenProps` em helper root
2. reconnectar o app raiz preservando os grupos `baseState`, `composerState`, `historyState`, `sessionState`, `shellState`, `speechState`, `threadContextState` e `threadState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline os props do branch autenticado
- o helper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-040` — Vigesimo sexto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair o branch autenticado para um shell dedicado fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a montagem inline dos props do branch de login
- manter a baseline movel completa verde apos o vigesimo sexto corte

### Escopo

- reaproveita `android/src/features/common/buildInspectorRootScreenProps.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o helper root de props do login
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular a montagem de `buildInspectorLoginScreenProps` em helper root
2. reconnectar o app raiz preservando os grupos `authActions`, `authState`, `baseState` e `presentationState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline os props do branch de login
- o helper novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-041` — Vigesimo setimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair o branch de login para um shell dedicado fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o branch autenticado final com o probe de automacao e o layout do inspetor
- manter a baseline movel completa verde apos o vigesimo setimo corte

### Escopo

- entra novo componente em `android/src/features/common/InspectorAuthenticatedShell.tsx`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o shell autenticado
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular o branch autenticado em componente dedicado com `authenticatedLayoutProps`, probe de automacao e `InspectorAuthenticatedLayout`
2. reconnectar o app raiz preservando os helpers root de props ja extraidos
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de renderizar inline o branch autenticado
- o shell novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-042` — Vigesimo oitavo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair o bloco local de efeitos de persistencia/privacidade/retenção para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o branch de login final
- manter a baseline movel completa verde apos o vigesimo oitavo corte

### Escopo

- entra novo componente em `android/src/features/auth/InspectorLoginShell.tsx`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o shell de login
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular o branch de login em componente dedicado com `loginScreenProps` ja montados
2. reconnectar o app raiz preservando o helper root de props do login ja extraido
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de renderizar inline o branch de login
- o shell novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-043` — Vigesimo nono corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e mover os helpers locais de persistencia/retenção para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o bloco local de efeitos de persistencia, privacidade, retenção e sincronizacao critica
- manter a baseline movel completa verde apos o vigesimo nono corte

### Escopo

- entra novo hook em `android/src/features/common/useInspectorRootPersistenceEffects.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova para o hook root de persistencia
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. encapsular os efeitos locais de sincronizacao critica, salvamento local, retencao e reautenticacao em hook root
2. reconnectar o app raiz por blocos `sessionState`, `settingsState`, `dataState`, `actionState` e `setterState`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de montar inline o bloco local de efeitos criticos
- o hook novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-044` — Trigesimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a logica pura de conversa/chat para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz os helpers locais de persistencia, privacidade e retencao ainda usados por bootstrap e efeitos root
- manter a baseline movel completa verde apos o trigesimo corte

### Escopo

- entra novo modulo em `android/src/features/common/inspectorLocalPersistence.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova em `android/src/features/common/inspectorLocalPersistence.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover leitura, escrita e limpeza do estado local de cache, fila offline, notificacoes e historico para utilitario dedicado
2. reconnectar o app raiz no bootstrap de sessao usando closures explicitas para os normalizadores injetados
3. validar com testes focais, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar os helpers locais de persistencia/retenção
- o modulo novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-045` — Trigesimo primeiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair os helpers puros de fila offline e notificacoes do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a logica pura de conversa/chat que ainda servia de cola para sessao, historico, anexos e envio
- manter a baseline movel completa verde apos o trigesimo primeiro corte

### Escopo

- entra novo modulo em `android/src/features/chat/conversationHelpers.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova em `android/src/features/chat/conversationHelpers.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover chaves de rascunho, normalizacao de modo, normalizacao de conversa, composicao de historico e helpers de anexo para utilitario dedicado
2. reconnectar o app raiz e os wrappers root consumindo o modulo novo
3. validar com testes focais, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar a logica pura de conversa/chat
- o modulo novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-046` — Trigesimo segundo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair o agrupamento cronologico do historico para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o pacote puro de fila offline, preview de mensagem e notificacoes de atividade
- manter a baseline movel completa verde apos o trigesimo segundo corte

### Escopo

- entram novos modulos em `android/src/features/common/messagePreviewHelpers.ts`, `android/src/features/offline/offlineQueueHelpers.ts` e `android/src/features/activity/activityNotificationHelpers.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entram coberturas focais novas para os tres modulos
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover preview resumido de referencias, status/backoff/prioridade da fila offline e criacao de notificacoes para modulos puros dedicados
2. reconnectar o app raiz preservando as mesmas interfaces ja consumidas por wrappers root, `derived state` e modais
3. validar com testes focais, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar o pacote puro de fila offline e notificacoes
- os modulos novos ficam cobertos por testes focais
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-047` — Trigesimo terceiro corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair os helpers puros de anexo/arquivo e suporte/export do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o agrupamento cronologico do historico, a aplicacao de preferencias de laudos e o filtro de chips de contexto
- manter a baseline movel completa verde apos o trigesimo terceiro corte

### Escopo

- entra novo modulo em `android/src/features/history/historyHelpers.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova em `android/src/features/history/historyHelpers.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover a logica de seccionamento cronologico e preferencias do historico para helper puro dedicado
2. reconnectar o app raiz e o estado derivado usando o modulo novo
3. validar com testes focais, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar a logica de historico e agrupamento
- o modulo novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-048` — Trigesimo quarto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e drenar o bloco local de `useState` para hook root dedicado

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz os helpers puros de anexo/arquivo, suporte/export e utilitarios de apresentacao que ainda restavam inline
- manter a baseline movel completa verde apos o trigesimo quarto corte

### Escopo

- entram novos modulos em `android/src/features/chat/attachmentFileHelpers.ts` e `android/src/features/common/appSupportHelpers.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entram coberturas focais novas para os dois modulos
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover identidade de anexo, montagem de anexos, exportacao, suporte, timeout e utilitarios de apresentacao para modulos dedicados
2. reconnectar o app raiz preservando as mesmas interfaces consumidas por wrappers root e operacoes de settings
3. validar com testes focais, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar os helpers puros de anexo/arquivo e suporte/export
- os modulos novos ficam cobertos por testes focais
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-049` — Trigesimo quinto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair wiring local de refs, callbacks e bridges de composicao do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o bloco de estado local/transiente que ainda ocupava uma parte grande do componente
- manter a baseline movel completa verde apos o trigesimo quinto corte

### Escopo

- entra novo hook em `android/src/features/common/useInspectorRootLocalState.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova em `android/src/features/common/useInspectorRootLocalState.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover o bloco de `useState` do root para hook dedicado com defaults explicitos
2. reconnectar o app raiz preservando os mesmos nomes publicos de estado e setters
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar o bloco local de estado transiente
- o hook novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-050` — Trigesimo sexto corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e consolidar o suporte de settings para tirar `presentation/navigation/security event log` do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz o pacote local de refs, callbacks imperativos e bridges de composicao usados por historico, voz, refresh e integrações do shell
- manter a baseline movel completa verde apos o trigesimo sexto corte

### Escopo

- entra novo hook em `android/src/features/common/useInspectorRootRefsAndBridges.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova em `android/src/features/common/useInspectorRootRefsAndBridges.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover refs imperativos e bridges de callback para hook root dedicado
2. reconnectar historico, voice input, refresh e shell usando o hook novo
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar refs e bridges imperativos locais
- o hook novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-051` — Trigesimo setimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de sessao/bootstrap/reset para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline de `useSettingsPresentation`, `useSettingsNavigation` e `useSecurityEventLog`
- manter a baseline movel completa verde apos o trigesimo setimo corte

### Escopo

- entra novo hook em `android/src/features/settings/useInspectorRootSettingsSupportState.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova em `android/src/features/settings/useInspectorRootSettingsSupportState.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. agregar presentation, navigation e security event log de settings em hook root unico
2. reconnectar o app raiz preservando os mesmos grupos de estado, setters e callbacks
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar a composicao inline de suporte de settings
- o hook novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-052` — Trigesimo oitavo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao de shell/reset lateral e acesso externo para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a composicao inline de sessao, bootstrap local e reset pos-logout
- manter a baseline movel completa verde apos o trigesimo oitavo corte

### Escopo

- entra novo hook em `android/src/features/session/useInspectorRootSessionFlow.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- entra cobertura focal nova em `android/src/features/session/useInspectorRootSessionFlow.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. agregar bootstrap readers locais, merge de bootstrap cache e reset pos-logout em hook root unico de sessao
2. reconnectar o app raiz preservando o mesmo contrato de `useInspectorRootSession`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar a composicao inline de sessao/bootstrap/reset
- o hook novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-053` — Trigesimo nono corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e extrair a composicao final de tela raiz (`authenticatedState`, `loginState`, `sessionModalsState` e `threadContextInput`) para fora do app raiz

### Objetivo

- continuar a drenagem do hotspot principal do mobile sem alterar comportamento publico
- tirar do app raiz a costura transversal entre shell root, acesso externo e a superficie inteira de settings
- manter a baseline movel completa verde apos o trigesimo nono corte

### Escopo

- entra novo hook em `android/src/features/settings/useInspectorRootSettingsSurface.ts`
- entra novo teste focal em `android/src/features/settings/useInspectorRootSettingsSurface.test.ts`
- entra ajuste de composicao em `android/src/features/InspectorMobileApp.tsx`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. agregar `useInspectorRootSettingsEntryActions`, `useInspectorRootSettingsSecurityActions`, `useInspectorRootSettingsOperationsActions` e `useInspectorRootSettingsUi` em uma superficie root unica de settings
2. reconnectar o app raiz usando `useInspectorRootSettingsSurface` e remover do componente os handlers intermediarios de `entry`, `security` e `operations`
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. fixar o proximo corte estrutural do hotspot sem ambiguidade

### Criterio de pronto

- `InspectorMobileApp.tsx` deixa de concentrar a costura transversal de settings e o wiring residual de shell/acesso externo ja fica fora do componente
- o hook novo fica coberto por teste focal
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural do hotspot fica identificado sem ambiguidade

### `MP-054` — Quadragesimo corte estrutural de `InspectorMobileApp.tsx`

- `status`: concluido em `2026-03-30`; proximo passo direto e quebrar `useInspectorRootApp.ts` por trilhos de sessao, shell, controladores, estado derivado e composicao final

### Objetivo

- concluir a drenagem do componente raiz do mobile sem alterar comportamento publico
- mover o corpo restante do componente para um hook root dedicado
- deixar `InspectorMobileApp.tsx` como orquestrador fino entre shell autenticado e shell de login

### Escopo

- entra novo hook em `android/src/features/useInspectorRootApp.ts`
- entra novo teste focal em `android/src/features/InspectorMobileApp.test.tsx`
- entra ajuste final de composicao em `android/src/features/InspectorMobileApp.tsx`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover o corpo restante do componente para `useInspectorRootApp`
2. reduzir `InspectorMobileApp.tsx` a um branch minimo entre shells autenticado/login
3. validar com teste focal, `typecheck`, `lint` e `npm run quality:baseline`
4. apontar o novo hotspot real apos a drenagem do componente

### Criterio de pronto

- `InspectorMobileApp.tsx` fica reduzido a orquestrador fino
- o wiring restante do root sai fisicamente do componente
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo hotspot fica explicitado sem ambiguidade

### `MP-055` — Quebra de `useInspectorRootApp.ts` em trilhos tematicos

- `status`: concluido em `2026-03-30`; proximo passo direto e quebrar `useInspectorRootPresentation.ts` por estado derivado, input de settings surface e composicao final de tela

### Objetivo

- deixar `useInspectorRootApp.ts` como orquestrador fino do root mobile
- retirar do hook raiz o bootstrap de sessao/settings, os controladores operacionais e a composicao final de tela
- explicitar o novo hotspot real apos a drenagem do hook root

### Escopo

- entra novo hook em `android/src/features/useInspectorRootBootstrap.ts`
- entra novo hook em `android/src/features/useInspectorRootControllers.ts`
- entra novo hook em `android/src/features/useInspectorRootPresentation.ts`
- entra ajuste final de composicao em `android/src/features/useInspectorRootApp.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. mover o bootstrap local de sessao/settings/shell para `useInspectorRootBootstrap`
2. mover os controladores, efeitos persistentes e estado operacional para `useInspectorRootControllers`
3. mover estado derivado, settings surface e composicao final de tela para `useInspectorRootPresentation`
4. reduzir `useInspectorRootApp.ts` a wiring minimo entre os tres trilhos e registrar o novo hotspot

### Criterio de pronto

- `useInspectorRootApp.ts` fica reduzido a orquestrador fino
- o hotspot residual deixa de ser o hook root e passa a estar explicito nos novos modulos grandes
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo corte estrutural fica identificado sem ambiguidade

### `MP-056` — Drenagem final do root móvel para builders e trilhos dedicados

- `status`: concluido em `2026-03-30`; proximo passo direto e atacar `web/app/domains/chat/mesa.py` como hotspot principal da `Fase 04`

### Objetivo

- remover a concentracao residual que ainda ficou em `useInspectorRootPresentation.ts` e `useInspectorRootControllers.ts`
- distribuir o root móvel em builders puros de tela/settings e trilhos operacionais dedicados
- retirar o Android root da frente crítica de hotspots da fase

### Escopo

- entram `buildInspectorRootDerivedState.ts` e `buildInspectorRootFinalScreenState.ts`
- entram `useInspectorRootConversationControllers.ts`, `useInspectorRootOperationalControllers.ts` e `useInspectorRootSecurityAndPersistence.ts`
- entra a familia `android/src/features/settings/buildInspectorRootSettings*State.ts`
- entram testes focais em `useInspectorRootPresentation.test.ts` e `useInspectorRootControllers.test.ts`
- nao entra redesign de tela
- nao entra alteracao de contrato publico

### Passos

1. separar o estado derivado e o wiring final de tela de `useInspectorRootPresentation.ts`
2. quebrar `useInspectorRootSettingsSurfaceUiState` em blocos menores por responsabilidade
3. quebrar `useInspectorRootControllers.ts` em trilhos de conversa, operacao e seguranca/persistencia
4. validar a baseline movel completa e reposicionar o hotspot ativo da fase para o backend web

### Criterio de pronto

- `useInspectorRootPresentation.ts` e `useInspectorRootControllers.ts` ficam como wrappers finos
- nenhum modulo residual do root móvel fica acima de `300` linhas
- `npm run quality:baseline` fecha verde apos a extracao
- o proximo hotspot da fase fica explicitado sem ambiguidade

### Resultado

- `InspectorMobileApp.tsx` manteve `29` linhas; `useInspectorRootApp.ts` ficou com `26`
- `useInspectorRootPresentation.ts` caiu para `37` linhas e `useInspectorRootControllers.ts` caiu para `29`
- os maiores modulos residuais do root móvel passaram a `289`, `274`, `252` e `228` linhas
- a baseline movel fechou verde com `86` suites e `223` testes

### `MP-057` — Drenagem estrutural de `mesa.py`

- `status`: concluido em `2026-03-30`; proximo passo direto e atacar `web/app/domains/chat/chat_stream_routes.py`

### Objetivo

- retirar de `mesa.py` o acoplamento entre thread, feed mobile, contrato publico V2 e mutacoes do canal
- manter a superficie publica estavel para `router.py`, `mobile_probe.py` e testes existentes
- deixar `mesa.py` apenas como shell de roteamento e export

### Escopo

- entram `mesa_common.py`, `mesa_thread_routes.py`, `mesa_feed_routes.py` e `mesa_message_routes.py`
- entra a reducao de `mesa.py` para shell com aliases/export publicos estaveis
- entram validacoes de contrato Android, sync móvel e rotas criticas
- nao entra redesign de payload
- nao entra troca de contrato publico

### Passos

1. mapear imports externos e manter os simbolos publicos de `mesa.py`
2. mover helpers compartilhados e fatias de rota para modulos dedicados
3. reduzir `mesa.py` a shell de `APIRouter` e `add_api_route`
4. validar sintaxe, contratos Android, sync móvel e rotas criticas
5. reposicionar o hotspot ativo da fase para `chat_stream_routes.py`

### Criterio de pronto

- `mesa.py` fica como shell fino e estavel
- feed/thread/mensagem/anexo da mesa ficam em modulos separados por responsabilidade
- contratos Android e rotas criticas fecham verdes sem regressao
- o proximo hotspot da fase fica explicito sem ambiguidade

### Resultado

- `mesa.py` caiu de `1504` para `117` linhas
- o canal foi distribuido em `mesa_common.py`, `mesa_thread_routes.py`, `mesa_feed_routes.py` e `mesa_message_routes.py`
- `python3 -m compileall` fechou verde para os modulos novos
- `pytest -q tests/test_v2_android_case_feed_adapter.py tests/test_v2_android_case_thread_adapter.py tests/test_v2_android_public_contract.py` fechou com `12 passed`
- `pytest -q tests/test_portais_acesso_critico.py tests/test_regras_rotas_criticas.py` fechou com `136 passed`
- `pytest -q tests/test_mesa_mobile_sync.py tests/test_v2_android_request_trace_gap.py tests/test_v2_android_rollout_metrics.py tests/test_v2_android_rollout.py tests/test_smoke.py` fechou com `39 passed`

### `MP-058` — Drenagem estrutural de `chat_stream_routes.py`

- `status`: concluido em `2026-03-30`; proximo passo direto e atacar `web/app/domains/cliente/dashboard_bootstrap.py`

### Objetivo

- retirar de `chat_stream_routes.py` a mistura entre preparacao de entrada, persistencia da mensagem inicial e transporte SSE
- preservar a superficie publica da rota e os pontos de monkeypatch dos testes do hard gate documental
- deixar `chat_stream_routes.py` apenas como shell de orquestracao

### Escopo

- entram `chat_stream_support.py` e `chat_stream_transport.py`
- entra a reducao de `chat_stream_routes.py` para shell fino
- entram validacoes de hard gate documental, rotas criticas e smoke do chat
- nao entra redesign de payload
- nao entra troca de contrato publico

### Passos

1. mapear os blocos de entrada/comando/laudo, persistencia inicial e transporte SSE
2. mover preparacao e persistencia inicial para modulo dedicado
3. mover whisper SSE e stream da IA para modulo dedicado
4. manter `rota_chat` no shell para preservar compatibilidade de monkeypatch
5. validar rotas e smokes do fluxo de chat

### Criterio de pronto

- `chat_stream_routes.py` fica como shell fino
- o transporte SSE fica isolado do preparo/persistencia do fluxo
- testes do hard gate documental e do chat seguem verdes
- o proximo hotspot fica explicito sem ambiguidade

### Resultado

- `chat_stream_routes.py` caiu de `479` para `97` linhas
- a preparacao/persistencia inicial foi movida para `chat_stream_support.py`
- o transporte SSE do whisper e da IA foi movido para `chat_stream_transport.py`
- `python3 -m compileall` fechou verde para os modulos novos
- `pytest -q tests/test_v2_document_hard_gate_10f.py tests/test_v2_document_hard_gate_10g.py` fechou com `5 passed`
- `pytest -q tests/test_regras_rotas_criticas.py tests/test_smoke.py` fechou com `149 passed`

### `MP-059` — Drenagem estrutural de `dashboard_bootstrap.py`

- `status`: concluido em `2026-03-30`; proximo passo direto e atacar `web/app/domains/revisor/panel.py`

### Objetivo

- retirar de `dashboard_bootstrap.py` a mistura entre serializacao publica, bootstrap legado e shadow canônico do admin-cliente
- preservar a superficie publica importada por `dashboard.py` e pelos testes do tenant admin
- deixar `dashboard_bootstrap.py` apenas como shell de composicao

### Escopo

- entram `dashboard_bootstrap_support.py` e `dashboard_bootstrap_shadow.py`
- entra a reducao de `dashboard_bootstrap.py` para shell fino
- entram validacoes do bootstrap do tenant admin, boundary do portal cliente e smoke do portal
- nao entra redesign do portal
- nao entra troca de contrato publico

### Passos

1. mover serializacao publica e listagens para modulo de suporte
2. mover o shadow canônico do tenant admin para modulo dedicado
3. reduzir `dashboard_bootstrap.py` a composicao do payload legado e do hook shadow
4. validar projeção, guards do portal cliente e smoke
5. reposicionar o hotspot ativo da fase para `panel.py`

### Criterio de pronto

- `dashboard_bootstrap.py` fica como shell fino
- leitura gerencial publica e shadow canônico ficam explicitamente separados
- os testes administrativos seguem verdes sem regressao
- o proximo hotspot da fase fica explicito sem ambiguidade

### Resultado

- `dashboard_bootstrap.py` caiu de `285` para `80` linhas
- a serializacao publica foi movida para `dashboard_bootstrap_support.py`
- o shadow canônico foi movido para `dashboard_bootstrap_shadow.py`
- `python3 -m compileall` fechou verde para os modulos novos
- `pytest -q tests/test_v2_tenant_admin_projection.py tests/test_cliente_portal_critico.py tests/test_portais_acesso_critico.py tests/test_tenant_boundary_matrix.py tests/test_rbac_action_matrix.py` fechou com `30 passed`
- `pytest -q tests/test_smoke.py` fechou com `26 passed`

### `MP-060` — Drenagem estrutural de `panel.py`

- `status`: concluido em `2026-03-30`; fechamento da `Fase 04`

### Objetivo

- retirar de `panel.py` a mistura entre filtros, queries, serializacao de fila, totais operacionais e render SSR
- preservar a rota `painel_revisor` e o monkeypatch de `templates` usado pelos testes
- deixar `panel.py` apenas como shell SSR fino da fila da mesa

### Escopo

- entram `panel_state.py` e `panel_shadow.py`
- entra a reducao de `panel.py` para shell fino
- entram validacoes da projeção da fila, boot do painel, contratos SSR e smoke amplo
- nao entra redesign do painel
- nao entra troca de contrato publico

### Passos

1. mover filtros, queries e serializacao de fila para modulo dedicado de estado
2. mover o shadow canônico da fila para modulo dedicado
3. reduzir `panel.py` a orquestracao do estado + render `TemplateResponse`
4. validar projeção, boot do painel, guards e smoke
5. promover a `Fase 04` se os gates globais continuarem verdes

### Criterio de pronto

- `panel.py` fica como shell fino
- fila, resumo e estado de tela deixam de ficar misturados na rota SSR
- os testes focais e amplos da mesa/revisor seguem verdes
- `make verify` e `make contract-check` voltam a fechar verdes

### Resultado

- `panel.py` caiu de `525` para `49` linhas
- o estado SSR da fila foi movido para `panel_state.py`
- o shadow canônico foi movido para `panel_shadow.py`
- `pytest -q tests/test_v2_review_queue_projection.py tests/test_reviewer_panel_boot_hotfix.py tests/test_multiportal_bootstrap_contracts.py tests/test_portais_acesso_critico.py tests/test_regras_rotas_criticas.py tests/test_smoke.py` fechou com `168 passed`
- `make contract-check` fechou com `16 passed`
- `make verify` voltou a fechar verde apos a formatacao do mobile e os cortes finais da fase

### `MP-061` — Promoção da `Fase 04`

- `status`: concluido em `2026-03-30`; frente atual passa a ser `Fase 05 - Inspetor web`

### Objetivo

- confirmar que os hotspots priorizados da arquitetura foram drenados sem regressao
- recolocar `make verify` e `make contract-check` como gates finais da promoção
- encerrar a fase com ownership claro e shells estáveis

### Resultado

- `mesa.py`, `chat_stream_routes.py`, `dashboard_bootstrap.py` e `panel.py` ficaram como shells finos
- o root móvel deixou de ser hotspot crítico e ficou em regime de guardrail
- `make verify` e `make contract-check` fecharam verdes em `2026-03-30`
- a frente principal passa a ser `Fase 05 - Inspetor web`

### `MP-062` — Fechamento da `Fase 05 - Inspetor web`

- `status`: concluido em `2026-03-30`; frente atual passa a ser `Fase 06 - Mesa`

### Objetivo

- fechar o trilho ponta a ponta do inspetor web antes de mover a frente principal para a Mesa
- validar envio do chat, envio da mesa no inspetor, anexos/preview, loading/fallback/retry, `SSE`/reconexao e coerencia entre `home`, sidebar, query param e sessao
- promover a fase apenas com os gates canonicos locais novamente verdes

### Escopo

- entram ajustes em `chat_index_page.js`, templates do workspace e `CSS` pontual do composer
- entram suites focais do inspetor e `Playwright` representativo
- entram `make verify` e `make contract-check` como gates finais
- nao entra redesign da interface do inspetor
- nao entra contrato novo multissuperficie

### Passos

1. corrigir preview e limpeza de anexo no composer tecnico
2. corrigir a autoridade do contexto com `?laudo=`/API e a resincronizacao de tela/SSE
3. eliminar a duplicidade do affordance `home` no header do workspace
4. validar com suites focais do inspetor, subset `Playwright` e gates completos do repositorio
5. promover a fase se os gates continuarem verdes

### Criterio de pronto

- o inspetor fecha os fluxos criticos de envio, mesa, anexo, `home`, sidebar, query param, sessao e `SSE` sem regressao conhecida
- o subset `Playwright` representativo do inspetor fica verde
- `make verify` e `make contract-check` ficam verdes
- a proxima fase fica explicita sem ambiguidade

### Resultado

- `preview-anexo` foi movido para dentro do composer tecnico em `web/templates/inspetor/_workspace.html`, eliminando o conflito de geometria com o header fixo
- o botao de remocao do preview foi reposicionado em `web/static/css/chat/chat_base.css`, preservando clique e visibilidade do chip de anexo
- `web/static/js/chat/chat_index_page.js` passou a tratar `?laudo=` e contexto vindo da API como autoridade suficiente para promover a superficie de inspecao, alem de resincronizar `screen`/`SSE` automaticamente apos snapshot valido
- a duplicidade de `.btn-home-cabecalho` foi eliminada em `web/templates/inspetor/workspace/_workspace_header.html`, preservando a semantica `data-action="go-home"` sem ambiguidade no DOM
- `pytest -q tests/test_inspector_active_report_authority.py tests/test_app_boot_query_reduction.py tests/test_chat_notifications.py tests/test_chat_runtime_support.py` fechou com `11 passed`
- `pytest -q tests/test_regras_rotas_criticas.py -k 'home_app_nao_desloga_inspetor or home_desativa_contexto_sem_excluir_laudo or home_nao_exibe_rascunho_sem_interacao_na_sidebar'` fechou com `3 passed`
- `RUN_E2E=1 pytest -q tests/e2e/test_portais_playwright.py -k 'home_com_laudo_ativo_retorna_para_tela_inicial_sem_deslogar or historico_pin_unpin_e_excluir_laudo'` fechou com `2 passed`
- `make contract-check` fechou com `16 passed`
- `make verify` voltou a fechar verde em `2026-03-30`
- a frente principal passa a ser `Fase 06 - Mesa`

## Template

### Objetivo

- o que precisa ficar resolvido

### Escopo

- o que entra
- o que não entra

### Passos

1. diagnóstico
2. implementação
3. validação
4. documentação

### Critério de pronto

- quais comandos precisam passar
- quais comportamentos precisam ser validados
- qual documento precisa ser atualizado
