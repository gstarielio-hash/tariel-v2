# Catálogo de Laudos Operacional

## Objetivo

Refatorar o Admin-CEO `/admin/catalogo-laudos` sem quebrar o pipeline canônico:

`family_schema -> template_master -> laudo_output -> renderer -> PDF final`

O catálogo agora separa:

- família técnica vendável
- modos técnicos
- oferta comercial
- calibração com material real
- liberação por tenant
- leitura executiva consolidada

## Rotas

- `GET /admin/catalogo-laudos`
  - home executiva com KPIs, filtros, busca e tabela consolidada
- `GET /admin/catalogo-laudos/familias/{family_key}`
  - detalhe da família com abas operacionais
- `POST /admin/catalogo-laudos/familias`
  - salva a família técnica
- `POST /admin/catalogo-laudos/ofertas-comerciais`
  - salva a oferta comercial da família
- `POST /admin/catalogo-laudos/familias/{family_key}/modos`
  - salva um modo técnico
- `POST /admin/catalogo-laudos/familias/{family_key}/calibracao`
  - salva calibração da família
- `POST /admin/catalogo-laudos/familias/{family_key}/liberacao-tenant`
  - salva a liberação por tenant
- `POST /admin/catalogo-laudos/familias/{family_key}/technical-status`
  - ação rápida de status técnico
- `POST /admin/catalogo-laudos/familias/{family_key}/offer-lifecycle`
  - ação rápida de lifecycle comercial

## Entidades

### technical_family

Tabela base: `familias_laudo_catalogo`

Campos novos principais:

- `nr_key`
- `technical_status`
- `catalog_classification`
- `governance_metadata_json`

Responsável por governança técnica da família vendável.

### family_mode

Tabela: `familias_laudo_modos_tecnicos`

Representa variações técnicas como:

- inicial
- periódica
- extraordinária
- documental
- engenharia

Não substitui pacote comercial.

### commercial_offer

Tabela base adaptada: `familias_laudo_ofertas_comerciais`

Campos novos principais:

- `offer_key`
- `family_mode_id`
- `lifecycle_status`
- `showcase_enabled`
- `material_level`
- `template_default_code`
- `flags_json`

Mantém compatibilidade com os campos legados da oferta.

### family_calibration

Tabela: `familias_laudo_calibracoes`

Separa o estado de calibração da leitura comercial.

### tenant_family_release

Tabela: `tenant_family_releases`

Guarda a governança por tenant:

- modos permitidos
- ofertas permitidas
- templates permitidos
- variantes permitidas
- template default
- status de release

Também sincroniza a projeção operacional já usada pelo tenant em `empresa_catalogo_laudo_ativacoes`.

### inspection_method / evidence_method

Tabela: `catalogo_metodos_inspecao`

Métodos como ultrassom, líquido penetrante, visual e hidrostático deixaram de ser tratados como família principal.

## Prontidão derivada

Implementada em `app/domains/admin/services.py` por `derivar_prontidao_catalogo`.

Estados:

- `technical_only`
- `partial`
- `sellable`
- `calibrated`

Sinais considerados:

- `technical_status`
- snapshot de artefatos técnicos
- existência de template válido
- lifecycle comercial
- calibração
- liberação ativa por tenant

## Estratégia de migração

Migration: `f1a2b3c4d5e6_catalogo_laudos_operating_model.py`

Compatibilidade aplicada:

- `status_catalogo` antigo mapeado para `technical_status`
- `ativo_comercial` antigo mapeado para `lifecycle_status`
- `material_real_status` antigo mapeado para `material_level` e `family_calibration`
- releases legados do tenant migrados para `tenant_family_releases`
- métodos clássicos de inspeção semeados em taxonomia separada
- migration idempotente para SQLite local

## Frontend

Arquitetura incremental sem trocar stack:

- Jinja continua como base
- home e detalhe viraram páginas separadas
- abas, badges, KPIs e editores estruturados são macros reutilizáveis
- listas de escopo, exclusões, insumos e variantes deixaram de depender de textarea livre
- JSON cru ficou restrito a modo avançado

## Regras de governança mantidas

- tenant não edita schema técnico
- tenant não edita checklist técnico
- tenant não altera política mínima de evidência
- family lock permanece compatível
- IA continua fora do PDF bruto
