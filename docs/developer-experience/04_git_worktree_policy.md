# Política de Git Worktree

## Objetivo

Impedir que o Tariel volte a ficar confuso por mistura de frentes no mesmo diretório.

## Regra principal

Usar `1 worktree por frente`.

Isso vale para:

- fase principal;
- hotfix;
- spike;
- auditoria longa;
- refatoração estrutural.

## Quando abrir um worktree novo

Abrir worktree novo quando:

- a tarefa muda muitos arquivos;
- a tarefa dura mais de um dia;
- a tarefa toca mais de um workspace;
- a tarefa pode quebrar baseline;
- você precisa manter outra frente estável aberta ao mesmo tempo.

## Quando não abrir

Não precisa abrir worktree novo quando:

- a tarefa é pequena;
- a correção é local e curta;
- não existe risco de colisão com outra frente;
- você vai terminar no mesmo ciclo.

## Padrão de nomenclatura

Branch:

- `fix/fase-02-baseline`
- `hotfix/home-sidebar-empty-state`
- `spike/reviewdesk-paridade`
- `refactor/mobile-root-breakup`

Diretório sugerido:

- `../tariel-f02-baseline`
- `../tariel-hotfix-sidebar`
- `../tariel-spike-reviewdesk`

## Comandos oficiais

Criar:

```bash
git worktree add ../tariel-f02-baseline -b fix/fase-02-baseline
```

Listar:

```bash
git worktree list
```

Remover depois de fechar:

```bash
git worktree remove ../tariel-f02-baseline
git branch -d fix/fase-02-baseline
```

## Regra de coordenação

- não usar duas sessões editando os mesmos arquivos em worktrees diferentes;
- não abrir spike em cima da mesma branch da correção principal;
- sempre começar uma frente longa atualizando `PLANS.md`;
- sempre validar no worktree certo antes de abrir PR.

## Fluxo recomendado

1. ler `PLAN_MASTER.md`
2. abrir worktree
3. atualizar `PLANS.md`
4. executar mudança
5. rodar checks
6. abrir PR
7. remover worktree quando a frente terminar
