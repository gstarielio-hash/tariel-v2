# Checkpoint Atual Tariel

Data: 2026-04-11
Horario de referencia: 20:29 -03

## Estado atual

- Branch atual: `checkpoint/20260331-current-worktree`
- HEAD local e remoto: `92603e0`
- Commit atual: `Add Tariel product checkpoint for document rendering`
- Commit de produto imediatamente anterior: `3316337` - `Polish Admin-CEO catalog density and preview`
- Worktree local: limpo

## Deploy online

- Servico Render: `https://tariel-web-free.onrender.com`
- Deploy ativo confirmado: `dep-d7dafsp9rddc73dq9t70`
- Commit publicado no Render: `331633716dc8c740ac5e0bc92aae2d37d75f2383`
- Status confirmado: `live`
- Ficou live em: `2026-04-11 17:03:38 -03`
- Diferenca atual: o checkpoint local `92603e0` ainda nao foi publicado no Render

## Onde parou de verdade

O checkpoint mais novo nao introduz codigo de produto novo; ele congela e
documenta o estado mais recente da fase de render documental.

O estado funcional herdado do commit de produto `3316337` e:

- refatoracao da tela `Admin-CEO` em `/admin/catalogo-laudos`
- transformacao da tela em vitrine premium de templates distribuidos por assinatura
- consolidacao do preview lateral e do modal de visualizacao do documento
- confirmacao de que o gargalo principal saiu de schema/JSON e entrou na composicao final do documento

## O que ja esta bom

- topo do `Admin-CEO` comunica catalogo comercial com mais clareza
- busca, filtros e navegacao por NR ficaram mais previsiveis
- cards do showroom ficaram mais compactos e legiveis
- preview da direita ficou mais convincente como documento
- distribuicao por assinatura esta mais clara na vitrine
- ordenacao visual de categorias por NR esta numerica real

## O problema atual mais importante

O problema principal nao e mais schema nem JSON.

O problema e:

- o sistema ja consegue montar o conteudo
- mas ainda nao compoe o documento final com qualidade premium
- o fallback visivel ainda pode entregar resultado fraco em familias sem template forte

Hoje o pipeline esta assim:

- `family/schema/seed -> payload documental -> render`

O proximo salto precisa ser:

- `family/schema/seed -> document_view_model -> layout documental -> render`

## Diagnostico tecnico atual

### 1. Pipeline estrutural

O payload canonico esta sendo montado aqui:

- `web/app/domains/chat/catalog_pdf_templates.py`

Funcoes principais:

- `build_catalog_pdf_payload(...)`
- `resolve_pdf_template_for_laudo(...)`
- `materialize_catalog_payload_for_laudo(...)`

Esse trecho ainda mistura:

- seeds canonicos
- dados reais do laudo
- branding
- controle documental
- projecoes por familia NR

### 2. Render do documento

Hoje existem 2 caminhos reais:

#### `editor_rico`

Arquivos principais:

- `web/nucleo/template_editor_word.py`
- `web/app/domains/revisor/templates_laudo_editor_routes.py`
- `web/app/domains/admin/client_routes.py`

Fluxo:

- JSON do documento com placeholders
- placeholders resolvidos contra `dados_formulario`
- nodes viram HTML
- HTML vira PDF A4 com Playwright

Esse continua sendo o caminho certo e mais forte.

#### `legado_pdf`

Arquivo principal:

- `web/nucleo/template_laudos.py`

Fluxo:

- pega um PDF-base
- aplica overlay de campos por coordenada

Problema atual:

- nas rotas principais, ele ainda pode entrar com `mapeamento_campos={}`
- o resultado final fica fraco ou quase sem projecao real

## Proxima sequencia recomendada

1. criar um `document_view_model` dedicado
2. criar um `template universal premium` para familias sem documento custom forte
3. separar `client_document` de `admin_document`
4. reduzir o caminho `legado_pdf` como fallback visivel principal
5. adicionar QA de render para bloquear PDF fraco, quase vazio ou com metadado interno exposto
