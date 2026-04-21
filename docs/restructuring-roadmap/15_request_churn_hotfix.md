# Fase 01.5 — Hotfix de Request Churn do Inspetor

## Objetivo

Reduzir churn de requests no Inspetor sem alterar backend de negócio, endpoints, contratos, payloads ou regras funcionais. O foco desta fase foi conter duplicação de fetch, polling implícito, recarga redundante de histórico e reconexão excessiva de SSE.

## Fontes principais de churn encontradas

### Confirmado no código

1. `web/static/js/shared/api.js`
   - `sincronizarEstadoRelatorioWrapper()` reemitia `tariel:estado-relatorio` e `tariel:laudo-card-sincronizado` mesmo depois de `web/static/js/shared/chat-network.js` já ter emitido esses eventos.
   - Isso dobrava handlers no Inspetor e multiplicava refresh de pendências, sidebar e estado derivado.

2. `web/static/js/shared/chat-network.js`
   - `sincronizarEstadoRelatorio()` e `consultarStatusRelatorioAtual()` consultavam `/app/api/laudo/status` sem deduplicação em voo.
   - Não havia cache curtíssimo nem supressão de emissão repetida do mesmo snapshot de status.

3. `web/static/js/shared/api.js`
   - `carregarLaudoPorId()` e `buscarPaginaHistoricoLaudo()` podiam abrir múltiplas chamadas iguais para `/app/api/laudo/{id}/mensagens` durante boot, troca de laudo, SSE e transições rápidas.

4. `web/static/js/chat/chat_painel_laudos.js`
   - `selecionarLaudo()` reemitia `tariel:laudo-selecionado` com facilidade mesmo para o mesmo laudo, o que reacionava o restante do runtime.

5. `web/static/js/inspetor/pendencias.js`
   - `carregarPendenciasMesa()` abortava e reiniciava fetches sem reaproveitar request idêntico em voo.
   - Refresh silencioso do mesmo recurso era refeito em sequência curta.

6. `web/static/js/inspetor/notifications_sse.js`
   - SSE podia abrir cedo demais, reconectar fora de contexto útil e disparar refresh para laudo que nem estava ativo.

7. `web/static/js/inspetor/mesa_widget.js`
   - `atualizarChatAoVivoComMesa()` podia chamar `window.TarielAPI.carregarLaudo(..., { forcar: true })` em eventos da mesa, gerando recarga redundante do histórico principal.

## Hotfix aplicado

### Deduplicação de status

Arquivos:
- `web/static/js/shared/chat-network.js`
- `web/static/js/shared/api.js`

Mudanças:
- adicionado dedupe em voo para `/app/api/laudo/status`
- adicionado cache curtíssimo para status recente
- adicionada supressão de emissão repetida do mesmo snapshot de `estado-relatorio`
- wrappers de `api.js` deixaram de reemitir eventos que a camada de rede já emitia

Efeito esperado:
- menos explosão de `tariel:estado-relatorio`
- menos refresh derivado em cascata
- menos requests duplicados para `/app/api/laudo/status`

### Deduplicação de histórico do laudo

Arquivos:
- `web/static/js/shared/api.js`
- `web/static/js/chat/chat_painel_laudos.js`

Mudanças:
- `buscarPaginaHistoricoLaudo()` agora reutiliza promise em voo por chave `laudo + cursor`
- `buscarPaginaHistoricoLaudo()` ganhou cache curto para páginas recém-carregadas
- `carregarLaudoPorId()` agora reutiliza carga em voo por laudo
- `carregarLaudoPorId()` ganhou cooldown curto para reload silencioso do mesmo laudo
- `selecionarLaudo()` passou a suprimir reemissão redundante do mesmo laudo quando a seleção já está resolvida

Efeito esperado:
- menos chamadas duplicadas para `/app/api/laudo/{id}/mensagens`
- menos recarga repetida de histórico ao abrir laudo, voltar foco ou receber evento repetido

### Contenção de pendências

Arquivos:
- `web/static/js/inspetor/pendencias.js`
- `web/static/js/chat/chat_index_page.js`

Mudanças:
- `carregarPendenciasMesa()` agora usa chave de request `laudo + filtro + pagina + tamanho + modo`
- requests idênticos em voo são reaproveitados
- refresh silencioso usa cache curto quando o payload acabou de ser recebido
- polling técnico silencioso passa a pausar fora de contexto técnico
- ações manuais relevantes (`carregar mais`, troca de filtro, marcar lidas, atualizar item`) usam `forcar: true`

Efeito esperado:
- menos churn em `/app/api/laudo/{id}/pendencias`
- menos abort/restart do mesmo fetch
- menos refresh técnico quando a UI está em conversa focada ou fora de tela

### SSE mais contido

Arquivos:
- `web/static/js/inspetor/notifications_sse.js`
- `web/static/js/chat/chat_index_page.js`

Mudanças:
- SSE só é iniciado quando existe laudo ativo e a tela realmente precisa do canal
- a reconexão agora respeita contexto e backoff crescente
- o orquestrador da página fecha SSE ao ocultar a aba e só reabre quando volta a existir contexto válido
- eventos SSE de laudo que não é o ativo deixam de disparar refresh local

Efeito esperado:
- menos reconexão em loop curto
- menos refresh derivado por SSE fora do contexto do usuário

### Mesa widget mais leve

Arquivo:
- `web/static/js/inspetor/mesa_widget.js`

Mudanças:
- requests do widget da mesa ganharam dedupe em voo e cache curto
- fallback de recarregar o histórico principal ficou restrito a cenário realmente vazio
- eventos da mesa deixam de provocar reload agressivo do histórico principal na maior parte dos casos

Efeito esperado:
- menos recarga de `mensagens_laudo`
- menos acoplamento entre chat principal e mesa widget

## O que continua igual

### Confirmado

- endpoints não foram alterados
- payloads não foram alterados
- regras de negócio não foram alteradas
- SSE continua existindo e com o mesmo contrato funcional
- fluxo principal de criação, seleção e uso de laudo continua o mesmo
- backend de negócio não foi modificado

## Riscos residuais

### Inferência provável

- ainda pode haver churn residual por combinações de eventos UI + SSE + refresh manual em transições muito rápidas
- `chat_index_page.js` continua concentrando orquestração demais e ainda pode disparar efeitos colaterais indiretos
- o widget da mesa ainda é um ponto sensível por depender do laudo ativo e do estado derivado do workspace

### Dúvida aberta

- a próxima medição precisa confirmar quanto do volume de `mensagens_laudo` vinha do fallback do widget da mesa e quanto vinha da seleção redundante
- também precisa confirmar se `inspection_conversation` ainda recebe refresh técnico acima do necessário em fluxos específicos de laudo reaberto

## Como validar na próxima medição

1. Abrir `/app` e observar queda de requests repetidos no boot.
2. Abrir um laudo recente e verificar que `/app/api/laudo/{id}/mensagens` não dispara em rajada curta.
3. Alternar entre portal, `assistant_landing`, `inspection_record` e `inspection_conversation`.
4. Verificar que pendências não continuam refreshando fora de `inspection_record`, exceto quando houver ação explícita.
5. Verificar que SSE não reconecta em loop ao ocultar e reexibir a aba.
6. Verificar contadores de `request_churn` em modo perf para:
   - reuse de inflight
   - cache hit
   - refresh suprimido por contexto

## Arquivos principais tocados nesta fase

- `web/static/js/shared/chat-network.js`
- `web/static/js/shared/api.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/inspetor/pendencias.js`
- `web/static/js/inspetor/notifications_sse.js`
- `web/static/js/inspetor/mesa_widget.js`
