# Política de Artifacts e Higiene de Workspace

## Objetivo

Evitar que o repositório volte a misturar `source`, `docs`, `fixture` e lixo operacional gerado localmente.

## Classificação oficial

- `source`
  Código, schema, contrato, template e config necessários para o produto.
- `docs`
  Documentação humana versionada.
- `fixture`
  Amostra pequena, estável e intencional usada por teste ou demo.
- `artifact intencional`
  Evidência pequena e estável promovida conscientemente para `docs/` ou fixture.
- `local/gerado/descartável`
  Output bruto de execução local, smoke, build, screenshot, dump, cache, banco temporário ou runner.

## Regra para `artifacts/`

- o root oficial de saída local é `artifacts/<lane>/<timestamp>/`
- outputs novos em `artifacts/` são locais e ignorados por Git
- `docs/` referencia caminhos de artifact quando necessário, mas não promove o conteúdo bruto
- quando a evidência precisar virar referência durável, extrair só o resumo final, nunca a pasta inteira da rodada

## Regra por workspace

### Root

- ignora caches, logs locais, `sqlite` temporário, screenshots operacionais e `artifacts/`
- mantém apenas policy/docs do diretório `artifacts/`

### `web/`

- ignora venvs, caches de teste/lint, `coverage`, uploads locais e `web/artifacts/`
- `web/artifacts/` serve apenas para evidence local temporária

### `android/`

- ignora `node_modules`, `dist`, `build`, `.expo`, `Maestro`, APK/AAB e logs locais

## Regras operacionais

- em tarefa longa ou multissuperfície, atualizar `PLANS.md` antes de expandir o escopo
- abrir `git worktree` para fase principal, hotfix longo, spike ou refatoração estrutural
- usar `make hygiene-check` para validar policy, ignores e entrypoints oficiais
- usar `make clean-generated` apenas para saídas seguras; nunca para apagar evidence que ainda precise ser lida

## Entry points oficiais

- `make hygiene-check`
- `make clean-generated`
- `docs/developer-experience/04_git_worktree_policy.md`
- `PLANS.md`
