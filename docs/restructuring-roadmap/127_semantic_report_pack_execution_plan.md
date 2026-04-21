# Laudos oficiais - plano de execucao por report packs semanticos

Criado em `2026-04-06`.

## Contexto

O valor central do produto nao e apenas conversar com a IA. O ponto critico e transformar uma inspecao real em um laudo oficial preenchido corretamente, com texto, validacoes, fotos e conclusoes coerentes com o tipo de relatorio exigido.

Hoje o sistema ja possui:

- captura de texto, imagem e documento no fluxo do chat;
- salvamento de interacoes do laudo;
- geracao estruturada parcial para alguns templates;
- renderizacao documental por template legado;
- um caminho de `editor_rico` na Mesa avaliadora para templates editaveis.

Mas ainda faltam as pecas que fecham o caso operacional completo:

- usar o conjunto inteiro de evidencias do caso, e nao apenas o payload corrente;
- representar cada tipo de laudo como contrato semantico forte;
- preencher fotos e marcacoes de checklist no laudo final;
- suportar tanto o fluxo `Mesa valida` quanto o fluxo `mobile autonomo`;
- tratar familias reais de laudos oficiais, nao apenas exemplos pontuais como `nr35`.

## Objetivo

Construir uma espinha unica para preenchimento correto de laudos oficiais baseada em `report packs` semanticos, de modo que qualquer inspecao possa ser convertida em um `JSON canonico do laudo` e depois renderizada no template final correto, com suporte a texto, decisoes por item, fotos selecionadas e politicas de validacao.

## Decisao central

O dono do processo passa a ser o `JSON canonico do laudo`, nao o PDF.

Fluxo alvo:

`inspecao -> evidence bundle -> report pack -> JSON canonico -> revisao/politica -> renderer -> PDF final`

Isso vale tanto para:

- PDFs oficiais travados existentes em `Templates/`;
- templates novos ou equivalentes criados no `editor_rico` da Mesa.

## O que e um report pack

Cada `tipo_template` relevante passa a ser governado por um `report pack` versionado.

Cada `report pack` precisa declarar:

- `family`: familia documental, por exemplo `nr35_periodica`, `nr12_maquinas`, `spda`, `pie`;
- `version`: versao interna do contrato;
- `schema`: modelo canonico estruturado do laudo;
- `evidence_policy`: evidencias minimas, obrigatorias e opcionais;
- `decision_policy`: regras para `C`, `NC`, `NA`, recomendacoes, conclusoes e riscos;
- `image_slots`: slots semanticos de foto exigidos ou opcionais;
- `validation_policy`: `mesa_required` ou `mobile_autonomous`;
- `render_strategy`: `pdf_overlay`, `editor_rico`, ou hibrido;
- `quality_gates`: bloqueios de emissao por faltas, baixa confianca ou conflito.

## Estado atual relevante do codigo

Os pontos ja existentes no sistema que servem de base para essa implementacao sao:

- `web/app/domains/chat/normalization.py`
  - ja normaliza familias e aliases de `tipo_template`;
- `web/app/domains/chat/templates_ai.py`
  - ja possui um registry parcial de schemas estruturados, mas ainda curto;
- `web/app/domains/chat/gate_helpers.py`
  - ja possui gates por template, mas ainda nao cobre o modelo completo de evidencias, confianca e autonomia;
- `web/app/domains/chat/report_finalize_stream_shadow.py`
  - ja faz a finalizacao estruturada, mas ainda perto demais do payload da interacao corrente;
- `web/nucleo/template_laudos.py`
  - ja renderiza texto em PDF legado, mas ainda nao resolve bem `checkbox` e `image slots` do caso;
- `web/app/domains/revisor/templates_laudo_editor_routes.py`
  - ja permite criar templates em `modo_editor_rico`;
- `web/nucleo/template_editor_word.py`
  - ja resolve placeholders textuais e gera PDF a partir do documento rico, mas ainda precisa receber imagens dinamicas vindas da inspecao.

## Fontes documentais que entram neste plano

1. `Templates/`
   - biblioteca de laudos oficiais existentes, com layout fiel e uso operacional real.
2. Mesa avaliadora `editor_rico`
   - camada semantica editavel para templates novos, equivalentes ou evoluidos.

Regra:

- o PDF oficial nao deve ser a fonte primaria de inteligencia;
- a fonte primaria deve ser o contrato semantico do `report pack`;
- o PDF e apenas uma estrategia de saida.

## Arquitetura alvo

### 1. Caso de inspecao como raiz

Toda inspecao precisa carregar:

- `case_id` ou `laudo_id`;
- `tipo_template` normalizado;
- `template_family` e `template_version`;
- ator responsavel;
- tenant;
- status operacional;
- politica de validacao.

### 2. Evidence bundle canonico

O sistema precisa montar um `evidence bundle` do caso inteiro, nao apenas da ultima mensagem.

Esse bundle deve reunir:

- mensagens do chat;
- transcricoes ou texto informado pelo inspetor;
- fotos tiradas na inspecao;
- OCR das fotos quando houver;
- documentos anexados;
- validacoes da Mesa;
- anotacoes humanas adicionais;
- respostas estruturadas ja produzidas pela IA;
- metadados de captura, origem e horario.

Cada evidencia deve ter contrato explicito, com no minimo:

- `evidence_id`;
- `kind`;
- `source`;
- `captured_at`;
- `captured_by`;
- `path_or_url`;
- `caption`;
- `ocr_text`;
- `checklist_tags`;
- `validation_status`.

### 3. Schema canonico do laudo

A IA nao deve gerar texto solto para o PDF. Ela deve preencher um schema por familia.

Cada item de checklist precisa poder carregar:

- `item_codigo`;
- `titulo`;
- `veredito`;
- `justificativa_curta`;
- `evidence_refs`;
- `confidence`;
- `human_review_required`;
- `missing_evidence`;
- `observacoes`.

Separadamente, o schema precisa carregar:

- identificacao do cliente e da inspecao;
- conclusao final;
- recomendacoes;
- calculos derivados;
- `image_slots`.

### 4. Image slots semanticos

Fotos nao devem ser escolhidas diretamente por coordenada.

O fluxo correto e:

- a IA ou o humano escolhem semanticamente a melhor evidencia para cada slot;
- o renderer aplica o slot na pagina correta do template.

Exemplo de contrato:

```json
{
  "image_slots": [
    { "slot": "foto_visao_geral", "evidence_id": "img_12" },
    { "slot": "foto_detalhe_1", "evidence_id": "img_14" }
  ]
}
```

### 5. Renderer por estrategia

Precisamos aceitar pelo menos tres estrategias:

- `pdf_overlay`
  - para templates oficiais estaticos;
- `editor_rico`
  - para templates novos e editaveis;
- `hybrid`
  - quando a familia tiver versao editavel e versao oficial de saida.

## Papel da Mesa avaliadora

O `editor_rico` da Mesa nao deve ser tratado como um editor solto de documento. Ele deve virar a camada de autoria semantica de templates.

O template criado na Mesa precisa saber:

- quais campos do schema ele consome;
- quais itens de checklist ele projeta;
- quais `image slots` ele suporta;
- qual politica de validacao aplica;
- qual familia documental representa.

Direcao correta:

- o usuario da Mesa cria ou ajusta o template editavel;
- o sistema vincula esse template a um `report pack`;
- a IA preenche o schema do `report pack`;
- o renderer do editor transforma o schema em documento final.

Melhoria obrigatoria no `editor_rico`:

- suporte a `image slots` dinamicos de evidencia do caso, nao apenas assets fixos do template.

## Politicas de validacao

Cada familia documental precisa suportar duas politicas explicitas:

### `mesa_required`

- a IA produz prefill estruturado;
- a Mesa revisa item a item;
- o laudo so e emitido apos aprovacao humana.

### `mobile_autonomous`

- o inspetor pode concluir no mobile sem depender da Mesa;
- a emissao so e liberada se os hard gates forem satisfeitos.

Hard gates minimos:

- checklist completo;
- fotos obrigatorias presentes;
- nenhum item critico com baixa confianca;
- nenhum conflito relevante entre evidencias;
- assinatura ou contexto minimo quando aplicavel;
- familia/template allowlisted para autonomia;
- perfil do usuario autorizado para autonomia.

Se qualquer gate falhar, o caso volta para `mesa_required`.

## Fases de implementacao

### Fase 0 - Catalogo de familias e freeze operacional

Objetivo:

- inventariar os laudos oficiais em `Templates/`;
- agrupar arquivos por familia, nao por arquivo solto;
- congelar versao, checksum, tenant e politica.

Entregas:

- catalogo de familias oficiais;
- tabela `family -> version -> template base -> policy`.

### Fase 1 - Contrato base de report pack

Objetivo:

- criar o registry de `report packs`;
- ligar `tipo_template` a `family/version`;
- formalizar `schema`, `evidence_policy`, `image_slots` e `validation_policy`.

Hotspots provaveis:

- `web/app/domains/chat/normalization.py`
- `web/app/domains/chat/templates_ai.py`
- modulo novo para registry de `report packs`

### Fase 2 - Evidence bundle do caso inteiro

Objetivo:

- parar de depender apenas do payload corrente;
- montar um bundle do laudo inteiro na finalizacao.

Hotspots provaveis:

- `web/app/domains/chat/report_finalize_stream_shadow.py`
- helpers de persistencia e consulta de mensagens/evidencias

Saida esperada:

- finalizacao passa a consumir `historico + evidencias + validacoes`, e nao apenas `mensagem + imagem atual`.

### Fase 3 - Renderer com texto, checkbox e imagem

Objetivo:

- evoluir o renderer legado para suportar:
  - `text`;
  - `checkbox_mark`;
  - `image`;
  - `repeat_table_row` quando aplicavel.

Hotspots provaveis:

- `web/nucleo/template_laudos.py`
- possiveis helpers novos de composicao PDF

### Fase 4 - Mesa editor_rico como autoria semantica

Objetivo:

- fazer o `editor_rico` declarar placeholders, checklist e `image slots`;
- permitir renderizacao dinamica de evidencias do caso.

Hotspots provaveis:

- `web/app/domains/revisor/templates_laudo_editor_routes.py`
- `web/nucleo/template_editor_word.py`

### Fase 5 - Gate de autonomia mobile

Objetivo:

- habilitar o fluxo `mobile_autonomous` apenas onde houver base confiavel;
- bloquear emissao quando faltarem evidencias ou confianca.

Hotspots provaveis:

- `web/app/domains/chat/gate_helpers.py`
- telas do mobile/web que exibem pendencias de completude

### Fase 6 - Rollout por familias

Ordem sugerida:

1. primeira familia oficial com checklist e fotos bem definidos;
2. segunda familia com maior variacao documental;
3. expansao gradual para demais familias.

Regra:

- nao abrir todas as familias ao mesmo tempo;
- consolidar `shadow mode` antes de liberar autonomia ampla.

## Ordem pratica de execucao recomendada

1. Catalogar as familias reais da pasta `Templates/`.
2. Escolher a primeira familia piloto.
3. Desenhar o schema canonico dessa familia.
4. Definir os `image slots` semanticos.
5. Adaptar a finalizacao para usar `evidence bundle`.
6. Adaptar o renderer para checkbox e imagem.
7. Publicar o primeiro fluxo em `mesa_required`.
8. Medir divergencia entre IA e revisao humana.
9. So depois considerar `mobile_autonomous`.

## Criterio de pronto desta frente

Esta frente so deve ser considerada fechada quando existir ao menos uma familia oficial operando ponta a ponta com:

- `report pack` versionado;
- evidence bundle do caso inteiro;
- JSON canonico do laudo preenchido pela IA;
- renderer com texto, checkbox e imagem;
- politica `mesa_required` funcionando;
- medicao clara de divergencia entre prefill da IA e decisao final humana.

O criterio de pronto expandido para autonomia mobile exige ainda:

- gates fortes ativos;
- allowlist por familia e perfil;
- trilha auditavel de emissao;
- rollback simples para `mesa_required`.

## Riscos que precisam ser evitados

- tratar PDF como fonte primaria de inteligencia;
- deixar a IA preencher texto livre sem contrato de schema;
- selecionar fotos por ordem de upload em vez de semantica;
- liberar autonomia mobile sem gate de completude e confianca;
- criar casos especiais demais para `nr35` e travar a generalizacao.

## Proximo passo exato

O proximo slice util e levantar a `Fase 0` dentro do repositorio:

- catalogar as familias da pasta `Templates/`;
- escolher a primeira familia piloto;
- definir o contrato inicial do primeiro `report pack`;
- registrar os slots semanticos de texto, checklist e foto dessa familia.

## Ponto de retomada

Se este trabalho for interrompido, retomar por esta ordem:

1. abrir este documento;
2. confirmar a familia piloto escolhida;
3. revisar `normalization.py`, `templates_ai.py`, `gate_helpers.py`, `report_finalize_stream_shadow.py`, `template_laudos.py` e `template_editor_word.py`;
4. iniciar a `Fase 0`, nao a autonomia mobile;
5. manter `Mesa valida` como politica padrao ate o primeiro fluxo ponta a ponta estabilizar.
