# Fase 01.7 - Congelamento do Contrato Shared API Web/Mobile

## Contexto

O roadmap da Fase 1 exige congelar e documentar formalmente os contratos consumidos pelo mobile antes de qualquer modularizacao mais agressiva do backend web.

O estado atual do repositorio mostra que:

- a observabilidade de backend e frontend ja entrou no codigo;
- os hotfixes `13`, `15` e `16` ja atacaram estabilidade, churn e N+1 no boot de `/app`;
- o app Android ja consome contratos reais separados por dominio em `android/src/config/*.ts`;
- ainda nao existia no pacote `docs/restructuring-roadmap/` um documento canonico consolidando a shared API usada pelo mobile.

Sem esse congelamento, a Fase 2 ficaria exposta a regressao silenciosa em rotas do inspetor que o mobile consome sem prefixo exclusivo de versao.

## Objetivo

Documentar a superficie HTTP real compartilhada entre backend web e app mobile do inspetor, registrando:

- quais rotas sao consumidas pelo app;
- quais contratos de request e response ja estao em uso;
- quais partes sao `mobile-only` e quais sao rotas compartilhadas com o portal web;
- quais invariantes nao podem mudar sem revisao especifica.

## Classe e escopo

- Fase: `Fase 1`
- Classe: `G0`
- Superficie dominante: `mobile/shared API`

Esta fase nao altera:

- endpoints;
- payloads;
- auth/session/multiportal;
- regras de negocio;
- frontend funcional;
- backend funcional.

## Fontes de verdade auditadas

### Backend

- `web/app/domains/chat/auth_mobile_routes.py`
- `web/app/domains/chat/auth_contracts.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/chat_aux_routes.py`
- `web/app/domains/chat/mesa.py`

### Mobile

- `android/src/config/api.ts`
- `android/src/config/authApi.ts`
- `android/src/config/chatApi.ts`
- `android/src/config/mesaApi.ts`
- `android/src/config/settingsApi.ts`
- `android/src/types/mobile.ts`

### Validacao existente no repositorio

- `web/tests/test_portais_acesso_critico.py`
- `web/tests/test_mesa_mobile_sync.py`
- `web/tests/test_smoke.py`
- `android/src/config/mesaApi.test.ts`

## Superficie canonica hoje usada pelo mobile

## 1. Rotas com prefixo `/app/api/mobile`

| Metodo | Rota | Consumidor mobile | Contrato principal |
| --- | --- | --- | --- |
| `POST` | `/app/api/mobile/auth/login` | `loginInspectorMobile()` | `MobileLoginResponse` |
| `GET` | `/app/api/mobile/bootstrap` | `carregarBootstrapMobile()` | `MobileBootstrapResponse` |
| `POST` | `/app/api/mobile/auth/logout` | `logoutInspectorMobile()` | `200 OK` sem payload obrigatorio no app |
| `GET` | `/app/api/mobile/laudos` | `carregarLaudosMobile()` | `MobileLaudoListResponse` |
| `PUT` | `/app/api/mobile/account/profile` | `atualizarPerfilContaMobile()` | `MobileAccountProfileResponse` |
| `POST` | `/app/api/mobile/account/password` | `alterarSenhaContaMobile()` | `MobileAccountPasswordResponse` |
| `POST` | `/app/api/mobile/account/photo` | `uploadFotoPerfilContaMobile()` | `MobileAccountProfileResponse` |
| `POST` | `/app/api/mobile/support/report` | `enviarRelatoSuporteMobile()` | `MobileSupportReportResponse` |
| `GET` | `/app/api/mobile/account/settings` | `carregarConfiguracoesCriticasContaMobile()` | `MobileCriticalSettingsResponse` |
| `PUT` | `/app/api/mobile/account/settings` | `salvarConfiguracoesCriticasContaMobile()` | `MobileCriticalSettingsResponse` |
| `GET` | `/app/api/mobile/mesa/feed` | `carregarFeedMesaMobile()` | `MobileMesaFeedResponse` |

## 2. Rotas do inspetor compartilhadas com web e mobile

O app nao consome apenas `/app/api/mobile/*`. Ele tambem depende de rotas compartilhadas do portal do inspetor.

| Metodo | Rota | Consumidor mobile | Observacao de contrato |
| --- | --- | --- | --- |
| `GET` | `/app/api/laudo/status` | `carregarStatusLaudo()` | status do laudo ativo |
| `GET` | `/app/api/laudo/{laudo_id}/mensagens` | `carregarMensagensLaudo()` | historico principal do laudo |
| `POST` | `/app/api/chat` | `enviarMensagemChatMobile()` | pode responder em JSON ou stream textual com eventos |
| `POST` | `/app/api/upload_doc` | `uploadDocumentoChatMobile()` | `multipart/form-data` |
| `POST` | `/app/api/laudo/{laudo_id}/reabrir` | `reabrirLaudoMobile()` | reaproveita contrato do inspetor |
| `GET` | `/app/api/laudo/{laudo_id}/mesa/mensagens` | `carregarMensagensMesaMobile()` | suporta `apos_id` para delta |
| `GET` | `/app/api/laudo/{laudo_id}/mesa/resumo` | `carregarResumoMesaMobile()` | resumo operacional da mesa |
| `POST` | `/app/api/laudo/{laudo_id}/mesa/mensagem` | `enviarMensagemMesaMobile()` | aceita `client_message_id` e `referencia_mensagem_id` |
| `POST` | `/app/api/laudo/{laudo_id}/mesa/anexo` | `enviarAnexoMesaMobile()` | `multipart/form-data` com idempotencia opcional |

## Invariantes congelados nesta fase

## 1. Autenticacao

- login mobile continua em `POST /app/api/mobile/auth/login`;
- o retorno de login continua com `auth_mode=bearer`, `access_token` e `token_type=bearer`;
- as chamadas autenticadas do app usam `Authorization: Bearer <token>`;
- logout mobile continua em `POST /app/api/mobile/auth/logout`;
- esta fase nao muda cookie, sessao web nem isolamento multiportal.

## 2. Contratos de request

### Payloads Pydantic canonicos no backend

Os contratos de entrada explicitamente tipados para a superficie mobile continuam em:

- `DadosLoginMobileInspetor`
- `DadosAtualizarPerfilUsuario`
- `DadosAtualizarSenhaMobileInspetor`
- `DadosRelatoSuporteMobileInspetor`
- `DadosConfiguracoesCriticasMobile`

Arquivo fonte:

- `web/app/domains/chat/auth_contracts.py`

### Formatos que o mobile depende hoje

- `application/json` para login, bootstrap, profile, password, support e settings;
- `multipart/form-data` para `account/photo` e upload/anexo;
- query string para `mesa/feed` (`laudo_ids`, `cursor_atualizado_em`) e `mesa/mensagens` (`apos_id`).

## 3. Contratos de response

### Tipos canonicamente usados pelo app

Arquivo fonte:

- `android/src/types/mobile.ts`

Tipos centrais:

- `MobileLoginResponse`
- `MobileBootstrapResponse`
- `MobileLaudoListResponse`
- `MobileLaudoStatusResponse`
- `MobileLaudoMensagensResponse`
- `MobileMesaMensagensResponse`
- `MobileMesaResumoResponse`
- `MobileMesaSendResponse`
- `MobileMesaFeedResponse`
- `MobileCriticalSettingsResponse`
- `MobileAccountProfileResponse`
- `MobileAccountPasswordResponse`
- `MobileSupportReportResponse`

### Particularidade critica: `/app/api/chat`

O app mobile depende de um contrato dual:

- se o backend responder `application/json`, o cliente le o payload final direto;
- se o backend responder stream textual, o cliente extrai eventos `data:` e reconcilia `laudo_id`, `laudo_card`, `texto`, `citacoes` e `confianca_ia`.

Isso significa que qualquer alteracao de semantica em `/app/api/chat` afeta:

- portal web do inspetor;
- possiveis reutilizacoes internas;
- app mobile do inspetor.

## 4. Idempotencia e sync da mesa

Invariantes ja em uso:

- `X-Client-Request-Id` pode ser enviado pelo app nas respostas da mesa;
- `client_message_id` e aceito no corpo das mensagens/anexos da mesa;
- `mesa/mensagens` suporta leitura delta por `apos_id`;
- `mobile/mesa/feed` suporta delta por `cursor_atualizado_em`.

Esses pontos estao protegidos por contrato e testes e nao devem mudar silenciosamente.

## O que esta explicitamente fora de escopo

- versionamento novo de API;
- geracao automatica de tipos;
- mudanca de payload;
- consolidacao de rotas compartilhadas para um prefixo novo;
- refactor de `chat_stream_routes.py`, `laudo.py` ou `mesa.py`.

## Riscos remanescentes

### 1. O contrato mobile nao vive so em `/app/api/mobile/*`

O maior risco estrutural restante e que o app tambem depende de rotas compartilhadas do inspetor, especialmente:

- `/app/api/chat`
- `/app/api/laudo/status`
- `/app/api/laudo/{id}/mensagens`
- `/app/api/laudo/{id}/reabrir`
- `/app/api/laudo/{id}/mesa/*`

### 2. Nao ha prefixo versionado

Sem `/v1`, `/v2` ou equivalente, a disciplina precisa vir de:

- documentacao canonica;
- testes de regressao;
- revisao explicita de contrato antes de mudar handlers.

### 3. `/app/api/chat` continua sendo a fronteira mais sensivel

Ele combina:

- rota compartilhada;
- contrato JSON/stream;
- fluxo critico do produto;
- impacto simultaneo em web e mobile.

## Efeito desta fase no roadmap

Esta fase fecha um bloqueio real da Fase 1:

- agora existe uma referencia canonica, dentro do proprio pacote `docs/restructuring-roadmap/`, para a shared API consumida pelo mobile;
- isso reduz a chance de entrar em Fase 2 com mudanca interna quebrando o app por efeito colateral nao mapeado.

## Validacao usada nesta fase

- `python3 -m pytest web/tests/test_portais_acesso_critico.py -q -k 'mobile'`
- `python3 -m pytest tests/test_mesa_mobile_sync.py -q` executado a partir de `web/`
- `python3 -m pytest web/tests/test_smoke.py -q -k 'openapi or mobile'`

## Proximo passo recomendado

A proxima fase mais segura continua documental:

- inventariar de forma canonica os `compat layers` ainda ativos;
- congelar os assets realmente carregados por portal no pacote `docs/restructuring-roadmap/`;
- so depois disso decidir se a proxima frente de Fase 1 sera medicao dedicada do `/revisao/painel` ou preparacao controlada para Fase 2.
