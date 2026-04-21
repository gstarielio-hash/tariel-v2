# Redesign da Mesa Avaliadora

## Objetivo

Reposicionar a Mesa Avaliadora como um workspace tecnico claro, focado em decisao e resposta, e nao como um conjunto de dashboards e paineis independentes.

O redesenho deve manter a base visual da Tariel, mas com:

- menos chrome
- menos cards concorrendo
- mais area util real
- paineis laterais mais calmos e colapsaveis
- uma hierarquia unica entre inbox, biblioteca e editor

## Diagnostico

Hoje a Mesa parece tres produtos diferentes:

1. `Inbox da Mesa`: fila operacional com conversacao e pendencias
2. `Biblioteca de Templates`: catalogo e ativacao de bases
3. `Editor Word`: ferramenta de montagem e revisao

O problema nao esta em um componente isolado. O problema esta na arquitetura visual:

- excesso de trilhos e faixas superiores
- muitas caixas com o mesmo peso
- area principal sem ancoragem suficiente
- lateral escura do editor quebra a linguagem do restante
- filtros e metricas ocupam mais espaco do que a tarefa ativa

## Direcao Sistêmica

### Linguagem visual

- superfícies claras e calmas
- bordas de 1px com baixo contraste
- blocos principais em `12px`
- inputs e botoes em `10px`
- sem gradientes escuros pesados na operacao principal
- menos sombras, mais hierarquia por alinhamento e espacamento

### Layout base

- topo global unico por produto
- subnavegacao curta e discreta
- coluna principal sempre dominante
- laterais como apoio, nao como protagonista
- estados vazios finalizados, nunca grandes areas em branco sem narrativa

### Comportamento

- drawers laterais colapsaveis
- filtros compactos e contextuais
- metricas so quando realmente ajudam a decidir
- prioridade visual para caso ativo, documento ativo ou acao principal

## Tela 1: Inbox da Mesa

### Problema atual

- a fila lateral pesa mais do que o caso ativo
- o centro da tela parece um canvas branco sem estrutura
- o composer fica enterrado
- resumo, status e metricas competem entre si
- nao existe um fluxo visual nitido de `fila -> caso -> resposta`

### Novo modelo

Trabalhar com tres zonas:

1. `Fila`
2. `Caso ativo`
3. `Drawer de contexto`

### Estrutura proposta

- esquerda: fila com largura entre `300px` e `340px`
- centro: coluna principal do caso com largura flexivel e eixo unico
- direita: drawer tecnico colapsado por padrao

### Fila

- remover o bloco introdutorio alto com muitos KPIs
- manter apenas:
  - titulo `Fila da Mesa`
  - busca
  - filtro rapido de estado
  - contador curto
- cada item da fila deve ter:
  - hash ou nome do caso
  - ultima mensagem ou proxima acao
  - status principal
  - indicadores pequenos de whisper, pendencia e aprendizado

Nao usar cards altos. A fila deve parecer lista operacional.

### Caso ativo

O centro deve virar uma thread tecnica clara:

- header compacto com identificacao do caso
- bloco curto de resumo tecnico
- timeline de conversa / eventos
- composer sempre visivel no fim

Se nao houver caso selecionado:

- empty state finalizado com texto curto
- CTA para selecionar um caso da fila

### Drawer de contexto

Conteudo:

- dados do inspetor
- contagem de pendencias
- checklist de aprovacao
- referencias rapidas

Esse drawer nao deve abrir por padrao.

### Resultado esperado

- menos sensacao de dashboard
- caso ativo passa a ser o foco inequivoco
- a Mesa parece operacao real, nao painel administrativo

### Arquivos alvo

- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/templates/painel_revisor.html`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/css/revisor/painel_revisor.css`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/js/revisor/painel_revisor_page.js`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/js/revisor/revisor_painel_core.js`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/js/revisor/revisor_painel_mesa.js`

## Tela 2: Biblioteca de Templates

### Problema atual

- tela funcional, mas com cara de admin dashboard
- KPIs ganham peso demais para uma biblioteca vazia
- filtros laterais ocupam mais espaco do que a descoberta
- o estado vazio nao conduz a acao principal

### Novo modelo

Transformar a biblioteca em uma tela de catalogo editorial:

- topo: busca + filtro essencial + CTA principal
- centro: lista de templates
- lateral: filtros secundarios, mais compactos
- historico: bloco secundario, abaixo

### Hierarquia proposta

- titulo e descricao mais curtos
- busca dominante
- CTA `Criar modelo` ou `Novo template` como principal
- KPIs reduzidos para uma faixa curta ou removidos quando vazia

### Estado vazio

Em vez de um grande espaco sem vida:

- icone ou marca discreta
- frase direta
- dois caminhos:
  - `Criar no editor Word`
  - `Importar base`

### Resultado esperado

- menos cara de backoffice
- mais clareza de biblioteca viva
- fluxo de criacao mais obvio

### Arquivos alvo

- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/templates/revisor_templates_biblioteca.html`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/css/revisor/templates_biblioteca.css`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/js/revisor/templates_biblioteca_page.js`

## Tela 3: Editor Word

### Problema atual

- a lateral escura domina o produto
- ha area vazia demais entre os trilhos e a folha
- a folha nao comanda a composicao
- o inspetor direito ainda compete com o canvas
- muitos controles ficam expostos ao mesmo tempo

### Novo modelo

O editor deve assumir um modelo de `canvas-first`.

Tres zonas:

1. `Drawer de insercao`
2. `Folha A4`
3. `Inspector`

### Drawer de insercao

Em vez de trilho fixo pesado:

- abrir como drawer claro ou semi-claro
- foco em acoes de insercao
- presets e blocos prontos em grupos colapsaveis
- menos botoes simultaneos

Estrutura ideal:

- `Comecar`
- `Presets`
- `Blocos`
- `Campos`
- `Assets`

### Folha A4

Deve ser o centro visual real:

- mais respiro em volta
- fundo do stage mais neutro
- toolbar superior mais curta
- largura suficiente para a folha respirar
- destaque da folha por contraste de superficie, nao por sombra exagerada

### Inspector

Manter a ideia de abas:

- `Documento`
- `Layout`
- `Comparar`
- `Preview`

Mas com painel mais estreito e mais silencioso. O inspector deve parecer apoio contextual, nao segunda coluna principal.

### Topo do editor

Hoje ha controles demais espalhados. O topo deve ser reduzido para:

- seletor de template
- salvar
- preview
- publicar

O restante deve ir para drawer ou menu secundario.

### Resultado esperado

- editor com cara de ferramenta premium
- mais foco no documento
- menos ruptura entre esquerda, centro e direita

### Arquivos alvo

- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/templates/revisor_templates_editor_word.html`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/css/revisor/templates_laudo.css`
- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web/static/js/revisor/templates_editor_word.js`

## Ordem de Implementacao

### Fase 1

Redesenhar o `Inbox da Mesa`.

Razao:

- e a tela mais critica operacionalmente
- hoje e a mais fraca em foco e hierarquia
- qualquer ganho ali melhora a percepcao do produto inteiro

### Fase 2

Refazer o `Editor Word`.

Razao:

- e onde a ruptura visual mais aparece
- a base funcional parece boa, mas a experiencia esta pesada e oca

### Fase 3

Refinar a `Biblioteca de Templates`.

Razao:

- ela ja esta menos errada
- pode herdar a linguagem das duas telas anteriores

## Limpeza de Legado

Ao implementar, remover o que ficar claramente sem uso:

- blocos introdutorios redundantes
- KPIs mortos
- cards de resumo duplicados
- estilos escuros do editor que perderem funcao
- filtros repetidos ou escondidos sem gatilho

Remocao so deve acontecer quando a substituicao estiver no runtime e sem referencias restantes.

## Primeira Entrega Recomendada

Primeira entrega de codigo:

1. reduzir o topo e o bloco de metricas do inbox
2. transformar a fila em lista mais compacta
3. reconstruir a coluna principal do caso ativo
4. mover contexto tecnico para drawer colapsavel

Se essa fase fechar bem, o resto da Mesa passa a ter uma direcao visual muito mais clara.
