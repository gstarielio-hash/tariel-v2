# Mapa Mental da Migracao V2

Objetivo deste arquivo:

- evitar que a migracao fique embaralhada entre "portal", "surface" e "workspace";
- fixar a hierarquia oficial de autoridade entre `Admin-CEO`, `Admin-cliente`, `Mesa Avaliadora` e `Chat inspetor`;
- deixar claro o que e vertical de produto, o que e shell/transicao e o que ainda e legado;
- servir como pagina zero antes de abrir `docs/LOOP_ORGANIZACAO_FULLSTACK.md`.

## 1. Frase principal da migracao

O `tariel-v2` e o caminho oficial.
O legado (`Tariel Control Consolidado` / Python + Jinja + JS antigo) virou backup, referencia e bridge temporaria.

Se surgir duvida sobre "para onde isso esta indo?", a resposta padrao e:

- frontend oficial dos portais novos: `Astro + React + TypeScript`
- backend oficial de dominio, policy, auditoria, `IA`, `dados_formulario`, preview e `PDF`: `Python + FastAPI`
- `bridge` existe so quando a migracao ainda exige adaptacao, nunca como destino final

## 2. Regra mais importante para nao se perder

Nao pense a migracao como "um portal do inspetor enorme".
Pense como troca de ownership por autoridade e por vertical operacional.

A pergunta certa nao e:

- "o inspetor ja foi migrado?"

A pergunta certa e:

- "qual autoridade governa qual surface?"
- "qual vertical ja tem login, sessao, leitura e escrita reais no V2?"
- "o que e `Chat inspetor` e o que e `Mesa avaliadora`?"

## 3. Os dois mundos que coexistem hoje

### Mundo A: sistema novo

Repositorio:

- `tariel-v2`

Workspace principal do frontend novo:

- `web/frontend-astro/`

Papel:

- receber os portais e surfaces oficiais por etapas;
- concentrar a nova stack web;
- substituir gradualmente o trafego do legado.

### Mundo B: sistema legado

Repositorio local relacionado:

- `Tariel Control Consolidado`

Papel atual:

- manter superfices ainda nao migradas;
- servir como referencia funcional e documental;
- cobrir bridges temporarias enquanto a vertical equivalente nao fecha no V2.

## 4. Hierarquia oficial de autoridade

Ordem canonica, de cima para baixo:

1. `Admin-CEO`
2. `Admin-cliente`
3. `Mesa Avaliadora`
4. `Inspetor`

Regra de autoridade:

- `Admin-CEO` governa o produto e os tenants
- `Admin-cliente` governa a operacao do proprio tenant
- `Admin-cliente` governa quem pode acessar `Mesa Avaliadora` e `Chat inspetor`
- `Mesa Avaliadora` e `Chat inspetor` sao surfaces irmas do mesmo caso tecnico
- `Mesa Avaliadora` nao governa `Admin-cliente`
- `Chat inspetor` nao governa `Mesa Avaliadora`

## 5. Mapa correto por dominio

### 5.1 `Admin-CEO`

O que e:

- a camada de governanca da plataforma
- cria tenants
- define politicas
- libera catalogo, familias, templates e capacidades

Nao e:

- surface de operacao do caso
- chat tecnico
- mesa de validacao do laudo

Estado mental no V2:

- vertical mais madura do frontend novo

### 5.2 `Admin-cliente`

O que e:

- o portal do cliente que compra o servico
- governa a propria empresa dentro do tenant
- controla equipe, operacao local, configuracoes e grants

Nao e:

- o lugar onde o inspetor executa a coleta tecnica
- a mesa em si

Regra central:

- `Admin-cliente` governa `Mesa Avaliadora` e `Chat inspetor`

### 5.3 `Chat inspetor`

O que e:

- a surface operacional do inspetor
- conversa com a IA
- coleta contexto, evidencia e pre-laudo
- move o caso entre estados operacionais

Nao e:

- portal administrativo
- painel de governanca do tenant
- a mesa de validacao

Observacao importante:

- "Inspetor" nao deve ser tratado como um bloco unico se isso misturar login/home/shell com `chat`, `historico`, `workspace` e `mesa`

### 5.4 `Mesa Avaliadora`

O que e:

- a surface de revisao e validacao humana
- responde ao caso vindo do `Chat inspetor`
- aprova, devolve, reabre, revisa e fecha o fluxo documental

Nao e:

- chat do inspetor
- admin do tenant
- admin da plataforma

Observacao importante:

- a `Mesa Avaliadora` conversa com o `Chat inspetor`, mas nao deve ser fundida semanticamente a ele

## 6. Como ler o estado do V2 hoje

### 6.1 `Admin-CEO`

Estado mental:

- frente mais madura dentro do V2
- ja saiu do modo "preview visual"
- ja tem autenticacao e sessao reais no Astro

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

Observacao:

- `configuracoes` ainda nao esta 100% fechada no Astro
- existe mistura entre secoes com escrita real no V2 e partes ainda em bridge

Arquivos ancora:

- `web/frontend-astro/src/pages/admin/*`
- `web/frontend-astro/src/lib/server/admin-auth.ts`
- `web/frontend-astro/src/lib/server/admin-mutations.ts`
- `web/frontend-astro/src/lib/server/admin-settings.ts`
- `web/frontend-astro/src/middleware.ts`

### 6.2 `Admin-cliente`

Estado mental:

- vertical real no V2
- nao e mais casca
- ja entrou em operacao parcial autentica

Ja roda no V2:

- login
- logout
- troca obrigatoria de senha
- painel
- equipe
- suporte

Ainda falta de verdade:

- fechar por completo as surfaces governadas do tenant
- garantir fechamento semantico da vertical `Admin-cliente`
- manter clara a separacao entre o portal do cliente e as surfaces operacionais que ele governa

Arquivos ancora:

- `web/frontend-astro/src/pages/cliente/*`
- `web/frontend-astro/src/lib/server/client-auth.ts`
- `web/frontend-astro/src/lib/server/client-portal.ts`
- `web/frontend-astro/src/lib/server/client-action-route.ts`

### 6.3 `Chat inspetor`

Estado mental:

- ja tem base funcional real no V2
- deixou de ser apenas `login`
- ainda nao esta semanticamente encerrado como vertical independente

Ja roda no V2:

- `app/login`
- `app/inicio`
- `app/mesa` como surface operacional de thread, historico, contexto, preview, iniciar inspecao, finalizar e reabrir

O que isso significa:

- boa parte da operacao web do inspetor ja saiu do legado em termos de surface Astro
- mas a classificacao documental ainda estava chamando isso genericamente de "Inspetor", misturando home, shell, chat e mesa

Ainda falta:

- reduzir residuos de navegacao e shell herdados do `assistant_landing`
- separar mental e documentalmente o que e `Chat inspetor` e o que e `Mesa Avaliadora`
- evitar que novas tarefas do `Chat inspetor` sejam descritas como se fossem mesa, e vice-versa

Arquivos ancora:

- `web/frontend-astro/src/pages/app/login.astro`
- `web/frontend-astro/src/pages/app/inicio.astro`
- `web/frontend-astro/src/pages/app/mesa.astro`
- `web/frontend-astro/src/lib/server/app-*`

### 6.4 `Mesa Avaliadora`

Estado mental:

- como vertical canonicamente distinta, ainda nao esta fechada no V2
- existe confusao potencial porque ha uma "mesa" dentro das surfaces do `app`, mas isso nao equivale automaticamente ao portal da `Mesa Avaliadora`

Ja existe no V2:

- `revisao/login`

Mas hoje isso funciona como:

- base visual e de direcionamento
- ponto de entrada preparado para integracao posterior
- nao como portal operacional completo da mesa

O que falta de verdade:

- autenticacao real da mesa avaliadora
- sessao propria
- fila da mesa
- historico da mesa
- resposta operacional da mesa
- fechamento da vertical `Mesa Avaliadora` sem depender do shell legado

Arquivos ancora:

- `web/frontend-astro/src/pages/revisao/login.astro`

## 7. Regra pratica para nao misturar as frentes

Quando aparecer uma tarefa nova, classifique primeiro em uma destas quatro caixas:

1. `Admin-CEO`
2. `Admin-cliente`
3. `Chat inspetor`
4. `Mesa Avaliadora`

Se a tarefa mexe em:

- grants, catalogo, tenant, planos ou governanca global: `Admin-CEO`
- equipe, operacao do tenant, configuracoes locais, acesso das surfaces: `Admin-cliente`
- conversa com IA, coleta, historico do caso, contexto tecnico do inspetor: `Chat inspetor`
- revisao humana, aprovacao, devolucao, reabertura pela surface da mesa: `Mesa Avaliadora`

Se a tarefa parece cair em duas caixas ao mesmo tempo:

- normalmente o problema esta na descricao da tarefa, nao no dominio
- reescreva a tarefa antes de implementar

## 8. Ordem de execucao que faz mais sentido agora

Ordem conceitual:

1. terminar a vertical atual em progresso sem distorcer o dominio
2. fechar `Admin-cliente`
3. fechar `Mesa Avaliadora`
4. limpar residuos do shell legado ligados a `Chat inspetor`
5. remover trafego de rota/template legado quando o conjunto novo estiver validado

Traduzindo isso para decisao diaria:

- se a duvida for entre abrir mais uma fatia ambigua no `app` ou fechar uma vertical clara, a vertical clara ganha
- se a duvida for entre "mexer no inspetor" genericamente ou distinguir `Chat inspetor` de `Mesa Avaliadora`, a distincao ganha
- se a duvida for entre refinar visual e fechar auth/sessao/acao real, auth/sessao/acao real ganha
- o legado so deve receber bridge, nao nova ownership de produto

## 9. Como pensar cada vertical como "fechada"

Uma vertical so pode ser considerada "quase migrada" quando tiver estes blocos:

1. rota oficial no V2
2. login e sessao reais
3. leitura real dos dados
4. escrita real das acoes principais
5. protecao de rota / middleware
6. auditoria ou vinculacao de ator quando necessario
7. sem depender do template legado no fluxo normal

Se faltar um desses blocos, a vertical ainda esta em transicao.

## 10. O que ja esta seguro afirmar hoje

- `Admin-CEO` e o portal mais avancado no V2
- `Admin-cliente` ja entrou em operacao parcial real no V2
- `Chat inspetor` ja tem surfaces reais no V2 e nao pode mais ser tratado como apenas `login`
- `Mesa Avaliadora`, como vertical propria, ainda nao esta fechada no V2
- parte da confusao recente veio de chamar de "Inspetor" mudancas que na verdade misturavam home, thread e mesa
- o destino final continua sendo `tariel-v2/web/frontend-astro`

## 11. Atalho mental correto

Quando voce abrir o projeto, pense assim:

- `Admin-CEO` = governanca da plataforma
- `Admin-cliente` = governanca do tenant
- `Chat inspetor` = operacao do caso com IA
- `Mesa Avaliadora` = validacao humana do caso

Em uma linha:

- plataforma governa tenant
- tenant governa chat e mesa
- chat produz o caso
- mesa valida o caso

## 12. Onde olhar primeiro quando bater confusao

Se a duvida for "qual e a direcao oficial?":

- `docs/TARIEL_V2_MIGRATION_CHARTER.md`

Se a duvida for "quem governa quem?":

- `docs/TARIEL_CONTEXT.md`
- `docs/STATUS_CANONICO.md`

Se a duvida for "qual foi o ultimo corte real executado?":

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Se a duvida for "quais sao os entrypoints por portal?":

- `docs/restructuring-roadmap/19_frontend_entrypoints_matrix.md`

Se a duvida for "o que ja existe de verdade no frontend novo?":

- `web/frontend-astro/src/pages/`

## 13. Resumo executivo

O mapa mais util hoje e este:

- `tariel-v2` = futuro oficial
- `web/frontend-astro` = frontend novo
- `Admin-CEO` = portal de governanca global
- `Admin-cliente` = portal de governanca do tenant
- `Chat inspetor` = surface operacional do inspetor
- `Mesa Avaliadora` = surface operacional de revisao humana
- legado = referencia + bridge, nao destino

## 14. Complemento arquitetural

Para a leitura separada de:

- o que fica no frontend novo;
- o que fica no backend Python;
- como deve funcionar o fluxo `IA -> dados_formulario -> preview/final PDF`;

use tambem:

- `docs/MAPA_ARQUITETURA_FRONT_BACK_IA_PDF.md`
- `docs/CHECKLIST_ABERTURA_TAREFA_ASTRO_PYTHON.md`
