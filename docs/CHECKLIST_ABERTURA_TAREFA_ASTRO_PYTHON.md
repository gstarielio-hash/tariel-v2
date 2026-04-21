# Checklist de Abertura de Tarefa: Astro ou Python?

Status deste arquivo:

- documento canônico para decidir ownership entre `Astro` e `Python`
- substitui a tabela separada como fonte principal
- deve ser o primeiro atalho antes de abrir um slice novo

Objetivo deste arquivo:

- classificar uma tarefa nova em menos de 1 minuto;
- evitar implementação no lugar errado;
- refletir a arquitetura real do projeto inteiro, não só do `frontend-astro`.

## 0. Regra de projeto ja fechada

Antes do checklist, considere estas regras como decisao ja tomada:

- `Astro + TypeScript` e a stack oficial para portais e para a experiencia web nova;
- `Python + FastAPI` e a stack oficial para dominio, policy, auditoria, `IA`, `dados_formulario`, preview e `PDF`;
- `bridge` existe so quando a migracao ainda exige adaptacao, nunca como destino final de ownership;
- a ordem operacional atual e: fechar `Admin-cliente` com `/cliente/mesa`, depois `Mesa Avaliadora`, e so depois abrir o `Inspetor` pesado.

## 1. Por que essa decisão existe neste projeto

Hoje, a leitura arquitetural mais fiel do Tariel inteiro e:

- `web/` continua como backend principal em `Python + FastAPI`;
- os dominios principais continuam em `web/app/domains/`;
- o nucleo pesado de `IA`, `OCR`, `template`, `preview` e `PDF` continua em `web/nucleo/`;
- `web/frontend-astro/` e a frente web nova, ainda parcial, para os portais em migracao;
- o frontend historico SSR/Jinja ainda existe no sistema vivo e ainda cobre partes relevantes do produto.

Entao a pergunta correta nao e:

- "qual linguagem eu prefiro usar?"

A pergunta correta e:

- "onde essa responsabilidade deve morar para nao quebrar ownership e fonte de verdade?"

## 2. Como usar

Leia as 5 perguntas abaixo na ordem.

Se a resposta for `sim` para uma pergunta decisiva, siga a indicação e pare.
Se tudo ficar ambíguo, use a regra final: manter a regra no backend e o frontend mais fino.

## 3. Checklist decisivo

### 1. A tarefa muda principalmente tela, layout, navegação, SSR ou auth de portal?

Se `sim`:

- tende a ir para `Astro`

Exemplos:

- nova pagina em `/admin`, `/cliente`, `/revisao` ou `/app`
- ajuste de shell, sidebar, fluxo de login ou logout
- formulario SSR de portal

### 2. A tarefa mexe em regra de negócio densa, policy, tenancy, RBAC ou auditoria?

Se `sim`:

- vai para `Python`

Exemplos:

- gate humano
- permissao por papel
- regra de aprovacao
- trilha auditavel
- regra documental

### 3. A tarefa toca IA, OCR, anexos, `dados_formulario`, template ou PDF?

Se `sim`:

- vai para `Python`

Exemplos:

- chamada de provider
- consolidacao de evidencias
- preenchimento estruturado
- preview PDF
- emissao final

### 4. A tarefa e uma acao leve de portal, mas depende de regra pesada no fundo?

Se `sim`:

- a interface fica em `Astro`
- a regra fica em `Python`

Exemplos:

- botao novo no portal que dispara regra de negocio central
- tela nova consumindo endpoint governado
- formulario de portal com validacao critica no backend

### 5. A tarefa existe so porque uma tela nova ainda depende do legado?

Se `sim`:

- pode entrar em `Astro` como bridge temporaria
- nao deve virar ownership definitiva do frontend

Exemplos:

- BFF
- adaptador de payload
- leitura provisoria para tela nova

## 4. Tabela rapida de consulta

| Se a tarefa for... | Dono principal | Observacao curta |
| --- | --- | --- |
| nova pagina ou shell de portal | `Astro` | Ex.: `/admin`, `/cliente`, `/revisao`, `/app` |
| layout, componente visual, UX e navegacao | `Astro` | React entra so onde houver interacao real |
| login, logout, sessao e protecao de rota de portal novo | `Astro` | Desde que a vertical ja esteja assumida no V2 |
| handler SSR pequeno ligado a formulario de portal | `Astro` | Especialmente mutacao administrativa leve |
| bridge/BFF de tela nova para backend antigo | `Astro` | Ponte controlada, nao destino final |
| leitura server-side com Prisma para portal ja migrado | `Astro` | Quando a ownership da fatia estiver clara no V2 |
| regra de negocio densa ou transversal | `Python` | Mantem uma fonte de verdade de dominio |
| API central do produto | `Python` | Especialmente inspetor, chat, mesa e revisor |
| tenancy, RBAC, policy e gates humanos | `Python` | Nao duplicar isso no frontend |
| trilha auditavel e vinculacao de ator | `Python` | O frontend consome, nao governa sozinho |
| IA, OCR ou integracao com provider | `Python` | Ownership natural do nucleo pesado |
| transformar entrada bruta em `dados_formulario` | `Python` | Esse e o contrato canonico do documento |
| preview PDF ou documento final | `Python` | Render documental continua aqui |
| binding de template e validacao documental | `Python` | Evita espalhar regra em varias stacks |

## 5. Casos de fronteira

### Caso 1: formulario do portal chama regra pesada

Separacao correta:

- `Astro` recebe a acao do usuario;
- `Python` executa a regra densa;
- `Astro` exibe resultado e feedback.

### Caso 2: tela nova precisa de dado que ainda mora no legado

Separacao correta:

- `Astro` pode fazer bridge temporaria;
- a regra nao deve ser reinventada no frontend;
- quando possivel, a ownership final deve descer para backend canonico.

### Caso 3: IA sugere conteudo para laudo

Separacao correta:

- `Python` chama provider e produz `dados_formulario`;
- `Python` valida e governa;
- `Astro` ou mobile apenas apresenta o estado do fluxo.

### Caso 4: preview documental dentro de portal novo

Separacao correta:

- `Astro` mostra a experiencia;
- `Python` monta preview e PDF;
- o frontend nao vira renderer de documento.

## 6. Sinais de que a tarefa esta indo para o lugar errado

Sinais de erro para `Astro`:

- comeca a concentrar regra de policy;
- escreve PDF;
- decide sozinho regra documental;
- replica validacao critica que ja existe no backend;
- cresce como motor de integracao pesada.

Sinais de erro para `Python`:

- comeca a assumir detalhe de layout;
- devolve HTML acoplado ao visual novo sem necessidade;
- vira lugar de comportamento puramente cosmetico;
- recebe responsabilidade de interacao que e apenas UX de portal.

## 7. Regra de saida

Se voce terminou o checklist com:

- maioria `portal`, `SSR`, `auth`, `UX`: `Astro`
- maioria `policy`, `IA`, `dados_formulario`, `PDF`, `audit`: `Python`
- mistura dos dois: `Astro` na interface, `Python` na regra

## 8. Pergunta final de desempate

Se eu mover esta regra para o frontend, estarei duplicando a fonte de verdade do sistema?

Se `sim`:

- nao leve a regra para o `Astro`
- mantenha no `Python`

## 9. Formula de bolso

- `Astro recebe a interacao.`
- `Python decide a verdade.`
