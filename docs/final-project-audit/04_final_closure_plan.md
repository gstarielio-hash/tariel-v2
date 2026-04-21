# Final Closure Plan

## Bloqueadores de finalização

1. Estabilizar `make mesa-acceptance` para que o gate visual da Mesa seja repetível e não falhe de forma intermitente no login do inspetor.
2. Se o nível de prova exigido for produção real, repetir a observação do cleanup automático no deploy-alvo oficial.

## Importante, mas não bloqueia estruturalmente

1. Atualizar `PROJECT_MAP.md` e o inventário heurístico de superfícies para o estado real pós-consolidação.
2. Reduzir ambiguidade em rotas de laudo verb-based e nos dois entrypoints de publish de template.
3. Manter o guardrail legado do mobile V2 documentado como decisão de design, não como transição aberta.

## Melhoria desejável

1. Fatiar `chat_index_page.js`, `chat_base.css`, `mobile_rollout.py` e `run_mobile_pilot_runner.py`.
2. Harmonizar confirmações destrutivas, toasts e mensagens de erro/sucesso entre portais.
3. Reduzir carga modular do shell do portal cliente.

## Pode ser adiado

1. Remoção futura do guardrail legado do mobile V2.
2. Refino visual amplo sem impacto em aceitação operacional.
3. Reorganização maior de serviços admin sem regressão de produto.

## Manter

- Mesa SSR como superfície oficial
- release gate e final-product-stamp como alvos canônicos
- cleanup automático com guardrails
- mobile V2 em `closed_with_guardrails`
