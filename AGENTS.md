# AGENTS

Guia local para agentes e automacoes trabalharem nesta base com o minimo de exploracao desnecessaria.

## Fonte de verdade

- Estado curto e direção vigente: `docs/STATUS_CANONICO.md`
- Frentes longas e checkpoints ativos: `PLANS.md`
- Roadmap funcional base: `docs/roadmap_execucao_funcional_web_mobile.md`
- Retomada da frente de `report pack` e entrada configurável: `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`
- Mapa do sistema vivo: `PROJECT_MAP.md`

## Comandos obrigatórios

- Baseline local: `make verify`
- Higiene operacional: `make hygiene-check`
- Web: `make web-ci`
- Mobile: `make mobile-ci`
- Mesa: `make mesa-smoke`

## Regras operacionais

- Não abrir fase nova com baseline quebrada.
- Não mudar contrato sem atualizar teste, fixture ou schema.
- Não commitar artefato gerado localmente.
- Em tarefa com mais de `30 min` ou multissuperfície, atualizar `PLANS.md`.
- Usar `git worktree` por frente estrutural, hotfix ou spike.
- Validar higiene do workspace antes de promover fase de governança: `make hygiene-check`.
- Sempre fazer busca na web quando isso reduzir risco de desatualizacao, dependencia externa ou duvida factual sobre servicos, bibliotecas, specs, produtos ou comportamento atual.
- Quando a tarefa exigir material externo atual para validar ou completar a execucao, downloads operacionais sao permitidos desde que tenham relacao direta com a frente ativa.

## Antes de mexer

- Leia `PROJECT_MAP.md` para localizar o fluxo certo.
- Use `README.md` para setup e comandos globais.
- Use `web/app/ARCHITECTURE.md` e `web/app/domains/chat/ARCHITECTURE.md` quando a duvida for estrutural.
- Use `web/docs/checklist_qualidade.md` e `web/docs/regras_de_encerramento.md` quando o assunto for finalizar, bloquear ou reabrir laudo.
- Use `web/docs/mesa_avaliadora.md` e `web/docs/frontend_mapa.md` para navegar mais rapido em mesa e UI.
- Se o usuario enviar link ou frame do Figma, use o servidor MCP da Figma antes de propor HTML/CSS/React; veja `docs/FIGMA_CODEX_WORKFLOW.md`.

## Onde olhar primeiro por assunto

### Portal do inspetor

- Backend: `web/app/domains/chat/router.py`, `web/app/domains/chat/laudo.py`, `web/app/domains/chat/chat.py`
- Frontend: `web/templates/index.html`, `web/static/js/chat/chat_index_page.js`

### Mesa Avaliadora

- Backend inspetor: `web/app/domains/chat/mesa.py`
- Backend revisor: `web/app/domains/revisor/routes.py`
- Servicos/contratos: `web/app/domains/mesa/service.py`, `web/app/domains/mesa/contracts.py`
- UI inspetor: `web/templates/index.html`, `web/static/js/chat/chat_index_page.js`
- UI revisor: `web/templates/painel_revisor.html`

### Pendencias e pacote da mesa

- `web/app/domains/chat/pendencias.py`
- `web/app/domains/chat/pendencias_helpers.py`
- `web/app/domains/mesa/service.py`

### Portal do admin-cliente

- Backend: `web/app/domains/cliente/routes.py`, `web/app/domains/cliente/common.py`
- Templates: `web/templates/login_cliente.html`, `web/templates/cliente_portal.html`
- Servicos administrativos reutilizados: `web/app/domains/admin/services.py`
- Seguranca/sessao: `web/app/shared/security.py`, `web/app/shared/database.py`

### Portal do admin-ceo

- Backend: `web/app/domains/admin/routes.py`, `web/app/domains/admin/services.py`
- Templates: `web/templates/admin/login.html`, `web/templates/admin/dashboard.html`, `web/templates/admin/clientes.html`, `web/templates/admin/novo_cliente.html`
- Seguranca/sessao: `web/app/shared/security.py`, `web/app/shared/database.py`

### Gate de qualidade e bloqueio de encerramento

- `web/app/domains/chat/gate_helpers.py`
- `web/app/domains/chat/laudo.py`
- `web/templates/index.html`
- `web/docs/checklist_qualidade.md`
- `web/docs/regras_de_encerramento.md`

### Perfil / Home / modo foco

- `web/templates/inspetor/base.html`
- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_perfil_usuario.js`
- `web/static/css/shared/app_shell.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`

## Regras praticas de navegacao

- Se o problema for de persistencia, abra `web/app/shared/database.py` cedo.
- Se o problema for visual no chat do inspetor, comece por `reboot.css`, `official_visual_system.css` e os slices `workspace_{chrome,history,rail,states}.css`.
- Se o problema for de shell global, comece por `web/templates/inspetor/base.html`, `web/static/js/shared/ui.js` e `web/static/css/shared/app_shell.css`.
- Se o problema for de revisor, confira `web/templates/painel_revisor.html` antes de procurar JS separado.
- Se o problema for do portal `/cliente`, confira primeiro `web/app/domains/cliente/routes.py` e depois os wrappers reaproveitados em `chat`/`revisor`.

## Busca recomendada

```powershell
rg -n "termo" web/app web/templates web/static web/tests android/src docs
sg run --lang python --pattern 'async def $NAME($$$): $$$' web/app/domains/chat/mesa.py
ctags --extras=+q --fields=+n -R web/app web/templates web/static web/tests android/src docs
```

## Testes recomendados por impacto

- Contrato/template: `cd web && PYTHONPATH=. python -m pytest tests/test_smoke.py -q`
- Regra critica: `cd web && PYTHONPATH=. python -m pytest tests/test_regras_rotas_criticas.py -q`
- Fluxo real: `cd web && RUN_E2E=1 PYTHONPATH=. python -m pytest tests/e2e/test_portais_playwright.py -q`

## Evite

- Reintroduzir arquivos legados removidos da raiz.
- Espalhar regra nova em `web/app/domains/chat/routes.py`; use os modulos tematicos.
- Mexer em CSS do chat sem checar se a regra pertence ao shell, ao nucleo ou a pagina index.
