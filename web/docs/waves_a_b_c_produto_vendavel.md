# Waves A-B-C Produto Vendavel

Documento de execucao para as tres ondas que fecham a transicao do Tariel para produto governado e vendavel:

- `Wave A`: biblioteca premium de templates + material real
- `Wave B`: variantes + produto comercial + governanca de tenant
- `Wave C`: emissao oficial transacional

Complementa:

- `web/docs/biblioteca_templates_inspecao_profissionais.md`
- `web/docs/catalogo_laudos_operating_model.md`
- `web/docs/fila_prioritaria_nrs_material_real.md`
- `web/docs/prontidao_comercial_primeiro_cliente.md`
- `web/docs/roadmap_premium_memoria_operacional.md`
- `web/docs/memoria_operacional_governada.md`
- `docs/TARIEL_CONTEXT.md`

## Invariantes

As tres waves preservam o pipeline canonico:

`family_schema -> master template -> family overlay -> laudo_output -> renderer -> PDF`

Regras que continuam valendo:

- `JSON canonico` segue como fonte de verdade;
- `Mesa` continua sendo camada governada de revisao;
- `mobile` e `Mesa` usam a mesma engine de validacao;
- `catalogo` governa familia, variante, release e tenant;
- `PDF` continua entrega final controlada;
- `emissao oficial` nao substitui aprovacao; ela congela uma aprovacao valida.

## Wave A

### Escopo

Fortalecer a biblioteca premium de templates e a calibracao com material real.

### Estado atual

Wave A ja esta implantada em base forte no repositorio.

### Artefatos principais

- biblioteca mestre: `docs/master_templates/library_registry.json`
- template master base: `docs/master_templates/inspection_conformity.template_master.json`
- direcao da biblioteca: `web/docs/biblioteca_templates_inspecao_profissionais.md`
- provisionamento nacional e ondas: `web/docs/portfolio_nacional_nrs_provisionamento.md`
- portfolio com material real: `docs/portfolio_empresa_nr13_material_real/`
- fila prioritaria de premiumizacao: `web/docs/fila_prioritaria_nrs_material_real.md`
- portfolios adicionais de wave 1:
  - `docs/portfolio_empresa_nr12_material_real/`
  - `docs/portfolio_empresa_nr20_material_real/`
  - `docs/portfolio_empresa_nr33_material_real/`
- importacao e profissionalizacao:
  - `web/scripts/importar_templates_docx.py`
  - `web/scripts/professionalize_inspection_templates.py`
  - `web/scripts/importar_referencias_preenchidas_zip.py`
  - `web/app/domains/revisor/reference_package_workspace.py`
  - `web/scripts/generate_material_real_portfolio_workspace.py`
  - `web/scripts/generate_internal_synthetic_reference_packages.py`

### O que esta resolvido

- existe biblioteca profissional inicial homologada;
- existe registry de templates mestres;
- existe workspace de material real por familia;
- existem pacotes de referencia e fluxo de promocao;
- existe base para overlays por familia a partir de referencias reais.
- a fila critica de `NR13`, `NR12`, `NR20` e `NR33` ja recebeu baseline sintetica interna promovida pelo proprio repositorio.

### O que ainda cresce dentro da Wave A

- substituir baseline sintetica por material real aprovado nas familias prioritarias;
- subir mais familias para baseline premium;
- refinar linguagem e secoes por familia;
- consolidar anexos materiais melhores por familia;
- aumentar qualidade visual do PDF final por familia vendavel.
- expandir a mesma trilha de bootstrap para novas familias criticas depois do fechamento de `NR13`, `NR12`, `NR20` e `NR33`.

## Wave B

### Escopo

Transformar familias tecnicas em produto comercial governado por variante, oferta e release por tenant.

### Estado atual

Wave B ja esta implantada e operacional no backend/admin.

### Artefatos principais

- operating model: `web/docs/catalogo_laudos_operating_model.md`
- modelos de governanca: `web/app/shared/db/models_review_governance.py`
- leitura comercial por tenant: `web/app/shared/tenant_report_catalog.py`
- servicos admin: `web/app/domains/admin/services.py`
- rotas admin e tenant: `web/app/domains/admin/client_routes.py`
- policy runtime: `web/app/v2/policy/governance.py`
- engine runtime: `web/app/v2/policy/engine.py`
- telas admin:
  - `web/templates/admin/catalogo_laudos.html`
  - `web/templates/admin/catalogo_familia_detalhe.html`
  - `web/templates/admin/cliente_detalhe.html`

### O que esta resolvido

- familias tecnicas governadas no catalogo;
- modos tecnicos e variantes por familia;
- ofertas comerciais por familia;
- liberacao por tenant com overrides;
- review mode governado por familia e tenant;
- red flags e politica por release;
- visao agregada no dashboard/admin.

### O que ainda cresce dentro da Wave B

- bundles comerciais maiores;
- entitlements mais detalhados por contrato;
- release channels mais finos por pilot/limited/general;
- UX comercial mais polida para venda e operacao do tenant.

## Wave C

### Escopo

Fechar a emissao oficial como ato transacional, auditavel e congelado.

### Estado atual

Wave C ficou completa no runtime nesta execucao.

### Artefatos principais

- modelo transacional: `web/app/shared/db/models_review_governance.py`
- migration: `web/alembic/versions/e7b4c1d9a2f6_emissao_oficial_transacional.py`
- resumo e governanca de emissao: `web/app/shared/official_issue_package.py`
- transacao de emissao: `web/app/shared/official_issue_transaction.py`
- verificacao publica: `web/app/shared/public_verification.py`
- exportacao material do bundle: `web/app/domains/revisor/service_package.py`
- API Mesa:
  - `web/app/domains/revisor/mesa_api.py`
  - `web/app/domains/revisor/base.py`
- superficie Mesa:
  - `web/app/domains/mesa/contracts.py`
  - `web/app/domains/mesa/service.py`
  - `web/static/js/revisor/revisor_painel_mesa.js`
  - `web/static/js/revisor/painel_revisor_page.js`
- verificacao publica HTML: `web/app/domains/chat/chat_aux_routes.py`
- superficie mobile de leitura:
  - `android/src/features/chat/ThreadConversationPane.tsx`
  - `android/src/config/mobileV2MesaAdapter.ts`

### O que a Wave C entrega

- `official_issue_record` persistido por laudo;
- numero oficial da emissao;
- hash do pacote emitido;
- fingerprint canonico para replay idempotente;
- congelamento do ZIP emitido em storage oficial;
- substituicao controlada de emissao anterior quando houver nova emissao;
- download do bundle congelado pela Mesa;
- verificacao publica com dados da emissao oficial;
- leitura do estado da emissao em Mesa e mobile.

### Regras operacionais da Wave C

- so emite quando `ready_for_issue == true`;
- exige signatario governado elegivel;
- usa aprovacao vigente como base;
- nao duplica emissao igual: reaproveita o mesmo registro se o fingerprint for o mesmo;
- se a aprovacao mudar, a emissao ativa passa a pedir reemissao;
- o pacote congelado vira a referencia oficial, nao o ZIP regenerado depois.

## Sequencia operacional A -> B -> C

1. `Wave A`
   biblioteca premium e material real consolidam template, overlay e linguagem.
2. `Wave B`
   o catalogo transforma isso em familia/variante/oferta/release vendavel.
3. `Mesa/mobile`
   o caso roda na engine governada e chega em aprovacao valida.
4. `Wave C`
   a aprovacao valida e o signatario elegivel geram a emissao oficial congelada.

## Status consolidado

- `Wave A`: ativa, bootstrap sintetico fechado nas familias criticas e aguardando pressao por material real
- `Wave B`: ativa e operacional
- `Wave C`: ativa e transacional

## Proximo passo depois da Wave C

Depois desta base, o caminho natural e:

- UX premium do catalogo e da biblioteca documental;
- mais familias com material real premium;
- entitlements comerciais mais fortes;
- assinatura/rotina documental ainda mais rigida quando o mercado pedir.
