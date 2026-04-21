# 03 - Frontend And Visual Review

## Resumo

A direção visual principal está melhor do que os primeiros materiais de auditoria sugeriam. O problema atual não é "falta de interface" e sim fragmentação.

## Hotspots visuais reais

- `web/static/js/chat/chat_index_page.js` — 6882 linhas
- `web/static/css/chat/chat_base.css` — 5682 linhas
- `web/static/css/inspetor/reboot.css` — 4132 linhas
- `web/static/css/inspetor/workspace.css` — 3897 linhas
- `web/static/css/revisor/painel_revisor.css` — 3649 linhas

## O que está bom

- Mesa SSR com leitura operacional clara
- Admin e Cliente com sistema de tipografia e cards mais consistente
- Mobile com arquitetura de features bem mais organizada que o web legado

## O que está ruim ou inconsistente

- inspetor web ainda concentra responsabilidade demais
- shell do cliente é funcional, mas pesado em módulos e folhas CSS
- coexistem CSS mais novo e legado em admin/chat/inspetor
- material de mapeamento do repo ficou atrás da UI real

## O que precisa padronizar antes de dizer "acabou"

- confirmações destrutivas
- mensagens de erro/sucesso
- linguagem de status operacional
- simplificação da camada visual legada ainda ativa

## O que claramente não precisa acontecer

- criar uma nova Mesa
- reescrever o mobile inteiro
- redesenhar o produto do zero
