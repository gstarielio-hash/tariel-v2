# Figma + Codex Workflow

Fluxo recomendado para transformar layout visual em implementacao no projeto com o Codex CLI.

## Estado local

O Codex desta maquina ja esta configurado com o servidor MCP remoto oficial da Figma em `~/.codex/config.toml`.
Verificacao rapida:

```bash
codex mcp list
```

Voce deve ver `figma` como `enabled` com `Auth = OAuth`.

## Como enviar um layout para o Codex

1. Abra o arquivo no Figma.
2. Selecione o frame ou componente que quer implementar.
3. Copie o link da selecao ou do frame.
4. Cole o link no prompt do Codex junto com a instrucao de implementacao.

## Prompt base

Use este prompt como ponto de partida:

```text
Use o MCP da Figma para ler este frame e implementar no projeto atual.

Link Figma: <cole-o-link-aqui>

Regras:
- mantenha a estrutura do projeto
- implemente com Astro + React 19 + Tailwind v4 + shadcn/ui quando fizer sentido
- reutilize componentes existentes antes de criar novos
- puxe tokens, espacamentos e tipografia do Figma
- se houver duvida visual, use screenshot e variables do Figma antes de inventar valores
- entregue codigo pronto no repositorio, nao apenas sugestoes
```

## Prompt para migrar uma tela existente

```text
Use o MCP da Figma para ler este frame e migrar a tela atual do projeto para esse layout.

Link Figma: <cole-o-link-aqui>

Objetivo:
- substituir a interface atual por esta versao
- manter os comportamentos e contratos da tela atual
- mapear o layout novo em componentes reutilizaveis
- apontar qualquer dependencia backend ou dado que ainda precisa ser adaptado
```

## Prompt para componente isolado

```text
Use o MCP da Figma para inspecionar este componente e implemente-o no projeto.

Link Figma: <cole-o-link-aqui>

Quero:
- componente reutilizavel
- variantes coerentes com o design
- props bem nomeadas
- uso de shadcn/ui apenas quando ajudar, sem forcar
- integracao com o estilo atual do projeto
```

## O que pedir ao Codex quando a fidelidade precisar ser maior

Se o resultado inicial vier generico demais, acrescente:

```text
Antes de implementar:
- use get_design_context
- use get_variable_defs
- use get_screenshot
- priorize correspondencia visual sobre simplificacao estetica
```

## Como revisar rapidamente no TUI

Dentro do Codex interativo:

- rode `/mcp` para confirmar que `figma` esta ativo
- envie o link do frame no prompt
- se houver mais de uma tela, implemente uma por vez

## Regras praticas

- Prefira um frame por vez; telas grandes demais reduzem a fidelidade.
- Quando houver design system no Figma, implemente primeiro os componentes-base.
- Nao peça “faça parecido”; peça “implemente este frame”.
- Se a tela tiver estados, envie os estados separadamente.
- Quando houver comportamento, descreva o comportamento em texto alem do link.
