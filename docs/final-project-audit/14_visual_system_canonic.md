# 14. Visual System Canonic

## Norte visual aprovado

Linguagem final escolhida para o produto oficial web:

- moderna
- sobria
- enterprise
- clara
- profissional
- orientada a operacao
- com baixa saturacao e baixo ruido

## Benchmarks usados

- principal: Carbon Design System
  - https://carbondesignsystem.com/
- secundario: Atlassian Design System
  - https://atlassian.design/
- apoio de organizacao de estados/tokens: Material 3
  - https://m3.material.io/

Essas referencias foram usadas como benchmark conceitual de sistema, nao como tentativa de copiar UI de fornecedor.

## Decisao canonica de composicao

- shell escuro apenas onde faz sentido operacional:
  - navegacao lateral do `/admin`
  - navegacao lateral do `/app`
- conteudo principal claro em todas as superficies oficiais
- destaque de acao por um azul unico e contido
- badges e estados com semantica unica entre portais
- cards e paines com borda suave, raio consistente e elevacao leve

## Tokens canonicos

Fonte de verdade:

- `web/static/css/shared/official_visual_system.css`
- `artifacts/final_visual_audit/20260404_191730/style_tokens.json`

### Paleta base

- page: `#f3f6f9`
- page subtle: `#ebf0f5`
- surface: `rgba(255, 255, 255, 0.96)`
- border: `#d5dfeb`
- text: `#16212d`
- text muted: `#58687a`
- accent: `#1f5e8e`
- accent hover: `#17496d`
- success: `#2f7d5a`
- warning: `#8a6425`
- danger: `#c55a52`

### Tipografia

- fonte principal: `IBM Plex Sans`
- display: `IBM Plex Sans`
- mono: `JetBrains Mono`

### Escala espacial

- `4, 8, 12, 16, 20, 24, 32, 40, 48`

### Raios

- `10, 14, 18, 24`

### Sombras

- `xs`: leitura de borda
- `sm`: card padrao
- `md`: painel elevado
- `lg`: shell/auth/card hero

## Regras canonicas de componentes

### Botoes

- `primary`: azul unico, foco da tela, no maximo uma acao dominante por cluster
- `ghost/secondary`: neutro, borda clara, usado para navegacao secundaria e utilitarios
- `danger`: reservado a acao destrutiva e nunca misturado com primary no mesmo peso

### Inputs e selects

- fundo claro e neutro
- borda unica baseada em `vf-border`
- foco com `vf-focus-ring`
- mesmo raio em todos os portais

### Badges e estados

- sucesso: verde suave
- alerta: ocre suave
- perigo: vermelho suave
- informativo/default: azul suave

### Cards, paineis e tabelas

- mesma familia de borda e elevacao
- fundo claro com gradiente sutil
- tabelas com cabecalho de baixa saturacao e linhas discretas

### Tabs e navegacao secundaria

- estado ativo com azul suave e borda reforcada
- estrutura visual reaproveitada entre `/cliente`, `/app` e `/revisao`

### Empty states e loading

- mais curtos
- sem bloco explicativo redundante
- foco em proxima acao ou ausencia objetiva de dados

## Regras canonicas de microcopy

- titulos curtos
- subtitulo apenas quando acrescenta contexto operacional real
- CTA com verbo direto
- estados vazios com uma frase de contexto e, quando necessario, uma proxima acao
- evitar repetir no corpo do card o que ja foi dito no topo da secao

## Regra de manutencao

Nao criar nova paleta local por portal. Toda nova superficie oficial deve:

1. carregar `official_visual_system.css`
2. reutilizar os tokens `--vf-*`
3. evitar introduzir novo CTA primario sem necessidade de hierarquia
4. reduzir microcopy antes de adicionar novos blocos
