# NR13 Vaso de Pressao: Laudo Output e Template

Documento curto que fecha a primeira materializacao canonica entre:

- `family_schema`
- `laudo_output`
- `template_master`
- renderizacao em documento humano e PDF

Familia-base:

- `docs/family_schemas/nr13_inspecao_vaso_pressao.json`

Artefatos associados:

- `docs/family_schemas/nr13_inspecao_vaso_pressao.laudo_output_seed.json`
- `docs/family_schemas/nr13_inspecao_vaso_pressao.laudo_output_exemplo.json`
- `docs/family_schemas/nr13_inspecao_vaso_pressao.template_master_seed.json`

## Regra pratica

O `family_schema` nao e o documento final.

Fluxo correto:

1. `family_schema` define a familia e sua politica.
2. O caso revisado pela Mesa vira `laudo_output`.
3. O `template_master` em `editor_rico` consome esse `laudo_output`.
4. O renderer materializa documento humano e PDF.

## Decisao de modelagem desta familia

O renderer atual do `editor_rico` suporta bem:

- `{{json_path:...}}`
- `{{token:...}}`
- texto, heading, lista, tabela e imagem estatica por asset

O renderer ainda nao suporta canonicamente:

- `{{evidence_image:...}}`
- repeticao dinamica de blocos por slot
- injecao automatica de galeria fotografica do caso

Por isso, o `laudo_output` desta familia foi desenhado com duas camadas:

- valores tecnicos principais em texto simples;
- evidencias visuais e documentos como objetos renderizaveis em texto.

Exemplo:

- `identificacao.placa_identificacao.referencias_texto`
- `caracterizacao_do_equipamento.vista_geral_equipamento.referencias_texto`
- `documentacao_e_registros.prontuario.referencias_texto`

Isso permite gerar documento legivel agora, mesmo antes da camada canonica de imagem dinamica.

## Regra de binding

Texto simples:

- campos `text`, `textarea`, `enum` e `boolean` devem chegar em leaf textuais ou enums diretos.

Imagem dinamica:

- campos `image_slot` devem virar objeto com pelo menos:
  - `disponivel`
  - `referencias`
  - `referencias_texto`
  - `descricao`

Documento referenciado:

- campos `document_ref` devem virar objeto com pelo menos:
  - `disponivel`
  - `referencias`
  - `referencias_texto`
  - `observacao`

Tokens de render:

- dados de cabecalho, assinatura e variaveis visuais ficam em `tokens`.

## Regra de template desta familia

O `template_master` seed desta familia foi desenhado para:

- abrir como documento humano normal no `editor_rico`;
- renderizar em HTML/PDF sem depender de listas JSON cruas;
- manter a Mesa visivel no documento final;
- continuar compativel com futura camada de imagem dinamica.

## Estrutura editorial atual

O overlay atual desta familia foi fechado com a seguinte sequencia documental:

- capa / folha de rosto;
- controle documental / ficha da inspecao;
- objeto, escopo, base normativa e limitacoes;
- metodologia, condicoes operacionais e equipe;
- identificacao tecnica do vaso;
- inspecao visual e integridade aparente;
- dispositivos de seguranca e acessorios;
- documentacao, registros e evidencias;
- nao conformidades, criticidade e recomendacoes;
- conclusao, parecer e proxima acao;
- governanca da Mesa;
- assinaturas e responsabilidade tecnica;
- anexos e referencias.

Essa estrutura segue a direcao canonica do projeto: laudo profissional com rastreabilidade tecnica, evidencia objetiva, apresentacao documental controlada e conclusao coerente com a revisao da Mesa.

## Mapa resumido de placeholders

- `{{token:cliente_nome}}`
- `{{token:unidade_nome}}`
- `{{json_path:case_context.laudo_id}}`
- `{{json_path:resumo_executivo}}`
- `{{json_path:identificacao.identificacao_do_vaso}}`
- `{{json_path:identificacao.localizacao}}`
- `{{json_path:identificacao.placa_identificacao.referencias_texto}}`
- `{{json_path:caracterizacao_do_equipamento.vista_geral_equipamento.referencias_texto}}`
- `{{json_path:inspecao_visual.condicao_geral}}`
- `{{json_path:inspecao_visual.pontos_de_corrosao.descricao}}`
- `{{json_path:dispositivos_e_acessorios.leitura_dos_dispositivos_de_seguranca}}`
- `{{json_path:documentacao_e_registros.prontuario.referencias_texto}}`
- `{{json_path:nao_conformidades.descricao}}`
- `{{json_path:recomendacoes.texto}}`
- `{{json_path:conclusao.conclusao_tecnica}}`
- `{{json_path:mesa_review.status}}`

## Entrega operacional

Para operar essa familia de ponta a ponta:

1. publicar o `family_schema` no catalogo do Admin-CEO;
2. usar o `laudo_output_seed` como contrato-base do caso revisado;
3. subir o `template_master_seed` como base inicial do template em `editor_rico`;
4. validar o render com o `laudo_output_exemplo`;
5. depois evoluir para imagem dinamica sem quebrar o contrato textual atual.
