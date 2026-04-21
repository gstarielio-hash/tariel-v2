# Inventário de Automação do Repositório

## Objetivo

Registrar, em um lugar curto, o que já está automatizado no Tariel e qual o papel de cada automação.

## Automação local canônica

- `make doctor`
  Confere versões e dependências locais.
- `make verify`
  Gate principal local do repositório.
- `make contract-check`
  Valida contratos sensíveis entre backend e mobile público.
- `make observability-acceptance`
  Runner oficial da `Fase 10 - Observabilidade, operação e segurança`.
- `make clean-generated`
  Limpa saídas locais seguras.
- `make hygiene-check`
  Valida a política de `artifacts/`, `.gitignore` por workspace e entrypoints de governança local.
- `make hygiene-acceptance`
  Runner oficial da `Fase 11 - Higiene permanente e governança`.
- `make baseline-snapshot`
  Gera snapshot enxuto da baseline em `.tmp_online/baseline/<timestamp>/`.
- `make hooks-install`
  Instala `pre-commit` e `pre-push` usando `.pre-commit-config.yaml`.

## Hooks locais

Arquivo: `.pre-commit-config.yaml`

### Pre-commit

- conflito de merge
- arquivos grandes adicionados
- validação de `json`
- validação de `yaml`
- validação de `toml`
- trailing whitespace
- EOF fixer
- `ruff` no `web/`
- `eslint` no `android/`
- `prettier --check` no `android/`

### Pre-push

- suíte crítica do `web`
- `typecheck` do `android`
- testes do `android`

## Workflows GitHub versionados

### `ci`

Arquivo: `.github/workflows/ci.yml`

Jobs:

- `quality`
- `backend-stack`
- `web-e2e-mesa`
- `mobile-quality`

### `contract-check`

Arquivo: `.github/workflows/contract-check.yml`

Função:

- institucionalizar contratos críticos em lane própria

### `devkit-operational-baseline`

Arquivo: `.github/workflows/devkit-operational-baseline.yml`

Função:

- baseline mais ampla do kit operacional

### `baseline-snapshot`

Arquivo: `.github/workflows/baseline-snapshot.yml`

Função:

- gerar snapshot operacional manual ou agendado
- publicar o diretório `.tmp_online/baseline` como artifact

### `codeql`

Arquivo: `.github/workflows/codeql.yml`

Função:

- análise estática de segurança para `python`
- análise estática de segurança para `javascript-typescript`

## Automação de dependências

Arquivo: `.github/dependabot.yml`

Cobertura atual:

- `github-actions`
- `web` via `pip`
- `android` via `npm`

## O que ainda depende de configuração no GitHub

- branch protection em `main` e `release/*`
- marcar checks obrigatórios
- exigir review de `CODEOWNERS`
- habilitar auto-merge só quando a política estiver estável

## Leitura recomendada

1. `05_branch_protection_and_merge_policy.md`
2. `06_repo_automation_inventory.md`
3. `/home/gabriel/Área de trabalho/Tarie 2/docs/migration/CI_BASELINE.md`
