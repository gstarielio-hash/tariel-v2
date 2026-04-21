# 07. Fluxos Ponta a Ponta

Este documento descreve os principais fluxos funcionais do produto de ponta a ponta, conectando entrada, backend, frontend, persistência e integrações.

## 1. Login e autenticação por portal

## 1.1 Inspetor web

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `GET /app/login` |
| Backend envolvido | `web/app/domains/chat/auth_portal_routes.py`, `web/app/shared/security.py` |
| Frontend envolvido | `web/templates/login_app.html`, `web/static/css/shared/auth_shell.css` |
| Persistência | `Usuario`, `SessaoAtiva`, sessão HTTP |
| Integração externa | nenhuma obrigatória |
| Pontos de risco | separação por portal, senha temporária, bloqueio de acesso |

Fluxo:

1. O usuário acessa `/app/login`.
2. O formulário posta para `/app/login`.
3. O backend valida CSRF, senha, perfil e bloqueios.
4. Se a senha estiver temporária, redireciona para `/app/trocar-senha`.
5. Se estiver tudo válido, registra sessão isolada do portal inspetor e redireciona para `/app/`.

## 1.2 Revisor web

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `GET /revisao/login` |
| Backend envolvido | `revisor/auth_portal.py`, `shared/security.py` |
| Frontend envolvido | `login_revisor.html` |
| Persistência | `Usuario`, `SessaoAtiva` |
| Integração externa | nenhuma obrigatória |
| Pontos de risco | isolamento de portal, websocket autenticado depois do login |

## 1.3 Admin-cliente

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `GET /cliente/login` |
| Backend envolvido | `cliente/routes.py`, `shared/security.py` |
| Frontend envolvido | `login_cliente.html` |
| Persistência | `Usuario`, `Empresa`, `SessaoAtiva` |
| Integração externa | nenhuma obrigatória |
| Pontos de risco | usuário no portal correto e troca obrigatória de senha |

## 1.4 Admin CEO

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `GET /admin/login` |
| Backend envolvido | `admin/routes.py`, `shared/security.py` |
| Frontend envolvido | `login.html` |
| Persistência | `Usuario`, `SessaoAtiva` |
| Integração externa | nenhuma obrigatória |
| Pontos de risco | governança de clientes e planos |

## 2. Home e dashboard do inspetor

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `GET /app/` |
| Backend envolvido | `chat/auth_portal_routes.py`, `chat/session_helpers.py`, `chat/laudo_service.py` |
| Frontend envolvido | `templates/index.html`, `templates/inspetor/base.html`, `static/js/chat/*`, `static/js/inspetor/*` |
| Persistência | `Laudo`, `MensagemLaudo`, dados de plano e sessão |
| Integração externa | service worker, SSE |
| Pontos de risco | boot inicial pesado, sincronização entre sidebar, laudo ativo, modais e notificações |

Fluxo:

1. O backend monta o contexto inicial do portal, incluindo dados do usuário, estado do relatório e laudos recentes.
2. O template `index.html` renderiza a shell e injeta os scripts.
3. O JS assume o controle da interface.
4. A página passa a conversar com `/app/api/*` e com `/app/api/notificacoes/sse`.

## 3. Chat do inspetor e ciclo do laudo

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `POST /app/api/chat` |
| Backend envolvido | `chat/chat_stream_routes.py`, `chat/laudo.py`, `chat/chat_service.py`, `nucleo/cliente_ia.py` |
| Frontend envolvido | `static/js/chat/chat_index_page.js`, `static/js/shared/api.js`, `static/js/shared/chat-network.js` |
| Persistência | `Laudo`, `MensagemLaudo`, `CitacaoLaudo`, `LaudoRevisao` |
| Integração externa | Google Gemini, Google Vision OCR |
| Pontos de risco | latência externa, consistência de estado do laudo, stream longo, anexos e comandos rápidos |

Fluxo:

1. O frontend envia mensagem, imagem e/ou documento.
2. O backend valida limites, CSRF, modo de resposta e histórico.
3. Se não houver laudo ativo, cria um novo `Laudo`.
4. Persiste a mensagem do usuário.
5. Aciona a IA e streama a resposta.
6. Persiste resposta, citações e metadados.
7. Atualiza o estado do laudo e devolve contexto ao frontend.

## 4. Mesa avaliadora do inspetor

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `/app/api/laudo/{laudo_id}/mesa/*` |
| Backend envolvido | `chat/mesa.py`, `domains/mesa/attachments.py`, `domains/mesa/service.py` |
| Frontend envolvido | `static/js/inspetor/mesa_widget.js`, `static/js/chat/chat_painel_mesa.js` |
| Persistência | `MensagemLaudo`, `AnexoMesa`, `Laudo`, pendências associadas |
| Integração externa | notificação para o revisor via realtime |
| Pontos de risco | ordenação de mensagens, anexos, idempotência mobile, sincronização entre campo e mesa |

Fluxo:

1. O inspetor envia mensagem ou anexo para a mesa.
2. O backend persiste a mensagem como whisper/canal técnico.
3. O revisor recebe atualização por painel, websocket ou polling do próprio frontend.
4. O inspetor consulta resumo, mensagens e anexos da mesa pelo próprio laudo.

## 5. Painel da mesa / revisor

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `GET /revisao/painel` |
| Backend envolvido | `revisor/panel.py`, `revisor/mesa_api.py`, `revisor/service.py`, `revisor/realtime.py` |
| Frontend envolvido | `templates/painel_revisor.html`, `static/js/revisor/*` |
| Persistência | `Laudo`, `MensagemLaudo`, `AprendizadoVisualIa`, `AnexoMesa` |
| Integração externa | Redis opcional para realtime distribuído |
| Pontos de risco | montagem pesada da fila, filtros, contadores operacionais e consistência de whispers não lidos |

Fluxo:

1. O backend monta a fila de laudos em campo e aguardando avaliação.
2. O template renderiza métricas, filtros e lista.
3. O frontend usa APIs `/revisao/api/laudo/*` para abrir histórico, pacote, responder e avaliar.
4. O websocket `/revisao/ws/whispers` alimenta eventos ao painel.

## 6. Fluxo de pendências, ajustes e reabertura

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `/app/api/laudo/{laudo_id}/pendencias/*`, `/revisao/api/laudo/{laudo_id}/pendencias/{mensagem_id}`, `/app/api/laudo/{laudo_id}/reabrir` |
| Backend envolvido | `chat/pendencias.py`, `chat/laudo.py`, `revisor/mesa_api.py` |
| Frontend envolvido | Inspetor e Revisor |
| Persistência | `MensagemLaudo`, `Laudo`, `LaudoRevisao` |
| Integração externa | PDF opcional para exportar pendências |
| Pontos de risco | estado do laudo, reabertura pendente, transições corretas entre rascunho, aguardando, aprovado e rejeitado |

Leitura:

- Esse é um fluxo sensível porque mexe no contrato operacional entre campo e mesa.
- Há defesa explícita de estados inválidos no backend.

## 7. Portal admin-cliente unificado

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `GET /cliente/painel` |
| Backend envolvido | `cliente/routes.py`, `cliente/chat_routes.py`, `cliente/management_routes.py`, `cliente/portal_bridge.py` |
| Frontend envolvido | `templates/cliente_portal.html`, `static/js/cliente/portal.js` |
| Persistência | `Empresa`, `Usuario`, `Laudo`, `MensagemLaudo`, `RegistroAuditoriaEmpresa` |
| Integração externa | nenhuma obrigatória |
| Pontos de risco | página muito grande, muitas áreas de responsabilidade em uma única shell, acoplamento com chat e revisor |

Fluxo:

1. O portal renderiza a shell SSR com dados básicos da empresa e do usuário.
2. O frontend consome `/cliente/api/bootstrap`.
3. A aba Admin usa `management_routes` e `admin.services`.
4. A aba Chat usa o bridge para reaproveitar fluxos do domínio `chat`.
5. A aba Mesa usa o bridge para reaproveitar fluxos do domínio `revisor`.

## 8. Gestão de clientes e planos pelo admin CEO

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `/admin/painel`, `/admin/clientes`, `/admin/novo-cliente` |
| Backend envolvido | `admin/routes.py`, `admin/client_routes.py`, `admin/services.py` |
| Frontend envolvido | `dashboard.html`, `clientes.html`, `cliente_detalhe.html`, `novo_cliente.html` |
| Persistência | `Empresa`, `Usuario`, `LimitePlano`, `RegistroAuditoriaEmpresa` |
| Integração externa | eventual backend de notificação de boas-vindas em modo log/noop |
| Pontos de risco | alteração de plano, onboarding, bloqueio e reset de senha impactam o restante do sistema |

## 9. Uploads e anexos

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `/app/api/upload_doc`, `/app/api/laudo/{id}/mesa/anexo`, `/cliente/api/chat/upload_doc`, `/revisao/api/laudo/{id}/responder-anexo` |
| Backend envolvido | `chat/chat_service.py`, `chat/mesa.py`, `domains/mesa/attachments.py`, `revisor/mesa_api.py` |
| Frontend envolvido | Inspetor web, Cliente e mobile |
| Persistência | `AnexoMesa`, metadados do laudo e do template |
| Integração externa | OCR em imagens, preview de documentos |
| Pontos de risco | tamanho de arquivo, conteúdo inválido, storage path e rastreabilidade do anexo |

## 10. Biblioteca e editor de templates de laudo

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `/revisao/templates-laudo` e `/revisao/api/templates-laudo*` |
| Backend envolvido | `revisor/templates_laudo.py`, `templates_laudo_editor_routes.py`, `templates_laudo_management_routes.py`, `templates_laudo_support.py` |
| Frontend envolvido | `revisor_templates_biblioteca.html`, `revisor_templates_editor_word.html`, `static/js/revisor/templates_*` |
| Persistência | `TemplateLaudo`, `RegistroAuditoriaEmpresa`, assets do editor |
| Integração externa | PDF.js, geração de preview/export |
| Pontos de risco | diffs, publicação, base recomendada, assets versionados e preview pesado |

Leitura:

- Esse fluxo já parece ser um subsistema interno completo, com CRUD, auditoria, diff, preview, publicação e assets.

## 11. Aprendizado visual da IA

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `/app/api/laudo/{id}/aprendizados`, `/revisao/api/laudo/{id}/aprendizados`, `/revisao/api/aprendizados/{aprendizado_id}/validar` |
| Backend envolvido | `chat/learning.py`, `chat/learning_helpers.py`, `revisor/learning_api.py` |
| Frontend envolvido | Inspetor e Revisor |
| Persistência | `AprendizadoVisualIa` |
| Integração externa | depende do fluxo que gerou o contexto de IA/imagem |
| Pontos de risco | coerência entre rascunho do inspetor e validação final do revisor |

## 12. Mobile bootstrap, histórico e sincronização de mesa

| Aspecto | Descrição |
| --- | --- |
| Ponto de entrada | `/app/api/mobile/bootstrap`, `/app/api/mobile/laudos`, `/app/api/mobile/mesa/feed` |
| Backend envolvido | `chat/auth_mobile_routes.py`, `chat/mesa.py` |
| Frontend envolvido | `android/src/features/InspectorMobileApp.tsx`, `chatApi.ts`, `mesaApi.ts` |
| Persistência | `PreferenciaMobileUsuario`, `Laudo`, `MensagemLaudo` e cache local mobile |
| Integração externa | recursos nativos do device |
| Pontos de risco | sessão bearer, sync parcial, offline queue, reconciliação depois de reconexão |

## Fluxos mais críticos para regressão

- Login e isolamento entre portais
- Chat do inspetor
- Mesa/revisor
- Reabertura/finalização de laudo
- Portal cliente por reuso de bridges
- Templates de laudo
- Mobile bootstrap + chat + mesa

## Confirmado no código

- O laudo é o centro do sistema e atravessa inspetor, cliente, revisor e mobile.
- A mesa avaliadora conecta backend, frontend web, mobile e realtime.
- O portal cliente é um consumidor interno de fluxos já existentes, não um domínio totalmente independente.
- O sistema possui fluxos documentais pesados além do chat, especialmente no revisor.

## Inferência provável

- O maior risco funcional não está em um endpoint isolado, mas nas transições de estado entre laudo em campo, pendência, avaliação, reabertura e fechamento.
- O portal cliente tende a ser sensível a regressões de integração porque depende de dois domínios centrais ao mesmo tempo: `chat` e `revisor`.
- O mobile amplia o alcance do sistema, mas também amplifica a importância de contratos estáveis em rotas do inspetor.

## Dúvida aberta

- O código mostra bem como os fluxos operam, mas não explicita métricas de uso real por fluxo. Por isso, a auditoria identifica criticidade estrutural, não frequência real de uso em produção.
