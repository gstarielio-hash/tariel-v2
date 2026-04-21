# Fase 11 - Higiene permanente e governança

Fechada em `2026-03-31`.

## Resultado

A `Fase 11` foi promovida com política explícita de `artifacts/`, revisão de `.gitignore` por workspace, entrypoint de verificação de higiene, runner oficial da fase e disciplina local amarrada em `README`, `AGENTS` e `PLANS.md`.

## O que entrou

- política versionada de `artifacts/` e higiene local em `docs/developer-experience/08_artifacts_and_workspace_hygiene_policy.md`
- `artifacts/` e `web/artifacts/` agora mantêm apenas policy/docs versionados; outputs novos passam a ser locais e ignorados
- `web/.gitignore` institucionaliza a regra do workspace web
- root e Android ganharam regras complementares para caches, builds, APK/AAB, SQLite temporário e outputs locais
- `make hygiene-check` valida presence de policy, textos obrigatórios, regras de ignore e `git worktree list`
- `make hygiene-acceptance` produz artifact autoritativo da fase
- `clean-generated` foi endurecido para limpar saídas seguras adicionais sem tocar evidence de rodada em `artifacts/`

## Arquivos centrais

- `.gitignore`
- `artifacts/.gitignore`
- `artifacts/README.md`
- `web/.gitignore`
- `web/artifacts/.gitignore`
- `web/artifacts/README.md`
- `Makefile`
- `README.md`
- `AGENTS.md`
- `scripts/check_workspace_hygiene.py`
- `scripts/run_hygiene_phase_acceptance.py`
- `docs/developer-experience/08_artifacts_and_workspace_hygiene_policy.md`

## Evidência operacional

- artifact oficial: `artifacts/hygiene_phase_acceptance/20260331_032540/hygiene_phase_acceptance_summary.json`
- relatório humano do runner: `artifacts/hygiene_phase_acceptance/20260331_032540/final_report.md`
- status do runner: `ok`

## Validação final

- `make hygiene-acceptance` verde em `2026-03-31`
- `make contract-check` verde em `2026-03-31`
- `make verify` verde em `2026-03-31`

## Observações

- a worktree global continua suja por histórico anterior, mas a política nova impede que novos outputs locais dominem o fluxo normal
- a fase não tentou reescrever histórico nem remover artifacts já versionados no passado; o foco foi impedir reincidência e institucionalizar a governança local

## Próximo passo

Promover a `Fase 12 - Evolução estrutural V2`, na ordem: envelopes canônicos, ACL do `Technical Case Core`, projeção do Inspetor, projeção da Mesa, provenance mínima, `policy engine`, facade documental e adapter Android
