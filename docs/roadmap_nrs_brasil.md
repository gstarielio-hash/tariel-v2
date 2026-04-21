# Roadmap Nacional de NRs

Documento canônico para orientar a expansão do Tariel a partir das Normas Regulamentadoras brasileiras.

Ele não substitui a regra central do produto:

- `NR` é macrocategoria regulatória;
- `familia` é a unidade vendável e operacional;
- `template` é a materialização documental;
- nem toda NR vira um único laudo;
- algumas NRs viram famílias principais, outras viram módulos, trilhas documentais ou governança.

## Base oficial

Como referência regulatória, o projeto passa a usar a lista oficial do Ministério do Trabalho e Emprego:

- página: `Normas Regulamentadoras Vigentes`
- data de referência adotada no projeto: `08/10/2024 15h34`
- universo atual considerado: `NR-1` até `NR-38`
- exceções explícitas: `NR-2` e `NR-27` aparecem como `revogadas`

Fonte oficial:

- `https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes`

## Regra de modelagem

Toda NR nova deve ser classificada antes de qualquer código:

1. `family_with_variants`
   Quando a NR gera laudos principais recorrentes, normalmente com variantes por ativo, escopo ou modalidade.

2. `documental_base`
   Quando a entrega principal é programa, prontuário, plano, laudo documental ou pacote de conformidade.

3. `module_or_annex`
   Quando a NR entra melhor como checklist, anexo técnico, módulo de apoio ou bloco reutilizável.

4. `support_only`
   Quando a NR orienta gate, compliance ou governança, mas não deve virar produto documental isolado.

5. `revogada`
   Quando não existe roadmap de produto ativo para a norma.

## Regra de execução

Nenhuma NR deve entrar no projeto pulando etapas.

Ordem obrigatória por família:

1. classificar a NR e definir as famílias vendáveis;
2. registrar a NR no `nr_programming_registry.json`;
3. criar `family_schema`;
4. criar `laudo_output_seed`;
5. criar `laudo_output_exemplo`;
6. criar `template_master_seed`;
7. profissionalizar o template;
8. publicar no catálogo Admin-CEO;
9. liberar para tenant piloto;
10. homologar com caso real ou sintético forte;
11. só então marcar a família como operacional.

## Ondas canônicas

### Onda 0. Plataforma transversal

Essa onda já está em curso e é pré-condição para o resto:

- Mesa estruturada;
- família canônica;
- catálogo Admin-CEO;
- template profissional em `editor_rico`;
- emissão versionada;
- variantes controladas por família.

Sem isso, abrir dezenas de NRs vira acúmulo de JSON sem produto real.

### Onda 1. Núcleo vendável de inspeção

Primeira expansão fora do escopo atual de `NR13`:

1. `NR-10`
2. `NR-12`
3. `NR-35`
4. `NR-33`
5. `NR-20`
6. consolidar `NR-13` como biblioteca premium

Motivo:

- alta recorrência comercial;
- forte aderência a laudos técnicos;
- boa sinergia com Mesa, evidência e checklist estruturado.

### Onda 2. Verticais setoriais

Depois do núcleo:

1. `NR-18`
2. `NR-22`
3. `NR-29`
4. `NR-30`
5. `NR-31`
6. `NR-32`
7. `NR-34`
8. `NR-36`
9. `NR-37`
10. `NR-38`

Motivo:

- grande especificidade setorial;
- exigem taxonomias próprias e variantes por ambiente operacional.

### Onda 3. Documental, programa e apoio

Entram depois do núcleo e das verticais:

- `NR-1`
- `NR-4`
- `NR-5`
- `NR-6`
- `NR-7`
- `NR-8`
- `NR-9`
- `NR-11`
- `NR-14`
- `NR-15`
- `NR-16`
- `NR-17`
- `NR-19`
- `NR-21`
- `NR-23`
- `NR-24`
- `NR-25`
- `NR-26`

Motivo:

- muitas dessas normas geram mais programas, laudos documentais, pareceres, módulos ou anexos do que uma biblioteca direta de inspeção.

### Onda 4. Governança e exceções

- `NR-2` revogada
- `NR-27` revogada
- `NR-3` e `NR-28` tratadas como apoio, gate ou compliance, não como biblioteca primária de laudos

## Estado atual do projeto

Estado consolidado no projeto:

- `Onda 0` fechada na plataforma transversal;
- `Onda 1` homologada com `NR10`, `NR12`, `NR13`, `NR20`, `NR33` e `NR35`;
- `Onda 2` homologada com as verticais setoriais `NR18`, `NR22`, `NR29`, `NR30`, `NR31`, `NR32`, `NR34`, `NR36`, `NR37` e `NR38`;
- `Onda 3` homologada com a biblioteca documental e de apoio `NR1`, `NR4`, `NR5`, `NR6`, `NR7`, `NR8`, `NR9`, `NR11`, `NR14`, `NR15`, `NR16`, `NR17`, `NR19`, `NR21`, `NR23`, `NR24`, `NR25` e `NR26`;
- `Onda 4` encerrada canonicamente, mantendo `NR-2` e `NR-27` como revogadas e `NR-3` e `NR-28` como apoio/compliance;
- `END` permanece como linha complementar forte já integrada ao produto.

## Como seguir até o final

O projeto deve seguir o registro máquina em:

- `docs/nr_programming_registry.json`

Esse arquivo passa a ser a fonte de verdade do backlog nacional de NRs.

Regras:

- não abrir NR nova fora da onda ativa sem motivo forte;
- não considerar uma NR “coberta” só porque existe um JSON isolado;
- só marcar `implemented_core` quando existir família, template profissional, catálogo, tenant piloto e emissão validada.

## Próxima frente prática

Com as ondas fechadas, a próxima ordem recomendada deixa de ser abrir novas NRs e passa a ser:

1. refino comercial por família e por variante vendável;
2. calibração com material real de mercado e da empresa atendida;
3. homologação fina de linguagem, anexos, tabelas e assinatura técnica;
4. promoção comercial progressiva dos templates já homologados;
5. abertura de bibliotecas especializadas só quando houver nova frente de produto fora do registro atual.

Esse passa a ser o caminho mais forte para transformar o Tariel em biblioteca nacional de laudos técnicos com produto vendável de verdade, sem perder coerência arquitetural.
