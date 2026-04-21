# Canonicalização de Eventos do Chat Inspetor

## Objetivo

Registrar a FASE 7 da reorganização do frontend do inspetor: eventos canônicos passaram a ter uma autoridade explícita, enquanto aliases legados continuam aceitos apenas como compatibilidade controlada.

## Confirmado no código

### Autoridade central de eventos

- Arquivo autoridade: `web/static/js/shared/api-core.js`
- Estrutura global criada:
  - `window.TarielInspectorEvents`
  - `window.TarielCore.EVENTOS_TARIEL`
  - `window.TarielCore.emitirEventoTariel(...)`
  - `window.TarielCore.ouvirEventoTariel(...)`
- O registry explícito agora fica em `EVENTOS_TARIEL`, com:
  - nome canônico
  - aliases legados aceitos
  - módulos relevantes por evento

### Helper de dispatch canônico

- Função principal: `emitirEventoTariel(...)`
- Comportamento:
  - sempre emite o evento canônico
  - emite aliases legados apenas como compatibilidade temporária
  - evita duplicação de dispatch quando recebe arrays antigos com canônico + alias
  - carimba o `detail` com metadados internos não enumeráveis para deduplicação segura

### Helper de listen com compatibilidade

- Função principal: `ouvirEventoTariel(...)`
- Comportamento:
  - escuta o nome canônico
  - escuta aliases legados quando o evento possui compatibilidade registrada
  - deduplica canonical + alias do mesmo fato
  - registra warning único quando o caminho legado é acionado

### Telemetria/warnings adicionados

- Warning único em desenvolvimento por alias legado usado em:
  - `dispatch`
  - `listen`
- Flags de debug no DOM:
  - `dataset.inspectorLegacyEventCompat`
  - `dataset.inspectorLegacyEventAlias`
  - `dataset.inspectorLegacyEventCanonical`
  - `dataset.inspectorLegacyEventChannel`

## Eventos canônicos formalizados

### Grupo principal

- `tariel:laudo-criado`
  - alias legado: `tariellaudo-criado`
- `tariel:estado-relatorio`
  - alias legado: `tarielestado-relatorio`
- `tariel:relatorio-iniciado`
  - alias legado: `tarielrelatorio-iniciado`
- `tariel:relatorio-finalizado`
  - alias legado: `tarielrelatorio-finalizado`
- `tariel:cancelar-relatorio`
  - alias legado: `tarielrelatorio-cancelado`
- `tariel:historico-laudo-renderizado`
  - alias legado: `tarielhistorico-laudo-renderizado`
- `tariel:mesa-avaliadora-ativada`
  - alias legado: `tarielmesa-avaliadora-ativada`
- `tariel:ativar-mesa-avaliadora`
  - alias legado: `tarielativar-mesa-avaliadora`
- `tariel:mesa-status`
  - alias legado: `tarielmesa-status`
- `tariel:gate-qualidade-falhou`
  - alias legado: `tarielgate-qualidade-falhou`
- `tariel:disparar-comando-sistema`
  - alias legado: `tarieldisparar-comando-sistema`
- `tariel:relatorio-finalizacao-falhou`
  - alias legado: `tarielrelatorio-finalizacao-falhou`

### Eventos canônicos mantidos sem alias

- `tariel:laudo-selecionado`
- `tariel:laudo-card-sincronizado`
- `tariel:thread-tab-alterada`
- `tariel:screen-synced`
- `tariel:navigate-home`
- `tariel:api-pronta`

## Módulos migrados para o helper central

### Dispatch

- `web/static/js/shared/chat-network-utils.js`
  - `emitirEvento(...)` agora delega para `window.TarielInspectorEvents.emit(...)`
- `web/static/js/shared/api.js`
  - `emitirEvento(...)` e `emitirEventos(...)` agora usam o helper central
  - os wrappers de relatório passaram a emitir só o nome canônico
- `web/static/js/chat/chat_painel_core.js`
  - `TP.emitir(...)` passou a usar o helper central
- `web/static/js/chat/chat_index_page.js`
  - `emitirSincronizacaoLaudo(...)` e a seleção manual de laudo passaram a usar o helper central
- `web/static/js/chat/chat_sidebar.js`
  - fallback de emissão sem `TP.emitir` agora usa `window.TarielInspectorEvents.emit(...)`

### Listen

- `web/static/js/chat/chat_index_page.js`
  - trocou binds duplos de `relatorio-*`, `mesa-*`, `gate-*` e `historico-*` por `ouvirEventoTariel(...)`
- `web/static/js/chat/chat_painel_relatorio.js`
  - trocou binds duplos de `relatorio-*` por `ouvirEventoTariel(...)`
- `web/static/js/chat/chat_painel_mesa.js`
  - trocou bind duplo de `ativar-mesa-avaliadora` por `ouvirEventoTariel(...)`
- `web/static/js/shared/api.js`
  - trocou bind duplo de `disparar-comando-sistema` por `ouvirEvento(...)`
- `web/static/js/shared/chat-network.js`
  - trocou bind manual de `CMD_SISTEMA` por `window.TarielInspectorEvents.on(...)`

## Quem dispara e quem consome

### `tariel:relatorio-iniciado`

- Disparo confirmado em:
  - `web/static/js/shared/chat-network.js`
  - `web/static/js/shared/api.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_index_page.js`
  - `web/static/js/chat/chat_painel_relatorio.js`
  - `web/static/js/chat/chat_painel_laudos.js`
  - `web/static/js/shared/ui.js`

### `tariel:relatorio-finalizado`

- Disparo confirmado em:
  - `web/static/js/shared/chat-network.js`
  - `web/static/js/shared/api.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_index_page.js`
  - `web/static/js/chat/chat_painel_relatorio.js`
  - `web/static/js/chat/chat_painel_laudos.js`
  - `web/static/js/shared/ui.js`

### `tariel:cancelar-relatorio`

- Disparo confirmado em:
  - `web/static/js/shared/chat-network.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_index_page.js`
  - `web/static/js/chat/chat_painel_relatorio.js`
  - `web/static/js/chat/chat_painel_laudos.js`
  - `web/static/js/shared/ui.js`

### `tariel:mesa-status`

- Disparo confirmado em:
  - `web/static/js/shared/chat-network.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_index_page.js`

### `tariel:mesa-avaliadora-ativada`

- Disparo confirmado em:
  - `web/static/js/chat/chat_painel_mesa.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_index_page.js`

### `tariel:ativar-mesa-avaliadora`

- Disparo confirmado em:
  - `web/static/js/chat/chat_sidebar.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_painel_mesa.js`

### `tariel:gate-qualidade-falhou`

- Disparo confirmado em:
  - `web/static/js/shared/chat-network.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_index_page.js`

### `tariel:historico-laudo-renderizado`

- Disparo confirmado em:
  - `web/static/js/shared/api.js`
- Consumo confirmado em:
  - `web/static/js/chat/chat_index_page.js`

### `tariel:disparar-comando-sistema`

- Disparo confirmado em:
  - `web/static/js/shared/chat-network.js`
- Consumo confirmado em:
  - `web/static/js/shared/chat-network.js`
  - `web/static/js/shared/api.js`

## Compatibilidade preservada

### Hooks públicos preservados

- `TP.emitir(...)`
- `window.TarielAPI`
- `window.TarielChatPainel`
- listeners que continuam escutando eventos canônicos via `document`
- fluxo Home centralizado por `tariel:navigate-home`
- integração com:
  - tabs do workspace
  - histórico
  - mesa widget
  - modais
  - toolbar
  - rail
  - composer

### Alias legados ainda aceitos

Os aliases abaixo continuam aceitos nesta fase, mas deixaram de ser a via principal:

- `tariellaudo-criado`
- `tarielestado-relatorio`
- `tarielrelatorio-iniciado`
- `tarielrelatorio-finalizado`
- `tarielrelatorio-cancelado`
- `tarielhistorico-laudo-renderizado`
- `tarielmesa-avaliadora-ativada`
- `tarielativar-mesa-avaliadora`
- `tarielmesa-status`
- `tarielgate-qualidade-falhou`
- `tarieldisparar-comando-sistema`
- `tarielrelatorio-finalizacao-falhou`

## O que esta fase resolveu

## Confirmado no código

- O nome canônico virou a via principal de dispatch e binding.
- O alias legado saiu do fluxo manual espalhado e foi movido para compatibilidade controlada.
- `chat_index_page.js` e `chat_painel_relatorio.js` deixaram de reagir em dobro ao mesmo fato por bind duplicado explícito.
- `shared/chat-network.js` e `shared/api.js` deixaram de tratar alias manualmente como primeira classe.

## Inferência provável

- A próxima remoção de aliases ficará muito menos arriscada, porque o uso legado agora é observável por warnings únicos e por flags de debug no DOM.

## Dúvida aberta

- Nenhuma dúvida estrutural nova apareceu nesta fase.
- Continua valendo a limitação já conhecida: ainda existem caminhos legados de dados e finalização fora do escopo desta fase, mas eles não foram alterados aqui.

## Próxima remoção segura

Quando a equipe quiser avançar:

1. Rodar o sistema em desenvolvimento e observar quais aliases ainda geram warning.
2. Confirmar se algum módulo externo ao escopo atual ainda depende desses aliases.
3. Desligar `emitirAliases` por evento ou remover aliases específicos do `EVENTOS_TARIEL`.
4. Só depois atacar fillers sintéticos e placeholders, como previsto no plano maior.
