# Mapa Mental da Migracao V2

Objetivo deste arquivo:

- evitar que a migracao fique "espalhada" demais na cabeca;
- deixar claro o que e sistema novo, o que e bridge e o que ainda e legado;
- servir como pagina zero antes de abrir `docs/LOOP_ORGANIZACAO_FULLSTACK.md`.

## 1. Frase principal da migracao

O `tariel-v2` e o caminho oficial.
O legado (`tariel-web` / Python + Jinja + JS antigo) virou backup, referencia e bridge temporaria.

Se surgir duvida sobre "para onde isso esta indo?", a resposta padrao e:

- frontend oficial dos portais novos: `Astro + React + TypeScript`
- backend oficial de dominio, policy, auditoria, `IA`, `dados_formulario`, preview e `PDF`: `Python + FastAPI`
- `bridge` existe so quando a migracao ainda exige adaptacao, nunca como destino final

## 2. Regra mais importante para nao se perder

Nao pense na migracao como "reescrever tudo".
Pense como troca de ownership por portal e por vertical.

A pergunta certa nao e:

- "o sistema inteiro ja foi migrado?"

A pergunta certa e:

- "qual portal ja tem login, sessao, leitura e escrita reais no V2?"

## 3. Os dois mundos que coexistem hoje

### Mundo A: sistema novo

Repositorio:

- `tariel-v2`

Workspace principal do frontend novo:

- `web/frontend-astro/`

Papel:

- receber os portais oficiais por etapas;
- concentrar a nova stack web;
- substituir gradualmente o trafego do legado.

### Mundo B: sistema legado

Repositorio local relacionado:

- `Tariel Control Consolidado`

Remoto correspondente:

- `tariel-web`

Papel atual:

- manter superfices ainda nao migradas;
- servir como referencia funcional;
- cobrir bridges temporarias enquanto a vertical equivalente nao fecha no V2.

## 4. Mapa por portal

### 4.1 Admin-CEO (`/admin`)

Estado mental:

- e a frente mais madura dentro do V2;
- ja saiu do modo "preview visual";
- ja tem autenticacao e sessao reais no Astro.

Ja roda no V2:

- login
- logout
- troca obrigatoria de senha
- MFA TOTP
- reauth / step-up
- painel
- clientes
- auditoria
- catalogo
- onboarding de cliente
- parte de configuracoes

Observacao importante:

- `configuracoes` ainda nao esta 100% fechada no Astro;
- hoje existe mistura entre secoes com escrita real no V2 e secoes ainda em bridge;
- pelo codigo atual, `access` e `defaults` ja estao com escrita no Astro, enquanto outras secoes ainda mostram estado e deixam parte da mutacao no legado.

Arquivos ancora:

- `web/frontend-astro/src/pages/admin/*`
- `web/frontend-astro/src/lib/server/admin-auth.ts`
- `web/frontend-astro/src/lib/server/admin-mutations.ts`
- `web/frontend-astro/src/lib/server/admin-settings.ts`
- `web/frontend-astro/src/middleware.ts`

Leitura curta:

- se voce quiser saber "como esta o admin?", comece aqui.

### 4.2 Admin-cliente (`/cliente`)

Estado mental:

- ja tem base real;
- nao e mais so casca;
- ja entrou na fase operacional inicial.

Ja roda no V2:

- login
- logout
- troca obrigatoria de senha
- painel
- equipe
- suporte

O que isso significa na pratica:

- o tenant ja consegue entrar no portal novo;
- a equipe operacional ja pode ser gerida no V2;
- suporte e interesse comercial ja possuem leitura e escrita reais no V2.

Ainda falta:

- fechar a vertical `/cliente/mesa`

Arquivos ancora:

- `web/frontend-astro/src/pages/cliente/*`
- `web/frontend-astro/src/lib/server/client-auth.ts`
- `web/frontend-astro/src/lib/server/client-portal.ts`
- `web/frontend-astro/src/lib/server/client-action-route.ts`

Leitura curta:

- o portal cliente ja existe de verdade no V2, mas ainda nao esta completo.

### 4.3 Mesa Avaliadora (`/revisao`)

Estado mental:

- esta aberta como proxima grande vertical;
- ainda nao fechou autenticacao real nem operacao de fila/historico/resposta no V2.

Ja existe no V2:

- a tela `revisao/login`

Mas hoje ela funciona como:

- base visual e de direcionamento;
- ponto de entrada preparado para a proxima integracao;
- nao como portal operacional completo.

O que falta de verdade:

- autenticacao real da mesa
- sessao
- leitura da fila
- historico
- resposta operacional

Arquivos ancora:

- `web/frontend-astro/src/pages/revisao/login.astro`

Leitura curta:

- a mesa ja tem "endereco" no V2, mas ainda nao tem "vida completa" no V2.

### 4.4 Inspetor (`/app`)

Estado mental:

- ainda e a parte mais pesada e mais acoplada ao legado;
- foi deixado para depois porque concentra home, workspace, chat, historico e mesas mais complexas.

Ja existe no V2:

- `app/login`

Mas ainda nao existe no V2 como portal completo:

- home operacional
- workspace principal
- chat
- historico
- fluxo pesado de trabalho do inspetor

Arquivos ancora:

- `web/frontend-astro/src/pages/app/login.astro`

Leitura curta:

- o inspetor ainda e a grande fase final da migracao web.

## 5. Ordem de execucao que esta valendo

Hoje a ordem operacional esta assim:

1. terminar a vertical atual em progresso;
2. fechar `Admin-cliente` com `/cliente/mesa`;
3. fechar `Admin-cliente` end-to-end;
4. migrar `Mesa Avaliadora`;
5. so depois abrir o `Inspetor` pesado;
6. remover trafego de rota/template legado quando o conjunto novo estiver validado.

Traduzindo isso para decisao diaria:

- se existir duvida entre abrir uma coisa nova no inspetor ou fechar um buraco do cliente, o cliente ganha;
- se existir duvida entre levar `IA/PDF` para Node ou manter no pipeline atual, o ownership continua no `Python`.
- se existir duvida entre refinar visual e fechar auth/sessao/acao real, auth/sessao/acao real ganha;
- o legado so deve receber bridge, nao nova ownership de produto.

## 6. Como pensar cada vertical

Uma vertical so pode ser considerada "quase migrada" quando tiver estes blocos:

1. rota oficial no V2
2. login e sessao reais
3. leitura real dos dados
4. escrita real das acoes principais
5. protecao de rota / middleware
6. auditoria ou vinculacao de ator quando necessario
7. sem depender do template legado no fluxo normal

Se faltar um desses blocos, a vertical ainda esta em transicao.

## 7. O que ja esta seguro afirmar hoje

- `Admin-CEO` e o portal mais avancado no V2
- `Admin-cliente` ja entrou em operacao parcial real no V2
- `Mesa Avaliadora` ainda e a proxima vertical relevante, nao a atual concluida
- `Inspetor` continua como frente pesada e tardia
- o legado ainda existe porque partes importantes ainda nao foram substituidas
- o destino final continua sendo `tariel-v2/web/frontend-astro`

## 8. Atalho mental para nao travar

Quando voce abrir o projeto, pense assim:

- `admin` = quase fechado, com alguns bridges restantes
- `cliente` = base real pronta, falta mesa
- `revisao` = proxima vertical
- `app` = fase pesada final

Em uma linha:

- primeiro fechar plataforma;
- depois fechar portal do cliente;
- depois fechar mesa;
- por ultimo atacar o inspetor pesado e desmontar o legado.

## 9. Onde olhar primeiro quando bater confusao

Se a duvida for "qual e a direcao oficial?":

- `docs/TARIEL_V2_MIGRATION_CHARTER.md`

Se a duvida for "qual foi o ultimo corte real executado?":

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Se a duvida for "qual e a stack nova?":

- `web/frontend-astro/README.md`
- `web/frontend-astro/package.json`
- `web/frontend-astro/astro.config.mjs`

Se a duvida for "o que ja existe de verdade no frontend novo?":

- `web/frontend-astro/src/pages/`

## 10. Resumo executivo

O mapa mais util hoje e este:

- `tariel-v2` = futuro oficial
- `web/frontend-astro` = frontend novo
- `Admin-CEO` = frente mais madura
- `Admin-cliente` = segunda frente mais madura, faltando mesa
- `Mesa Avaliadora` = proxima etapa
- `Inspetor` = fase final pesada
- legado = referencia + bridge, nao destino

## 11. Complemento arquitetural

Para a leitura separada de:

- o que fica no frontend novo;
- o que fica no backend Python;
- como deve funcionar o fluxo `IA -> dados_formulario -> preview/final PDF`;

use tambem:

- `docs/MAPA_ARQUITETURA_FRONT_BACK_IA_PDF.md`
- `docs/CHECKLIST_ABERTURA_TAREFA_ASTRO_PYTHON.md`
