# Política de Branch Protection e Merge

## Objetivo

Tornar a qualidade do Tariel enforcement real de merge, não só intenção em documento.

## Branches protegidas

Proteger no mínimo:

- `main`
- `release/*`

## Regras mínimas obrigatórias

- pull request obrigatório antes de merge;
- bloquear push direto em branch protegida;
- pelo menos `1` aprovação obrigatória;
- exigir review de `CODEOWNERS` para áreas sensíveis;
- impedir merge com checks obrigatórios vermelhos;
- exigir branch atualizada antes de merge quando houver conflito relevante;
- preferir histórico linear.

## Checks obrigatórios recomendados

Checks já existentes e prontos para entrar na política:

- `quality`
- `backend-stack`
- `contract-check`
- `mobile-quality`
- `web-e2e-mesa`

Checks recomendados para ativar depois que estiverem institucionais:

- `devkit-baseline`
- `analyze (python)`
- `analyze (javascript-typescript)`

Checks informativos, não obrigatórios de merge:

- `baseline-snapshot`

## Observação importante

Hoje alguns workflows ainda têm gatilho por `paths`.

Antes de transformar um job em `required check` global no GitHub, confirmar se ele realmente executa em todos os PRs que precisam daquele gate.

Se um check não roda para todo PR relevante, ele não deve ser marcado como obrigatório global até o gatilho ser consolidado.

## Áreas que devem exigir atenção de owner

- auth
- tenant
- sessão
- admin
- cliente
- documento/template
- mobile rollout
- workflows de CI
- governança de Codex

## Merge policy operacional

- não abrir PR com baseline global quebrada sem justificativa explícita;
- não misturar cleanup estrutural, feature e redesign no mesmo PR;
- PR multissuperfície precisa referenciar `PLANS.md`;
- contrato alterado exige teste/fixture/schema atualizado;
- PR que toca observabilidade ou segurança precisa descrever risco e rollback.

## Pull request template

Usar o template versionado em:

- `.github/pull_request_template.md`

## CODEOWNERS

Usar o arquivo versionado em:

- `.github/CODEOWNERS`

## Próximo passo recomendado

Aplicar esta política nas configurações do GitHub do repositório:

- branch protection em `main` e `release/*`;
- required checks alinhados aos jobs atuais;
- code owner review obrigatório;
- revisar `analyze (python)` e `analyze (javascript-typescript)` depois da primeira execução do `codeql`;
- manter `Dependabot` ativo como trilha contínua de atualização.
