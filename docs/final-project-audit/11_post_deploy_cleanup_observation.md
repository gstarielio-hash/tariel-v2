# 11 - Post-Deploy Cleanup Observation

Data de fechamento desta fase: 2026-04-04.

## O que foi observado de verdade

A primeira execução automática do cleanup foi observada com sucesso em um ambiente local `production-like` com:

- `AMBIENTE=production`
- storage persistente real no filesystem do host
- scheduler ativo
- política automática de cleanup habilitada
- retenção e grace window explícitas
- relatório persistido em `_cleanup_reports/`

A observação não foi fingida como deploy real. Ela foi executada em ambiente equivalente forte, controlado e descartável.

## Evidência objetiva

Artifact canônico desta fase:

- `artifacts/final_product_stamp/20260404_194522/post_deploy_cleanup_observation.md`
- `artifacts/final_product_stamp/20260404_194522/final_product_status.json`
- `artifacts/final_product_stamp/20260404_194522/source_index.txt`

Sinais confirmados:

- `source=web_scheduler`
- `mode=apply`
- `status=ok`
- `production_ops_ready=true`
- `uploads_cleanup_scheduler_running=true`
- `uploads_cleanup_last_source=web_scheduler`
- `uploads_cleanup_last_mode=apply`

Resultado operacional observado:

- órfãos antigos elegíveis removidos automaticamente
- arquivos referenciados preservados
- arquivos recentes preservados
- nenhum erro de deleção
- relatório JSON persistido com trilha rastreável

## Ajustes necessários para a observação ficar honesta

Durante esta fase, dois pontos foram corrigidos para a observabilidade ficar confiável:

- o runtime do scheduler deixou de apagar a última evidência útil ao parar
- `uploads_cleanup_runtime.json` deixou de ser confundido com `latest_report`

Sem esses ajustes, o summary operacional podia descrever incorretamente o estado do último ciclo.

## Leitura honesta

A observação automática foi comprovada em ambiente equivalente forte.

Ela ainda não foi observada em um deploy real com mount persistente oficial. Por isso, esta fase fecha a lacuna técnica e observacional equivalente, mas não declara falsamente que houve observação em produção real.

## Estado final desta frente

- cleanup automático: comprovado
- guardrails de exclusão: comprovados
- summary operacional: consistente
- evidência persistida: comprovada
- deploy real observado: não

## Conclusão

Depois desta fase, a limpeza operacional deixa de ser um bloqueador estrutural. O que sobra é apenas a eventual repetição do mesmo protocolo em um ambiente de deploy real, se o time quiser esse último nível de prova operacional.
