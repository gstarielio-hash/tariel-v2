# Laudos oficiais - governanca normativa, override humano e aprendizado seguro

Criado em `2026-04-06`.

## Contexto

O sistema precisa aceitar que a validacao final do laudo e humana, mas isso nao pode significar que toda decisao humana vira automaticamente verdade para a IA.

Em inspecoes reais, tres coisas diferentes podem acontecer ao mesmo tempo:

- a norma e o `report pack` indicam que um item esta `NC`;
- o humano decide aprovar operacionalmente mesmo assim;
- o sistema precisa impedir que essa excecao vire referencia futura como se fosse a regra correta.

Esse problema fica ainda mais importante quando:

- o template ja esta pronto e bem mapeado;
- a IA consegue justificar tecnicamente a divergencia;
- existe fluxo `mobile_autonomous` alem do fluxo com Mesa;
- o produto precisa manter coerencia com normas, nao apenas com habitos locais.

## Problema a resolver

Hoje o sistema ja possui trilha de aprendizado e validacao humana em:

- `AprendizadoVisualIa`, com `veredito_inspetor`, `veredito_mesa` e `status`;
- contexto de aprendizado validado usado para alimentar a IA;
- pontos de `validacao_humana` e gate de confianca.

Mas a governanca ainda esta curta para o caso normativo:

- `validado pela mesa` nao pode significar automaticamente `serve para treinar a IA`;
- o sistema precisa registrar quando o humano aprovou algo apesar de conflito normativo;
- o motor de aprendizado precisa diferenciar `caso aprovado` de `caso elegivel para referencia futura`.

## Regra principal

O sistema deve separar explicitamente tres eixos:

1. `verdade normativa`
2. `decisao operacional humana`
3. `elegibilidade para aprendizado`

Regra de ouro:

- o humano pode ter a palavra final sobre emissao operacional;
- a IA deve avisar quando a decisao humana divergir da base normativa vigente;
- essa divergencia nao pode alimentar automaticamente o banco de referencia da IA.

## Modelo de decisao recomendado

### Eixo 1 - Verdade normativa

E o que o `report pack` e a base normativa vigente concluem para o item.

Cada item precisa registrar:

- `veredito_ia_normativo`
- `confidence_ia`
- `norma_refs`
- `evidence_refs`
- `rule_version`
- `divergencia_detectada`

### Eixo 2 - Decisao operacional humana

E o que a Mesa ou o fluxo permitido decide para emissao do laudo.

Cada item precisa registrar:

- `veredito_humano_final`
- `decisor_tipo`
- `decisor_id`
- `override_reason`
- `override_class`
- `approved_for_emission`

### Eixo 3 - Elegibilidade para aprendizado

E a decisao do sistema sobre se aquele caso pode ou nao virar referencia futura.

Cada item precisa registrar:

- `learning_disposition`
- `curation_required`
- `curated_by`
- `curated_at`
- `learning_notes`

Valores recomendados para `learning_disposition`:

- `eligible`
- `blocked_normative_conflict`
- `blocked_low_confidence`
- `blocked_missing_evidence`
- `curation_required`
- `curated_exception`

## Contrato por item de checklist

Cada item do laudo deve sair do prefill estruturado com um contrato como este:

```json
{
  "item_codigo": "nr35_ancoragem_integridade",
  "veredito_ia_normativo": "nao_conforme",
  "confidence_ia": "high",
  "norma_refs": ["NR35: item interno pack v3.2", "ABNT XYZ: secao 4.1"],
  "evidence_refs": ["img_12", "ocr_12"],
  "veredito_humano_final": "conforme",
  "override_reason": "substituicao programada com ART anexada e aceite formal do engenheiro responsavel",
  "override_class": "operational_exception",
  "approved_for_emission": true,
  "learning_disposition": "blocked_normative_conflict",
  "curation_required": true
}
```

O ponto central e:

- emissao aprovada nao implica aprendizado aprovado.

## Politica de override

Nem todo override humano deve ter o mesmo peso.

Sugestao de classes:

### `editorial_adjustment`

- divergencia leve de redacao, organizacao ou sintese;
- pode seguir para aprendizado se a norma nao foi contrariada.

### `evidence_interpretation`

- o humano leu a mesma evidencia de forma diferente da IA;
- exige justificativa;
- por padrao vai para `curation_required`.

### `operational_exception`

- a operacao aceitou emitir apesar de conflito com regra normativa padrao;
- nunca entra em aprendizado automatico;
- pode emitir, mas fica bloqueado para referencia futura.

### `normative_pack_gap`

- o humano aponta que o problema esta no `report pack`, nao no caso;
- nao deve ensinar a IA diretamente;
- deve abrir backlog para corrigir a regra do pack.

## Regra por criticidade

Uma automacao melhor do que "humano sempre pode tudo" e usar criticidade por item.

### Itens de baixa criticidade

- override permitido com justificativa curta;
- emissao pode seguir;
- aprendizado continua bloqueado se houver conflito normativo.

### Itens de media criticidade

- override permitido apenas com justificativa estruturada;
- emissao pode seguir;
- caso vai para `curation_required`.

### Itens de alta criticidade ou juridico-regulatorios

- override nao deve fechar em `mobile_autonomous`;
- o caso cai automaticamente para `mesa_required` ou dupla aprovacao;
- aprendizado bloqueado ate curadoria normativa.

Essa e uma melhoria importante para a automacao porque reduz risco sem matar produtividade.

## Comportamento esperado da IA

Quando houver divergencia, a IA deve:

- avisar objetivamente que a decisao humana conflita com a leitura normativa vigente;
- citar a referencia do `report pack` e da norma utilizada;
- explicar por que concluiu `C`, `NC` ou `NA`;
- listar qual evidencia suportou a decisao;
- sugerir o que faltaria para reverter a conclusao.

A IA nao deve:

- reescrever a propria conclusao so porque o humano discordou;
- assumir que o override humano atual redefine a regra futura;
- absorver excecoes operacionais como padrao de treinamento.

## Comportamento esperado da interface

Quando IA e humano divergirem, a interface deve mostrar:

- banner de conflito normativo;
- base da divergencia;
- nivel de criticidade do item;
- decisao sugerida pela IA;
- justificativa obrigatoria do override;
- impacto do override no aprendizado.

Texto de efeito operacional sugerido:

- `Aprovado para emissao pelo humano`
- `Nao elegivel para aprendizado automatico`
- `Curadoria normativa pendente`

## Ajuste estrutural no aprendizado

O sistema nao deve mais tratar `VALIDADO_MESA` como sinonimo de `pode ensinar a IA`.

Separacao recomendada:

- `review_status`
  - expressa se o humano aprovou ou rejeitou operacionalmente;
- `learning_disposition`
  - expressa se o caso pode virar referencia da IA.

Mesmo se um item ou caso continuar em `VALIDADO_MESA`, ele pode ter:

- `learning_disposition = blocked_normative_conflict`

Isso impede que a IA use um caso operacionalmente aceito como se fosse padrao correto.

## Melhorias de automacao recomendadas

### 1. Motor hibrido de regra + IA

Nao deixar toda a decisao nas costas do LLM.

Fluxo recomendado:

- camada deterministica do `report pack` valida requisitos objetivos;
- IA interpreta evidencias e preenche justificativas;
- motor de reconciliacao detecta conflito entre norma, evidencia e decisao humana.

### 2. Duas passagens da IA

Em vez de uma unica resposta longa:

- `passo A`: extrair fatos e evidencias;
- `passo B`: julgar conformidade usando apenas fatos estruturados.

Isso reduz alucinacao e melhora auditoria.

### 3. Score de conflito normativo

Criar um `conflict_score` por item e por laudo.

Uso:

- baixo score: humano pode concluir com justificativa curta;
- medio score: requer justificativa forte;
- alto score: derruba para Mesa ou dupla aprovacao.

### 4. Shadow learning

Mesmo depois da emissao, casos com conflito devem entrar numa fila de comparacao:

- decisao da IA;
- decisao humana;
- decisao da curadoria normativa.

So depois disso um caso pode mudar de `blocked` para `curated_exception`.

### 5. Packs normativos versionados

Quando o humano estiver certo e a IA errada de forma recorrente, o caminho correto e:

- corrigir o `report pack`;
- versionar a regra;
- reprocessar amostras antigas se necessario.

Nao usar excecao manual recorrente como substituto de manutencao normativa.

### 6. Autonomia mobile por tier

Em vez de liberar ou bloquear tudo de uma vez:

- `tier 0`: sem autonomia;
- `tier 1`: autonomia apenas para itens de baixa criticidade;
- `tier 2`: autonomia com revisao amostral;
- `tier 3`: autonomia plena apenas para familias muito estaveis.

## Impacto no fluxo `mobile_autonomous`

Melhor regra para mobile:

- se houver conflito normativo de alta criticidade, o mobile perde autonomia naquele caso;
- o caso sobe automaticamente para `mesa_required`;
- se o conflito for leve, o mobile pode concluir com justificativa, mas o caso fica bloqueado para aprendizado.

Isso e melhor do que permitir override irrestrito no mobile.

## Ajustes de modelo de dados recomendados

No minimo, o sistema precisa carregar estes campos por item estruturado:

- `veredito_ia_normativo`
- `confidence_ia`
- `norma_refs_json`
- `evidence_refs_json`
- `rule_version`
- `criticidade`
- `veredito_humano_final`
- `override_reason`
- `override_class`
- `approved_for_emission`
- `learning_disposition`
- `curation_required`
- `curation_notes`

Em nivel de laudo, recomenda-se tambem:

- `has_normative_conflict`
- `max_conflict_score`
- `final_validation_mode`
- `learning_eligible`
- `requires_normative_curation`

## Hotspots provaveis de implementacao

- `web/app/shared/db/models_auth.py`
  - hoje guarda trilha de aprendizado visual, mas ainda sem separacao forte entre aprovacao humana e elegibilidade para aprendizado;
- `web/app/domains/chat/learning_helpers.py`
  - hoje injeta casos `VALIDADO_MESA` como referencia futura;
- `web/app/domains/revisor/learning_api.py`
  - hoje valida o aprendizado, mas ainda sem `learning_disposition` explicito;
- `web/nucleo/inspetor/confianca_ia.py`
  - ja produz sinais de validacao humana e pode alimentar criticidade/gates;
- `web/app/domains/chat/gate_helpers.py`
  - precisa decidir quando conflito normativo derruba autonomia e exige Mesa;
- `web/app/domains/chat/report_finalize_stream_shadow.py`
  - ponto natural para consolidar o veredito final estruturado do caso.

## Sequencia recomendada de implementacao

1. Introduzir `learning_disposition` no contrato estruturado do item.
2. Separar `aprovacao operacional` de `aprendizado elegivel` no backend.
3. Impedir que `VALIDADO_MESA` sozinho alimente o contexto de aprendizado.
4. Exigir `override_reason` quando humano divergir da IA normativa.
5. Bloquear `mobile_autonomous` para conflitos de alta criticidade.
6. Criar fila de `curation_required` para conflitos normativos.
7. So depois disso ligar feedback curado de volta ao contexto da IA.

## Criterio de pronto desta camada

Esta camada so esta pronta quando:

- um override humano pode aprovar emissao sem contaminar o banco de referencia da IA;
- conflitos normativos ficam auditaveis por item;
- autonomia mobile cai para Mesa quando a criticidade exigir;
- so casos elegiveis entram como referencia futura;
- excecoes recorrentes geram manutencao de `report pack`, nao memoria errada para a IA.

## Proximo passo exato

O proximo slice util desta frente e desenhar o contrato estruturado por item e aplicar a regra:

- `emitir` e uma decisao;
- `ensinar a IA` e outra decisao.

Enquanto isso nao existir, o produto corre o risco de aprender excecoes operacionais como se fossem regra normativa.
