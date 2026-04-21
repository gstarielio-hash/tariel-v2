# Fase 01.9 - Baseline dedicada do boot de `/revisao/painel`

## Objetivo

Registrar a cadeia real de boot do painel do revisor antes do hotfix da fase, com foco em:

- SSR inicial;
- ordem real de scripts;
- globals obrigatorios;
- requests do first load;
- pontos de custo confirmados por medicao local.

Este documento e a fotografia de entrada da fase. Ele nao descreve a correcao; isso fica em `25_reviewer_panel_boot_hotfix.md`.

## Cadeia real de boot

### Handler e SSR inicial

Rota HTML:

- `web/app/domains/revisor/panel.py`
- handler: `painel_revisor()`

Blocos SSR entregues na primeira resposta:

- resumo dos whispers pendentes;
- lista `Em Andamento em Campo`;
- lista `Aguardando Avaliacao`;
- lista `Historico / avaliados`;
- filtros de inspetor, busca, aprendizados e operacao;
- totais operacionais usados pelos badges do shell.

Consultas SSR relevantes antes do hotfix:

- `inspetores_empresa`;
- `whispers_pendentes_db` com `MensagemLaudo` + anexos de mesa;
- tres consultas separadas para laudos:
  - rascunho
  - aguardando
  - aprovados/rejeitados
- duas agregacoes por laudo em `mensagens_laudo`;
- uma agregacao por laudo em `aprendizados_visuais_ia`.

### Template e ordem real dos scripts

Template de entrada:

- `web/templates/painel_revisor.html`

CSS carregado:

- Google Fonts (`IBM Plex Sans`, `Space Grotesk`)
- Google Material Symbols
- `/static/css/revisor/painel_revisor.css?v={{ v_app }}`

JS carregado no shell do revisor:

1. `/static/js/shared/api-core.js?v={{ v_app }}` quando `perf_mode`
2. `/static/js/revisor/revisor_painel_core.js?v={{ v_app }}`
3. `/static/js/revisor/revisor_painel_mesa.js?v={{ v_app }}`
4. `/static/js/revisor/revisor_painel_historico.js?v={{ v_app }}`
5. `/static/js/revisor/revisor_painel_aprendizados.js?v={{ v_app }}`
6. `/static/js/revisor/painel_revisor_page.js?v={{ v_app }}`

Dependencias de ordem confirmadas:

- `revisor_painel_core.js` precisa carregar primeiro para expor `window.TarielRevisorPainel`;
- `revisor_painel_mesa.js`, `revisor_painel_historico.js` e `revisor_painel_aprendizados.js` dependem do namespace criado pelo core;
- `painel_revisor_page.js` assume que todos os submodulos ja anexaram suas funcoes em `window.TarielRevisorPainel`;
- o contrato escondido `#revisor-front-contract` e lido como fonte de verdade para URLs e hooks do painel.

### Globals obrigatorios

Globais observados no boot:

- `window.TarielRevisorPainel`
- `window.TarielPerf` e `window.TarielCore` quando `perf_mode`
- `window.WebSocket`
- `#revisor-front-contract` com:
  - `/revisao/ws/whispers`
  - templates de `/pacote`
  - template de `marcar-whispers-lidos`
  - template de pendencias
  - template de responder anexo

## Cadeia real do first load de um laudo

Antes do hotfix, a primeira abertura de um laudo em `painel_revisor_page.js` fazia:

1. `GET /revisao/api/laudo/{id}/completo`
2. `GET /revisao/api/laudo/{id}/mensagens?limite=60`
3. `GET /revisao/api/laudo/{id}/pacote`
4. `POST /revisao/api/laudo/{id}/marcar-whispers-lidos` quando havia whisper pendente

O `GET /completo` ja suportava `incluir_historico=true`, mas o frontend nao aproveitava isso e sempre abria um request extra para `/mensagens`.

## Baseline local medido

### Cenario de medicao

Seed local usada na fase:

- 1 revisor;
- 1 inspetor;
- 7 laudos misturando `rascunho`, `aguardando`, `aprovado` e `rejeitado`;
- whispers, pendencias e aprendizados em alguns laudos;
- instrumentacao via `app.core.perf_support`.

### GET `/revisao/painel`

Baseline antes do hotfix:

- `status_code=200`
- `sql_count=16`
- `duration_ms=12.601`

### Primeiro laudo aberto

Baseline antes do hotfix:

- cadeia de 3 requests
- `total_sql=18`

Detalhe do cenario medido:

- `GET /revisao/api/laudo/1/completo` -> `sql_count=5`, `duration_ms=5.936`
- `GET /revisao/api/laudo/1/mensagens` -> `sql_count=6`, `duration_ms=6.676`
- `GET /revisao/api/laudo/1/pacote` -> `sql_count=7`, `duration_ms=7.751`

## Gargalos confirmados

### 1. Fan-out no first load do laudo

O custo principal do primeiro laudo aberto nao estava no SSR puro, e sim em abrir tres requests sequenciais/paralelos para dados do mesmo contexto:

- resumo/base do laudo;
- timeline/historico;
- pacote operacional da mesa.

### 2. Duplicacao de runtime em voo

O painel mantinha controladores de abort, mas nao reutilizava request em voo para:

- `carregarLaudo()`
- `obterPacoteMesaLaudo()`

Na pratica, reabrir o mesmo laudo ou clicar rapidamente em acoes de mesa podia reiniciar fetches equivalentes.

### 3. Lazy access por item no SSR

No SSR do painel, os loops acessavam relacoes que nao estavam materializadas em lote:

- `laudo.usuario.nome` ao serializar as listas;
- `item.laudo.codigo_hash` ao montar whispers.

Em datasets com varios inspetores e varios whispers de laudos diferentes, isso podia crescer por item.

### 4. Stack monolitica ainda carregada inteira

Mesmo sem abrir um laudo, o portal ainda entrega:

- core
- mesa
- historico
- aprendizados
- page

O custo de parse/boot JS ainda nao foi modularizado nesta fase; a meta aqui foi apenas cortar fan-out e duplicacao segura.

## O que nao apareceu como causa raiz

- o template Jinja nao dispara requests adicionais sozinho;
- o websocket de whispers nao domina o custo do first load;
- o HTML inicial nao e o gargalo principal atual quando comparado ao fan-out da primeira abertura de laudo.
