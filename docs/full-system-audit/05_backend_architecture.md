# 05. Arquitetura do Backend

Este documento descreve a arquitetura backend do sistema web: bootstrap, configuração, dependências, dados, autenticação, integrações e fluxo de request.

## 1. Entry point principal

O ponto de entrada do backend é `web/main.py`.

### Responsabilidades confirmadas em `main.py`

- configurar logging via `configurar_logging()`;
- validar ambiente via `get_settings()`;
- criar `FastAPI` em `create_app()`;
- registrar middlewares e exception handlers;
- montar `/static`;
- incluir roteadores de admin, cliente, inspetor e revisor;
- registrar `/health`, `/ready`, `/favicon.ico`, manifesto e service worker;
- executar `inicializar_banco()` no lifespan;
- testar conectividade do banco com `SELECT 1`;
- iniciar e encerrar realtime do revisor com `startup_revisor_realtime()` e `shutdown_revisor_realtime()`.

### Diagrama simplificado

```text
cliente HTTP
  -> web/main.py:create_app()
    -> app/core/http_runtime_support.py
    -> app/core/http_setup_support.py
    -> app/domains/router_registry.py
      -> admin
      -> cliente
      -> chat/inspetor
      -> revisor
    -> app/shared/database.py
    -> app/shared/security.py
    -> app/domains/revisor/realtime.py
```

## 2. Configuração e bootstrap

### Configuração de ambiente

Arquivo central: `web/app/core/settings.py`

Pontos confirmados:

- `AMBIENTE` é obrigatório.
- `REVISOR_REALTIME_BACKEND` aceita `memory` ou `redis`.
- `REDIS_URL` é lida do ambiente.
- Em produção, o app recusa chave de sessão curta e host mal configurado.

### Logging

Arquivo central: `web/app/core/logging_support.py`

Leitura:

- Em desenvolvimento, o logging é mais legível e textual.
- Em produção, o logging é estruturado em JSON.
- Há correlação por request via `X-Correlation-ID`.

### Segurança HTTP e middlewares

Arquivo central: `web/app/core/http_runtime_support.py`

Pontos confirmados:

- `GZipMiddleware`
- `TrustedHostMiddleware`
- `SessionMiddleware`
- `SlowAPIMiddleware`
- middleware próprio de correlation ID
- middleware próprio de headers de segurança
- CSP para páginas protegidas
- política `no-store` em rotas HTML protegidas

## 3. Registro de domínios

O backend usa `web/app/domains/router_registry.py` como ponto único de exposição dos roteadores:

- `roteador_admin`
- `roteador_cliente`
- `roteador_inspetor`
- `roteador_revisor`

Isso é importante porque a aplicação conhece explicitamente os portais, e não descobre rotas de forma dinâmica.

## 4. Estrutura por camadas

## 4.1 Camada HTTP / portal

Responsável por:

- declarar rotas;
- receber `Request`, forms, uploads e JSON;
- aplicar dependências de auth;
- renderizar templates ou devolver JSON/stream/arquivo;
- chamar serviços/helpers do domínio.

Exemplos:

- `web/app/domains/admin/routes.py`
- `web/app/domains/chat/auth_portal_routes.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/cliente/chat_routes.py`
- `web/app/domains/revisor/mesa_api.py`

## 4.2 Camada de domínio / serviços

Responsável por:

- regras de negócio;
- serialização de payloads;
- montagem de cards, gates, revisões e pacotes;
- coordenação entre modelos, sessão e integrações.

Exemplos:

- `web/app/domains/admin/services.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/chat/chat_service.py`
- `web/app/domains/mesa/service.py`
- `web/app/domains/revisor/service.py`
- `web/app/domains/revisor/service_package.py`

## 4.3 Camada compartilhada

Responsável por:

- banco e modelos;
- autenticação e RBAC;
- multiempresa;
- sessão;
- contratos e enums centrais.

Exemplos:

- `web/app/shared/database.py`
- `web/app/shared/db/models_auth.py`
- `web/app/shared/db/models_laudo.py`
- `web/app/shared/security.py`
- `web/app/shared/tenant_access.py`

## 4.4 Camada de integrações pesadas

Responsável por:

- IA;
- OCR;
- geração de PDF e previews;
- lógica mais pesada ou especializada fora dos domínios HTTP.

Exemplos:

- `web/nucleo/cliente_ia.py`
- `web/nucleo/gerador_laudos.py`
- `web/nucleo/template_editor_word.py`

## 5. Camada de dados

## 5.1 Modelos principais

### Autenticação e tenancy

- `Empresa`
- `Usuario`
- `LimitePlano`
- `SessaoAtiva`
- `PreferenciaMobileUsuario`
- `RegistroAuditoriaEmpresa`
- `AprendizadoVisualIa`

### Laudo e operação

- `Laudo`
- `MensagemLaudo`
- `LaudoRevisao`
- `CitacaoLaudo`
- `TemplateLaudo`
- `AnexoMesa`

## 5.2 Observações arquiteturais sobre o banco

Pontos confirmados no código:

- Há índices relevantes nas tabelas principais, especialmente em `usuarios`, `empresas`, `laudos`, `mensagens_laudo`, `anexos_mesa`, `sessoes_ativas` e `templates_laudo`.
- O backend usa Alembic para evolução de schema.
- O runtime local padrão agora usa Postgres; SQLite permanece como opção isolada para testes e fluxos temporários.

Leitura:

- O risco principal não parece ser “ausência total de índice”.
- O risco mais provável é composição de consultas, agregações em tempo de request e atravessamento repetido de relações em fluxos densos.

## 5.3 Sessão e transação

Arquivo central: `web/app/shared/database.py`

Pontos confirmados:

- `obter_banco()` abre uma `Session`, entrega ao request e faz commit automático se detectar mutações pendentes.
- Há listeners SQLAlchemy para marcar mutações inclusive em bulk operations.
- Em caso de erro, o código faz rollback e fecha a sessão.

Implicação arquitetural:

- O padrão reduz boilerplate em rotas simples.
- Em contrapartida, o contrato transacional fica bastante implícito e espalhado pelo request inteiro.

## 6. Autenticação, autorização e isolamento

Arquivo central: `web/app/shared/security.py`

### Modos de autenticação

- Sessão HTML por cookie para portais web.
- Token bearer para o app mobile do inspetor.

### Papéis confirmados no código

- `INSPETOR`
- `REVISOR`
- `ADMIN_CLIENTE`
- `DIRETORIA`

### Dependências de acesso relevantes

- `exigir_inspetor`
- `exigir_revisor`
- `exigir_admin_cliente`
- `exigir_diretoria`

### Isolamento por portal

Arquivos relevantes:

- `web/app/shared/security_portal_state.py`
- `web/app/shared/security_session_store.py`

Leitura:

- O sistema explicitamente evita vazamento de sessão entre portais.
- Isso é importante porque a mesma aplicação entrega múltiplos contextos com perfis diferentes.

## 7. Módulos backend mais importantes

## 7.1 `chat`

É o maior domínio backend e o principal fluxo operacional do produto.

Funções típicas:

- login inspetor;
- bootstrap da home do inspetor;
- criação, reabertura, finalização e pinagem de laudos;
- chat com IA em stream;
- mesa avaliadora do inspetor;
- pendências;
- notificações SSE;
- APIs mobile do inspetor.

Pontos de entrada principais:

- `web/app/domains/chat/router.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/mesa.py`

## 7.2 `revisor`

É o segundo núcleo mais complexo.

Funções típicas:

- login do revisor;
- fila operacional da mesa;
- respostas técnicas ao campo;
- validação de aprendizados;
- websocket e redis/memory realtime;
- biblioteca e editor de templates.

Pontos de entrada principais:

- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/revisor/realtime.py`
- `web/app/domains/revisor/templates_laudo.py`

## 7.3 `cliente`

É um portal de composição company-scoped.

Funções típicas:

- login do admin-cliente;
- bootstrap do portal;
- gestão da empresa;
- chat da empresa;
- mesa da empresa.

Ponto central:

- `web/app/domains/cliente/portal_bridge.py`

Esse arquivo prova que o portal do cliente foi desenhado para reaproveitar fluxos de `chat` e `revisor`.

## 8. Integrações externas

## 8.1 Google Gemini

Arquivo: `web/nucleo/cliente_ia.py`

Uso confirmado:

- geração de resposta com IA;
- modos de resposta curto, detalhado e deep research;
- streaming;
- extração de citações;
- análise contextual do histórico.

## 8.2 Google Vision OCR

Arquivo: `web/nucleo/cliente_ia.py`

Uso confirmado:

- OCR de imagens anexadas no fluxo de inspeção.
- O código desativa OCR se a API estiver indisponível.

## 8.3 Redis

Arquivos:

- `web/app/domains/revisor/realtime.py`
- `render.yaml`

Uso confirmado:

- backend distribuído opcional para o realtime do revisor.
- canais por usuário e por empresa.

## 8.4 PDF e documentos

Arquivos:

- `web/nucleo/gerador_laudos.py`
- `web/nucleo/template_editor_word.py`
- `web/nucleo/template_laudos.py`

Uso confirmado:

- exportação de pacote da mesa;
- geração de laudos;
- preview e publicação de templates.

## 9. Jobs, background e realtime

### O que existe

- Lifespan assíncrono da aplicação.
- `ThreadPoolExecutor(max_workers=4)` em `web/app/domains/chat/chat_runtime.py`.
- SSE do inspetor.
- WebSocket do revisor.
- Listener Redis do revisor.

### O que não apareceu como parte explícita do repositório

- Celery
- RQ
- Dramatiq
- Huey
- APScheduler
- workers separados de fila de jobs

Leitura:

- O sistema tem concorrência e realtime, mas não uma camada explícita de jobs assíncronos desacoplados.
- O trabalho pesado mais sensível parece acontecer dentro do request ou do stream.

## 10. Fluxo típico de request

## 10.1 Fluxo HTML de portal

```text
browser
  -> rota HTML (`/app/`, `/cliente/painel`, `/revisao/painel`, `/admin/painel`)
    -> dependência de autenticação/sessão
    -> consultas SQL + contexto base + dados do portal
    -> render Jinja2
    -> frontend hidrata com JS específico
```

## 10.2 Fluxo do chat do inspetor

```text
frontend inspetor
  -> POST /app/api/chat
    -> exigir_inspetor + CSRF
    -> valida histórico, imagem, documento e limites
    -> cria ou carrega `Laudo`
    -> salva `MensagemLaudo`
    -> chama `obter_cliente_ia_ativo()`
    -> usa `nucleo/cliente_ia.py`
    -> stream da resposta
    -> persiste resposta/citações/metadados
    -> notifica mesa quando aplicável
```

## 10.3 Fluxo mesa/revisor

```text
frontend revisor
  -> /revisao/painel
    -> monta fila operacional e métricas
  -> /revisao/api/laudo/{id}/...
    -> histórico, pacote, responder, avaliar
    -> usa `revisor.service` + `domains.mesa.service`
  -> /revisao/ws/whispers
    -> recebe notificações realtime por empresa/usuário
```

## 10.4 Fluxo portal cliente

```text
frontend cliente
  -> /cliente/painel
    -> shell SSR
  -> /cliente/api/bootstrap
    -> dados gerais da empresa
  -> /cliente/api/chat/* e /cliente/api/mesa/*
    -> rotas próprias
    -> reaproveitam `chat` e `revisor` via `portal_bridge.py`
```

## 11. Pontos de acoplamento relevantes

- `web/app/shared/database.py` é o maior hub de importação interna.
- `web/app/shared/security.py` é o segundo hub mais central.
- `web/app/domains/cliente/portal_bridge.py` conecta cliente com chat e revisor.
- `web/app/domains/chat/chat_stream_routes.py` conecta domínio de laudo com IA, gate, aprendizado e mesa.
- `web/app/domains/revisor/realtime.py` conecta painel do revisor, websocket e notificações.

## 12. Arquivos backend mais críticos

- `web/main.py`
- `web/app/core/settings.py`
- `web/app/core/http_runtime_support.py`
- `web/app/shared/database.py`
- `web/app/shared/security.py`
- `web/app/shared/security_session_store.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/cliente/portal_bridge.py`
- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/revisor/realtime.py`
- `web/app/domains/admin/services.py`
- `web/nucleo/cliente_ia.py`

## Confirmado no código

- O backend é um monólito modular FastAPI.
- Banco, auth e tenancy são infraestrutura compartilhada e extremamente centrais.
- O ciclo do laudo e a mesa avaliadora atravessam múltiplos domínios.
- Há suporte real a SSE, WebSocket e backend Redis para realtime.
- O mobile usa contratos do backend web, não uma API separada.

## Inferência provável

- O maior risco arquitetural do backend é excesso de orquestração concentrada em poucos arquivos e poucas request paths críticas.
- A arquitetura atual privilegia velocidade de entrega e coesão de produto, mas paga isso com hotspots de acoplamento.
- Qualquer refatoração futura relevante precisará preservar com muito cuidado o isolamento entre portais, porque esse é um requisito estrutural do sistema.

## Dúvida aberta

- Não ficou claro se parte das operações mais pesadas de geração documental já sofre volume suficiente para exigir fila assíncrona dedicada. O código ainda trata isso majoritariamente dentro do request.
