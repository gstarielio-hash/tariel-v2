---
name: Tarefa Arquitetural
about: Abrir tarefa com recorte claro entre Astro, Python, bridge, ownership e validacao
title: "[area] "
labels: []
assignees: []
---

## Resumo

Descreva em 3 a 8 linhas o problema real.

Explique:

- o que esta errado, faltando ou ambiguo;
- onde isso aparece no produto;
- por que vale mexer nisso agora.

## Contexto e motivacao

Explique o contexto operacional da tarefa.

Use este espaco para responder, quando fizer sentido:

- isso veio de bug, rollout, refactor, migracao, CI, produto ou operacao?
- isso bloqueia uma vertical do V2?
- isso toca uma superficie oficial ou uma bridge temporaria?
- isso reduz risco, fecha ownership ou apenas melhora UX?

## Classificacao arquitetural

Preencha tudo. Se algo estiver ambíguo, diga explicitamente.

- tipo da tarefa: `Astro` | `Python` | `Astro + Python` | `bridge temporaria`
- portal ou superficie principal: `admin` | `cliente` | `revisao` | `app` | `mobile` | `backend shared` | `documento` | `infra`
- camada principal: `UI/SSR` | `dominio` | `policy/auth/audit` | `IA/OCR` | `template/PDF` | `bridge/BFF`
- toca regra de negocio densa? `sim` | `nao`
- toca tenancy, RBAC, auth, policy ou auditoria? `sim` | `nao`
- toca IA, OCR, `dados_formulario`, template, preview ou PDF? `sim` | `nao`
- existe dependencia do legado? `sim` | `nao`
- isso e ownership definitiva ou bridge? `ownership` | `bridge`

## Decisao de ownership

Preencha explicitamente para evitar discussao tardia no review.

- interface fica em:
- regra fica em:
- fonte de verdade do dado fica em:
- se houver bridge, onde ela termina:
- o que **nao** deve ser feito nesta tarefa:

## Perguntas de desempate

Responda com honestidade:

- se eu levar isso para o frontend, vou duplicar a fonte de verdade? `sim` | `nao`
- se eu levar isso para o backend, vou misturar detalhe de UX com dominio? `sim` | `nao`
- o frontend pode ficar fino e chamar uma regra central? `sim` | `nao`
- a tarefa exige contrato novo ou apenas consumo de contrato existente? `novo` | `existente`

## Fonte de verdade consultada

Marque o que foi lido antes de abrir a tarefa.

- [ ] `PROJECT_MAP.md`
- [ ] `web/PROJECT_MAP.md`
- [ ] `docs/CHECKLIST_ABERTURA_TAREFA_ASTRO_PYTHON.md`
- [ ] `docs/MAPA_ARQUITETURA_FRONT_BACK_IA_PDF.md`
- [ ] `docs/MAPA_MENTAL_MIGRACAO_V2.md`
- [ ] `docs/TARIEL_V2_MIGRATION_CHARTER.md`
- [ ] `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- [ ] `docs/full-system-audit/05_backend_architecture.md`
- [ ] `docs/full-system-audit/06_frontend_architecture.md`
- [ ] outra documentacao relevante foi consultada e citada abaixo

Referencias adicionais:

- caminho 1:
- caminho 2:
- caminho 3:

## Escopo

Defina com clareza o que entra e o que nao entra.

### Entra

-
-
-

### Nao entra

-
-
-

## Estado atual

Descreva o comportamento atual com o maximo de concretude.

Inclua, quando aplicavel:

- rota ou tela afetada;
- modulo ou dominio afetado;
- contrato atual;
- limitações conhecidas;
- bridges ou acoplamentos existentes;
- risco atual se nada for feito.

## Resultado esperado

Descreva como o sistema deve ficar depois da tarefa.

Se possivel, diferencie:

- efeito no frontend;
- efeito no backend;
- efeito em contrato;
- efeito em observabilidade;
- efeito em rollout ou migracao.

## Criterios de aceite

Liste criterios verificaveis.

- [ ] comportamento principal funciona como descrito
- [ ] ownership entre `Astro` e `Python` fica explicito e coerente
- [ ] nao ha duplicacao indevida de regra de negocio
- [ ] auth, role, tenant e auditoria foram revisados quando aplicavel
- [ ] bridges novas, se existirem, ficam marcadas como temporarias
- [ ] docs relevantes foram atualizadas quando a decisao for arquitetural

Criterios especificos desta tarefa:

- [ ]
- [ ]
- [ ]

## Validacao esperada

Liste o menor conjunto de checks que deve provar a tarefa.

### Frontend / Astro

- [ ] `./bin/npm22 run check`
- [ ] `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- [ ] validacao manual da rota/tela

### Backend / Python

- [ ] `python -m py_compile` nos modulos tocados
- [ ] teste direcionado em `pytest -k ...`
- [ ] smoke do fluxo principal

### Contrato / integracao

- [ ] contrato novo ou alterado coberto por teste
- [ ] tenant/auth/audit revisados
- [ ] rollout/bridge revisados

Checks especificos desta tarefa:

-
-
-

## Risco e rollout

- risco principal:
- impacto se der errado:
- rollback esperado:
- observabilidade ou alerta relevante:
- precisa de feature flag, bridge ou rollout progressivo? `sim` | `nao`

## Dependencias e bloqueios

Liste tudo que pode travar a tarefa.

- dependencia tecnica:
- dependencia de produto:
- dependencia de dados:
- dependencia externa:

## Evidencias de apoio

Cole aqui o que ajuda o implementador e o reviewer:

- print
- log
- stacktrace
- payload
- referencia de arquivo
- link de artifact

## Notas para implementacao

Use este espaco para restricoes ou preferencias fortes.

Exemplos:

- "nao reabrir ownership no legado"
- "manter regra no backend e frontend fino"
- "nao alterar contrato externo"
- "fechar primeiro o portal cliente antes de abrir inspetor"
