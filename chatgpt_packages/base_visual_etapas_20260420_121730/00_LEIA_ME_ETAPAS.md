# Base Visual por Etapas

Pasta gerada para servir como referência visual rápida do produto, organizada por portal e ordem de navegação.

Estrutura:
- `01_admin`
  - `01_login`
  - `02_dashboard`
  - `03_clientes`
- `02_cliente`
  - `01_login`
  - `02_painel_admin`
  - `03_chat`
  - `04_mesa`
- `03_app`
  - `01_login`
  - `02_home`
  - `03_workspace`
  - `04_workspace_mesa`
- `04_revisao`
  - `01_login`
  - `02_painel`
  - `03_templates_biblioteca`
  - `04_templates_editor`

Origem da coleta:
- Captura local automatizada com Playwright e servidor temporário da própria base.
- O fluxo principal foi coletado em `visual_base_20260420_121730_raw`.
- As telas faltantes foram complementadas por uma coleta dirigida em `visual_base_20260420_121730_missing`.

Uso recomendado:
- usar esta pasta como base visual para auditoria externa;
- comparar hierarquia, densidade, espaçamento e consistência entre portais;
- anexar junto do zip de código-fonte enxuto ao pedir revisão para o ChatGPT.
