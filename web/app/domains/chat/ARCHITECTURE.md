# Arquitetura do Domínio `chat`

Este domínio foi modularizado para reduzir acoplamento e facilitar manutenção.

## Camada de Rotas

- `router.py`: agrega os subrouters e expõe `roteador_inspetor`.
- `auth.py`: login, logout, troca de senha, páginas do portal.
- `laudo.py`: ciclo de vida do laudo (iniciar, finalizar, versões, etc.).
- `chat.py`: chat IA, SSE, upload de evidências e histórico.
- `chat_stream_routes.py`: shell do fluxo principal do chat/stream do inspetor.
- `chat_stream_support.py`: preparação de entrada, resolução de laudo/comandos e persistência inicial do stream.
- `chat_stream_transport.py`: transporte SSE do whisper para mesa e da resposta incremental da IA.
- `mesa.py`: shell do canal mesa e registro estável das rotas públicas.
- `mesa_thread_routes.py`: thread detalhada, resumo e contrato público V2 da thread da mesa.
- `mesa_feed_routes.py`: feed mobile legado e contrato público V2 do feed da mesa.
- `mesa_message_routes.py`: envio de mensagem, envio de anexo e download de anexo da mesa.
- `pendencias.py`: pendências de revisão e exportações relacionadas.

## Camada de Helpers (Domínio)

- `auth_helpers.py`: regras e fluxo auxiliar de autenticação.
- `session_helpers.py`: CSRF, contexto base e estado do relatório em sessão.
- `limits_helpers.py`: regras de limite/plano por empresa.
- `gate_helpers.py`: gate de qualidade para finalização de laudos.
- `revisao_helpers.py`: versionamento e diff de revisões de laudo.
- `mensagem_helpers.py`: serialização de mensagens e notificação mesa.
- `pendencias_helpers.py`: filtros, paginação e serialização de pendências.
- `media_helpers.py`: validações de arquivo/imagem e utilitários de mídia.
- `template_helpers.py`: seleção de template ativo e limites de template.
- `normalization.py`: aliases e normalização de tipos de laudo/template.
- `core_helpers.py`: utilitários comuns (tempo UTC, JSON/SSE, respostas).
- `laudo_access_helpers.py`: acesso/autorização de laudo por empresa/inspetor.
- `ia_runtime.py`: bootstrap do cliente de IA e validação de disponibilidade.
- `chat_runtime.py`: constantes de runtime do chat e recursos opcionais.
- `mesa_common.py`: helpers compartilhados do canal mesa para contexto canônico, parsing e estado da thread.
- `notifications.py`: gerenciador SSE por usuário (`inspetor_notif_manager`).
- `app_context.py`: logger, templates e configuração compartilhada.

## Compatibilidade Legada

- `routes.py`: **compat layer mínima**.
  - Mantém `roteador_inspetor`.
  - Mantém `SessaoLocal`, `cliente_ia`, `inspetor_notif_manager`.
  - Mantém `obter_cliente_ia_ativo()` para patches em testes legados.

## Observações de Evolução

- Novas regras de negócio devem entrar nos módulos de helper temáticos.
- Evitar adicionar lógica nova em `routes.py`; usar apenas compatibilidade.
- Sempre que possível, manter imports diretos dos helpers (menos acoplamento).
