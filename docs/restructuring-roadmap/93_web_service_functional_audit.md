# Auditoria funcional do servico web e mapa inicial Mesa-template

## Objetivo

Registrar, com base no codigo atual e nas rotas reais expostas por `web/main.py`, como o servico web esta organizado hoje e onde vivem, de fato:

- os portais ativos
- as rotas principais de cada superficie
- a operacao da Mesa Avaliadora
- o lifecycle de templates

## Pre-checagem

- `pwd`:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - worktree ampla e suja fora do recorte
  - havia mudancas preexistentes relevantes em `web/app/domains/revisor/panel.py` e `web/templates/painel_revisor.html`
  - esta fase ficou restrita a:
    - auditoria
    - artifacts
    - docs
    - um slice pequeno no painel da Mesa
- boot real das rotas:
  - `web/main.py` registra quatro roteadores principais:
    - `roteador_admin` em `/admin`
    - `roteador_cliente` em `/cliente`
    - `roteador_inspetor` em `/app`
    - `roteador_revisor` em `/revisao`
- inventario real:
  - `create_app()` foi usado para listar as rotas HTTP atuais do servico
  - total auditado: `177` rotas HTTP

## Como o web funciona hoje

O servico web continua organizado como um modular monolith com quatro superfices SSR/API principais e um pequeno conjunto de rotas compartilhadas:

- `admin`
  - portal do admin-geral
  - autentica, opera SaaS e consulta observabilidade administrativa
- `cliente`
  - portal do admin-cliente
  - mistura gestao company-scoped, wrappers de chat e wrappers de mesa
- `app`
  - portal do inspetor
  - concentra ciclo do laudo, gate de qualidade, chat, pendencias e mesa bilateral
- `revisao`
  - portal da Mesa Avaliadora
  - concentra inbox tecnico, decisao de revisao, aprendizados e todo o lifecycle de templates
- `shared`
  - healthchecks, redirect raiz, manifest e service worker

Leitura estrutural importante:

- o portal `revisao` hoje nao e apenas um inbox de avaliacao
- ele tambem e o backoffice documental do produto para templates
- por isso Mesa e templates compartilham o mesmo ownership tecnico real

## Superficies reais em uso

### Admin Geral

- entrada:
  - `GET /admin/painel`
- modulos principais:
  - `web/app/domains/admin/routes.py`
  - `web/app/domains/admin/client_routes.py`
- papel:
  - autenticar diretoria
  - operar empresas/clientes
  - consultar observabilidade administrativa

### Admin Cliente

- entrada:
  - `GET /cliente/painel`
- modulos principais:
  - `web/app/domains/cliente/routes.py`
  - `web/app/domains/cliente/management_routes.py`
  - `web/app/domains/cliente/chat_routes.py`
- papel:
  - administrar empresa e usuarios
  - consumir wrappers company-scoped de chat e mesa

### Chat Inspetor

- entrada:
  - `GET /app/`
- modulos principais:
  - `web/app/domains/chat/auth_portal_routes.py`
  - `web/app/domains/chat/laudo.py`
  - `web/app/domains/chat/chat.py`
  - `web/app/domains/chat/mesa.py`
  - `web/app/domains/chat/pendencias.py`
- papel:
  - iniciar, editar, finalizar e reabrir laudos
  - conversar com IA
  - trocar mensagens com a mesa

### Mesa Avaliadora

- entrada:
  - `GET /revisao/painel`
- modulos principais:
  - `web/app/domains/revisor/panel.py`
  - `web/app/domains/revisor/mesa_api.py`
  - `web/app/domains/revisor/learning_api.py`
  - `web/templates/painel_revisor.html`
- papel:
  - triagem
  - whispers
  - pendencias
  - pacote operacional
  - aprovacao/rejeicao

### Templates da Mesa

- entradas:
  - `GET /revisao/templates-laudo`
  - `GET /revisao/templates-laudo/editor`
- modulos principais:
  - `web/app/domains/revisor/templates_laudo.py`
  - `web/app/domains/revisor/templates_laudo_editor_routes.py`
  - `web/app/domains/revisor/templates_laudo_management_routes.py`
  - `web/app/domains/revisor/templates_laudo_support.py`
- papel:
  - biblioteca
  - editor Word
  - diff
  - preview
  - auditoria
  - publicacao/ativacao
  - ciclo de vida do template

## Rotas principais e classificacao canonica

O inventario completo ficou em:

- `artifacts/web_service_audit/20260328_090546/route_inventory.json`

Os agrupamentos mais importantes do servico atual sao:

### Rotas de Mesa

- leitura:
  - `GET /revisao/painel`
  - `GET /revisao/api/laudo/{laudo_id}/completo`
  - `GET /revisao/api/laudo/{laudo_id}/mensagens`
  - `GET /revisao/api/laudo/{laudo_id}/pacote`
  - `GET /revisao/api/laudo/{laudo_id}/pacote/exportar-pdf`
- mutacao:
  - `POST /revisao/api/laudo/{laudo_id}/responder`
  - `POST /revisao/api/laudo/{laudo_id}/responder-anexo`
  - `PATCH /revisao/api/laudo/{laudo_id}/pendencias/{mensagem_id}`
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
  - `POST /revisao/api/laudo/{laudo_id}/marcar-whispers-lidos`

### Rotas de Templates

- leitura:
  - `GET /revisao/templates-laudo`
  - `GET /revisao/templates-laudo/editor`
  - `GET /revisao/api/templates-laudo`
  - `GET /revisao/api/templates-laudo/auditoria`
  - `GET /revisao/api/templates-laudo/{template_id}`
  - `GET /revisao/api/templates-laudo/{template_id}/arquivo-base`
  - `GET /revisao/api/templates-laudo/diff`
- mutacao:
  - `POST /revisao/api/templates-laudo/upload`
  - `POST /revisao/api/templates-laudo/editor`
  - `PUT /revisao/api/templates-laudo/editor/{template_id}`
  - `POST /revisao/api/templates-laudo/{template_id}/preview`
  - `POST /revisao/api/templates-laudo/editor/{template_id}/preview`
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
  - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
  - `PATCH /revisao/api/templates-laudo/{template_id}/status`
  - `POST /revisao/api/templates-laudo/lote/status`
  - `POST /revisao/api/templates-laudo/lote/excluir`
  - `POST /revisao/api/templates-laudo/{template_id}/clonar`
  - `POST|DELETE /revisao/api/templates-laudo/{template_id}/base-recomendada`

### Rotas de revisao/aprovacao/rejeicao/finalizacao

- no inspetor:
  - `POST /app/api/laudo/{laudo_id}/finalizar`
  - `POST /app/api/laudo/{laudo_id}/reabrir`
- na mesa:
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
- no template lifecycle:
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
  - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`

## Rotas sensiveis, atuais e concorrencias

### Sensiveis

No estado atual, sao claramente sensiveis:

- autenticacao e troca de senha em todos os portais
- mutacoes de empresa/usuario no `admin` e `cliente`
- finalizacao e reabertura do laudo no `app`
- respostas, pendencias e avaliacao da mesa em `revisao`
- todo o fluxo de publicar, excluir, clonar e alterar status de template em `revisao`

### Atuais x guardas de compatibilidade

A maior parte das rotas inventariadas e atual.

Os pontos com cara de compatibilidade guardada sao:

- endpoints `nao_suportado` no `app`
- superfice mobile adjacente em `/app/api/mobile/*`

### Duplicadas ou concorrentes

O inventario mostrou tres familias que merecem nota:

- `POST /revisao/api/templates-laudo/{template_id}/publicar`
- `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`

Leitura correta:

- nao sao rotas conflitantes
- sao dois entrypoints complementares da mesma familia de publicacao, separados pelo modo de edicao

Tambem ha paralelismo entre:

- `revisao/api/laudo/*`
- `cliente/api/mesa/laudos/*`

Leitura correta:

- o fluxo principal da mesa vive em `revisao`
- `cliente` expoe uma superficie company-scoped paralela e mais estreita

## Onde a Mesa vive e onde os templates vivem

### Mesa

Mesa vive, de fato, em:

- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/mesa/service.py`
- `web/templates/painel_revisor.html`
- `web/static/js/revisor/revisor_painel_core.js`
- `web/static/js/revisor/painel_revisor_page.js`

### Templates

Templates vivem, de fato, em:

- `web/app/domains/revisor/templates_laudo.py`
- `web/app/domains/revisor/templates_laudo_editor_routes.py`
- `web/app/domains/revisor/templates_laudo_management_routes.py`
- `web/app/domains/revisor/templates_laudo_support.py`
- `web/templates/revisor_templates_biblioteca.html`
- `web/templates/revisor_templates_editor_word.html`
- `web/static/js/revisor/templates_biblioteca_page.js`
- `web/static/js/revisor/templates_editor_word.js`

## Melhor primeira frente de melhoria na Mesa

Conclusao da auditoria:

- o problema principal nao era falta de rota
- o problema principal era distancia operacional entre:
  - o inbox da Mesa em `/revisao/painel`
  - e a governanca real da biblioteca de templates em `/revisao/templates-laudo`

Por isso, a melhor primeira frente segura foi:

- aproximar a visao de templates do proprio painel da Mesa
- sem mexer no contrato publico
- sem alterar o fluxo de publicacao
- sem refatoracao transversal

## Artefatos desta auditoria

- `artifacts/web_service_audit/20260328_090546/route_inventory.json`
- `artifacts/web_service_audit/20260328_090546/portal_matrix.md`
- `artifacts/web_service_audit/20260328_090546/mesa_template_focus.md`
- `artifacts/web_service_audit/20260328_090546/source_index.txt`
