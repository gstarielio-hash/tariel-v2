# Status Canonico

Data de referencia: 2026-04-21
Branch operacional: `main`
Repositorio remoto: `gstarielio-hash/tariel-v2`
Commit de referencia: `7d7255a`

## Objetivo

Ser a referencia curta e pratica do estado atual do `tariel-v2`.

Este arquivo responde:

- onde a migracao realmente esta hoje;
- quais caixas ja tem ownership real no V2;
- o que ja foi migrado e o que ainda esta confuso;
- qual deve ser o proximo tipo de trabalho.

## Direcao canonica atual

O `tariel-v2` e o caminho oficial.
O legado em `Tariel Control Consolidado` continua como referencia funcional, backup e bridge temporaria.

Ownership oficial:

- `Astro + React + TypeScript` governam portais, rotas SSR e experiencia web nova;
- `Python + FastAPI` governam dominio, policy, auditoria, IA, `dados_formulario`, preview e PDF;
- `bridge` e camada de transicao, nunca destino final.

## As 4 caixas oficiais da migracao

O produto deve ser lido em 4 caixas novas, cada uma puxando conteudo da sua caixa antiga correspondente:

1. `Admin-CEO`
2. `Admin-cliente`
3. `Chat inspetor`
4. `Mesa avaliadora`

Regra principal:

- comunicacao entre caixas nao muda ownership;
- uma tela de `Chat inspetor` nao vira `Mesa avaliadora` so porque fala do mesmo laudo;
- uma acao de governanca do tenant nao deve ser tratada como se fosse runtime do chat;
- toda nova fatia deve declarar de qual caixa antiga vem e em qual caixa nova entra.

## Estado resumido das caixas no V2

### 1. `Admin-CEO`

Estado atual:

- caixa nova mais madura do V2;
- autenticacao, MFA, reauth, dashboard, clientes, auditoria e catalogo ja estao materializados em rotas Astro;
- onboarding inicial e parte relevante de configuracoes tambem ja migraram.

Rotas-ancora:

- `/admin/login`
- `/admin/mfa/*`
- `/admin/reauth`
- `/admin/painel`
- `/admin/clientes`
- `/admin/clientes/[id]`
- `/admin/catalogo-laudos`
- `/admin/auditoria`
- `/admin/configuracoes`
- `/admin/novo-cliente`

Leitura canonica:

- `Admin-CEO` esta `quase fechado`;
- ainda nao deve ser vendido internamente como `100%` porque configuracoes e algumas mutacoes seguem em fechamento parcial.

Percentual aproximado:

- `90%`

### 2. `Admin-cliente`

Estado atual:

- vertical real no V2, nao apenas preview;
- login, logout, troca obrigatoria de senha, painel, equipe, suporte e mesa do cliente ja existem no Astro;
- esta caixa governa o tenant e precisa continuar separada das caixas operacionais.

Rotas-ancora:

- `/cliente/login`
- `/cliente/painel`
- `/cliente/equipe`
- `/cliente/suporte`
- `/cliente/mesa`
- `/cliente/mesa/[laudoId]/avaliar`
- `/cliente/mesa/[laudoId]/responder`

Leitura canonica:

- `Admin-cliente` esta `avancado`;
- o que falta agora e mais fechamento semantico do portal e menos abertura de novas superfices misturadas.

Percentual aproximado:

- `80%`

### 3. `Chat inspetor`

Estado atual:

- ja tem login, home, mesa, thread, preview, resposta, pendencias, anexos, finalizacao e reabertura no Astro;
- deixou de ser apenas tela de entrada;
- a principal bagunca restante nao e falta de rota, e sim residuo de shell e classificacao conceitual do workspace legado.

Rotas-ancora:

- `/app/login`
- `/app/inicio`
- `/app/mesa`
- `/app/mesa/iniciar`
- `/app/mesa/[laudoId]/preview`
- `/app/mesa/[laudoId]/responder`
- `/app/mesa/[laudoId]/finalizar`
- `/app/mesa/[laudoId]/reabrir`

Leitura canonica:

- `Chat inspetor` esta `operacional`;
- o que ainda falta e limpar residuos de `assistant_landing`, `context rail`, navegacao herdada e qualquer duplicacao conceitual entre home e mesa.

Percentual aproximado:

- `75%`

### 4. `Mesa avaliadora`

Estado atual:

- mais avancada do que a leitura antiga sugeria;
- login, painel, thread, resposta, avaliacao, emissao oficial, exportacoes e marcacao de whispers ja existem no Astro;
- essa caixa precisa ser lida como vertical propria, irma do `Chat inspetor`, nao como extensao dele.

Rotas-ancora:

- `/revisao/login`
- `/revisao/painel`
- `/revisao/painel/[laudoId]/avaliar`
- `/revisao/painel/[laudoId]/responder`
- `/revisao/painel/[laudoId]/emitir-oficialmente`
- `/revisao/painel/[laudoId]/pacote/exportar-pdf`
- `/revisao/painel/[laudoId]/pacote/exportar-oficial`

Leitura canonica:

- `Mesa avaliadora` esta `avancada`;
- ainda falta fechamento semantico final para confirmar que o painel legado do revisor virou apenas referencia e nao dependencia ativa.

Percentual aproximado:

- `78%`

## Consolidacao do que ja foi migrado

Ja esta migrado em codigo real no `tariel-v2`:

- autenticacoes separadas por dominio;
- trocas obrigatorias de senha por portal;
- `Admin-CEO` com dashboard, clientes, auditoria, catalogo e onboarding inicial;
- `Admin-cliente` com painel, equipe, suporte e mesa do cliente;
- `Chat inspetor` com home operacional e mesa Astro com acoes principais;
- `Mesa avaliadora` com painel Astro, fila, thread, resposta e emissao oficial.

Ainda esta baguncado ou incompleto:

- classificacao documental antiga que ainda chama tudo de `inspetor`;
- residuos de shell legado no `Chat inspetor`;
- fechamento semantico final da `Mesa avaliadora`;
- confirmacao objetiva do que ainda depende de bridge em `Admin-CEO` e `Admin-cliente`.

## O que nao fazer daqui para frente

- nao abrir nova tarefa dizendo apenas "migrar inspetor";
- nao misturar `Chat inspetor` com `Mesa avaliadora`;
- nao tratar `Admin-cliente` como uma pasta generica onde cabe qualquer tela do tenant;
- nao usar comunicacao entre caixas como justificativa para borrar fronteiras.

## Proximo corte oficial

1. usar `docs/CAIXAS_MIGRACAO_POR_DOMINIO.md` como inventario operacional;
2. tratar organizacao e limpeza como prioridade antes de novas migracoes largas;
3. fechar os residuos semanticos do `Chat inspetor`;
4. fechar o ownership da `Mesa avaliadora`;
5. so depois retomar novas fatias de migracao com a classificacao ja limpa.

## Regra de manutencao

Sempre que o estado de uma caixa mudar de forma relevante:

- atualizar este arquivo;
- atualizar `docs/CAIXAS_MIGRACAO_POR_DOMINIO.md` se a fronteira mudou;
- registrar a mudanca no `docs/LOOP_ORGANIZACAO_FULLSTACK.md`.
