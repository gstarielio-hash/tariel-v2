# Focused Entry Screen do Novo Chat

## Objetivo

Reduzir a experiência de `assistant_landing` para uma tela inicial de chat livre mais calma e focada, sem alterar backend, endpoints, contratos, regras de negócio ou o fluxo funcional da primeira mensagem.

## O que esta fase faz

- separa visualmente o `portal_dashboard` como home/apresentação
- mantém `Novo Chat` abrindo o modo já existente `assistant_landing`
- transforma `assistant_landing` em uma superfície mínima de entrada de conversa
- preserva o `#campo-mensagem` como ponto central da interação
- preserva o foco final no composer ao abrir `Novo Chat`

## O que saiu da antiga landing

- hero operacional grande e duplicada
- grade de cards grandes
- exemplos pesados abaixo da dobra
- CTA visível de `Nova Inspeção` dentro da landing/header do assistente
- barra visual de dashboard na entrada de chat livre

## O que fica visível na nova entry screen

- link discreto `Portal` no topo
- badge discreto `CHAT LIVRE`
- título curto `Novo Chat`
- subtítulo curto e direto
- composer premium dark como protagonista
- até 4 chips curtos de entrada logo abaixo do composer

## O que continua preservado

- `open-assistant-chat`
- `abrirChatLivreInspector(...)`
- `assistant_landing` como screen mode de entrada
- foco no `#campo-mensagem`
- transição atual após a primeira mensagem
- criação de laudo apenas quando o fluxo atual já decidir isso
