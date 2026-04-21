# Direcao Operacional da Mesa

Documento curto que consolida a linha de raciocinio de produto para o fluxo inspetor -> IA -> Mesa.

Este arquivo descreve a direcao desejada. O estado atual do sistema continua documentado em `mesa_avaliadora.md`.

## Objetivo

Sair do modelo de chat solto e chegar a um fluxo operacional:

- rastreavel;
- revisavel;
- auditavel;
- orientado por pendencias e evidencias.

## Modelo alvo

1. inspetor coleta o caso;
2. IA organiza o caso;
3. IA gera draft inicial do laudo;
4. caso sobe para a Mesa;
5. Mesa revisa;
6. Mesa abre pendencias estruturadas;
7. inspetor responde as pendencias com evidencias vinculadas;
8. IA reprocessa o draft;
9. Mesa aprova, reabre ou rejeita;
10. sistema materializa o documento final.

## Papel de cada parte

### Inspetor

- coleta evidencias;
- confirma dados factuais;
- responde pendencias da Mesa;
- envia fotos, documentos e observacoes vinculadas ao caso.

### IA

- identifica a familia principal do caso;
- organiza a conversa;
- sugere preenchimento do `laudo_output`;
- marca lacunas e baixa confianca;
- sugere relacao entre evidencia e slot;
- reprocessa o draft quando entram respostas relevantes.

### Mesa

- revisa tecnicamente;
- valida ou corrige a familia;
- abre pendencias objetivas;
- valida evidencias;
- registra overrides auditados;
- aprova ou rejeita a emissao.

## Caso estruturado

Cada caso deve ter:

- `family_key`;
- `family_lock`;
- `scope_mismatch_detected`;
- `scope_mismatch_items`;
- status operacional;
- status documental;
- status de revisao.

## Regra de familia

Um caso deve ter uma familia principal.

Depois que a familia e definida:

- a IA nao pode migrar silenciosamente de familia;
- conteudo fora do escopo nao entra automaticamente no laudo;
- a Mesa decide ignorar, reclassificar ou mandar abrir outro caso.

## Pendencia estruturada

Pendencia nao deve ser so mensagem com `resolvida_em`.

Ela deve carregar pelo menos:

- `type`
- `title`
- `description`
- `severity`
- `status`
- `blocking`
- `binding_path`
- `slot_id`
- `evidence_requirement`
- `opened_by`
- `assigned_to`
- `mesa_reason`
- `override_allowed`
- `audit_trail`

## Tipos minimos de pendencia

- `solicitar_foto`
- `solicitar_documento`
- `pedir_confirmacao`
- `apontar_inconsistencia`
- `corrigir_familia`
- `evidencia_insuficiente`
- `campo_critico_ausente`
- `revisao_conclusao`
- `aprovacao_com_ressalva`

## Estados minimos de pendencia

- `open`
- `waiting_inspector`
- `waiting_ai`
- `ready_for_review`
- `resolved`
- `rejected`
- `overridden`
- `cancelled`

## Evidencia vinculada

Toda evidencia relevante deve poder ficar vinculada a:

- uma pendencia;
- um `binding_path`;
- um `image_slot`;
- ou a uma observacao de escopo.

## Estados minimos de evidencia

- `accepted`
- `rejected`
- `out_of_scope`
- `needs_review`
- `selected_for_slot`
- `unused`

## Regras de bloqueio

Devem bloquear emissao:

- familia indefinida;
- pendencia critica em aberto;
- campo critico ausente;
- checklist obrigatorio incompleto;
- conflito grave entre evidencia e conclusao;
- ausencia de evidencia minima obrigatoria.

Nao precisam bloquear automaticamente:

- evidencia abaixo do recomendado, mas nao do minimo duro;
- pequenas inconsistencias textuais;
- material extra fora do escopo;
- pendencias nao criticas aprovadas com override auditado.

## Regras de UX

### Inspetor

O inspetor deve ver:

- o que falta para aprovar;
- o que bloqueia emissao;
- pendencias abertas;
- motivo da pendencia;
- botao claro para responder com evidencia.

### Mesa

A Mesa deve ver:

- resumo do caso;
- familia atual;
- alertas de escopo;
- draft do laudo;
- evidencias aceitas;
- pendencias abertas;
- itens bloqueantes;
- confianca do draft.

## Antipadroes

- usar chat puro como canal principal;
- tratar toda mensagem como evidencia elegivel;
- deixar a Mesa escrever o laudo inteiro manualmente;
- deixar o inspetor sem clareza do que falta;
- contar foto solta sem vinculo com slot ou pendencia.

## Regra de transicao

Enquanto o codigo legado ainda existir, a Mesa atual pode continuar operando.

Mas a evolucao oficial deve caminhar para:

- pendencia estruturada;
- evidencia com estado;
- familia travada por caso;
- IA como triagem e draft;
- Mesa como revisao e aprovacao.
