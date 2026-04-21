# Checkpoint Tecnico Atual

Data: 2026-04-13
Horario de referencia: 16:35 -03

## Contexto

Este checkpoint congela o estado tecnico depois da grande consolidacao do branch
`feature/canonical-case-lifecycle-v1`.

O `HEAD` base ao iniciar este checkpoint e `771e3f5`, commit que consolidou a
plataforma canônica entre tenant, web, mobile e entrega documental. A partir
desse ponto, o trabalho seguiu aprofundando principalmente o Android e a
higiene estrutural do chat.

## Estado Git

- branch: `feature/canonical-case-lifecycle-v1`
- HEAD base: `771e3f5` - `Consolidate canonical case platform across tenant, web, mobile, and PDF delivery`
- objetivo do corte atual: estabilizar e limpar a experiencia real do app Android sem perder o núcleo canônico já consolidado

## Entregas técnicas deste corte

### 1. Chat mobile mais limpo

- `preferencias_ia_mobile` deixaram de trafegar como texto visível no chat;
- preferências da IA passaram a subir como contexto interno da requisição;
- histórico, cache e previews passaram a sanitizar blocos internos antigos;
- render do chat ganhou proteção final para não exibir esse bloco mesmo em estado legado.

Arquivos centrais:

- `web/app/domains/chat/mobile_ai_preferences.py`
- `web/app/domains/chat/chat_stream_support.py`
- `web/app/domains/chat/core_helpers.py`
- `web/app/domains/chat/mensagem_helpers.py`
- `android/src/features/chat/preferences.ts`
- `android/src/features/chat/conversationHelpers.ts`
- `android/src/features/common/inspectorLocalPersistence.ts`

### 2. Android em aparelho real

- fullscreen por padrão validado em aparelho;
- loop de render ligado à persistência/configuração foi corrigido;
- runtime de env e transporte HTTP do dev client foram corrigidos para voltar a falar com o backend local;
- a navegação do caso ficou mais coerente com `Chat`, `Mesa` condicional e `Finalizar`.

Arquivos centrais:

- `android/src/config/apiCore.ts`
- `android/src/config/authApi.ts`
- `android/src/features/common/useInspectorRootPersistenceEffects.ts`
- `android/src/settings/repository/settingsRemoteAdapter.ts`
- `android/src/features/InspectorAuthenticatedLayout.tsx`
- `android/src/features/chat/ThreadHeaderControls.tsx`
- `android/src/features/chat/ThreadConversationPane.tsx`
- `android/src/features/chat/ThreadContextCard.tsx`

### 3. Continuidade canônica no mobile

- grants, lifecycle e ações de superfície continuaram sendo a fonte principal de decisão do app;
- quality gate, override humano, offline e mesa nativa foram mantidos integrados ao núcleo canônico;
- report pack draft e insights do caso seguiram disponíveis, mas com a conversa principal menos poluída.

## Diagnóstico técnico atual

### Backend

O backend já tem o núcleo canônico de caso técnico e a trilha de governança por tenant,
mas ainda carrega acoplamentos em camadas legadas de `chat`, `cliente` e `revisor`.

### Web

O inspetor web e os portais já obedecem muito mais o contrato canônico, porém a
desglobalização do runtime e a redução de compat layers ainda não terminaram.

### Mobile

O Android já saiu da fase de prova de conceito e entrou na fase de refinamento real.
Os problemas mais importantes restantes são visualização, densidade de informação e
consistência de fluxo nas telas auxiliares.

### Documento

O pipeline documental premium continua como próxima frente grande depois da
estabilização do núcleo e da UX operacional.

## Próxima sequência recomendada

1. limpar `Finalizar`, `Configurações` e `Histórico` no app Android;
2. validar login, anexos, offline e mesa no aparelho depois desse ajuste;
3. continuar a extração do núcleo compartilhado de caso técnico;
4. reduzir `window.*`, ordem manual de scripts e compat layers no frontend web;
5. retomar a frente de `document_view_model -> editor -> render`.
