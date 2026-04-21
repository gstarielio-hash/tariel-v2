# Tariel Context

Atualizado em `2026-04-09`.

## Objetivo

Este é o documento geral de contexto do projeto Tariel.

Ele existe para responder, de forma única e direta:

- o que o produto é;
- como o fluxo funciona;
- quem governa o quê;
- como templates, famílias, tenants, IA, Mesa e PDF se relacionam;
- qual é o estado atual do programa nacional.

Este arquivo deve ser lido antes de decisões estruturais novas.

## Tese central do produto

O Tariel não é um chat que produz PDF.

O Tariel é uma plataforma governada de emissão de laudos e documentos técnicos, em que:

- a `NR` é a macrocategoria regulatória;
- a `família` é a entrega real vendável;
- a IA organiza e preenche o caso em `JSON canônico`;
- a Mesa revisa e valida;
- o renderer materializa o documento final;
- o PDF é saída versionada, não fonte de verdade.

## Arquitetura documental

Fluxo correto:

`family_schema -> master template -> family overlay -> laudo_output -> renderer -> PDF final`

Camadas:

### 1. `family_schema`

Contrato técnico da família.

Define:

- campos e seções obrigatórias;
- política de evidência;
- regras de bloqueio;
- conclusão permitida;
- dados derivados;
- comportamento da família no catálogo.

### 2. `master template`

Template mestre por tipo documental.

Define:

- estrutura do documento;
- ordem das seções;
- linguagem visual base;
- cabeçalho e rodapé;
- tokens documentais;
- placeholders semânticos.

### 3. `family overlay`

Especialização da família sobre o mestre.

Define:

- seções específicas;
- checklist técnico;
- tabelas repetíveis;
- campos da família;
- ajustes de linguagem;
- exigências documentais particulares.

### 4. `laudo_output`

Fonte de verdade do caso revisado.

Ele concentra:

- dados factuais;
- evidências aceitas;
- checklist preenchido;
- não conformidades;
- recomendações;
- conclusão técnica;
- anexos e referências.

### 5. `renderer`

Camada de materialização.

Recebe:

- template governado;
- branding do tenant;
- controle documental;
- `laudo_output`.

Entrega:

- documento renderizado;
- PDF final;
- snapshot auditável da emissão.

## Hierarquia oficial de papéis

Ordem correta:

1. `Admin-CEO`
2. `Admin Cliente`
3. `Mesa Avaliadora`
4. `Inspetor`

## Regra de autoridade

- `Admin-CEO` governa `Admin Cliente`.
- `Admin Cliente` governa `Mesa Avaliadora` e `Inspetor`.
- `Mesa Avaliadora` e `Inspetor` não governam perfis administrativos.

## Regra de criação de usuários

- `Admin-CEO` cria o tenant administrativo.
- `Admin-CEO` cria o `Admin Cliente`.
- `Admin Cliente` nunca cria outro `Admin Cliente`.
- `Admin Cliente` cria apenas usuários de `Mesa Avaliadora` e `Inspetor` do próprio tenant.
- criação de tenant novo e de novo `Admin Cliente` sempre fica no nível `Admin-CEO`.

## Governança de templates e catálogo

Decisão oficial:

- template estrutural fica no poder do `Admin-CEO`;
- `Admin Cliente` não cria template técnico;
- `Mesa Avaliadora` não cria template;
- `Inspetor` não cria template;
- tenant consome somente o que foi liberado pelo `Admin-CEO`.

O `Admin-CEO` governa:

- famílias técnicas;
- `family_schema`;
- templates mestres;
- overlays por família;
- versões;
- branding permitido;
- liberação por tenant;
- homologação;
- rollout por contrato/assinatura.

O `Admin Cliente` governa:

- usuários do próprio tenant;
- branding leve permitido;
- operação do tenant;
- escolha entre templates já liberados;
- solicitação de customização à Tariel.

O `Admin Cliente` não governa:

- estrutura técnica do documento;
- checklist técnico;
- política mínima de evidência;
- regras de conclusão;
- publicação de template.

## Regra de liberação por tenant

Nada entra automaticamente no tenant.

O fluxo correto é:

1. `Admin-CEO` define catálogo oficial.
2. `Admin-CEO` habilita famílias para o tenant.
3. `Admin-CEO` habilita templates para o tenant conforme contrato, assinatura ou pacote.
4. `Admin Cliente` passa a enxergar somente esse subconjunto.
5. `Mesa Avaliadora` e `Inspetor` operam somente sobre o subconjunto liberado.

Resumo:

- o tenant não vê a biblioteca inteira;
- o tenant não publica template;
- o tenant não escolhe algo fora do que foi liberado.

## Regra de liberação por contrato e assinatura

A liberação não deve acontecer apenas no nível do tenant.

Ela deve respeitar também:

- contrato vigente;
- plano ou assinatura;
- pacote comercial adquirido;
- variantes realmente compradas.

Regra prática:

- o tenant pode existir sem enxergar toda a biblioteca;
- a família pode estar disponível para um tenant e indisponível para outro;
- a variante comercial pode estar contratada mesmo dentro da mesma família;
- o template final visível precisa respeitar esse recorte comercial.

## Separação entre família técnica e variante comercial

A família técnica não é o mesmo objeto que a variante comercial.

Exemplo:

- família: `nr13_inspecao_vaso_pressao`
- variantes comerciais possíveis: `inicial`, `periodica`, `extraordinaria`, `documental`, `com_end`

Regra:

- a família governa a estrutura técnica principal;
- a variante governa o produto vendido;
- o tenant contrata e recebe variantes, não apenas famílias abstratas.

## Matriz de compatibilidade

O sistema deve respeitar uma matriz explícita:

`familia x variante x template x tenant`

Isso significa:

- nem toda variante serve para toda família;
- nem todo template serve para toda variante;
- nem todo tenant recebe todas as combinações;
- a emissão só deve usar combinações homologadas.

## Fluxo operacional do caso até o PDF

Este é o fluxo oficial:

1. `Admin-CEO` libera famílias e templates para o tenant.
2. `Admin Cliente` cria os usuários de `Mesa Avaliadora` e `Inspetor`.
3. `Inspetor` abre o caso dentro de uma família habilitada.
4. o chat/IA organiza a inspeção, consolida evidências e monta o draft do caso.
5. a `Mesa Avaliadora` revisa, abre pendências, valida evidências e fecha a decisão técnica.
6. com o caso validado, o laudo é preparado em cima do template governado selecionado para aquela família/tenant.
7. a IA da Mesa preenche o `laudo_output` canônico com base no caso validado.
8. o renderer materializa o documento final.
9. o sistema gera o PDF completo para entrega ao responsável.

Regra importante:

- o PDF só nasce depois da validação operacional do caso;
- a fonte de verdade é o `laudo_output`, não o PDF;
- o template usado já precisa ter sido governado e liberado antes.

## Travas estruturais do caso

### `family lock`

Depois que a família do caso for confirmada ou aprovada pela Mesa, ela não deve mudar livremente.

Mudança posterior de família:

- só com evento auditado;
- com ator identificado;
- com motivo explícito;
- com revalidação do caso.

### `template lock`

No momento da emissão, o caso deve travar:

- `template_id`
- versão do template
- overlay da família
- snapshot de branding
- snapshot do `laudo_output`

Sem esse lock, reemissão, auditoria e comparação histórica ficam frágeis.

## Estados formais do caso

Estados recomendados:

- `rascunho`
- `em_coleta`
- `em_revisao_mesa`
- `pendente_inspetor`
- `aprovado_para_emissao`
- `emitido`
- `reaberto`
- `cancelado`

Regra:

- mudança de estado relevante deve ser auditável;
- emissão só pode ocorrer a partir de `aprovado_para_emissao`.

## Estados formais da evidência

Estados recomendados:

- `coletada`
- `em_analise`
- `aceita`
- `rejeitada`
- `substituida`

Regra:

- evidência aceita entra no `laudo_output`;
- evidência rejeitada não deve sustentar conclusão final;
- substituição deve preservar histórico.

## Hard gates de emissão

O sistema não deve emitir PDF quando houver:

- campo crítico ausente;
- checklist obrigatório incompleto;
- evidência mínima obrigatória ausente;
- conflito grave entre evidência e conclusão;
- pendência crítica em aberto;
- família indefinida;
- template incompatível com a variante;
- caso fora do estado `aprovado_para_emissao`.

## Override auditado

Override é exceção controlada.

Só deve existir quando:

- perfil autorizado o executa;
- motivo fica registrado;
- ator fica registrado;
- data e hora ficam registradas;
- diff curto ou impacto da decisão fica registrado.

Override não deve apagar a trilha anterior.

## Reemissão controlada

Depois de emitido, o documento não deve ser sobrescrito silenciosamente.

Regra:

- mudança relevante gera nova revisão;
- revisão nova gera novo snapshot;
- PDF antigo continua auditável;
- comparação entre revisões deve continuar possível.

## Limites de branding

Branding do tenant pode alterar:

- logo;
- razão social;
- dados institucionais;
- tema autorizado;
- elementos visuais permitidos.

Branding do tenant não pode alterar:

- checklist técnico;
- regra de conclusão;
- evidência mínima;
- ordem estrutural obrigatória;
- campos críticos exigidos pela família.

## Papel da Mesa Avaliadora

A `Mesa Avaliadora` não é mais autora de template.

Seu papel é:

- revisar tecnicamente o draft;
- validar evidências;
- abrir e fechar pendências;
- corrigir inconsistências;
- aprovar ou rejeitar emissão;
- operar sobre famílias e templates já governados.

Ela atua sobre:

- caso;
- evidência;
- conclusão;
- validação operacional.

Ela não atua sobre:

- criação livre de template;
- criação de catálogo;
- liberação estrutural por tenant.

Regra adicional:

- a Mesa não deve reconstruir o laudo inteiro manualmente como fluxo normal;
- a Mesa revisa, corrige, valida e decide;
- autoria estrutural do documento continua fora da Mesa.

## Papel do Inspetor

O `Inspetor` é responsável por:

- coletar evidências;
- alimentar o caso;
- responder pendências;
- complementar fatos;
- executar a coleta de campo.

Ele não decide catálogo, não publica template e não governa emissão.

## Ciclo de vida do catálogo

Cada família, variante e template deveria seguir estados claros:

- `draft`
- `internal_review`
- `homologated`
- `released`
- `deprecated`
- `revoked`

Regra:

- só itens `released` entram em tenant produtivo;
- itens `deprecated` continuam auditáveis, mas não são primeira opção nova;
- itens `revoked` não podem ser usados para emissão nova.

## Política de validade e próxima inspeção

Algumas famílias exigem validade formal ou próxima ação obrigatória.

Exemplos típicos:

- `NR35`
- `NR13`
- permissões controladas
- documentos com inspeção periódica

Regra:

- quando a família exigir, o documento precisa carregar validade, próxima inspeção ou próxima ação;
- ausência desse dado deve bloquear emissão se a política da família assim exigir.

## Branding e identidade do cliente

A estrutura técnica do documento não pertence ao cliente.

O que pertence ao cliente é a camada de branding controlado:

- logo;
- razão social;
- nome exibido;
- CNPJ;
- contato;
- unidade/localização;
- aviso de confidencialidade;
- status de assinatura;
- elementos visuais liberados.

No runtime isso entra como `tenant_branding`.

## Controle documental

Além do branding, o runtime injeta `document_control`, com campos como:

- código do documento;
- revisão;
- título;
- tipo mestre;
- status de assinatura;
- emissão;
- identificadores de verificação.

## Biblioteca mestre atual

Tipos mestres definidos hoje:

- `inspection_conformity`
- `risk_analysis`
- `integrity_specialized`
- `controlled_permit`
- `technical_dossier`
- `program_plan`

Estado atual:

- contrato documental criado;
- branding por tenant integrado ao runtime;
- placeholders documentais padronizados;
- primeiro template mestre base criado: `inspection_conformity`.

## Programa nacional de NRs

Estado atual:

- `wave_0` fechada
- `wave_1` homologada
- `wave_2` homologada
- `wave_3` homologada
- `wave_4` fechada como governança das exceções

Resumo prático:

- o programa nacional planejado foi fechado;
- `NR-2` e `NR-27` seguem fora por revogação;
- `NR-28` está tratado como suporte/governança, não biblioteca vendável principal;
- o foco atual não é abrir novas ondas;
- o foco atual é refino de produto, biblioteca premium, variantes e material real.

## O que está consolidado no código

Hoje já está consolidado:

- runtime canônico por família;
- persistência do `laudo_output` antes do PDF;
- emissão por template governado;
- leitura estruturada pela Mesa;
- homologação por ondas;
- contrato documental e biblioteca mestre base;
- governança de templates separada da operação da Mesa.

## Regras que não podem ser quebradas

- a IA não preenche PDF bruto diretamente;
- template não pode ser criado livremente pelo tenant;
- `Admin Cliente` não cria outro `Admin Cliente`;
- `Mesa Avaliadora` não vira autora de template;
- branding não pode alterar a estrutura técnica do documento;
- PDF final não é fonte de verdade;
- emissão não deve acontecer com caso crítico pendente.

## Prioridades atuais

### 1. Biblioteca premium de templates

- transformar benchmarks reais em templates mestres melhores;
- manter casca profissional e estrutura reutilizável;
- derivar overlays por família.

### 2. Variantes e produto comercial

- variantes por família;
- ofertas comerciais por variante;
- liberação clara por contrato;
- catálogo comercial mais forte.

### 3. Material real

- ingestão de documentos reais;
- calibração da linguagem;
- ajuste fino de seções, anexos e evidências;
- melhoria da qualidade visual do PDF final.

### 4. UX de produto

- acabamento premium no frontend;
- melhor leitura para `Admin-CEO`, `Admin Cliente`, `Mesa` e `Inspetor`;
- biblioteca e preview documental mais claros.

## Ideias adicionais recomendadas

As ideias abaixo ainda não são contrato oficial do produto, mas fazem sentido como evolução forte do Tariel.

### 1. `fit score` de família e variante

Antes da Mesa assumir a decisão final, o sistema pode calcular um score de aderência entre:

- família sugerida;
- variante sugerida;
- evidências presentes;
- vocabulário do caso;
- objeto técnico identificado.

Uso prático:

- score baixo força revisão antecipada da Mesa;
- score alto acelera triagem;
- discrepância vira alerta auditável.

### 2. `entitlements` por contrato

Além de liberar famílias e templates, o contrato pode controlar:

- quantidade de usuários por papel;
- quantidade de emissões;
- acesso a variantes premium;
- acesso a recursos avançados;
- limites de operação do tenant.

### 3. QR Code ou hash público de verificação

Cada PDF emitido pode carregar:

- identificador único;
- hash de verificação;
- QR Code para conferência pública.

Isso fortalece:

- autenticidade documental;
- rastreabilidade;
- confiança comercial.

### 4. `coverage map` de evidência

Antes da emissão, o sistema pode mostrar um mapa visual de cobertura:

- o que a família exige;
- o que foi coletado;
- o que foi aceito;
- o que ainda falta.

Isso melhora:

- trabalho do inspetor;
- revisão da Mesa;
- clareza do hard gate.

### 5. Revisão por bloco

Em vez de aprovar o laudo apenas como um bloco único, a Mesa pode revisar por seções:

- identificação;
- metodologia;
- checklist;
- evidências;
- conclusão;
- anexos.

Isso permite:

- revisão mais objetiva;
- reabertura parcial;
- diffs mais claros.

### 6. `red flags` por família

Algumas condições devem forçar comportamento mais rígido.

Exemplos:

- não conformidade crítica em `NR35`;
- ausência documental grave em `NR13`;
- falta de autorização em documento controlado por permissão.

Uso prático:

- impedir aprovação simplificada;
- elevar revisão obrigatória;
- restringir certos resultados finais.

### 7. `clone from last inspection`

Para casos periódicos, o sistema pode abrir o novo caso usando a última inspeção como base:

- identificação do ativo;
- anexos recorrentes;
- referências anteriores;
- estrutura do caso;
- dados estáveis.

Mas:

- sem herdar automaticamente conclusão;
- sem reaproveitar evidência como se fosse nova;
- exigindo revalidação do que mudou.

### 8. `renewal engine`

Famílias com validade ou próxima inspeção podem gerar:

- data de vencimento;
- fila de renovação;
- alertas operacionais;
- oportunidade comercial automática.

### 9. `anexo pack` automático

Além do PDF principal, o sistema pode gerar pacote anexado com:

- ART/RRT;
- certificados;
- fotos numeradas;
- documentos-base;
- relatórios auxiliares;
- índices de anexo.

### 10. Signatários governados

O tenant pode ter cadastro controlado de signatários aprovados, com:

- nome;
- função;
- registro profissional;
- validade;
- famílias compatíveis;
- tenant compatível.

### 11. `release channels` do catálogo

Famílias, variantes e templates podem circular por canais:

- `pilot`
- `limited_release`
- `general_release`

Isso ajuda em:

- rollout progressivo;
- validação com clientes-piloto;
- rollback mais seguro.

### 12. `tenant policy profile`

Cada tenant pode operar sob um perfil de política configurado pela Tariel, por exemplo:

- mais evidências obrigatórias;
- revisão humana mais rígida;
- override mais restrito;
- anexos mínimos maiores.

### 13. Diff entre emissões

Revisões sucessivas do laudo podem exibir:

- o que mudou no `laudo_output`;
- o que mudou no template;
- o que mudou na conclusão;
- o que mudou entre revisões emitidas.

### 14. Biblioteca de linguagem por setor

Sem mexer na estrutura técnica, o sistema pode aplicar vocabulário controlado por setor:

- alimentos;
- mineração;
- naval;
- saúde;
- rural;
- óleo e gás.

### 15. Pacotes comerciais

Em vez de vender apenas famílias soltas, o produto pode oferecer bundles, como:

- `NR13 Core`
- `NR35 Altura`
- `Industrial Safety Pack`
- `Programas Legais SST`

## Ideias adicionais prioritárias

Se fosse necessário escolher as próximas ideias com maior retorno, a ordem sugerida seria:

1. QR Code ou hash público de verificação
2. `coverage map` de evidência
3. revisão por bloco
4. `clone from last inspection`
5. `entitlements` por contrato

## Arquivos de apoio mais importantes

Leitura recomendada complementar:

- `README.md`
- `web/docs/preenchimento_laudos_canonico.md`
- `web/docs/catalog_document_contract.md`
- `web/docs/portfolio_nacional_nrs_provisionamento.md`
- `docs/nr_programming_registry.json`
- `docs/master_templates/library_registry.json`
- documentos de homologação das ondas

Fora do repositório, no Desktop:

- `/home/gabriel/Área de trabalho/CHECKPOINT_PRINCIPAL_TARIEL_2026-04-09.md`
- `/home/gabriel/Área de trabalho/CURADORIA_MODELOS_REFERENCIA_TARIEL_2026-04-09.md`
- `/home/gabriel/Área de trabalho/GOVERNANCA_DE_TEMPLATES_E_LIBERACAO_TARIEL.md`

## Regra de retomada

Se uma sessão futura precisar entender o Tariel rapidamente, ler nesta ordem:

1. este arquivo;
2. `web/docs/catalog_document_contract.md`;
3. `web/docs/preenchimento_laudos_canonico.md`;
4. `docs/nr_programming_registry.json`;
5. documentos de homologação das ondas;
6. checkpoint principal no Desktop.

## Decisão final deste contexto

O Tariel saiu da fase de provar arquitetura e entrou na fase de produto governado, biblioteca premium e operação vendável.

O centro do sistema agora é:

- catálogo governado;
- papéis bem separados;
- `JSON` canônico como fonte de verdade;
- template mestre como materialização;
- Mesa como revisão;
- PDF como entrega final controlada.
