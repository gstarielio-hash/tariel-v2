# Caixas da Migracao por Dominio

Objetivo deste arquivo:

- organizar a migracao em 4 "caixinhas" separadas;
- deixar claro o que esta na caixa antiga e o que ja entrou na caixa nova;
- delimitar as rotas de cada dominio sem misturar `portal`, `surface` e `shell`;
- servir como quadro de controle para continuar puxando conteudo das caixas antigas para as novas.

## 1. Modelo mental oficial

Imagine 8 caixas:

- 4 caixas antigas = implementacao legada em `Tariel Control Consolidado`
- 4 caixas novas = implementacao em `tariel-v2`

As 4 caixas sao:

1. `Admin-CEO`
2. `Admin-cliente`
3. `Chat inspetor`
4. `Mesa avaliadora`

Elas conversam entre si, mas continuam separadas.

Regra principal:

- cada fatia nova deve ser puxada da caixa antiga correta para a caixa nova correta
- nao devemos continuar puxando algo da caixa antiga do `Chat inspetor` e chamar isso de `Mesa avaliadora`
- nao devemos puxar algo da caixa antiga de `Admin-cliente` e chamar isso genericamente de `portal cliente` sem dizer a surface

## 2. Mapa resumido das 8 caixas

### Caixa antiga 1 -> Caixa nova 1

- dominio: `Admin-CEO`
- legado: `web/templates/admin/*`
- novo: `web/frontend-astro/src/pages/admin/*`

### Caixa antiga 2 -> Caixa nova 2

- dominio: `Admin-cliente`
- legado: `web/templates/cliente_portal.html` + `web/templates/cliente/*`
- novo: `web/frontend-astro/src/pages/cliente/*`

### Caixa antiga 3 -> Caixa nova 3

- dominio: `Chat inspetor`
- legado: `web/templates/index.html` + `web/templates/inspetor/*` + `web/templates/inspetor/workspace/*`
- novo: `web/frontend-astro/src/pages/app/*`

### Caixa antiga 4 -> Caixa nova 4

- dominio: `Mesa avaliadora`
- legado: `web/templates/painel_revisor.html` + `web/templates/login_revisor.html`
- novo: `web/frontend-astro/src/pages/revisao/*`

## 3. Caixa 1 — `Admin-CEO`

### 3.1 Caixa antiga

Fonte legacy principal:

- `web/templates/admin/dashboard.html`
- `web/templates/admin/clientes.html`
- `web/templates/admin/cliente_detalhe.html`
- `web/templates/admin/catalogo_laudos.html`
- `web/templates/admin/admin_auditoria.html`
- `web/templates/admin/admin_configuracoes.html`
- `web/templates/admin/login.html`
- `web/templates/admin/trocar_senha.html`
- `web/templates/admin/admin_mfa.html`
- `web/templates/admin/novo_cliente.html`

### 3.2 Caixa nova

Rotas atuais no V2:

- `/admin/login`
- `/admin/login/entrar`
- `/admin/logout`
- `/admin/trocar-senha`
- `/admin/trocar-senha/confirmar`
- `/admin/mfa/setup`
- `/admin/mfa/setup/confirmar`
- `/admin/mfa/challenge`
- `/admin/mfa/challenge/confirmar`
- `/admin/reauth`
- `/admin/reauth/confirmar`
- `/admin/painel`
- `/admin/clientes`
- `/admin/clientes/[id]`
- `/admin/clientes/[id]/bloquear`
- `/admin/clientes/[id]/trocar-plano`
- `/admin/clientes/[id]/catalogo-laudos`
- `/admin/clientes/[id]/adicionar-admin-cliente`
- `/admin/catalogo-laudos`
- `/admin/auditoria`
- `/admin/configuracoes`
- `/admin/configuracoes/acesso`
- `/admin/configuracoes/defaults`
- `/admin/novo-cliente`
- `/admin/novo-cliente/criar`

### 3.3 Leitura da caixa

Ja migrado de forma real:

- autenticacao
- logout
- troca obrigatoria de senha
- MFA e reauth
- dashboard
- carteira de clientes
- detalhe do cliente
- catalogo administrativo
- auditoria
- onboarding inicial
- parte importante de configuracoes

Ainda nao assumir como "100% fechado":

- configuracoes completas
- qualquer mutacao que ainda esteja parcialmente em bridge

### 3.4 Status da caixa

- caixa nova: bem preenchida
- caixa antiga: ainda existe como referencia e fallback semantico
- estado geral: `quase fechada`

## 4. Caixa 2 — `Admin-cliente`

### 4.1 Caixa antiga

Fonte legacy principal:

- `web/templates/cliente_portal.html`
- `web/templates/cliente/painel/*`
- `web/templates/cliente/chat/*`
- `web/templates/cliente/mesa/*`
- `web/templates/login_cliente.html`
- `web/templates/cliente/usuario_acesso_inicial.html`

### 4.2 Caixa nova

Rotas atuais no V2:

- `/cliente/login`
- `/cliente/login/entrar`
- `/cliente/logout`
- `/cliente/trocar-senha`
- `/cliente/trocar-senha/salvar`
- `/cliente`
- `/cliente/painel`
- `/cliente/equipe`
- `/cliente/equipe/criar`
- `/cliente/equipe/[userId]/bloquear`
- `/cliente/equipe/[userId]/resetar-senha`
- `/cliente/suporte`
- `/cliente/suporte/diagnostico`
- `/cliente/suporte/plano-interesse`
- `/cliente/suporte/registrar`
- `/cliente/mesa`
- `/cliente/mesa/[laudoId]/avaliar`
- `/cliente/mesa/[laudoId]/responder`
- `/cliente/mesa/[laudoId]/marcar-whispers-lidos`

### 4.3 Leitura da caixa

Ja migrado de forma real:

- autenticacao
- logout
- troca obrigatoria de senha
- painel do tenant
- equipe
- suporte
- mesa do cliente com leitura e acoes principais

Ponto de atencao:

- esta caixa governa o tenant e conversa com as outras duas caixas operacionais
- ela nao deve ser confundida com `Mesa avaliadora` nem com `Chat inspetor`

Ainda falta melhorar:

- fechamento semantico completo da vertical
- confirmar se ainda resta algum recorte importante do portal cliente preso ao shell antigo

### 4.4 Status da caixa

- caixa nova: substancialmente preenchida
- caixa antiga: ainda serve de referencia para recortes nao fechados
- estado geral: `avancada`

## 5. Caixa 3 — `Chat inspetor`

### 5.1 Caixa antiga

Fonte legacy principal:

- `web/templates/index.html`
- `web/templates/login_app.html`
- `web/templates/inspetor/_portal_home.html`
- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/_mesa_widget.html`
- `web/templates/inspetor/workspace/_assistant_landing.html`
- `web/templates/inspetor/workspace/_inspection_conversation.html`
- `web/templates/inspetor/workspace/_inspection_history.html`
- `web/templates/inspetor/workspace/_inspection_record.html`
- `web/templates/inspetor/workspace/_workspace_context_rail.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`

### 5.2 Caixa nova

Rotas atuais no V2:

- `/app`
- `/app/login`
- `/app/login/entrar`
- `/app/logout`
- `/app/trocar-senha`
- `/app/trocar-senha/salvar`
- `/app/inicio`
- `/app/mesa`
- `/app/mesa/iniciar`
- `/app/mesa/[laudoId]/preview`
- `/app/mesa/[laudoId]/finalizar`
- `/app/mesa/[laudoId]/reabrir`
- `/app/mesa/[laudoId]/responder`
- `/app/mesa/[laudoId]/pendencias/[messageId]`
- `/app/mesa/[laudoId]/anexos/[attachmentId]`

### 5.3 Leitura da caixa

Ja migrado de forma real:

- autenticacao
- logout
- troca obrigatoria de senha
- home operacional do inspetor
- leitura de fila pessoal
- leitura de thread
- historico
- contexto tecnico
- iniciar inspecao
- preview de PDF
- responder thread
- tratar pendencia
- baixar anexo
- finalizar
- reabrir

Ponto de atencao:

- essa caixa ainda carrega residuos conceituais do shell legado
- o nome `Inspetor` vinha misturando `chat`, `home`, `mesa` e `workspace`
- aqui estamos tratando estritamente a surface de operacao do caso pelo inspetor

Ainda falta puxar da caixa antiga:

- partes do shell legado ligadas a `assistant_landing`
- navegacao e contexto ainda acoplados ao workspace antigo
- residuos de widget/context rail que nao foram substituidos por surface nova clara

### 5.4 Status da caixa

- caixa nova: forte e funcional
- caixa antiga: ainda guarda shell, contexto e residuos de navegação
- estado geral: `operacional, mas semanticamente ainda em limpeza`

## 6. Caixa 4 — `Mesa avaliadora`

### 6.1 Caixa antiga

Fonte legacy principal:

- `web/templates/login_revisor.html`
- `web/templates/painel_revisor.html`
- `web/templates/revisor_templates_biblioteca.html`
- `web/templates/revisor_templates_editor_word.html`

### 6.2 Caixa nova

Rotas atuais no V2:

- `/revisao`
- `/revisao/login`
- `/revisao/login/entrar`
- `/revisao/logout`
- `/revisao/trocar-senha`
- `/revisao/trocar-senha/salvar`
- `/revisao/painel`
- `/revisao/painel/[laudoId]/avaliar`
- `/revisao/painel/[laudoId]/responder`
- `/revisao/painel/[laudoId]/marcar-whispers-lidos`
- `/revisao/painel/[laudoId]/emitir-oficialmente`

### 6.3 Leitura da caixa

Ja migrado de forma real:

- autenticacao
- logout
- troca obrigatoria de senha
- painel da mesa
- fila
- thread
- resposta
- decisao
- emissao oficial
- marcacao de whispers lidos

Ponto de atencao:

- esta caixa e separada do `Chat inspetor`, mesmo quando ambos falam do mesmo laudo
- a mesa dentro do `app` nao substitui semanticamente esta caixa

Ainda falta confirmar:

- se toda a operacao da `Mesa avaliadora` ja pode ser considerada fechada no V2
- se restam bridges importantes com o painel legado fora dessas rotas

### 6.4 Status da caixa

- caixa nova: mais cheia do que parecia
- caixa antiga: ainda serve de referencia, mas ja nao deve ser tratada como unica source operacional
- estado geral: `provavelmente avancada, precisa fechamento semantico final`

## 7. Comunicacao entre as caixas

As caixas conversam, mas continuam separadas:

- `Admin-CEO` -> governa catalogo, tenant, grants e capacidades das outras 3
- `Admin-cliente` -> governa equipe e acesso de `Chat inspetor` e `Mesa avaliadora`
- `Chat inspetor` -> produz e movimenta o caso tecnico
- `Mesa avaliadora` -> revisa, devolve, aprova, reabre e emite

Regra operacional:

- conversa entre caixas nao justifica misturar ownership
- comunicacao nao muda a fronteira do dominio

## 8. Quadro rapido de enchimento das caixas novas

### Caixa nova 1 — `Admin-CEO`

- enchimento atual: `alto`
- percentual aproximado: `90%`

### Caixa nova 2 — `Admin-cliente`

- enchimento atual: `alto`
- percentual aproximado: `80%`

### Caixa nova 3 — `Chat inspetor`

- enchimento atual: `alto`, mas ainda com residuos de shell legado
- percentual aproximado: `75%`

### Caixa nova 4 — `Mesa avaliadora`

- enchimento atual: `medio para alto`, com necessidade de fechamento semantico final
- percentual aproximado: `78%`

## 9. Quadro de consolidacao objetiva

### Caixa 1 — `Admin-CEO`

- origem antiga: `web/templates/admin/*`
- destino novo: `web/frontend-astro/src/pages/admin/*`
- tipo de migracao ja visivel: autenticacao, leitura, escrita e governanca
- ja esta dentro da caixa nova: login, MFA, reauth, dashboard, clientes, detalhe do cliente, auditoria, catalogo, onboarding inicial
- bagunca remanescente: configuracoes e algumas mutacoes ainda precisam fechamento final de ownership
- estado pratico: `quase fechada`

### Caixa 2 — `Admin-cliente`

- origem antiga: `web/templates/cliente_portal.html` + `web/templates/cliente/*`
- destino novo: `web/frontend-astro/src/pages/cliente/*`
- tipo de migracao ja visivel: autenticacao, leitura, escrita e governanca de tenant
- ja esta dentro da caixa nova: login, painel, equipe, suporte, mesa do cliente, respostas e acoes principais
- bagunca remanescente: restos do portal antigo ainda precisam ser confirmados e recortes governados precisam continuar separados das superfices operacionais
- estado pratico: `avancada`

### Caixa 3 — `Chat inspetor`

- origem antiga: `web/templates/index.html` + `web/templates/inspetor/*` + `web/templates/inspetor/workspace/*`
- destino novo: `web/frontend-astro/src/pages/app/*`
- tipo de migracao ja visivel: autenticacao, leitura, escrita e operacao do caso
- ja esta dentro da caixa nova: login, home operacional, mesa, historico, resposta, pendencia, anexo, preview, iniciar inspecao, finalizar e reabrir
- bagunca remanescente: shell, navegacao e contexto ainda herdados do workspace legado
- estado pratico: `operacional, em limpeza`

### Caixa 4 — `Mesa avaliadora`

- origem antiga: `web/templates/login_revisor.html` + `web/templates/painel_revisor.html` + biblioteca/editor do revisor
- destino novo: `web/frontend-astro/src/pages/revisao/*`
- tipo de migracao ja visivel: autenticacao, leitura, escrita, decisao e emissao
- ja esta dentro da caixa nova: login, painel, fila, thread, resposta, avaliacao, emissao oficial, exportacoes, whispers lidos
- bagunca remanescente: falta fechamento semantico final para garantir que a operacao real nao depende mais do painel legado
- estado pratico: `avancada, precisa fechamento final`

## 10. Como usar este quadro no proximo passo

Antes de abrir qualquer nova tarefa:

1. diga de qual caixa antiga ela vem
2. diga para qual caixa nova ela vai
3. diga se e:
   - autenticacao
   - shell
   - leitura
   - escrita
   - bridge
   - limpeza de legado
4. so depois implemente

Se a tarefa nao couber claramente em uma das 4 caixas:

- a tarefa esta mal definida
- ela precisa ser reclassificada antes de virar codigo
