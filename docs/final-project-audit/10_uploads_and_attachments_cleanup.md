# 10 - Uploads And Attachments Cleanup

Data de fechamento desta fase: 2026-04-04.

## Decisão canônica

A política operacional deixou de ser `manual_review` implícita. O projeto agora tem cleanup automatizado e guardado para arquivos órfãos, com dry-run explícito, apply explícito, lock de execução e relatórios persistidos.

## Escopo coberto

O cleanup cobre três categorias reais do produto:

- `profile_uploads`
- `mesa_attachments`
- `visual_learning_uploads`

## Regra de exclusão

Um arquivo só é elegível quando todas as condições abaixo são verdadeiras:

- está dentro de uma raiz canônica de uploads
- não está referenciado no banco
- está além de `retention_days + cleanup_grace_days`
- não é arquivo de lock nem relatório do próprio cleanup

Arquivos referenciados nunca entram como elegíveis.

## Guardrails implementados

- `dry-run` por padrão no CLI
- `--apply` explícito para exclusão real
- lock de execução para evitar corrida
- limite por rodada via `TARIEL_UPLOADS_CLEANUP_MAX_DELETIONS_PER_RUN`
- relatório JSON persistido em `_cleanup_reports/`
- pruning apenas de diretórios vazios após deleção real
- distinção clara entre checagem local e política de produção

## Implementação

Arquivos principais desta fase:

- `web/app/domains/admin/uploads_cleanup.py`
- `scripts/run_uploads_cleanup.py`
- `web/app/domains/admin/production_ops_summary.py`
- `web/app/core/http_setup_support.py`
- `web/main.py`
- `Makefile`
- `render.yaml`
- `web/.env.example`

## Operação automática

Quando `TARIEL_UPLOADS_CLEANUP_ENABLED=1`, o web inicia um scheduler leve que:

- observa o intervalo configurado
- executa cleanup real com `source=web_scheduler`
- grava estado runtime e relatório persistido

O check manual continua disponível via:

- `python3 scripts/run_uploads_cleanup.py --json --strict`
- `python3 scripts/run_uploads_cleanup.py --apply --json --strict`
- `make uploads-cleanup-check`
- `make uploads-cleanup-apply`

## Estado validado nesta fase

- dry-run local: verde
- produção estrita: verde em política e readiness
- warning honesto remanescente em modo produção: `automatic_upload_cleanup_has_not_run_yet`

Esse warning significa apenas que o ciclo automatizado ainda não executou num contexto configurado como produção neste host. Ele não invalida a política nem o gate.

## Estado final desta frente

- política de cleanup: automatizada e canônica
- exclusão insegura de dados referenciados: bloqueada
- retenção e grace window: explícitas
- relatórios operacionais: disponíveis
- resumo administrativo e `/ready`: atualizados

## Ressalva remanescente

A primeira observação em ambiente de produção real ainda deve confirmar a geração do primeiro relatório automático em `_cleanup_reports/` no disco persistente. Isso é observação operacional pós-deploy, não lacuna de implementação.
