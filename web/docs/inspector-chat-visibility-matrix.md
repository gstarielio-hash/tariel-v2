# Matriz de Visibilidade do Inspetor

Legenda:

- `visível`: superfície principal do modo
- `oculto`: não deve aparecer
- `contextual`: pode existir como apoio, conforme viewport, overlay ou ação do usuário

## Matriz final

| Screen mode | Quick dock | Mesa widget | Context rail | Ações rápidas | CTA `Nova Inspeção` | CTA `Novo Chat` | Atalhos operacionais | Entradas de mesa |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `portal_dashboard` | oculto | oculto | oculto | oculto | visível no portal/home | visível no portal/home | oculto | oculto |
| `assistant_landing` | oculto | oculto | oculto | visível na landing do assistente | visível na landing do assistente | oculto | contextual no composer do assistente | oculto como CTA visual; `@insp` preservado como comando |
| `new_inspection` | oculto | oculto | oculto | oculto | visível no próprio modal | contextual no modal | oculto | oculto |
| `inspection_record` | contextual no layout compacto | contextual, sob demanda | visível no desktop e oculto no layout compacto | visível no workspace | contextual na sidebar | oculto | visível | primária no rail no desktop; contextual no composer no compacto |
| `inspection_conversation` | contextual no layout compacto | contextual, sob demanda | visível no desktop e oculto no layout compacto | visível no workspace | contextual na sidebar | oculto | visível | primária no rail no desktop; contextual no composer no compacto |

## Aplicação prática desta fase

### `portal_dashboard`

- mantém `Nova Inspeção` e `Novo Chat` no hero do portal
- mantém `Novo Chat` visível no hero mesmo com laudo/contexto restaurado localmente
- esconde o botão de `Nova Inspeção` da sidebar para evitar duplicidade visual
- mantém widget/rail/dock fora da superfície

### `assistant_landing`

- deixa a landing como superfície principal para iniciar `Nova Inspeção`
- remove o CTA equivalente do header do workspace da superfície visível
- mantém o chat livre sem widget/mesa competindo visualmente

### `new_inspection`

- overlay vira a única superfície operacional
- quick dock, rail e widget ficam fora de cena
- `Abrir chat sem modelo` vira o único atalho alternativo dentro desse contexto

### `inspection_record` e `inspection_conversation`

- no desktop:
  - rail vira a superfície principal de contexto e mesa
  - `Abrir canal` e `Enviar para Mesa` ficam no rail
  - `Enviar para Mesa` some do header
  - o botão `Mesa` do composer some para não competir com o rail
- no layout compacto:
  - quick dock reaparece
  - rail deixa de ser a superfície principal
  - `Enviar para Mesa` volta para o header
  - `Mesa` volta ao composer como affordance contextual

## Entrypoints operacionais após a estabilização

### `Nova Inspeção`

- principal em `portal_dashboard`: hero do portal
- principal em `assistant_landing`: card primário da landing
- contextual em inspeção ativa: botão da sidebar
- preservado como hook no header do workspace, mas fora da superfície primária

### `Novo Chat`

- principal em `portal_dashboard`
- contextual no modal de `Nova Inspeção`
- oculto nos demais modos

### Mesa

- principal no rail em desktop de inspeção ativa
- contextual no composer em layout compacto
- widget dedicado apenas em modos de inspeção
- `@insp` e aliases permanecem como caminho textual compatível
