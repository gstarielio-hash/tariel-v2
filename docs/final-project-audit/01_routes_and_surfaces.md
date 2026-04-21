# 01 - Routes And Surfaces

## Superfícies confirmadas

- `/admin`
- `/cliente`
- `/app`
- `/revisao`
- mobile Android via `/app/api/mobile/*`
- compartilhadas (`/health`, `/ready`, `/debug-sessao`, estáticos)

## Inventário vivo

Resumo do inventário gerado diretamente da aplicação FastAPI atual:

- total de rotas: 207
- por superfície: {"admin": 50, "app": 63, "cliente": 40, "revisao": 44, "shared": 10}
- por modo: {"mutation": 106, "read": 101}
- rotas marcadas como legado/transição: 8
- rotas concorrentes/paralelas relevantes: 5

O inventário canônico completo está em `artifacts/final_project_audit/20260404_171250/route_inventory.json`.

## Incoerências encontradas

- `PROJECT_MAP.md` ainda aponta templates admin em caminhos antigos.
- o surface audit heurístico também ficou atrás da reorganização real de templates.
- no inspetor, continuam visíveis rotas verb-based e aliases de compatibilidade em torno de laudo.
- mobile mantém coexistência de contratos legado/V2 por design, agora como guardrail, não como superfície concorrente.

## Leitura prática

Não há duas Mesas oficiais. A superfície oficial continua sendo a SSR em `/revisao/painel`.

As áreas com mais contratos críticos hoje são:

- `/app/api/laudo/*`
- `/app/api/mobile/*`
- `/cliente/api/chat/*`
- `/cliente/api/mesa/*`
- `/revisao/api/laudo/*`
- `/revisao/api/templates-laudo/*`
- `/admin/api/*summary`
