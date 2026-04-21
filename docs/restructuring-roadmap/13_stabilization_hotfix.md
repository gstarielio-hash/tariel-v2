# Fase de Estabilização Urgente do Web

## Objetivo

Restaurar a usabilidade básica do ambiente web antes de qualquer nova medição ou reestruturação profunda, com foco em:

- `/app`
- Portal do Inspetor
- fluxo de `Novo Chat`
- `Nova Inspeção`
- abertura de laudo recente
- conversa focada
- boot básico de `/cliente` e `/revisao`

Esta fase foi tratada como hotfix de estabilização. Não houve mudança de arquitetura, regra de negócio, endpoint, contrato, payload, auth/session/multiportal ou comportamento funcional de produto fora do escopo de correção de regressão.

## Escopo do hotfix

Arquivos estabilizados diretamente:

- `web/static/js/shared/api-core.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-render.js`
- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`
- `web/app/core/perf_support.py`
- `web/app/domains/chat/session_helpers.py`
- `web/templates/base.html`
- `web/templates/dashboard.html`
- `web/templates/cliente_portal.html`
- `web/templates/painel_revisor.html`

## Causas raiz confirmadas no código

### 1. Perf mode contaminando o modo normal

Confirmado em `web/static/js/shared/api-core.js`.

Antes do hotfix, a ativação de performance podia continuar viva no frontend por:

- `?perf=1`
- `localStorage.tarielPerf=1`

Isso era perigoso porque `api-core.js` instrumenta runtime global quando o perf está ativo:

- `fetch`
- XHR
- `EventTarget.addEventListener`
- `MutationObserver`
- `Storage`

Na prática, isso aumentava custo de boot, frequência de callbacks e ruído no runtime do `/app`, inclusive quando a intenção do usuário era usar o modo normal.

### 2. Observer global de UI sensível demais

Confirmado em `web/static/js/shared/ui.js`.

O dock rápido observava `document.body` com `MutationObserver` em um escopo amplo demais para um shell que troca datasets e regiões do DOM com frequência. Esse tipo de observação no corpo inteiro amplifica:

- callbacks por mutação visual irrelevante
- sincronizações redundantes
- custo de navegação entre estados

### 3. Observer do workspace reagindo demais ao churn do chat

Confirmado em `web/static/js/chat/chat_index_page.js`.

O workspace do inspetor observava `#area-mensagens` e, a cada ciclo de mutação, disparava recomposição derivada do painel. Como o chat gera mutação contínua durante:

- streaming de mensagens
- anexos
- cartões derivados
- mudança de estado da tela

isso criava risco de cascata entre observador, re-render derivado e sincronização de tela.

### 4. Falta de guarda contra reentrância na sincronização principal do Inspetor

Confirmado em `web/static/js/chat/chat_index_page.js`.

`sincronizarInspectorScreen()` é um orquestrador central. Sem contenção, chamadas concorrentes ou encadeadas durante a mesma fase de renderização podiam amplificar:

- escrita repetida em `dataset`
- emissão redundante de `tariel:screen-synced`
- recomputação de visibilidade de raízes, rail e widgets

### 5. Falha de módulo opcional podendo contaminar o boot

Confirmado em `web/static/js/chat/chat_index_page.js` e `web/static/js/shared/api.js`.

Módulos auxiliares do inspetor e factories compartilhadas tinham pontos de inicialização frágeis. Se um módulo opcional falhasse, o efeito colateral podia quebrar o resto da página em vez de degradar com segurança.

### 6. Assunções rígidas de DOM em áreas parciais

Confirmado em `web/static/js/shared/chat-render.js` e reforçado em `web/static/js/shared/ui.js`.

Algumas rotinas assumiam presença obrigatória de elementos que, em boot parcial, telas incompletas ou transições intermediárias, podem ainda não existir.

## O que foi corrigido ou protegido

### Isolamento real do perf mode

Aplicado em:

- `web/static/js/shared/api-core.js`
- `web/app/core/perf_support.py`
- `web/app/domains/chat/session_helpers.py`
- `web/templates/base.html`
- `web/templates/dashboard.html`
- `web/templates/cliente_portal.html`
- `web/templates/painel_revisor.html`

Mudanças:

- o frontend só entra em perf mode se o backend autorizar explicitamente via `perf_mode`
- `?perf=1` e `localStorage.tarielPerf=1` não ativam mais instrumentação sozinhos
- `window.__TARIEL_DISABLE_PERF__ === true` continua como kill switch global
- rotas `/debug-perf/*` agora só existem quando `settings.perf_mode` está ativo e fora de produção
- instrumentação SQL não registra fora do modo de backend permitido

Resultado esperado:

- o modo normal não fica mais contaminado por estado antigo de debug/perf
- `/app`, `/cliente` e `/revisao` carregam sem o custo extra do coletor global

### Contenção de observers e sincronizações em cascata

Aplicado em:

- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`

Mudanças:

- o observer do dock rápido passou a observar apenas atributos específicos do `body`
- o observer do workspace foi reduzido para `childList + subtree`, removendo `characterData`
- sincronizações passaram a ser agendadas por `requestAnimationFrame`
- a recomposição do painel derivado ganhou guarda contra reentrância
- a sincronização central da tela ganhou guarda contra reentrância e colapso de chamadas pendentes
- limpeza de `requestAnimationFrame` foi adicionada no `pagehide`

Resultado esperado:

- menos loops de recomposição
- menos eventos em cascata
- menos chance de travamento do navegador durante churn do chat

### Fail-safe no boot do Inspetor

Aplicado em:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-render.js`

Mudanças:

- ações opcionais do runtime do inspetor agora têm defaults no-op
- registro de módulos opcionais foi cercado por `try/catch`
- falha em `registerModals`, `registerPendencias`, `registerMesaWidget` ou `registerNotifications` passa a registrar warning e degradar
- `ChatRenderFactory` e `ChatNetworkFactory` em `api.js` agora falham com segurança
- `chat-render.js` não derruba a página se `areaMensagens` estiver ausente; registra warning e sai

Resultado esperado:

- falhas localizadas deixam de derrubar a página inteira
- o shell principal do inspetor continua inicializando mesmo com módulo opcional falhando

### Resiliência de foco e DOM parcial

Aplicado em:

- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`

Mudanças:

- foco no composer agora só acontece se o campo realmente estiver visível e interativo
- rotinas de foco ignoram elementos escondidos, `hidden`, `inert` ou sem caixa visível

Resultado esperado:

- menos loops de foco
- menos scroll/focus em elementos indisponíveis
- menos risco de travamento visual em transição de tela

## O que foi desativado por segurança

Desativado no modo normal:

- ativação implícita de perf via query string ou `localStorage` sem autorização do backend
- rotas `/debug-perf/*` fora de `PERF_MODE`
- instrumentação SQL fora de `PERF_MODE`

Reduzido por segurança:

- observação ampla do `body` no shell de UI
- frequência de sincronização derivada do workspace
- propagação de falha de módulos opcionais do inspetor

## O que continua frágil

### Confirmado

- `web/static/js/chat/chat_index_page.js` continua concentrando responsabilidade demais
- o runtime do inspetor ainda depende de muitos estados globais e datasets no `body`
- a tela do inspetor ainda possui alta sensibilidade a sincronização entre `workspaceStage`, `inspectorScreen` e `inspectorBaseScreen`

### Inferência provável

- ainda existe risco residual em fluxos longos com streaming, anexos e troca rápida entre portal/workspace
- o shell visual do inspetor ainda merece revisão futura de fronteiras entre controller central e módulos de apoio
- `/cliente` e `/revisao` ficaram protegidos contra contaminação de perf, mas ainda podem ter gargalos próprios não tratados nesta fase

### Dúvida aberta

- não houve evidência confirmada de travamento primário causado por CSS/overflow nesta rodada
- os CSS de shell e chat ainda têm várias regras de overlay, `pointer-events` e estados globais; isso permanece como área de inspeção futura se a UX ainda reportar “travamento”

## Como validar manualmente

Validar sempre sem `PERF_MODE`.

### Boot e login

1. Subir o web em modo normal:

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web"
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

2. Confirmar:

- `/app` abre e redireciona/login carrega normalmente
- `/cliente/login` abre sem crash
- `/revisao/login` abre sem crash

### Inspetor

Após login no `/app`, validar:

1. Portal do Inspetor carrega sem congelar a página.
2. `Novo Chat` abre uma tela limpa de entrada.
3. O composer aparece uma vez só.
4. Digitar no composer não cria duplicação visual.
5. Enviar a primeira mensagem leva para a conversa focada.
6. A conversa continua utilizável sem travar a aba.
7. `Nova Inspeção` abre sem quebrar o restante da UI.
8. Abrir um laudo recente não gera regressão grave de navegação.

### Sinais negativos a observar

- uso de CPU alto logo após abrir `/app`
- congelamento ao digitar
- scroll/foco “saltando”
- overlay invisível bloqueando clique
- composer duplicado
- rail, histórico ou pendências piscando/recompondo sem interação

## Validação executada nesta fase

### Sintaxe JavaScript

Executado com sucesso:

- `node --check web/static/js/chat/chat_index_page.js`
- `node --check web/static/js/shared/chat-render.js`
- `node --check web/static/js/shared/api-core.js`
- `node --check web/static/js/shared/api.js`
- `node --check web/static/js/shared/ui.js`
- `node --check web/static/js/inspetor/pendencias.js`
- `node --check web/static/js/inspetor/mesa_widget.js`

### Testes Python

Executado com sucesso:

- `python3 -m pytest web/tests/test_smoke.py -q`
- `python3 -m pytest web/tests/test_perf_support.py -q`

Resultados:

- `web/tests/test_smoke.py`: `26 passed`
- `web/tests/test_perf_support.py`: `2 passed`

### Smoke de boot HTTP

Executado com `uvicorn` local em modo normal, sem `PERF_MODE`.

Confirmado:

- `/app/` responde e entrega HTML
- `/cliente/login` responde e entrega HTML
- `/revisao/login` responde e entrega HTML

## Limites desta fase

Não foi feito:

- refactor estrutural
- modularização grande
- troca de contratos
- mudança de endpoints
- alteração de payloads
- mudança de regras de negócio
- mudança de auth/session/multiportal
- ajuste de backend de negócio
- otimização profunda de performance

## Evolução posterior de higiene de runtime

Após esta estabilização, a fase seguinte de higiene local refinou pontos que ainda poluíam o uso diário em desenvolvimento:

- Service Worker desativado automaticamente em `localhost`;
- bypass explícito de SSE no worker;
- warnings opcionais rebaixados para debug ou silêncio;
- divergência transitória de `estadoRelatorio` tratada antes de virar warning persistente;
- helpers mais claros para diferenciar terminal e console do navegador.

Referência operacional:

- `web/docs/restructuring-roadmap/14_runtime_hygiene_dev.md`

## Próximo passo correto

Não retomar medição ampla ou reestruturação profunda antes de confirmar manualmente que:

- `/app` voltou a abrir com estabilidade
- `Novo Chat` voltou a ser utilizável
- a primeira mensagem entra em conversa focada sem congelar
- `/cliente` e `/revisao` bootam sem crash evidente

Somente depois disso faz sentido reabrir a fase de observabilidade/perf.
