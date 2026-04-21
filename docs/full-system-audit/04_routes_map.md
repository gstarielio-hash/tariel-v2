# 04. Mapa de Rotas

Este documento mapeia a superfície HTTP do sistema inteiro a partir da aplicação FastAPI já montada. As rotas foram agrupadas por portal e por tipo de interface.

## Visão geral

| Grupo | Quantidade | Prefixo principal | Arquivos-base |
| --- | --- | --- | --- |
| Operacional | 5 | `/`, `/health`, `/ready` | `web/app/core/http_setup_support.py` |
| Admin HTML | 16 | `/admin` | `web/app/domains/admin/routes.py`, `client_routes.py` |
| Admin API | 1 | `/admin/api` | `web/app/domains/admin/routes.py` |
| Inspetor HTML | 10 | `/app` | `web/app/domains/chat/auth_portal_routes.py` |
| Inspetor API | 37 | `/app/api` | `chat_stream_routes.py`, `laudo.py`, `mesa.py`, `pendencias.py`, `learning.py`, `auth_portal_routes.py` |
| Inspetor mobile API | 11 | `/app/api/mobile` | `auth_mobile_routes.py`, `mesa.py` |
| Cliente HTML | 7 | `/cliente` | `web/app/domains/cliente/routes.py` |
| Cliente API | 29 | `/cliente/api` | `routes.py`, `chat_routes.py`, `management_routes.py` |
| Revisor HTML | 8 | `/revisao` | `auth_portal.py`, `panel.py`, `templates_laudo.py` |
| Revisor API | 35 | `/revisao/api` | `mesa_api.py`, `learning_api.py`, `templates_laudo*.py` |
| WebSocket | 1 | `/revisao/ws` | `web/app/domains/revisor/ws.py` |
| Assets estáticos | 1 mount | `/static` | `web/main.py` |

## Como as rotas são registradas

- `web/main.py` inclui:
  - `roteador_admin` com prefixo `/admin`
  - `roteador_cliente` com prefixo `/cliente`
  - `roteador_inspetor` com prefixo `/app`
  - `roteador_revisor` sem prefixo adicional, porque o próprio domínio já define `/revisao/...`
- `web/app/domains/chat/router.py` agrega os subrouters do inspetor uma única vez.
- `web/app/domains/cliente/routes.py` inclui as rotas de chat e management do portal cliente.
- `web/app/domains/revisor/routes.py` é fachada compatível do domínio revisor.

## 1. Rotas operacionais

| Método | Rota | Handler | Resposta | Papel |
| --- | --- | --- | --- | --- |
| `GET` | `/` | `app.core.http_setup_support.redirecionamento_raiz` | redirect | Redireciona conforme o perfil autenticado. |
| `GET` | `/debug-sessao` | `app.core.http_setup_support.debug_sessao` | debug/JSON | Inspeção de sessão em ambiente não produtivo. |
| `GET` | `/favicon.ico` | `app.core.http_setup_support.favicon` | arquivo | Ícone global. |
| `GET` | `/health` | `app.core.http_setup_support.health_check` | JSON | Liveness básico. |
| `GET` | `/ready` | `app.core.http_setup_support.readiness_check` | JSON | Readiness com estado do banco/realtime. |

## 2. Portal Admin CEO: HTML e ações

### Leitura do grupo

- Prefixo: `/admin`
- Arquivos: `web/app/domains/admin/routes.py`, `web/app/domains/admin/client_routes.py`
- Templates: `login.html`, `dashboard.html`, `novo_cliente.html`, `clientes.html`, `cliente_detalhe.html`, `trocar_senha.html`

| Método | Rota | Handler | Template/resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/admin/login` | `tela_login` | `login.html` | `admin.routes`, `portal_support` |
| `POST` | `/admin/login` | `processar_login` | redirect/form response | `admin.routes`, `shared.security` |
| `POST` | `/admin/logout` | `fazer_logout` | redirect | `admin.routes` |
| `GET` | `/admin/painel` | `painel_faturamento` | `dashboard.html` | `admin.routes`, `admin.services` |
| `GET` | `/admin/novo-cliente` | `pagina_novo_cliente` | `novo_cliente.html` | `admin.client_routes` |
| `POST` | `/admin/novo-cliente` | `processar_novo_cliente` | redirect/form response | `admin.client_routes`, `admin.services` |
| `POST` | `/admin/cadastrar-empresa` | `cadastrar_empresa` | form response | `admin.client_routes`, `admin.services` |
| `GET` | `/admin/clientes` | `lista_clientes` | `clientes.html` | `admin.client_routes`, `admin.services` |
| `GET` | `/admin/clientes/{empresa_id}` | `detalhe_cliente` | `cliente_detalhe.html` | `admin.client_routes`, `admin.services` |
| `POST` | `/admin/clientes/{empresa_id}/adicionar-inspetor` | `novo_inspetor` | action response | `admin.client_routes`, `admin.services` |
| `POST` | `/admin/clientes/{empresa_id}/bloquear` | `toggle_bloqueio` | action response | `admin.client_routes`, `admin.services` |
| `POST` | `/admin/clientes/{empresa_id}/resetar-senha/{usuario_id}` | `resetar_senha` | action response | `admin.client_routes`, `admin.services` |
| `POST` | `/admin/clientes/{empresa_id}/trocar-plano` | `trocar_plano` | action response | `admin.client_routes`, `admin.services` |
| `POST` | `/admin/clientes/{empresa_id}/usuarios/{usuario_id}/atualizar-crea` | `atualizar_crea_usuario_operacional` | action response | `admin.client_routes`, `admin.services` |
| `GET` | `/admin/trocar-senha` | `tela_troca_senha_admin` | `trocar_senha.html` | `admin.routes` |
| `POST` | `/admin/trocar-senha` | `processar_troca_senha_admin` | redirect/form response | `admin.routes`, `shared.security` |

### API administrativa

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/admin/api/metricas-grafico` | `api_metricas_grafico` | JSON | `admin.routes`, `admin.services` |

## 3. Portal do Inspetor: HTML

### Leitura do grupo

- Prefixo: `/app`
- Arquivo-base: `web/app/domains/chat/auth_portal_routes.py`
- Templates: `login_app.html`, `index.html`, `planos.html`, `trocar_senha.html`

| Método | Rota | Handler | Template/resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/app/` | `pagina_inicial` | `index.html` | `chat.auth_portal_routes`, `chat.session_helpers`, `chat.laudo_service` |
| `GET` | `/app/laudo/{laudo_id:int}` | `pagina_laudo_alias` | redirect | `chat.auth_portal_routes` |
| `GET` | `/app/login` | `tela_login_app` | `login_app.html` | `chat.auth_portal_routes` |
| `POST` | `/app/login` | `processar_login_app` | redirect/form response | `chat.auth_portal_routes`, `shared.security` |
| `POST` | `/app/logout` | `logout_inspetor` | redirect | `chat.auth_portal_routes` |
| `GET` | `/app/planos` | `pagina_planos` | `planos.html` | `chat.auth_portal_routes` |
| `GET` | `/app/trocar-senha` | `tela_troca_senha_app` | `trocar_senha.html` | `chat.auth_portal_routes` |
| `POST` | `/app/trocar-senha` | `processar_troca_senha_app` | redirect/form response | `chat.auth_portal_routes`, `shared.security` |
| `GET` | `/app/manifesto.json` | `manifesto` | JSON | `http_setup_support` |
| `GET` | `/app/trabalhador_servico.js` | `service_worker` | JS | `http_setup_support` |

## 4. Portal do Inspetor: APIs web

### Chat, perfil e notificações

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `POST` | `/app/api/chat` | `rota_chat` | JSON ou `StreamingResponse` SSE-like | `chat.chat_stream_routes`, `nucleo.cliente_ia`, `shared.database` |
| `POST` | `/app/api/feedback` | `rota_feedback` | JSON | `chat.chat_aux_routes` |
| `POST` | `/app/api/gerar_pdf` | `rota_pdf` | arquivo/JSON | `chat.chat_aux_routes`, `nucleo.gerador_laudos` |
| `GET` | `/app/api/notificacoes/sse` | `sse_notificacoes_inspetor` | `StreamingResponse` | `chat.chat_runtime_support`, `chat.notifications` |
| `GET` | `/app/api/perfil` | `api_obter_perfil_usuario` | JSON | `chat.auth_portal_routes` |
| `PUT` | `/app/api/perfil` | `api_atualizar_perfil_usuario` | JSON | `chat.auth_portal_routes` |
| `POST` | `/app/api/perfil/foto` | `api_upload_foto_perfil_usuario` | JSON | `chat.auth_portal_routes` |
| `POST` | `/app/api/upload_doc` | `rota_upload_doc` | JSON | `chat.chat_aux_routes`, `chat.chat_service` |

### Ciclo de vida do laudo

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `POST` | `/app/api/laudo/iniciar` | `api_iniciar_relatorio` | JSON | `chat.laudo` |
| `DELETE` | `/app/api/laudo/iniciar` | `api_rota_laudo_post_nao_suportado` | erro controlado | `chat.laudo` |
| `GET` | `/app/api/laudo/status` | `api_status_relatorio` | JSON | `chat.laudo` |
| `DELETE` | `/app/api/laudo/status` | `api_status_relatorio_delete_nao_suportado` | erro controlado | `chat.laudo` |
| `POST` | `/app/api/laudo/cancelar` | `api_cancelar_relatorio` | JSON | `chat.laudo` |
| `DELETE` | `/app/api/laudo/cancelar` | `api_rota_laudo_post_nao_suportado` | erro controlado | `chat.laudo` |
| `POST` | `/app/api/laudo/desativar` | `api_desativar_relatorio_ativo` | JSON | `chat.laudo` |
| `DELETE` | `/app/api/laudo/desativar` | `api_rota_laudo_post_nao_suportado` | erro controlado | `chat.laudo` |
| `POST` | `/app/api/laudo/{laudo_id}/finalizar` | `api_finalizar_relatorio` | JSON | `chat.laudo`, `gate_helpers` |
| `POST` | `/app/api/laudo/{laudo_id}/reabrir` | `api_reabrir_laudo` | JSON | `chat.laudo` |
| `PATCH` | `/app/api/laudo/{laudo_id}/pin` | `rota_pin_laudo` | JSON | `chat.laudo` |
| `DELETE` | `/app/api/laudo/{laudo_id}` | `rota_deletar_laudo` | JSON | `chat.laudo` |
| `GET` | `/app/api/laudo/{laudo_id}/gate-qualidade` | `api_obter_gate_qualidade_laudo` | JSON | `chat.laudo`, `gate_helpers` |
| `GET` | `/app/api/laudo/{laudo_id}/mensagens` | `obter_mensagens_laudo` | JSON | `chat.chat_aux_routes`, `chat.chat_service` |
| `GET` | `/app/api/laudo/{laudo_id}/revisoes` | `listar_revisoes_laudo` | JSON | `chat.laudo` |
| `GET` | `/app/api/laudo/{laudo_id}/revisoes/diff` | `obter_diff_revisoes_laudo` | JSON | `chat.laudo` |

### Aprendizado visual

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/app/api/laudo/{laudo_id}/aprendizados` | `listar_aprendizados_visuais_inspetor` | JSON | `chat.learning` |
| `POST` | `/app/api/laudo/{laudo_id}/aprendizados` | `registrar_aprendizado_visual_inspetor` | JSON | `chat.learning`, `learning_helpers` |

### Mesa e pendências do inspetor

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `POST` | `/app/api/laudo/{laudo_id}/mesa/mensagem` | `enviar_mensagem_mesa_laudo` | JSON | `chat.mesa`, `domains.mesa` |
| `POST` | `/app/api/laudo/{laudo_id}/mesa/anexo` | `enviar_mensagem_mesa_laudo_com_anexo` | JSON | `chat.mesa`, `domains.mesa.attachments` |
| `GET` | `/app/api/laudo/{laudo_id}/mesa/mensagens` | `listar_mensagens_mesa_laudo` | JSON | `chat.mesa` |
| `GET` | `/app/api/laudo/{laudo_id}/mesa/resumo` | `obter_resumo_mesa_laudo` | JSON | `chat.mesa`, `domains.mesa.service` |
| `GET` | `/app/api/laudo/{laudo_id}/mesa/anexos/{anexo_id}` | `baixar_anexo_mesa_laudo` | arquivo | `chat.mesa`, `domains.mesa.attachments` |
| `GET` | `/app/api/laudo/{laudo_id}/pendencias` | `obter_pendencias_laudo` | JSON | `chat.pendencias` |
| `POST` | `/app/api/laudo/{laudo_id}/pendencias/marcar-lidas` | `marcar_pendencias_laudo_como_lidas` | JSON | `chat.pendencias` |
| `PATCH` | `/app/api/laudo/{laudo_id}/pendencias/marcar-lidas` | `api_pendencias_marcar_lidas_patch_nao_suportado` | erro controlado | `chat.pendencias` |
| `PATCH` | `/app/api/laudo/{laudo_id}/pendencias/{mensagem_id}` | `atualizar_pendencia_laudo` | JSON | `chat.pendencias` |
| `GET` | `/app/api/laudo/{laudo_id}/pendencias/exportar-pdf` | `exportar_pendencias_laudo_pdf` | arquivo | `chat.pendencias`, `nucleo.gerador_laudos` |
| `PATCH` | `/app/api/laudo/{laudo_id}/pendencias/exportar-pdf` | `api_pendencias_exportar_pdf_patch_nao_suportado` | erro controlado | `chat.pendencias` |

## 5. Inspetor mobile API

### Leitura do grupo

- Prefixo: `/app/api/mobile`
- Arquivos: `web/app/domains/chat/auth_mobile_routes.py`, `web/app/domains/chat/mesa.py`
- Consumidor principal: `android/src/config/*.ts`

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `POST` | `/app/api/mobile/auth/login` | `api_login_mobile_inspetor` | JSON bearer | `chat.auth_mobile_routes`, `shared.security` |
| `POST` | `/app/api/mobile/auth/logout` | `api_logout_mobile_inspetor` | JSON | `chat.auth_mobile_routes` |
| `GET` | `/app/api/mobile/bootstrap` | `api_bootstrap_mobile_inspetor` | JSON | `chat.auth_mobile_routes` |
| `GET` | `/app/api/mobile/laudos` | `api_listar_laudos_mobile_inspetor` | JSON | `chat.auth_mobile_routes` |
| `GET` | `/app/api/mobile/mesa/feed` | `feed_mesa_mobile` | JSON | `chat.mesa` |
| `PUT` | `/app/api/mobile/account/profile` | `api_atualizar_perfil_mobile_inspetor` | JSON | `chat.auth_mobile_routes` |
| `POST` | `/app/api/mobile/account/photo` | `api_upload_foto_perfil_mobile_usuario` | JSON | `chat.auth_mobile_routes` |
| `POST` | `/app/api/mobile/account/password` | `api_alterar_senha_mobile_inspetor` | JSON | `chat.auth_mobile_routes` |
| `GET` | `/app/api/mobile/account/settings` | `api_obter_configuracoes_criticas_mobile_inspetor` | JSON | `chat.auth_mobile_routes`, `PreferenciaMobileUsuario` |
| `PUT` | `/app/api/mobile/account/settings` | `api_salvar_configuracoes_criticas_mobile_inspetor` | JSON | `chat.auth_mobile_routes`, `PreferenciaMobileUsuario` |
| `POST` | `/app/api/mobile/support/report` | `api_relato_suporte_mobile_inspetor` | JSON | `chat.auth_mobile_routes` |

## 6. Portal Admin-Cliente: HTML

### Leitura do grupo

- Prefixo: `/cliente`
- Arquivo-base: `web/app/domains/cliente/routes.py`
- Templates: `login_cliente.html`, `cliente_portal.html`, `trocar_senha.html`

| Método | Rota | Handler | Template/resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/cliente/` | `raiz_cliente` | redirect | `cliente.routes` |
| `GET` | `/cliente/login` | `tela_login_cliente` | `login_cliente.html` | `cliente.routes` |
| `POST` | `/cliente/login` | `processar_login_cliente` | redirect/form response | `cliente.routes`, `shared.security` |
| `POST` | `/cliente/logout` | `logout_cliente` | redirect | `cliente.routes` |
| `GET` | `/cliente/painel` | `painel_cliente` | `cliente_portal.html` | `cliente.routes`, `route_support` |
| `GET` | `/cliente/trocar-senha` | `tela_troca_senha_cliente` | `trocar_senha.html` | `cliente.routes` |
| `POST` | `/cliente/trocar-senha` | `processar_troca_senha_cliente` | redirect/form response | `cliente.routes`, `shared.security` |

## 7. Portal Admin-Cliente: APIs

### Bootstrap, resumo e gestão da empresa

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/cliente/api/bootstrap` | `api_bootstrap_cliente` | JSON | `cliente.routes`, `dashboard_bootstrap` |
| `GET` | `/cliente/api/empresa/resumo` | `api_empresa_resumo_cliente` | JSON | `cliente.routes`, `dashboard` |
| `GET` | `/cliente/api/auditoria` | `api_auditoria_cliente` | JSON | `cliente.management_routes` |
| `PATCH` | `/cliente/api/empresa/plano` | `api_alterar_plano_cliente` | JSON | `cliente.management_routes`, `admin.services` |
| `POST` | `/cliente/api/empresa/plano/interesse` | `api_registrar_interesse_plano_cliente` | JSON | `cliente.management_routes` |
| `GET` | `/cliente/api/usuarios` | `api_listar_usuarios_cliente` | JSON | `cliente.management_routes` |
| `POST` | `/cliente/api/usuarios` | `api_criar_usuario_cliente` | JSON | `cliente.management_routes`, `admin.services` |
| `PATCH` | `/cliente/api/usuarios/{usuario_id}` | `api_atualizar_usuario_cliente` | JSON | `cliente.management_routes`, `admin.services` |
| `PATCH` | `/cliente/api/usuarios/{usuario_id}/bloqueio` | `api_bloqueio_usuario_cliente` | JSON | `cliente.management_routes`, `admin.services` |
| `POST` | `/cliente/api/usuarios/{usuario_id}/resetar-senha` | `api_resetar_senha_usuario_cliente` | JSON | `cliente.management_routes`, `admin.services` |

### Chat company-scoped

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/cliente/api/chat/status` | `api_chat_status_cliente` | JSON | `cliente.chat_routes`, `cliente.portal_bridge`, `chat.laudo_service` |
| `GET` | `/cliente/api/chat/laudos` | `api_chat_laudos_cliente` | JSON | `cliente.chat_routes` |
| `POST` | `/cliente/api/chat/laudos` | `api_chat_criar_laudo_cliente` | JSON | `cliente.chat_routes`, `cliente.portal_bridge` |
| `GET` | `/cliente/api/chat/laudos/{laudo_id}/mensagens` | `api_chat_mensagens_cliente` | JSON | `cliente.chat_routes`, `chat.chat_service` |
| `GET` | `/cliente/api/chat/laudos/{laudo_id}/gate` | `api_chat_gate_cliente` | JSON | `cliente.chat_routes`, `chat.laudo_service` |
| `POST` | `/cliente/api/chat/laudos/{laudo_id}/finalizar` | `api_chat_finalizar_cliente` | JSON | `cliente.chat_routes`, `chat.laudo_service` |
| `POST` | `/cliente/api/chat/laudos/{laudo_id}/reabrir` | `api_chat_reabrir_cliente` | JSON | `cliente.chat_routes`, `chat.laudo_service` |
| `POST` | `/cliente/api/chat/mensagem` | `api_chat_enviar_cliente` | JSON/stream | `cliente.chat_routes`, `cliente.portal_bridge`, `chat.chat_stream_routes` |
| `POST` | `/cliente/api/chat/upload_doc` | `api_chat_upload_doc_cliente` | JSON | `cliente.chat_routes`, `chat.chat_service` |

### Mesa company-scoped

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/cliente/api/mesa/laudos` | `api_mesa_laudos_cliente` | JSON | `cliente.chat_routes` |
| `GET` | `/cliente/api/mesa/laudos/{laudo_id}/mensagens` | `api_mesa_mensagens_cliente` | JSON | `cliente.chat_routes`, `cliente.portal_bridge`, `revisor.mesa_api` |
| `GET` | `/cliente/api/mesa/laudos/{laudo_id}/completo` | `api_mesa_completo_cliente` | JSON | `cliente.chat_routes`, `revisor.mesa_api` |
| `GET` | `/cliente/api/mesa/laudos/{laudo_id}/pacote` | `api_mesa_pacote_cliente` | JSON | `cliente.chat_routes`, `domains.mesa.service` |
| `POST` | `/cliente/api/mesa/laudos/{laudo_id}/responder` | `api_mesa_responder_cliente` | JSON | `cliente.chat_routes`, `revisor.mesa_api` |
| `POST` | `/cliente/api/mesa/laudos/{laudo_id}/responder-anexo` | `api_mesa_responder_anexo_cliente` | JSON | `cliente.chat_routes`, `revisor.mesa_api` |
| `PATCH` | `/cliente/api/mesa/laudos/{laudo_id}/pendencias/{mensagem_id}` | `api_mesa_pendencia_cliente` | JSON | `cliente.chat_routes`, `revisor.mesa_api` |
| `POST` | `/cliente/api/mesa/laudos/{laudo_id}/avaliar` | `api_mesa_avaliar_cliente` | JSON | `cliente.chat_routes`, `revisor.mesa_api` |
| `POST` | `/cliente/api/mesa/laudos/{laudo_id}/marcar-whispers-lidos` | `api_mesa_marcar_whispers_lidos_cliente` | JSON | `cliente.chat_routes`, `revisor.mesa_api` |
| `GET` | `/cliente/api/mesa/laudos/{laudo_id}/anexos/{anexo_id}` | `api_mesa_baixar_anexo_cliente` | arquivo | `cliente.chat_routes`, `revisor.mesa_api` |

## 8. Portal Revisor: HTML

### Leitura do grupo

- Prefixo: `/revisao`
- Arquivos: `auth_portal.py`, `panel.py`, `templates_laudo.py`
- Templates: `login_revisor.html`, `painel_revisor.html`, `revisor_templates_biblioteca.html`, `revisor_templates_editor_word.html`, `trocar_senha.html`

| Método | Rota | Handler | Template/resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/revisao/login` | `tela_login_revisor` | `login_revisor.html` | `revisor.auth_portal` |
| `POST` | `/revisao/login` | `processar_login_revisor` | redirect/form response | `revisor.auth_portal`, `shared.security` |
| `POST` | `/revisao/logout` | `logout_revisor` | redirect | `revisor.auth_portal` |
| `GET` | `/revisao/painel` | `painel_revisor` | `painel_revisor.html` | `revisor.panel` |
| `GET` | `/revisao/templates-laudo` | `tela_templates_laudo` | `revisor_templates_biblioteca.html` | `revisor.templates_laudo` |
| `GET` | `/revisao/templates-laudo/editor` | `tela_editor_templates_laudo` | `revisor_templates_editor_word.html` | `revisor.templates_laudo` |
| `GET` | `/revisao/trocar-senha` | `tela_troca_senha_revisor` | `trocar_senha.html` | `revisor.auth_portal` |
| `POST` | `/revisao/trocar-senha` | `processar_troca_senha_revisor` | redirect/form response | `revisor.auth_portal`, `shared.security` |

## 9. Portal Revisor: APIs

### Mesa, histórico e learnings

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/revisao/api/laudo/{laudo_id}/mensagens` | `obter_historico_chat_revisor` | JSON | `revisor.mesa_api` |
| `GET` | `/revisao/api/laudo/{laudo_id}/completo` | `obter_laudo_completo` | JSON | `revisor.mesa_api` |
| `GET` | `/revisao/api/laudo/{laudo_id}/pacote` | `obter_pacote_mesa_laudo` | JSON | `revisor.mesa_api`, `domains.mesa.service` |
| `GET` | `/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf` | `exportar_pacote_mesa_laudo_pdf` | arquivo | `revisor.mesa_api`, `nucleo.gerador_laudos` |
| `POST` | `/revisao/api/laudo/{laudo_id}/responder` | `responder_chat_campo` | JSON | `revisor.mesa_api`, `revisor.service` |
| `POST` | `/revisao/api/laudo/{laudo_id}/responder-anexo` | `responder_chat_campo_com_anexo` | JSON | `revisor.mesa_api`, `revisor.service` |
| `PATCH` | `/revisao/api/laudo/{laudo_id}/pendencias/{mensagem_id}` | `atualizar_pendencia_mesa_revisor` | JSON | `revisor.mesa_api`, `revisor.service` |
| `POST` | `/revisao/api/laudo/{laudo_id}/avaliar` | `avaliar_laudo` | JSON | `revisor.mesa_api`, `revisor.service` |
| `POST` | `/revisao/api/laudo/{laudo_id}/marcar-whispers-lidos` | `marcar_whispers_lidos` | JSON | `revisor.mesa_api`, `revisor.realtime` |
| `GET` | `/revisao/api/laudo/{laudo_id}/mesa/anexos/{anexo_id}` | `baixar_anexo_mesa_revisor` | arquivo | `revisor.mesa_api`, `domains.mesa.attachments` |
| `POST` | `/revisao/api/whisper/responder` | `whisper_responder` | JSON | `revisor.mesa_api`, `revisor.realtime` |
| `GET` | `/revisao/api/laudo/{laudo_id}/aprendizados` | `listar_aprendizados_visuais_revisor` | JSON | `revisor.learning_api` |
| `POST` | `/revisao/api/aprendizados/{aprendizado_id}/validar` | `validar_aprendizado_visual_revisor` | JSON | `revisor.learning_api` |

### Biblioteca e editor de templates de laudo

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `GET` | `/revisao/api/templates-laudo` | `listar_templates_laudo` | JSON | `revisor.templates_laudo` |
| `GET` | `/revisao/api/templates-laudo/auditoria` | `listar_auditoria_templates_laudo` | JSON | `revisor.templates_laudo` |
| `GET` | `/revisao/api/templates-laudo/diff` | `comparar_versoes_template_laudo` | JSON | `revisor.templates_laudo`, `templates_laudo_diff` |
| `POST` | `/revisao/api/templates-laudo/upload` | `upload_template_laudo` | JSON | `revisor.templates_laudo` |
| `GET` | `/revisao/api/templates-laudo/{template_id:int}` | `detalhar_template_laudo` | JSON | `revisor.templates_laudo` |
| `DELETE` | `/revisao/api/templates-laudo/{template_id:int}` | `excluir_template_laudo` | JSON | `revisor.templates_laudo` |
| `POST` | `/revisao/api/templates-laudo/{template_id:int}/preview` | `preview_template_laudo` | preview/PDF | `revisor.templates_laudo`, `nucleo.template_laudos` |
| `GET` | `/revisao/api/templates-laudo/{template_id:int}/arquivo-base` | `baixar_pdf_base_template_laudo` | arquivo | `revisor.templates_laudo` |
| `POST` | `/revisao/api/templates-laudo/{template_id:int}/publicar` | `publicar_template_laudo` | JSON | `templates_laudo_management_routes` |
| `PATCH` | `/revisao/api/templates-laudo/{template_id:int}/status` | `atualizar_status_template_laudo` | JSON | `templates_laudo_management_routes` |
| `POST` | `/revisao/api/templates-laudo/{template_id:int}/clonar` | `clonar_template_laudo` | JSON | `templates_laudo_management_routes` |
| `POST` | `/revisao/api/templates-laudo/{template_id:int}/base-recomendada` | `promover_template_como_base_recomendada` | JSON | `templates_laudo_management_routes` |
| `DELETE` | `/revisao/api/templates-laudo/{template_id:int}/base-recomendada` | `restaurar_base_recomendada_automatica` | JSON | `templates_laudo_management_routes` |
| `POST` | `/revisao/api/templates-laudo/lote/status` | `atualizar_status_template_laudo_em_lote` | JSON | `templates_laudo_management_routes` |
| `POST` | `/revisao/api/templates-laudo/lote/excluir` | `excluir_template_laudo_em_lote` | JSON | `templates_laudo_management_routes` |
| `POST` | `/revisao/api/templates-laudo/editor` | `criar_template_editor_laudo` | JSON | `templates_laudo_editor_routes` |
| `GET` | `/revisao/api/templates-laudo/editor/{template_id:int}` | `detalhar_template_editor_laudo` | JSON | `templates_laudo_editor_routes` |
| `PUT` | `/revisao/api/templates-laudo/editor/{template_id:int}` | `salvar_template_editor_laudo` | JSON | `templates_laudo_editor_routes` |
| `POST` | `/revisao/api/templates-laudo/editor/{template_id:int}/assets` | `upload_asset_template_editor_laudo` | JSON | `templates_laudo_editor_routes` |
| `GET` | `/revisao/api/templates-laudo/editor/{template_id:int}/assets/{asset_id}` | `baixar_asset_template_editor_laudo` | arquivo | `templates_laudo_editor_routes` |
| `POST` | `/revisao/api/templates-laudo/editor/{template_id:int}/preview` | `preview_template_editor_laudo` | preview/PDF | `templates_laudo_editor_routes`, `nucleo.template_editor_word` |
| `POST` | `/revisao/api/templates-laudo/editor/{template_id:int}/publicar` | `publicar_template_editor_laudo` | JSON | `templates_laudo_management_routes` |

## 10. Realtime e assets

| Método | Rota | Handler | Resposta | Módulos envolvidos |
| --- | --- | --- | --- | --- |
| `WS` | `/revisao/ws/whispers` | `websocket_whispers` | WebSocket | `revisor.ws`, `revisor.realtime`, `shared.security` |
| `MOUNT` | `/static` | `StaticFiles` | arquivos estáticos | `web/main.py` |

## Rotas mais importantes do sistema

As rotas abaixo representam os fluxos mais críticos do produto:

- `/app/`
- `/app/api/chat`
- `/app/api/laudo/status`
- `/app/api/notificacoes/sse`
- `/app/api/mobile/bootstrap`
- `/cliente/painel`
- `/cliente/api/bootstrap`
- `/cliente/api/chat/mensagem`
- `/cliente/api/mesa/laudos/{laudo_id}/pacote`
- `/revisao/painel`
- `/revisao/api/laudo/{laudo_id}/responder`
- `/revisao/api/templates-laudo`
- `/revisao/ws/whispers`
- `/admin/painel`

## Confirmado no código

- O sistema é multiportal, mas centraliza tudo na mesma aplicação FastAPI.
- O inspetor tem três superfícies distintas: HTML, API web e API mobile.
- O portal cliente reaproveita fluxos de chat e mesa por bridge, não por duplicação total.
- O revisor combina HTTP tradicional com WebSocket.
- Há rotas explícitas de “método não suportado” em algumas áreas do laudo e de pendências, sugerindo defesa de contrato já incorporada ao código.

## Inferência provável

- O mapa de rotas mostra que o sistema cresceu por adição incremental de capacidades sobre poucos domínios muito centrais, especialmente `chat` e `revisor`.
- A superfície do inspetor e da mesa é a mais sensível a regressões, porque cruza API, SSR, SSE, WebSocket, arquivos e regras de estado.

## Dúvida aberta

- A aplicação não expõe versionamento de API por prefixo. Isso sugere evolução contínua da mesma superfície, mas o código inspecionado não deixa claro se há consumidores externos além do próprio web/mobile que dependam desses contratos.
