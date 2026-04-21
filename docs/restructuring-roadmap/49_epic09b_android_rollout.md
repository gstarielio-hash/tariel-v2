# Epic 09B - rollout controlado do consumo mobile V2 com observabilidade de fallback

## Objetivo

Transformar a adocao opt-in do mobile V2 em um rollout controlado, observavel e reversivel, sem:

- mudar a UX do app Android;
- alterar o payload legado ja consumido hoje;
- remover o caminho legado;
- alterar auth, session ou multiportal;
- exigir rollout universal para todos os tenants.

## Estrategia escolhida

Foi escolhido um endpoint aditivo e pequeno:

- `GET /app/api/mobile/v2/capabilities`

Motivos:

- nao altera o shape do bootstrap mobile legado;
- e versionado e isolado no namespace `mobile/v2`;
- permite decisao remota por tenant/coorte sem tocar na UI;
- falha de forma segura: se o endpoint negar ou falhar, o app continua no legado.

## Backend implementado

Nova camada de rollout:

- `web/app/v2/mobile_rollout.py`

Capacidades suportadas nesta fase:

- flag global de rollout `TARIEL_V2_ANDROID_ROLLOUT`
- flag ja existente `TARIEL_V2_ANDROID_PUBLIC_CONTRACT`
- allowlist por tenant via `TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST`
- coorte estavel por tenant via `TARIEL_V2_ANDROID_ROLLOUT_PERCENT`
- ativacao separada de rota por:
  - `TARIEL_V2_ANDROID_FEED_ENABLED`
  - `TARIEL_V2_ANDROID_THREAD_ENABLED`

Decisao retornada ao app:

- `mobile_v2_reads_enabled`
- `mobile_v2_feed_enabled`
- `mobile_v2_thread_enabled`
- `reason` / `source`
- `feed_reason` / `feed_source`
- `thread_reason` / `thread_source`

O endpoint exige papel `Inspetor` e devolve apenas o minimo necessario para o cliente decidir entre V2 e legado.

## Integracao escolhida no app

O ponto de integracao continuou em:

- `android/src/config/mesaApi.ts`

Com um novo resolvedor local+remoto em:

- `android/src/config/mobileV2Rollout.ts`

Motivo:

- evita espalhar condicoes no estado de sessao e no bootstrap;
- mantem a UI recebendo os mesmos modelos legados;
- deixa rollout e fallback encapsulados na camada de rede da mesa.

## Precedencia de decisao no app

Ordem aplicada:

1. se `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED` estiver desligada, usa legado puro;
2. se a flag local estiver ligada, o app consulta `/app/api/mobile/v2/capabilities`;
3. se o backend negar `reads` ou a rota especifica (`feed`/`thread`), usa legado;
4. se o gate remoto falhar, usa legado;
5. se o gate remoto aprovar, tenta V2;
6. se o V2 falhar por `404`, erro HTTP, parse ou visibilidade, usa legado automaticamente.

O resolvedor usa cache em memoria de curta duracao por token para evitar chamadas repetidas em cascata sem transformar o gate remoto em hard dependency de sessao.

## Observabilidade de fallback

No app:

- eventos existentes `mesa_feed_v2_read` e `mesa_thread_v2_read` continuam sendo registrados;
- agora tambem diferenciam fallback por:
  - `remote_gate_off:<motivo>`
  - `remote_gate_error`
  - `404`
  - `http_error`
  - `parse`
  - `visibility_denied`

No backend:

- `GET /app/api/mobile/v2/capabilities` registra resumo discreto de rollout por request;
- as rotas V2 publicas de feed/thread registram uso do contrato V2;
- quando o app cai para o legado, ele envia headers discretos:
  - `X-Tariel-Mobile-V2-Attempted`
  - `X-Tariel-Mobile-V2-Route`
  - `X-Tariel-Mobile-V2-Fallback-Reason`
  - `X-Tariel-Mobile-V2-Gate-Source`
- as rotas legadas de feed/thread leem esses headers e registram o fallback sem alterar payload.

## Arquivos tocados nesta fase

Backend:

- `web/app/v2/mobile_rollout.py`
- `web/app/domains/chat/auth_mobile_routes.py`
- `web/app/domains/chat/mesa.py`
- `web/tests/test_v2_android_rollout.py`

App Android:

- `android/src/config/mobileV2Rollout.ts`
- `android/src/config/mobileV2Rollout.test.ts`
- `android/src/config/mesaApi.ts`
- `android/src/config/mesaApi.test.ts`

Documentacao:

- `docs/restructuring-roadmap/49_epic09b_android_rollout.md`
- `docs/restructuring-roadmap/99_execution_journal.md`

## Rollback

Rollback rapido e seguro:

1. desligar `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED` no app para voltar imediatamente ao legado;
2. ou desligar `TARIEL_V2_ANDROID_ROLLOUT` no backend para negar o gate remoto;
3. ou desligar `TARIEL_V2_ANDROID_PUBLIC_CONTRACT` para indisponibilizar as rotas V2 publicas.

Nenhuma dessas opcoes exige mudar UX ou remover o caminho legado.

## O que ainda falta antes de ligar para tenants reais

- definir allowlist/coortes reais de piloto por tenant;
- acompanhar telemetria de fallback em ambiente controlado;
- avaliar se o cache curto de capabilities deve virar cache persistido ou permanecer apenas em memoria;
- decidir criterio operacional para promover feed/thread V2 a default.
