# Loop de Refatoração do Frontend

## Objetivo

Executar a refatoração completa do frontend do projeto oficial de forma iterativa, segura e rastreável, sem perder o estado do trabalho quando o contexto da conversa for compactado.

Repositório oficial:

- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`

Remoto oficial:

- `git@github.com:gstarielio-hash/tariel-web.git`

Branch operacional atual:

- `checkpoint/20260331-current-worktree`

## Regra do loop

Cada ciclo deve seguir exatamente esta ordem:

1. Reanalisar o frontend e localizar o maior hotspot estrutural seguro.
2. Escolher um corte pequeno e coeso.
3. Refatorar sem alterar regra de negócio.
4. Validar com checagens e testes compatíveis com o corte.
5. Fazer commit.
6. Fazer push.
7. Reanalisar o restante e registrar o próximo hotspot.

## Critérios obrigatórios por ciclo

- Trabalhar apenas no projeto oficial.
- Não usar `/tmp` como base de trabalho do produto.
- Não alterar autenticação, permissões, cobrança, banco ou endpoints críticos sem necessidade explícita.
- Preferir cortes estruturais com baixo risco:
  - extração de módulos;
  - separação por responsabilidade;
  - redução de arquivos monolíticos;
  - consolidação de helpers;
  - organização de templates, JS e CSS;
  - melhoria de nomenclatura e previsibilidade.
- Rodar validação antes de commit e push.
- Registrar o que foi feito e o próximo corte neste arquivo.

## Critério de parada

Encerrar o loop quando os pontos abaixo forem verdadeiros ao mesmo tempo:

- não houver mais arquivos monolíticos ou acoplamentos gritantes no frontend;
- o próximo corte passar a ser mais arriscado do que útil;
- a arquitetura do frontend estiver estável, previsível e dividida por responsabilidade;
- os principais portais estiverem organizados sem dívida estrutural relevante remanescente.

## Mapa inicial dos hotspots

### Web

- `web/static/js/chat/chat_index_page.js`
  - hotspot principal atual;
  - arquivo monolítico com mais de 8 mil linhas;
  - concentra estado, boot, bindings de UI, sincronização e fluxo do inspetor.

- `web/templates/admin/catalogo_familia_detalhe.html`
  - template grande e denso.

- `web/templates/admin/cliente_detalhe.html`
  - template grande e denso.

- `web/templates/painel_revisor.html`
  - template central da revisão técnica; já passou por ajustes, mas continua importante.

- `web/static/css/revisor/painel_revisor.css`
  - folha grande, candidata a divisão futura por regiões.

### Mobile

- existe superfície Android no diretório `android/`;
- a refatoração começa pelo web;
- o mobile será reavaliado em ciclos próprios depois da estabilização estrutural inicial do web.

## Ciclos

### Ciclo 0 — Saneamento da branch

Status:

- concluído

Objetivo:

- restaurar a saúde da branch antes de iniciar a nova refatoração do frontend.

Resultado:

- suíte crítica voltou a passar;
- branch voltou a publicar;
- commit publicado:
  - `a621c34 fix(web): restore critical branch health`

### Ciclo 1 — Separação dos bindings de UI do inspetor

Status:

- concluído

Hotspot atacado:

- `web/static/js/chat/chat_index_page.js`

Corte escolhido:

- extrair os bindings de UI do inspetor para módulo próprio em `web/static/js/inspetor/ui_bindings.js`

Objetivo do corte:

- reduzir acoplamento do arquivo principal do inspetor;
- mover wiring de interface para módulo específico;
- preparar próximos cortes sem alterar comportamento funcional.

Arquivos do ciclo:

- `web/static/js/inspetor/ui_bindings.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`
- `web/scripts/inspecao_visual_inspetor.py`

Validação executada:

- `node --check` nos arquivos JS alterados;
- `git diff --check`;
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - corrigido o seletor do modal de nova inspeção para usar o contrato real da UI;
  - capturas geradas em:
    - `web/artifacts/visual/inspetor/20260419-164640/`
- `AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py`
  - comportamento padrão:
    - `skipped`
    - motivo: exige `RUN_E2E=1`
- `RUN_E2E=1 AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py`
  - resultado:
    - `1 passed`

Resultado estrutural do ciclo:

- `chat_index_page.js` perdeu o bloco central de bindings de interface;
- o wiring de UI do inspetor ficou isolado em módulo próprio;
- a inspeção visual do inspetor voltou a localizar e abrir o modal de nova inspeção;
- o loop segue íntegro no repositório oficial, sem uso de `/tmp`.

## Próximo hotspot provável após o ciclo 1

Próximos candidatos, em ordem:

1. separar eventos de sistema do inspetor do `chat_index_page.js`
   - hoje `bindEventosSistema()` ainda concentra sincronização de workspace, mesa, histórico e tela.
2. separar boot/orquestração do inspetor
   - reduzir o papel do arquivo principal como ponto único de inicialização.
3. revisar extrações restantes de workspace, histórico e fluxo de mesa
   - continuar removendo responsabilidade transversal do monólito.
4. só depois avançar para CSS e templates grandes do admin/revisão
   - especialmente `painel_revisor.css`, `catalogo_familia_detalhe.html` e `cliente_detalhe.html`.

### Ciclo 2 — Separação dos eventos de domínio do inspetor

Status:

- concluído

Hotspot atacado:

- `web/static/js/chat/chat_index_page.js`

Corte escolhido:

- extrair os listeners de eventos de domínio do inspetor para `web/static/js/inspetor/system_events.js`

Objetivo do corte:

- reduzir o papel do arquivo principal como central de eventos;
- isolar sincronizações de relatório, mesa, histórico e seleção de laudo;
- preservar no arquivo principal apenas os listeners de ciclo de vida da página e o modo foco.

Arquivos do ciclo:

- `web/static/js/inspetor/system_events.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`

Validação executada:

- `node --check web/static/js/inspetor/system_events.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `git diff --check`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `31 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - capturas geradas em:
    - `web/artifacts/visual/inspetor/20260419-165926/`
- `RUN_E2E=1 AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py`
  - resultado:
    - `1 passed`

Resultado estrutural do ciclo:

- os eventos de domínio saíram do arquivo principal e foram para um módulo dedicado;
- `chat_index_page.js` caiu para `8096` linhas;
- o boot do inspetor ficou mais legível;
- o comportamento visual do inspetor continuou íntegro com validação real.

## Próximo hotspot provável após o ciclo 2

Próximos candidatos, em ordem:

1. separar boot/orquestração do inspetor
   - reduzir o arquivo principal como ponto único de inicialização.
2. revisar extrações restantes de workspace, histórico e fluxo de mesa
   - especialmente sincronização de telas e contexto lateral.
3. só depois avançar para CSS e templates grandes do admin/revisão
   - `painel_revisor.css`, `catalogo_familia_detalhe.html` e `cliente_detalhe.html`.

### Ciclo 3 — Separação do boot/orquestração do inspetor

Status:

- concluído

Hotspot atacado:

- `web/static/js/chat/chat_index_page.js`

Corte escolhido:

- extrair a orquestração de inicialização para `web/static/js/inspetor/bootstrap.js`

Objetivo do corte:

- reduzir o arquivo principal como ponto único de inicialização;
- isolar o fluxo de bootstrap do inspetor em módulo próprio;
- manter no arquivo principal apenas a casca do `boot()` e a instrumentação de performance.

Arquivos do ciclo:

- `web/static/js/inspetor/bootstrap.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`

Validação executada:

- `node --check web/static/js/inspetor/bootstrap.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `git diff --check`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `31 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - capturas geradas em:
    - `web/artifacts/visual/inspetor/20260419-170731/`
- `RUN_E2E=1 AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py`
  - resultado:
    - `1 passed`

Resultado estrutural do ciclo:

- o fluxo de bootstrap saiu do arquivo principal e foi para um módulo dedicado;
- `chat_index_page.js` caiu para `7949` linhas;
- a orquestração do inspetor ficou mais previsível;
- a captura visual e o E2E real do inspetor continuaram íntegros após a extração.

## Próximo hotspot provável após o ciclo 3

Próximos candidatos, em ordem:

1. revisar extrações restantes de workspace, histórico e fluxo de mesa
   - especialmente observadores, sincronização lateral e atualização derivada de telas.
2. separar observadores do inspetor
   - `inicializarObservadorSidebarHistorico()` e `inicializarObservadorWorkspace()` ainda vivem no monólito.
3. só depois avançar para CSS e templates grandes do admin/revisão
   - `painel_revisor.css`, `catalogo_familia_detalhe.html` e `cliente_detalhe.html`.

### Ciclo 4 — Separação dos observers do inspetor

Status:

- concluído

Hotspot atacado:

- `web/static/js/chat/chat_index_page.js`

Corte escolhido:

- extrair os observers do sidebar e do workspace para `web/static/js/inspetor/observers.js`

Objetivo do corte:

- remover watchers e cleanup manual do arquivo principal;
- isolar a inicialização e o teardown dos observers em módulo próprio;
- reduzir o acoplamento entre renderização do workspace e ciclo de vida da página.

Arquivos do ciclo:

- `web/static/js/inspetor/observers.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`

Validação executada:

- `node --check web/static/js/inspetor/observers.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `git diff --check`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `31 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - capturas geradas em:
    - `web/artifacts/visual/inspetor/20260419-171340/`
- `RUN_E2E=1 AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py`
  - resultado:
    - `1 passed`

Resultado estrutural do ciclo:

- os observers saíram do arquivo principal e ganharam teardown explícito;
- `chat_index_page.js` caiu para `7888` linhas;
- o cleanup de `pagehide` ficou mais simples e previsível;
- a captura visual e o E2E real do inspetor continuaram estáveis.

## Próximo hotspot provável após o ciclo 4

Próximos candidatos, em ordem:

1. revisar extrações restantes de workspace, histórico e fluxo de mesa
   - especialmente atualização derivada do workspace e sincronização lateral.
2. separar blocos derivativos do workspace
   - `atualizarPainelWorkspaceDerivado()` e renderizações associadas ainda concentram bastante responsabilidade.
3. só depois avançar para CSS e templates grandes do admin/revisão
   - `painel_revisor.css`, `catalogo_familia_detalhe.html` e `cliente_detalhe.html`.

### Ciclo 5 — Separação das derivadas do workspace

Status:

- concluído

Hotspot atacado:

- `web/static/js/chat/chat_index_page.js`

Corte escolhido:

- extrair os resumos e renderizações derivadas do workspace para `web/static/js/inspetor/workspace_derivatives.js`

Objetivo do corte:

- remover do arquivo principal o bloco de derivação visual do workspace;
- isolar resumos de histórico e pendências, atividade, progresso, anexos e atualização derivada;
- reduzir o acoplamento entre leitura do DOM e renderizações auxiliares do workspace.

Arquivos do ciclo:

- `web/static/js/inspetor/workspace_derivatives.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`

Validação executada:

- `node --check web/static/js/inspetor/workspace_derivatives.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `git diff --check`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `31 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - capturas geradas em:
    - `web/artifacts/visual/inspetor/20260419-172458/`
- `RUN_E2E=1 AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py`
  - resultado:
    - `1 passed`

Resultado estrutural do ciclo:

- o pacote de derivação visual do workspace saiu do arquivo principal;
- `chat_index_page.js` caiu para `7461` linhas;
- a atualização derivada do workspace ficou encapsulada em módulo próprio;
- a captura visual e o E2E real do inspetor seguiram íntegros após a extração.

## Próximo hotspot provável após o ciclo 5

Próximos candidatos, em ordem:

1. revisar extrações restantes do fluxo de mesa
   - ainda há bastante responsabilidade operacional concentrada em integrações do widget e do workspace.
2. separar blocos de renderização de governança e resumo executivo do inspetor
   - ainda existem renderizações acopladas ao arquivo principal.
3. só depois avançar para CSS e templates grandes do admin/revisão
   - `painel_revisor.css`, `catalogo_familia_detalhe.html` e `cliente_detalhe.html`.

### Ciclo 6 — Separação da governança do inspetor

Status:

- concluído

Hotspot atacado:

- `web/static/js/chat/chat_index_page.js`

Corte escolhido:

- extrair o bloco de governança documental do inspetor para `web/static/js/inspetor/governance.js`

Objetivo do corte:

- remover do arquivo principal as regras de resumo de governança e reemissão;
- isolar a decisão de finalização, verificação pública e emissão oficial em módulo próprio;
- preparar a próxima extração do resumo executivo do workspace sem misturar responsabilidades.

Arquivos do ciclo:

- `web/static/js/inspetor/governance.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`

Validação executada:

- `node --check web/static/js/inspetor/governance.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `git diff --check`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `31 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - capturas geradas em:
    - `web/artifacts/visual/inspetor/20260419-183729/`

Resultado estrutural do ciclo:

- o pacote de governança do inspetor saiu do arquivo principal;
- `chat_index_page.js` caiu para `7245` linhas;
- o contrato de ações do runtime do inspetor ficou mais explícito;
- a captura visual do inspetor continuou íntegra após a extração.

## Próximo hotspot provável após o ciclo 6

Próximos candidatos, em ordem:

1. separar o resumo executivo e os cards de verificação/emissão do workspace
   - ainda há renderizações resumidas e acopladas ao arquivo principal.
2. revisar extrações restantes do fluxo de mesa
   - ainda existe responsabilidade operacional relevante entre workspace e widget.
3. só depois avançar para CSS e templates grandes do admin/revisão
   - `painel_revisor.css`, `catalogo_familia_detalhe.html` e `cliente_detalhe.html`.

### Ciclo 7 — Separação do overview do workspace

Status:

- concluído

Hotspot atacado:

- `web/static/js/chat/chat_index_page.js`

Corte escolhido:

- extrair o resumo executivo, navegação e cards de verificação/emissão do workspace para `web/static/js/inspetor/workspace_overview.js`

Objetivo do corte:

- remover do arquivo principal o pacote de overview do workspace;
- isolar navegação lateral, resumo executivo e status documental em módulo próprio;
- continuar reduzindo o acoplamento entre estado do inspetor e renderização resumida da interface.

Arquivos do ciclo:

- `web/static/js/inspetor/workspace_overview.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`

Validação executada:

- `node --check web/static/js/inspetor/workspace_overview.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `git diff --check`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `31 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - capturas geradas em:
    - `web/artifacts/visual/inspetor/20260419-184957/`

Resultado estrutural do ciclo:

- o pacote de overview do workspace saiu do arquivo principal;
- `chat_index_page.js` caiu para `7058` linhas;
- a navegação resumida e os cards documentais do workspace ficaram encapsulados;
- a auditoria visual continuou íntegra após a extração e o ajuste do wiring de runtime.

## Próximo hotspot provável após o ciclo 7

Próximos candidatos, em ordem:

1. revisar extrações restantes do fluxo de mesa
   - ainda existe responsabilidade operacional relevante entre workspace e widget.
2. separar mais blocos do contexto IA e ações do workspace
   - ainda há renderizações e utilitários de contexto presos ao arquivo principal.
3. só depois avançar para CSS e templates grandes do admin/revisão
   - `painel_revisor.css`, `catalogo_familia_detalhe.html` e `cliente_detalhe.html`.
