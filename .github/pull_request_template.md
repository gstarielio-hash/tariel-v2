## Resumo executivo

Explique em 5 a 12 linhas:

- qual problema este PR resolve;
- em qual parte do produto ele mexe;
- qual foi a decisao de ownership entre `Astro` e `Python`;
- qual risco principal foi atacado.

## Classificacao arquitetural

Preencha tudo para facilitar review.

- tipo do PR: `Astro` | `Python` | `Astro + Python` | `bridge temporaria`
- portal ou superficie principal: `admin` | `cliente` | `revisao` | `app` | `mobile` | `backend shared` | `documento` | `infra`
- camada principal: `UI/SSR` | `dominio` | `policy/auth/audit` | `IA/OCR` | `template/PDF` | `bridge/BFF`
- toca regra de negocio densa? `sim` | `nao`
- toca tenancy, RBAC, auth, policy ou auditoria? `sim` | `nao`
- toca IA, OCR, `dados_formulario`, template, preview ou PDF? `sim` | `nao`
- resolve ownership definitiva ou apenas bridge? `ownership` | `bridge`

## Decisao de ownership

- interface ficou em:
- regra ficou em:
- fonte de verdade do dado ficou em:
- bridge criada ou mantida:
- o que este PR deliberadamente **nao** faz:

## Relacao com a issue

- issue principal:
- outras issues relacionadas:
- este PR fecha totalmente a issue? `sim` | `nao`
- se nao fecha, o que ainda sobra:

## Escopo

### Entra

-
-
-

### Nao entra

-
-
-

## Mudancas por area

### Frontend / Astro

-
-
-

### Backend / Python

-
-
-

### Contratos / dados / auth / audit

-
-
-

### Docs / operacao / rollout

-
-
-

## Fonte de verdade consultada

- [ ] consultei `PROJECT_MAP.md`
- [ ] consultei `web/PROJECT_MAP.md`
- [ ] consultei `docs/CHECKLIST_ABERTURA_TAREFA_ASTRO_PYTHON.md`
- [ ] consultei `docs/MAPA_ARQUITETURA_FRONT_BACK_IA_PDF.md`
- [ ] consultei `docs/MAPA_MENTAL_MIGRACAO_V2.md`
- [ ] consultei `docs/TARIEL_V2_MIGRATION_CHARTER.md` quando o PR toca migracao
- [ ] atualizei `PLANS.md` se a tarefa foi longa ou multissuperficie

Referencias adicionais:

- caminho 1:
- caminho 2:
- caminho 3:

## Antes e depois

### Estado antes

Descreva o comportamento ou acoplamento anterior.

### Estado depois

Descreva o comportamento ou ownership final apos este PR.

## Validacao executada

Marque apenas o que realmente rodou.

### Frontend / Astro

- [ ] `./bin/npm22 run check`
- [ ] `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- [ ] validacao manual de rota/tela

### Backend / Python

- [ ] `python -m py_compile` nos modulos tocados
- [ ] `pytest -q ...`
- [ ] smoke do fluxo principal

### Repositorio / CI / contratos

- [ ] `make verify`
- [ ] `make web-ci`
- [ ] `make mobile-ci`
- [ ] `make contract-check`
- [ ] `make smoke-web`
- [ ] `make smoke-mobile`
- [ ] `make mesa-smoke`
- [ ] `make mesa-acceptance`
- [ ] `git diff --check`

Comandos e resultados relevantes:

```text
cole aqui os comandos principais e um resumo dos resultados
```

## Contratos, seguranca e governanca

- [ ] nao alterei contrato sensivel sem teste, fixture ou schema
- [ ] revisei tenant, auth, papel e auditoria quando aplicavel
- [ ] nao repliquei regra critica no frontend sem necessidade
- [ ] bridges novas, se existirem, ficaram explicitamente marcadas como temporarias
- [ ] nao versionei artefato local gerado por engano

Observacoes:

-
-

## Risco, rollout e rollback

- risco principal:
- impacto se der errado:
- rollback esperado:
- observabilidade ou alerta relevante:
- precisa de rollout progressivo, bridge ou follow-up? `sim` | `nao`

## Evidencias

- prints:
- logs:
- payloads:
- artifacts:
- links:
- observacoes adicionais:

## Checklist final do autor

- [ ] o PR resolve o problema descrito sem expandir escopo escondido
- [ ] a decisao entre `Astro` e `Python` ficou coerente com a arquitetura real
- [ ] a fonte de verdade do dominio nao ficou duplicada
- [ ] a validacao executada e suficiente para o risco deste PR
- [ ] os proximos passos, se existirem, ficaram descritos
