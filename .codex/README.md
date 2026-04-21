# Codex Modes

Guia curto para usar o Codex CLI neste repositório no Ubuntu.

## Modo auditoria

```bash
codex --sandbox read-only -a never "audite a Fase 02 e liste os blockers reais"
```

## Modo planejamento

```bash
codex
```

Dentro da sessão, usar `/plan` quando a tarefa for longa ou confusa.

## Modo correção local controlada

```bash
codex --sandbox workspace-write -a on-request "corrija o web-ci sem abrir frente lateral"
```

## Modo não interativo

```bash
codex exec "resuma a baseline atual e proponha próximos 3 passos"
```

## Sandbox Linux

```bash
codex sandbox linux bash -lc 'make verify'
```

## Regras

- não usar bypass perigoso fora de runner isolado;
- preferir um worktree por frente;
- atualizar `PLANS.md` em tarefa longa;
- começar pelo `PROJECT_MAP.md` e pelo `PLAN_MASTER.md`.
