# Checkpoint Tecnico Atual

Data: 2026-04-11
Horario de referencia: 20:29 -03

## Contexto

Este checkpoint substitui a referencia tecnica anterior da fase de regressao
ampla. O `HEAD` atual passou a ser `92603e0`, um commit de checkpoint
documental que congela o estado mais recente da frente de renderizacao de
documentos.

## Estado Git

- branch: `checkpoint/20260331-current-worktree`
- HEAD atual: `92603e0` - `Add Tariel product checkpoint for document rendering`
- ultimo commit de produto antes do checkpoint: `3316337` - `Polish Admin-CEO catalog density and preview`
- objetivo da fase: elevar a qualidade de composicao e render do documento final

## Estado operacional confirmado

- `gh` autenticado como `gstarielio-hash`
- conector GitHub do Codex autorizado para `gstarielio-hash/tariel-web`
- Render CLI autenticado no workspace `Gabriel's workspace`
- servico online ativo em `https://tariel-web-free.onrender.com`
- deploy live atual: `dep-d7dafsp9rddc73dq9t70`
- commit live no Render: `331633716dc8c740ac5e0bc92aae2d37d75f2383`

## Entregas que definem o estado atual

- refino da tela `Admin-CEO` em `/admin/catalogo-laudos`
- vitrine premium de templates por assinatura estabilizada
- preview lateral e modal de PDF real consolidados no catalogo
- checkpoint documental consolidado em `docs/checkpoint_atual_tariel_2026-04-11.md`

## Diagnostico tecnico atual

### 1. Pipeline estrutural

O payload canonico esta sendo montado em:

- `web/app/domains/chat/catalog_pdf_templates.py`

Funcoes centrais:

- `build_catalog_pdf_payload(...)`
- `resolve_pdf_template_for_laudo(...)`
- `materialize_catalog_payload_for_laudo(...)`

O problema atual nao e ausencia de dados. O problema e mistura excessiva entre:

- seeds canonicos
- dados reais do laudo
- branding
- controle documental
- projecoes por familia

### 2. Motores de render

#### `editor_rico`

Arquivos principais:

- `web/nucleo/template_editor_word.py`
- `web/app/domains/revisor/templates_laudo_editor_routes.py`
- `web/app/domains/admin/client_routes.py`

Estado:

- caminho principal mais forte hoje
- trabalha com JSON documental, placeholders resolvidos e HTML final em Playwright

#### `legado_pdf`

Arquivo principal:

- `web/nucleo/template_laudos.py`

Estado:

- ainda existe como fallback real
- pode entrar em rotas principais com `mapeamento_campos={}`
- gera resultado fraco quando falta template custom forte

### 3. Gargalo atual

O gargalo principal agora esta na ultima milha do documento:

- payload canonico razoavelmente bom
- view model documental ainda inexistente ou insuficiente
- layout final ainda nao entrega documento premium de forma consistente

## Proxima sequencia recomendada

1. criar `web/app/domains/chat/catalog_document_view_model.py`
2. criar um shell universal premium para familias sem template custom forte
3. separar projecoes `client_document` e `admin_document`
4. reduzir dependencia do `legado_pdf` como saida visivel principal
5. adicionar QA de render para barrar pagina quase vazia, fallback textual feio e metadado interno no PDF do cliente

## Arquivos centrais desta fase

- `web/app/domains/chat/catalog_pdf_templates.py`
- `web/nucleo/template_editor_word.py`
- `web/nucleo/template_laudos.py`
- `web/static/js/admin/admin_catalogo_laudos_page.js`
- `web/app/domains/chat/chat_aux_routes.py`
