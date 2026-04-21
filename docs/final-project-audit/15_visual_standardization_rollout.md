# 15. Visual Standardization Rollout

## Slice executado

Fase executada em 2026-04-04:

- auditoria visual completa das superficies oficiais
- definicao do novo sistema visual canonico
- rollout real de padronizacao visual nas superficies web oficiais

## Implementacao principal

### 1. Sistema visual compartilhado

Novo arquivo:

- `web/static/css/shared/official_visual_system.css`

Esse arquivo passou a concentrar:

- tokens canonicos `--vf-*`
- aliases por portal
- acabamento compartilhado de cards, paineis, inputs, tabelas, tabs e CTA
- unificacao de auth shells, admin, cliente, inspetor e revisao

### 2. Superficies conectadas ao sistema canonico

O CSS canonico foi carregado nas bases e templates oficiais de:

- `/admin`
- `/cliente`
- `/app`
- `/revisao`
- auth pages oficiais
- biblioteca de templates e editor Word da mesa

### 3. Reducao de ruido textual

Microcopy foi encurtada nos shells e heads criticos de:

- `cliente`
- `app`
- `revisao`
- auth pages
- editor e biblioteca de templates

### 4. CTA e estados

- botoes principais ficaram ancorados no mesmo azul canonico
- botoes ghost ficaram neutros e consistentes
- badges ganharam a mesma semantica de cor entre portais
- a tela de resposta da mesa no `/cliente` saiu com hierarquia mais clara:
  - `Aprovar` como CTA primario
  - `Devolver` como CTA secundaria

## Arquivos principais alterados

- `web/scripts/final_visual_audit.py`
- `web/static/css/shared/official_visual_system.css`
- `web/templates/inspetor/base.html`
- `web/templates/cliente_portal.html`
- `web/templates/painel_revisor.html`
- `web/templates/revisor_templates_biblioteca.html`
- `web/templates/revisor_templates_editor_word.html`
- `web/templates/login_app.html`
- `web/templates/login_cliente.html`
- `web/templates/login_revisor.html`
- `web/templates/admin/login.html`
- `web/templates/admin/admin_mfa.html`
- `web/templates/admin/trocar_senha.html`
- `web/templates/trocar_senha.html`
- shells e heads principais de `cliente`, `inspetor` e `revisao`

## Validacao executada

- `python -m py_compile web/scripts/final_visual_audit.py` -> ok
- `web/scripts/final_visual_audit.py --stage before` -> ok
- `web/scripts/final_visual_audit.py --stage after` -> ok
- `make verify` -> ok
- `make mesa-smoke` -> ok
- `make mesa-acceptance` -> ok

## O que melhorou objetivamente

- convergencia visual entre `/admin`, `/cliente`, `/app` e `/revisao`
- reducao real de texto em logins, hubs e superficies de triagem
- menos disputa de cor e menos semantica visual concorrente
- auth pages com leitura mais limpa e corporativa
- biblioteca/editor da mesa alinhados ao mesmo sistema

## O que ainda nao foi esgotado

- consolidacao estrutural profunda de CSS legacy ainda muito grande
- troca gradual de overrides por componentes/tokens nativos nas folhas antigas
- gates visuais automatizados por diff de screenshot no CI hospedado

## Regra de continuidade

Qualquer nova alteracao visual oficial deve seguir esta ordem:

1. alterar token compartilhado quando o problema for sistêmico
2. alterar template oficial quando o problema for hierarquia ou microcopy
3. evitar novo CSS local se o token/override compartilhado ja resolver
4. nunca usar `mesa-next` como referencia visual ativa do produto
