# Padrao de Base Oficial para Familias NR

## Objetivo

Padronizar o endurecimento das familias NR para que cada template, payload canonico e QA documental partam de base normativa oficial pesquisada, e nao apenas de inferencia interna.

## Regra de Ouro

Toda implementacao ou reforco de familia NR deve distinguir duas camadas:

1. Requisito normativo objetivo, ancorado em fonte oficial vigente.
2. Estrutura editorial da Tariel, usada para transformar esses requisitos em documento comercial, operacional e auditavel.

## Hierarquia de Fontes

1. Texto oficial vigente da NR no `gov.br` do Ministerio do Trabalho e Emprego.
2. Manuais oficiais de interpretacao, guias tecnicos e materiais oficiais publicados em `gov.br`, `Fundacentro` ou orgao oficial equivalente.
3. Normas tecnicas ou anexos expressamente citados pela NR, apenas quando houver acesso oficial ou licenciado.

## Como aplicar no projeto

- Registrar no `family_schema` um bloco `normative_basis`.
- Informar as fontes oficiais usadas, com URL e itens/ancoras relevantes.
- Mapear cada exigencia usada para os campos do payload, checklist, documentacao e conclusao.
- Declarar explicitamente quando uma secao do template for apenas decisao editorial da Tariel.
- Ao tocar uma familia existente, retrofitar sua base normativa no mesmo pacote.
- Rodar `python3 scripts/sync_nr_official_basis.py` quando novas familias `NR` entrarem no catalogo, para impedir schema sem fonte oficial registrada.
- Usar `python3 scripts/check_nr_official_updates.py` em modo manual para auditoria do admin/CEO antes de qualquer acao sobre templates oficiais.

## Operacao recomendada agora

- deixar o monitoramento oficial preparado, mas com gatilho manual;
- revisar pessoalmente qualquer mudanca detectada nas fontes oficiais;
- so depois decidir se uma familia precisa de endurecimento, ajuste de checklist ou revisao de template.

## Governanca de atualizacao oficial

- O monitoramento de fontes oficiais pode ser automatizado para detectar mudancas, mas a aplicacao no produto nao deve ser automatica nesta fase.
- Nenhum template, payload, checklist ou family schema deve ser alterado automaticamente so porque uma fonte oficial mudou.
- O fluxo padrao e: detectar mudanca oficial, gerar diff tecnico, revisar manualmente como admin/CEO e so depois decidir se vira pacote de implementacao.
- Agendamento semanal pode existir no futuro apenas para observabilidade, nunca para publicar alteracoes sozinho.
- Enquanto o sistema nao tiver uma camada madura de aprovacao humana e trilha de auditoria especifica para isso, manter o workflow manual.

## O que nao fazer

- Nao inventar requisito obrigatorio sem ancora oficial.
- Nao tratar manual comercial, blog ou material de treinamento privado como fonte primaria.
- Nao preencher clausulas de norma tecnica externa que nao foi efetivamente acessada.
- Nao mascarar inferencia editorial como se fosse texto da NR.
- Nao atualizar template oficial automaticamente sem revisao humana do admin responsavel.

## Minimo esperado por familia

Cada familia endurecida deve deixar claro:

- objetivo e escopo normativo usados;
- evidencias e documentos obrigatorios ou fortemente exigidos pela base oficial;
- checklist tecnico principal derivado da norma;
- criterio de conclusao e de recomendacao;
- aviso de que headings, ordem e acabamento do template sao estrutura editorial da Tariel.

## Exemplo pratico

Na `NR10`, o pacote deve partir do texto oficial da norma para itens como:

- `10.2.4`: conteudo minimo do Prontuario de Instalacoes Eletricas;
- `10.2.8.2`: priorizacao da desenergizacao como medida coletiva;
- `10.3.1`: recursos para impedimento de reenergizacao no projeto;
- `10.4.4`: inspecao e controle periodico dos sistemas de protecao;
- `10.5.1`: sequencia minima para considerar a instalacao desenergizada.

O template final pode reorganizar isso em secoes como identificacao, checklist tecnico, evidencias, documentacao e conclusao, desde que a base normativa continue rastreavel.
