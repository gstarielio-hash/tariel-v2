# Flow Audit

Data: 2026-04-04 17:12:54

## Login por portal

- Admin: funcional, incluindo MFA/reauth e identity login; fluxo real confirmado por rotas e painel vivo.
- Inspetor web (`/app`): funcional, mas o aceite visual mostrou flake no login em uma reexecução (`mesa-acceptance` falhou uma vez e passou no rerun imediato).
- Cliente: funcional com shell único e boot modular explícito.
- Revisor (`/revisao`): funcional com SSR da Mesa e templates.

Impedimento para chamar de finalizado: repetibilidade do aceite Playwright do portal do inspetor/revisor.

## Fluxo do inspetor

- Funciona: iniciar laudo, conversar com IA, abrir workspace, anexar, enviar para Mesa, histórico, pendências, PDF.
- Parcial/frágil: contratos legado de laudo (`status`, `cancelar`, `desativar`) ainda coexistem com estilo mais resource-oriented.
- Redundante/confuso: grande parte da experiência está concentrada em `web/static/js/chat/chat_index_page.js` (6882 linhas) e compatibilidades visuais em `chat_base.css` (5682 linhas).

## Mesa oficial SSR

- Funciona: fila, whispers, histórico completo, pacote, pendências, resposta e anexos.
- Funciona parcial: aceite visual web não é totalmente repetível; falha intermitente atual no login do inspetor em E2E.
- O que impediria "produto finalizado": manter o gate `mesa-acceptance` flakey enfraquece qualquer carimbo final confiável.

## Fluxo do cliente

- Funciona: shell admin/chat/mesa, bootstrap, criação de laudo, upload, finalizar/reabrir, responder Mesa, suporte e gestão de usuários.
- Frágil: `portal_bridge.py` ainda expõe acoplamento direto com chat/revisor.
- Confuso: o portal tem contrato de boot explícito e forte, mas depende de muitos módulos JS e várias folhas CSS.

## Templates / documento / PDF

- Funciona: biblioteca, editor, preview, publicação, base recomendada, auditoria, diff e gates documentais verdes.
- Parcial: coexistem entrypoints de publicação pela rota do editor e pela rota geral; isso é funcional, mas aumenta ambiguidade.
- O que falta: mais simplificação semântica, não funcionalidade core.

## Mobile

- Funciona: bootstrap, login, histórico, chat, Mesa, operator-run/smoke e contratos V2.
- Estado atual: `closed_with_guardrails`; guardrail legado permanece por design e não bloqueia o produto.
- Limitação real: a lane real depende de host Android local/assistido; CI hospedada ainda não representa o gate real completo.

## Observabilidade e notificações

- Funciona: health/ready, summaries admin, observability acceptance, traces/IDs e artefatos de auditoria.
- Parcial: carimbo observacional real do cleanup em deploy-alvo ainda não ocorreu; só há evidência production-like equivalente.
