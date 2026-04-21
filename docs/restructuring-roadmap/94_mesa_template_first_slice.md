# Primeiro slice pequeno e seguro da Mesa focado em templates

## Slice escolhido

`Resumo operacional da biblioteca de templates dentro do painel da Mesa`

## Por que este slice foi escolhido

A auditoria mostrou um desenho muito claro:

- a Mesa vive no portal `revisao`
- o lifecycle completo de templates tambem vive no portal `revisao`
- mas o inbox tecnico `/revisao/painel` so oferecia um link seco para templates
- faltava contexto local para a mesa saber:
  - quantas versoes existem
  - quantas estao ativas
  - quantas estao em teste
  - e, principalmente, quantos codigos aparecem na operacao sem versao ativa

Esse recorte era o melhor primeiro slice porque:

- e diretamente ligado ao lifecycle de templates
- e util para o backoffice da mesa
- e read-only
- tem rollback simples
- nao altera payload publico
- nao mexe no Android
- nao abre uma refatoracao transversal

## O que foi alterado

### Backend

- `web/app/domains/revisor/templates_laudo_support.py`
  - novo helper `resumir_operacao_templates_mesa(...)`
  - consolida:
    - total de templates
    - total de codigos
    - total de ativos
    - total em teste
    - total Word
    - total PDF base
    - codigos sem ativo
    - codigos em operacao sem ativo
    - bases fixadas manualmente pela mesa
- `web/app/domains/revisor/panel.py`
  - injeta `templates_operacao` no contexto SSR do painel

### Front da Mesa

- `web/templates/painel_revisor.html`
  - novo bloco `mesa-template-focus`
  - mostra resumo operacional da biblioteca dentro do inbox
  - adiciona atalhos locais para:
    - abrir biblioteca
    - abrir editor Word
- `web/static/css/revisor/painel_revisor.css`
  - estilos locais do novo bloco
  - sem impacto no shell global

### Teste

- `web/tests/test_regras_rotas_criticas.py`
  - novo teste para o resumo operacional de templates no painel da mesa

## Como validar

Executado nesta fase:

- `cd web && python3 -m pytest -q tests/test_regras_rotas_criticas.py -k "painel_exibe_resumo_operacional_templates or revisor_publicar_template_desativa_ativo_anterior or revisor_publicar_template_editor_rico_desativa_ativo_anterior"`
  - `3 passed`
- `cd web && python3 -m pytest -q tests/test_smoke.py`
  - `26 passed`
- `cd web && python3 -m pytest -q tests/test_v2_document_hard_gate_10i.py`
  - `5 passed`
- `cd web && python3 -m py_compile app/domains/revisor/panel.py app/domains/revisor/templates_laudo_support.py`
  - `ok`

Validacao funcional esperada:

- abrir `/revisao/painel`
- conferir o bloco `Biblioteca no fluxo operacional`
- conferir os atalhos:
  - `Abrir biblioteca`
  - `Novo Word`
- conferir se o contador `em operacao sem ativa` sobe quando houver codigo usado em laudo sem versao ativa

## Rollback

Rollback rapido e local:

1. remover `templates_operacao` de `web/app/domains/revisor/panel.py`
2. remover o bloco `mesa-template-focus` de `web/templates/painel_revisor.html`
3. remover os estilos locais em `web/static/css/revisor/painel_revisor.css`
4. remover o helper `resumir_operacao_templates_mesa(...)`

Nenhuma migracao de banco, payload publico ou contrato de API precisa ser revertido.

## O que este slice provou

- a primeira melhoria util da Mesa por causa dos templates nao precisava mexer no fluxo de publicar
- o ownership real de templates ja e da Mesa no portal `revisao`
- havia espaco para ganhar contexto operacional sem abrir risco funcional
- o painel da Mesa agora enxerga um sinal concreto de governanca documental:
  - codigos em operacao sem versao ativa

## Proximo passo recomendado

Segundo slice pequeno e seguro na mesma linha:

- transformar o bloco de templates do painel em entrada guiada para a biblioteca
- idealmente com deep link/filtro para os codigos em operacao sem versao ativa
