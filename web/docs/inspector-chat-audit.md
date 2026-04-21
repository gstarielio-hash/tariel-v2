# Auditoria do Frontend do Chat Inspetor

## Escopo

Esta auditoria cobre somente a arquitetura de frontend da área do inspetor, sem refatoração e sem alteração de backend, handlers, integrações ou regras de negócio.

O objetivo foi mapear:

- quais telas e fluxos coexistem dentro do mesmo runtime;
- quais estados e flags determinam qual layout aparece;
- quais wrappers estruturais participam de cada fluxo;
- onde existem duplicações de shell, header, toolbar e navegação;
- quais arquivos de estilo e runtime influenciam o comportamento visual atual;
- qual parece ser a raiz da inconsistência entre Home, assistente, nova inspeção, laudos recentes e conversa ativa.

---

## Inventário dos Arquivos Relevantes

### Entrada da rota e contexto inicial

- `app/domains/chat/auth_portal_routes.py`
  - `pagina_inicial()` monta o contexto do portal do inspetor e injeta `estado_relatorio`, `laudos_recentes`, `portal_contexto` e `home_forcado_inicial`.
  - `pagina_laudo_alias()` redireciona `/app/laudo/{id}` para `/app/?laudo={id}` e usa `/app/?home=1` como fallback.

### Templates principais

- `templates/index.html`
  - template da rota `/app/`;
  - monta `_portal_main.html`;
  - monta os modais `_nova_inspecao.html`, `_gate_qualidade.html` e `_perfil.html`;
  - carrega o runtime híbrido do inspetor.

- `templates/inspetor/base.html`
  - base visual atual do inspetor;
  - ainda injeta elementos globais de shell, como `shell-quick-actions` e `overlay-sidebar`.

- `templates/inspetor/_portal_main.html`
  - shell raiz do inspetor;
  - decide estado inicial com `data-inspecao-ui` e `data-workspace-stage`;
  - renderiza ao mesmo tempo:
    - `_sidebar.html`
    - `_portal_home.html`
    - `_workspace.html`
    - `_mesa_widget.html`

- `templates/inspetor/_sidebar.html`
  - sidebar esquerda do portal;
  - contém branding, botão `Nova Inspeção`, busca de histórico, navegação e lista de laudos recentes.

- `templates/inspetor/_portal_home.html`
  - home/portal do inspetor;
  - contém hero, estatísticas, `Laudos Recentes` e `Modelos Técnicos`.

- `templates/inspetor/_workspace.html`
  - tela do registro técnico/chat;
  - serve tanto para:
    - assistente sem laudo ativo;
    - laudo em andamento;
    - laudo aguardando/ajustes/aprovado;
    - visualização de anexos;
    - painel lateral de contexto IA.

- `templates/inspetor/modals/_nova_inspecao.html`
  - modal central de `Nova Inspeção`.

### Runtime JavaScript

- `static/js/chat/chat_index_page.js`
  - principal state machine do frontend do inspetor;
  - coordena home, workspace, stage assistant/inspection, modal, quick actions, busca/filtros, composer, mesa widget, pendências e SSE.

- `static/js/inspetor/modals.js`
  - comportamento do modal de nova inspeção;
  - criação do contexto visual do workspace;
  - gate de qualidade.

- `static/js/inspetor/pendencias.js`
  - carregamento e renderização do painel de pendências.

- `static/js/inspetor/mesa_widget.js`
  - widget lateral da mesa avaliadora.

- `static/js/inspetor/notifications_sse.js`
  - SSE do inspetor para pendências, mesa e banners.

- `static/js/chat/chat_sidebar.js`
  - comportamento da sidebar esquerda e compatibilidade legada.

- `static/js/shared/ui.js`
  - shell global, dock rápido e sincronização do botão Home global.

- `static/js/shared/api.js`
  - expõe `window.TarielAPI`;
  - ainda concentra envio do chat, carregamento de laudo e preparo de anexos.

- `static/js/chat/chat_painel_core.js`
  - core legado compartilhado `window.TarielChatPainel`;
  - fornece selectors, estado compartilhado, eventos e utilitários do painel.

- `static/js/chat/chat_painel_laudos.js`
  - seleção de laudos, sincronização de URL, breadcrumb, tabs e boot inicial do laudo.

- `static/js/chat/chat_painel_relatorio.js`
  - leitura/bloqueio/reabertura/finalização do laudo.

### Estilos ativos no runtime atual

- `static/css/shared/global.css`
- `static/css/shared/material-symbols.css`
- `static/css/inspetor/tokens.css`
- `static/css/shared/app_shell.css`
- `static/css/inspetor/reboot.css`

### Estilos legados ainda presentes no repositório, mas fora do pipeline atual do inspetor

- `static/css/inspetor/home.css`
- `static/css/inspetor/mesa.css`
- `static/css/inspetor/modals.css`
- `static/css/inspetor/profile.css`
- `static/css/inspetor/shell.css`
- `static/css/inspetor/workspace.css`
- `static/css/inspetor/responsive.css`
- `static/css/chat/chat_index.css`
- `static/css/chat/chat_mobile.css`
- `static/css/shared/layout.css`

Observação: esses arquivos não são carregados pelo `inspetor/base.html` atual, mas ainda existem com seletores da mesma família. Eles já não conflitam diretamente no runtime do inspetor, mas continuam gerando conflito cognitivo e risco de manutenção.

---

## Mapa de Rotas, Gatilhos e Telas

### 1. Home / Portal

- Rota ou gatilho
  - `/app/?home=1`
  - clique em Home no workspace
  - clique no breadcrumb Home
  - navegação que força `forceHomeLanding`
- Template principal renderizado
  - `templates/inspetor/_portal_home.html`
- Wrappers visuais
  - `.container-app`
  - `.painel-chat`
  - `.inspetor-shell-grid`
  - `.inspetor-main`
  - `#tela-boas-vindas.inspetor-portal`
  - `.portal-columns`
  - `.portal-column--surface`
- Sidebars/painéis usados
  - sidebar esquerda `_sidebar.html`
  - mesa widget continua montado na página, embora não seja o foco do fluxo
- Estados/flags envolvidos
  - backend: `home_forcado_inicial = true`
  - template: `modo_inspecao_inicial = "home"`
  - JS: `estado.modoInspecaoUI = "home"`
  - body dataset: `forceHomeLanding = true`
- Estilos envolvidos
  - `tokens.css`
  - `reboot.css` na parte de shell e portal
  - `app_shell.css` para quick-actions/overlay

### 2. Assistente Tariel IA sem laudo ativo

- Rota ou gatilho
  - `/app/` sem `home=1`
  - `estado_relatorio = sem_relatorio`
- Template principal renderizado
  - `templates/inspetor/_workspace.html`
- Wrappers visuais
  - `.chat-dashboard-grid`
  - `.chat-dashboard-thread`
  - `.chat-thread-surface`
  - `.technical-record-header`
  - `.thread-nav`
  - `.technical-chat-bar`
  - `.area-mensagens`
  - `#workspace-assistant-landing`
  - `.rodape-entrada`
- Sidebars/painéis usados
  - sidebar esquerda do portal permanece no shell
  - rail direita `.chat-dashboard-rail` existe no DOM, mas fica escondida
- Estados/flags envolvidos
  - template: `workspace_assistant_inicial = true`
  - backend/template: `data-workspace-stage = "assistant"`
  - JS local: `estado.workspaceStage = "assistant"`
  - JS local: `estado.modoInspecaoUI = "workspace"`
- Estilos envolvidos
  - `reboot.css` na parte de workspace e assistant landing
  - `app_shell.css` continua sobreposto globalmente

### 3. Nova Inspeção

- Rota ou gatilho
  - botão `Nova Inspeção` no home
  - botão `Nova Inspeção` na sidebar
  - botão `Nova Inspeção` no header do workspace
  - CTA `Nova Inspeção Guiada` na landing do assistente
  - cards de modelo técnico no home, quando não há laudo ativo
- Componente principal renderizado
  - `templates/inspetor/modals/_nova_inspecao.html`
- Wrappers visuais
  - `.modal-overlay`
  - `.modal-container`
  - `.modal-body`
- Sidebars/painéis usados
  - nenhum painel estrutural muda; o modal sobe por cima do shell atual
- Estados/flags envolvidos
  - `estado.modalNovaInspecaoPrePrompt`
  - validação em `modalNovaInspecaoEstaValida()`
  - após confirmar: `iniciarInspecao()`, `tariel:relatorio-iniciado`
- Estilos envolvidos
  - `reboot.css`

### 4. Laudos Recentes / Registro Técnico

- Rota ou gatilho
  - card de laudo recente no home
  - item do histórico na sidebar
  - URL `/app/?laudo={id}`
  - alias `/app/laudo/{id}` com redirect
- Componente principal renderizado
  - `templates/inspetor/_workspace.html`
- Wrappers visuais
  - mesmos wrappers do workspace
- Sidebars/painéis usados
  - sidebar esquerda
  - rail direita quando o stage vira `inspection`
- Estados/flags envolvidos
  - `abrirLaudoPeloHome()`
  - `TarielChatPainel.selecionarLaudo()`
  - `tariel:laudo-selecionado`
  - `estado.modoInspecaoUI = "workspace"`
  - `estado.workspaceStage = "inspection"`
- Estilos envolvidos
  - `reboot.css`

### 5. Laudo em andamento / Conversa ativa

- Rota ou gatilho
  - laudo já ativo no boot
  - retorno de `iniciarInspecao()`
  - seleção de laudo
  - `tariel:estado-relatorio` com contexto
- Componente principal renderizado
  - `templates/inspetor/_workspace.html`
- Wrappers visuais
  - mesmos wrappers do workspace
  - rail direita vira visível
  - composer, anexos, filtros e preview/finalizar ficam ativos
- Sidebars/painéis usados
  - sidebar esquerda
  - painel lateral direito `chat-dashboard-rail`
  - mesa widget
  - pendências
- Estados/flags envolvidos
  - `estado.workspaceStage = "inspection"`
  - `estadoRelatorio = relatorio_ativo | aguardando | ajustes | aprovado`
  - `chat_painel_relatorio.js` decide leitura/bloqueio/finalização
- Estilos envolvidos
  - `reboot.css`
  - `app_shell.css` por causa do dock global

---

## Mapa de Estados e Autoridades de Layout

Um dos principais problemas é que a decisão sobre “qual tela está ativa” não mora em um único lugar.

### Camadas que controlam layout

| Camada | Estado/Flag | Onde aparece | Efeito |
|---|---|---|---|
| Query string | `?home=1` | `auth_portal_routes.py`, `chat_painel_laudos.js`, `chat_index_page.js` | força home/portal |
| Query string | `?laudo={id}` | `pagina_laudo_alias()`, `chat_painel_laudos.js` | força seleção de laudo |
| Template Jinja | `home_forcado_inicial` | `_portal_main.html`, `_workspace.html` | define modo inicial |
| Template Jinja | `modo_inspecao_inicial` | `_portal_main.html` | `home` ou `workspace` |
| Template Jinja | `workspace_stage_inicial` | `_portal_main.html` | `assistant` ou `inspection` |
| Template Jinja | `workspace_assistant_inicial` | `_workspace.html` | esconde/mostra CTA e botões |
| JS local | `estado.modoInspecaoUI` | `chat_index_page.js` | alterna home vs workspace |
| JS local | `estado.workspaceStage` | `chat_index_page.js` | alterna assistant vs inspection |
| Body dataset | `forceHomeLanding` | `chat_painel_laudos.js`, `chat_index_page.js`, `chat_painel_relatorio.js` | reforça landing home |
| Body dataset | `inspecaoUi`, `workspaceStage`, `threadTab`, `estadoRelatorio` | `chat_index_page.js`, `chat_painel_*` | sincroniza visual, filtros e leitura |
| Core compartilhado | `TP.state.laudoAtualId`, `TP.state.estadoRelatorio` | `chat_painel_core.js`, `chat_painel_relatorio.js`, `chat_painel_laudos.js` | reflete seleção e modo leitura |

### Diagnóstico

A mesma tela depende ao mesmo tempo de:

- query param;
- dataset no `body`;
- dataset no `#painel-chat`;
- estado local em `chat_index_page.js`;
- estado legado em `window.TarielChatPainel`;
- estado exposto em `window.TarielAPI`.

Isso cria múltiplas autoridades competindo pelo layout.

---

## Mapa dos Wrappers Estruturais

### Shell do portal

- `.container-app`
  - wrapper global vindo do `base.html`
- `#painel-chat.painel-chat`
  - shell raiz da tela
- `.inspetor-shell-grid`
  - grid macro da página
  - coluna esquerda do portal + coluna principal
- `.inspetor-sidebar`
  - sidebar esquerda do portal
- `.inspetor-main`
  - área onde home e workspace coexistem

### Home / Portal

- `#tela-boas-vindas.inspetor-portal`
- `.inspetor-portal__header`
- `.portal-stat-grid`
- `.portal-columns`
- `.portal-column--surface`

### Workspace

- `.chat-dashboard-grid`
  - segundo grid estrutural, agora interno ao workspace
- `.chat-dashboard-thread`
- `.chat-thread-surface`
- `.technical-record-header`
- `.thread-nav`
- `.technical-chat-bar`
- `.area-mensagens`
- `.rodape-entrada`
- `.chat-dashboard-rail`
- `.chat-dashboard-rail__panel`

### Painéis globais sempre montados

- `#shell-quick-actions`
- `#overlay-sidebar`
- `#painel-mesa-widget`
- banners/toasts globais do shell

### Observação crítica

Hoje existem dois grids estruturais independentes na mesma rota:

- grid do portal: `.inspetor-shell-grid`
- grid do workspace: `.chat-dashboard-grid`

Além disso, o portal e o workspace permanecem montados ao mesmo tempo dentro de `.inspetor-main`.

---

## Onde Estão as Duplicações e Inconsistências

### 1. Wrappers duplicados de layout

Duplicações principais:

- shell do portal:
  - `.container-app`
  - `.painel-chat`
  - `.inspetor-shell-grid`
  - `.inspetor-main`
- shell da área técnica:
  - `.chat-dashboard-grid`
  - `.chat-dashboard-thread`
  - `.chat-thread-surface`

Isso significa que o sistema tem um shell macro do portal e, dentro dele, um segundo shell macro do chat.

### 2. Headers duplicados

- header do home:
  - `.inspetor-portal__header`
- header do workspace:
  - `.technical-record-header`
- sub-header do workspace:
  - `.thread-nav`
- barra global flutuante:
  - `shell-quick-actions`

Na prática, há mais de um nível de “topo” ativo na mesma página.

### 3. Toolbar, busca e filtros duplicados

- busca da sidebar:
  - `#busca-historico-input`
- busca do workspace:
  - `#chat-thread-search`
- filtros do workspace:
  - `[data-chat-filter]`
- tabs do workspace:
  - `.thread-tab`
- fallback legado:
  - `chat_painel_laudos.js` consegue recriar `.thread-nav` e `.thread-tabs` se não encontrar no DOM

Conclusão: mesmo a barra interna do workspace tem duas fontes de existência:

- template `_workspace.html`;
- injeção de fallback em `chat_painel_laudos.js`.

### 4. Renderização inconsistente do botão Home

O botão Home não tem uma única fonte.

Fontes atuais:

- sidebar esquerda:
  - link `Portal` em `_sidebar.html`
- header do workspace:
  - `.btn-home-cabecalho` em `_workspace.html`
- breadcrumb do workspace:
  - `.thread-breadcrumb [data-bc='home']` em `_workspace.html`
- botão global do shell:
  - `#btn-shell-home` em `base.html`
  - controlado por `shared/ui.js`

Inconsistência observada:

- o botão do header intercepta clique e navega para `/app/?home=1`;
- o breadcrumb também é interceptado e normalizado para `/app/?home=1`;
- o botão global do shell não navega sozinho: ele procura se existe `.btn-home-cabecalho` ou `.thread-breadcrumb` e clica neles;
- a sidebar esquerda tem seu próprio link `Portal`.

Resultado: há múltiplas affordances de Home com escopos diferentes e uma delas depende da presença das outras no DOM.

### 5. Onde o painel “Nova Inspeção” é montado

O painel de `Nova Inspeção` é um modal único, montado em:

- `templates/inspetor/modals/_nova_inspecao.html`

Mas ele é aberto a partir de vários entrypoints:

- home header
- sidebar esquerda
- header do workspace
- landing do assistente
- cards rápidos do home

Inconsistência aqui não é o modal em si, e sim a quantidade de shells diferentes que o acionam.

### 6. Painéis que entram no fluxo errado

Os seguintes blocos continuam montados mesmo quando não deveriam ser a tela dominante:

- `_portal_home.html`
- `_workspace.html`
- `_mesa_widget.html`
- `shell-quick-actions`
- `overlay-sidebar`
- painel lateral direito do workspace
- painel de anexos do workspace

No runtime atual, a maior parte da troca de tela acontece por `hidden`, datasets e mutação de estado, não por montagem/desmontagem real de tela.

### 7. Containers com max-width, margin auto, overflow e sticky que governam o comportamento

Arquitetonicamente relevantes no runtime atual:

- `tokens.css`
  - `body.pagina-chat-dashboard-v2 { overflow-x: hidden; }`
  - wrappers base com `width: 100%`, `max-width: none`, `margin: 0`
- `reboot.css`
  - `.inspetor-shell-grid`
    - grid macro do portal
  - `.chat-dashboard-grid`
    - grid macro do workspace
  - grupo de wrappers internos com `max-width: var(--chat-content-max)`:
    - `.technical-record-header__row`
    - `.thread-nav-inner`
    - `.technical-chat-bar`
    - `.technical-chat-empty`
    - mensagens
    - `.composer-suggestions`
    - `.rodape-entrada__contexto`
    - `.rodape-entrada__acoes`
    - `.pilula-entrada`
    - `.workspace-anexos-panel`
  - `.technical-record-header`
    - `position: sticky`
    - `z-index: 20`
  - `.rodape-entrada`
    - `position: sticky`
    - `z-index: 15`
  - `.chat-dashboard-rail__panel`
    - `position: sticky`
    - `max-height` fixada ao viewport
- `app_shell.css`
  - `.toast-sw`
    - `z-index: 9999`
  - `.barra-status-rede`
    - `z-index: 9998`
  - `.shell-quick-actions`
    - `z-index: 9996`

Diagnóstico:

- hoje já não existe um único `max-width` errado apertando a página inteira;
- o problema maior é haver vários níveis de shell e vários níveis de sticky/floating coexistindo;
- o layout parece “bagunçado” porque portal, workspace, rail direita e shell global são todos autoridades visuais simultâneas.

### 8. Componentes grandes demais

Componentes e arquivos com responsabilidade ampla demais:

- `chat_index_page.js`
  - controla home, workspace, stage assistant/inspection, modal, quick actions, busca, filtros, pendências, mesa widget, SSE, composer e navegação Home
- `shared/api.js`
  - rede, envio do chat, anexo, carregar laudo, sincronizar estado
- `chat_painel_laudos.js`
  - URL, histórico, breadcrumb, tabs, seleção de laudo e boot inicial
- `chat_painel_relatorio.js`
  - finalização, modo leitura, reabertura, botão finalizar, campo bloqueado

Isso aumenta a chance de um estado visual depender de arquivos diferentes ao mesmo tempo.

---

## Arquitetura Atual por Fluxo

### Home / Portal

Arquitetura visual ativa:

- shell portal esquerdo + home
- workspace continua montado em paralelo
- rail direita continua montada em paralelo

Sintoma derivado:

- a página parece um “super app interno” com múltiplas telas empilhadas, não um conjunto claro de telas mutuamente exclusivas.

### Assistente sem laudo ativo

Arquitetura visual ativa:

- mesmo template do laudo técnico;
- mesmos wrappers de conversa;
- stage diferente;
- rail direita escondida;
- CTA de `Nova Inspeção` exposto no header e na landing.

Sintoma derivado:

- o assistente sem laudo e o registro técnico ativo não são páginas diferentes;
- são apenas estados diferentes do mesmo workspace.

### Nova Inspeção

Arquitetura visual ativa:

- modal global único;
- contexto visual pré-aplicado no workspace;
- confirmação ainda depende do mesmo runtime híbrido.

Sintoma derivado:

- como o modal pode nascer de vários shells, a experiência muda conforme o ponto de entrada, mesmo com o mesmo modal.

### Laudos Recentes / Registro Técnico

Arquitetura visual ativa:

- home recente usa CTA do portal;
- sidebar usa histórico lateral;
- seleção também pode vir da URL;
- todos convergem no mesmo workspace.

Sintoma derivado:

- o usuário navega entre “home”, “histórico”, “registro técnico” e “chat” sem trocar de página real, só trocando datasets e handlers.

### Laudo em andamento / Conversa ativa

Arquitetura visual ativa:

- workspace completo;
- composer;
- rail direita;
- mesa widget;
- pendências;
- estados de leitura/finalização por módulo legado.

Sintoma derivado:

- o fluxo ativo funciona, mas depende de estado visual controlado por múltiplas camadas.

---

## Raiz da Bagunça Arquitetural

### Diagnóstico principal

A raiz mais forte da inconsistência não é um CSS isolado.

A raiz é esta combinação:

1. uma única rota `/app/` tentando hospedar várias telas conceitualmente diferentes;
2. portal e workspace montados ao mesmo tempo no DOM;
3. múltiplas autoridades de estado visual:
   - backend/Jinja
   - query string
   - sessionStorage
   - datasets no `body`
   - estado local em `chat_index_page.js`
   - estado compartilhado em `TarielChatPainel`
4. componentes globais do shell ainda ativos por cima do inspetor;
5. runtime híbrido:
   - frontend novo do inspetor
   - core legado compartilhado do painel
   - API wrapper compartilhada

### Em termos práticos

O sistema hoje não está organizado como:

- uma tela Home;
- uma tela Assistente;
- uma tela Conversa ativa.

Ele está organizado como:

- uma página grande com várias sub-telas coexistindo e sendo alternadas por flags.

Isso explica a sensação de fluxo inconsistente entre:

- Home/Portal
- Assistente sem laudo
- Nova Inspeção
- Laudos Recentes
- Conversa ativa

---

## Proposta Resumida de Reorganização Sem Mexer em Backend

Sem alterar backend, a reorganização recomendada seria:

1. manter `/app/` como rota única, mas separar os shells visuais em telas mutuamente exclusivas;
2. tornar uma única camada a autoridade de layout:
   - `screen = portal | assistant | workspace`
3. manter `_sidebar.html` como shell do portal e não como parte do estado técnico do chat;
4. manter `_workspace.html` somente para assistant + inspection, sem coexistir visualmente com a home;
5. remover o fallback de criação dinâmica de `.thread-nav` quando o template já fornece a estrutura;
6. escopar ou desligar `shell-quick-actions` para o inspetor, ou transformar isso em parte explícita do layout do portal;
7. manter modal de `Nova Inspeção` e mesa widget montados uma única vez no root, mas fora da responsabilidade do screen controller;
8. preservar todo o backend, os contratos e os endpoints existentes.

### Ordem recomendada

- Fase 1: consolidar mapa de estados para um único controller de screen
- Fase 2: desacoplar Home do workspace no DOM
- Fase 3: simplificar navegação Home/breadcrumb/dock global
- Fase 4: remover fallback legado de thread nav e reduzir dependência do core compartilhado para layout

---

## Conclusão

O frontend do inspetor está funcional, mas arquiteturalmente híbrido.

O principal problema não é “tema visual solto”. O problema é que Home, Assistant, Workspace, Sidebar do portal, Rail lateral do laudo e Dock global ainda coexistem dentro de um único runtime e são controlados por várias fontes de verdade.

Enquanto isso continuar, qualquer ajuste visual tende a parecer inconsistente entre fluxos, porque a estrutura da página não representa telas independentes; ela representa estados concorrentes de um mesmo shell.

Nenhuma refatoração foi aplicada nesta fase. Este documento é apenas o mapa da auditoria.
