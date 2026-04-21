# Matriz Comercial de Planos Tariel

Documento de referencia para desenho comercial dos planos do Tariel.

Objetivo:

- definir uma divisao de assinatura simples de vender;
- separar o que e `volume`, `governanca`, `catalogo` e `customizacao`;
- transformar limites tecnicos em linguagem comercial;
- preparar a base para `entitlements por contrato`, `bundles comerciais` e `release channels`.

Data de referencia: `2026-04-10`.

Complementa:

- `web/docs/prontidao_comercial_primeiro_cliente.md`
- `web/docs/waves_a_b_c_produto_vendavel.md`
- `web/docs/catalogo_laudos_operating_model.md`
- `web/docs/mobile_review_operating_model.md`
- `web/docs/memoria_operacional_governada.md`

## Leitura executiva

Recomendacao de lineup comercial:

- `Tariel Go`
- `Tariel Plus`
- `Tariel Scale`
- `Tariel Enterprise`

Se a marca quiser manter `Tariel Plus+`, isso e possivel. Ainda assim, para venda B2B, `Scale` comunica melhor a ideia de operacao maior e reduz ruido visual no catalogo.

A regra central e:

- `Go` entra com operacao governada e volume baixo;
- `Plus` amplia operacao e libera mais produtividade;
- `Scale` abre automacao e governanca mais forte;
- `Enterprise` vira negociacao consultiva com customizacao e contrato proprio.

## Principio de desenho dos planos

O cliente nao compra `tokens`, `tabelas` ou `red flags`.

O cliente compra:

- capacidade operacional;
- nivel de governanca;
- quantidade de familias e variantes;
- confianca documental;
- autonomia da operacao;
- suporte e customizacao.

Por isso, os planos devem ser montados em 4 blocos.

### 1. Uso

Controla capacidade mensal e custo variavel.

- emissoes por mes
- creditos de IA por mes
- retencao documental
- armazenamento e anexos

### 2. Operacao

Controla a quantidade de pessoas e papeis usando o sistema.

- admins cliente
- inspetores
- revisores da Mesa
- signatarios governados

### 3. Catalogo

Controla o quanto do produto o cliente pode operar.

- familias ativas
- variantes ativas
- bundles comerciais
- integracoes

### 4. Governanca premium

Controla profundidade de qualidade, autonomia e sofisticacao.

- review mobile
- mobile autonomous
- anexo pack
- emissao oficial
- verificacao publica
- memoria operacional
- memoria por familia
- suporte prioritario
- customizacao

## Regra comercial importante

Nao vender `tokens brutos de IA` como frente principal.

O recomendavel e vender:

- `creditos IA mensais`
- ou `capacidade mensal de processamento`

Motivo:

- o cliente entende resultado, nao infraestrutura;
- os modelos podem mudar ao longo do tempo;
- voce preserva flexibilidade tecnica;
- o comercial fica menos fragil quando houver troca de modelo ou custo por chamada.

No contrato interno, ainda faz sentido mapear isso para:

- consumo de IA
- limites de uso por tenant
- throttling
- overruns e excedentes

## O que deveria existir em todos os planos pagos

Nao vale esconder o nucleo de confianca do produto atras de paywall.

Todos os planos pagos deveriam ter:

- emissao de PDF final;
- QR Code e hash publico de verificacao;
- coverage map basico;
- revisao por bloco;
- trilha auditavel;
- emissao oficial basica;
- anexo pack basico;
- pelo menos um signatario governado;
- acesso ao catalogo governado dentro do limite contratado.

Esses itens ajudam o cliente a perceber o Tariel como produto serio desde a entrada.

## Diferenciacao recomendada entre planos

Os diferenciais devem ficar concentrados em:

- volume mensal;
- quantidade de usuarios;
- familias e variantes ativas;
- integracoes;
- nivel de automacao mobile;
- profundidade da memoria governada;
- suporte;
- customizacao.

Evitar diferenciar por:

- numero de red flags;
- numero de regras;
- numero de templates "internos";
- quantidade de campos tecnicos expostos.

Isso e tecnico demais para virar eixo comercial principal.

## Matriz proposta

### Tariel Go

Plano de entrada para piloto pago, cliente menor ou operacao inicial acompanhada.

Perfil:

- cliente que precisa começar a operar sem comprar uma estrutura grande;
- bom para primeiro contrato e descoberta controlada;
- venda assistida, com mais governanca e menos liberdade.

Entitlements recomendados:

- `50 emissoes/mes`
- `creditos IA baixos`
- `2 admins cliente`
- `5 inspetores`
- `2 revisores`
- `1 signatario governado`
- `3 familias ativas` ou `1 bundle`
- `8 variantes ativas`
- `0 integracoes externas`
- `retencao de 30 dias`

Recursos incluidos:

- catalogo governado
- Mesa Avaliadora
- review mobile nas familias elegiveis
- coverage map
- revisao por bloco
- refazer_inspetor
- QR/hash publico
- emissao oficial basica
- anexo pack basico
- memoria operacional basica

Recursos restritos:

- sem autonomia mobile ampla
- sem bundles premium multiplos
- sem customizacao de template por cliente
- sem integracoes enterprise
- sem suporte prioritario forte

Mensagem comercial:

- `entra rapido, opera com seguranca e comeca a padronizar a emissao`

### Tariel Plus

Plano para cliente que ja esta rodando operacao recorrente e quer mais folego sem entrar em negociacao enterprise.

Perfil:

- cliente que ja validou o fluxo;
- precisa abrir mais familias, mais usuarios e um pouco mais de autonomia;
- ainda dentro de uma esteira comercial padrao.

Entitlements recomendados:

- `150 emissoes/mes`
- `creditos IA medios`
- `3 admins cliente`
- `10 inspetores`
- `3 revisores`
- `3 signatarios governados`
- `8 familias ativas` ou `2 bundles`
- `20 variantes ativas`
- `1 integracao`
- `retencao de 90 dias`

Recursos incluidos:

- tudo do `Tariel Go`
- anexo pack mais forte
- preview premium
- memoria operacional consolidada
- memoria por familia em nivel basico
- variantes premium selecionadas
- suporte melhorado

Recursos restritos:

- autonomia mobile ainda limitada a familias elegiveis
- sem customizacao profunda por cliente
- sem rollout comercial muito fino por contrato complexo

Mensagem comercial:

- `opera mais, revisa melhor e ganha produtividade sem perder governanca`

### Tariel Scale

Plano para cliente com operacao maior, mais recorrencia e necessidade de acelerar com controle.

Perfil:

- cliente com mais volume, mais equipe e mais maturidade operacional;
- precisa usar mobile com mais autonomia onde a policy permitir;
- comeca a exigir governanca premium de verdade.

Entitlements recomendados:

- `400 emissoes/mes`
- `creditos IA altos`
- `5 admins cliente`
- `25 inspetores`
- `8 revisores`
- `8 signatarios governados`
- `15 familias ativas` ou `4 bundles`
- `40 variantes ativas`
- `3 integracoes`
- `retencao de 180 dias`

Recursos incluidos:

- tudo do `Tariel Plus`
- `mobile_autonomous` em familias elegiveis
- memoria operacional forte
- memoria por familia ativa
- governanca de emissao mais refinada
- anexo pack premium
- suporte prioritario
- acesso a features em `limited_release`

Recursos restritos:

- ainda sem customizacao livre e ilimitada;
- personalizacao continua dentro de guardrails do catalogo;
- projetos sob medida grandes ficam para `Enterprise`.

Mensagem comercial:

- `escala a operacao com mais autonomia e mais inteligencia governada`

### Tariel Enterprise

Plano de negociacao consultiva para cliente estrategico, complexo ou com demanda forte de customizacao.

Perfil:

- cliente com processo proprio, exigencia juridica alta ou operacao grande;
- quer bundles exclusivos, integracoes, templates ajustados e politica mais fina;
- normalmente entra com onboarding mais intenso e contrato negociado.

Entitlements recomendados:

- emissao mensal sob contrato
- creditos IA sob contrato
- usuarios sob contrato
- familias e variantes sob contrato
- integracoes customizadas
- retencao sob contrato

Recursos incluidos:

- tudo do `Tariel Scale`
- customizacao de templates e overlays
- bundles dedicados
- politicas por tenant mais refinadas
- onboarding forte
- SLA
- suporte prioritario maximo
- canal de evolucao dedicada
- roadmap conjunto em casos acordados
- configuracao setorial e documental mais profunda

Mensagem comercial:

- `produto governado com adaptacao de alto nivel para a operacao do cliente`

## Tabela resumida

| Eixo | Tariel Go | Tariel Plus | Tariel Scale | Tariel Enterprise |
| --- | --- | --- | --- | --- |
| Emissoes/mes | 50 | 150 | 400 | sob contrato |
| Creditos IA | baixo | medio | alto | sob contrato |
| Admins cliente | 2 | 3 | 5 | sob contrato |
| Inspetores | 5 | 10 | 25 | sob contrato |
| Revisores | 2 | 3 | 8 | sob contrato |
| Signatarios | 1 | 3 | 8 | sob contrato |
| Familias ativas | 3 | 8 | 15 | sob contrato |
| Variantes ativas | 8 | 20 | 40 | sob contrato |
| Integracoes | 0 | 1 | 3 | sob contrato |
| Retencao | 30 dias | 90 dias | 180 dias | sob contrato |
| Review mobile | parcial | sim | sim | sim |
| Mobile autonomous | nao | restrito | sim, elegivel | sob desenho |
| Memoria por familia | nao | basica | forte | forte + customizada |
| Suporte prioritario | nao | moderado | sim | maximo |
| Customizacao | nao | muito limitada | limitada | sim |

## Bundles comerciais recomendados

Em vez de vender somente familia solta, o Tariel deve poder vender bundles.

Bundles sugeridos:

- `NR13 Core`
- `NR10 Eletrica`
- `NR35 Altura`
- `NR33 Espaco Confinado`
- `Industrial Safety Pack`
- `Programas Legais SST`

Uso comercial sugerido:

- `Go`: 1 bundle ou ate 3 familias soltas
- `Plus`: ate 2 bundles
- `Scale`: ate 4 bundles
- `Enterprise`: bundles sob contrato e bundles exclusivos

## Release channels recomendados

Os canais de release ajudam a controlar rollout comercial e tecnico.

### Pilot

Uso:

- cliente piloto
- familias novas
- features ainda em observacao

Regra:

- menor abertura comercial
- maior governanca
- mais acompanhamento

### Limited release

Uso:

- clientes selecionados
- familias maduras, mas ainda nao generalizadas
- features premium sob observacao controlada

Regra:

- rollout progressivo
- acompanhamento mais leve que `pilot`
- bom para `Plus` e `Scale`

### General release

Uso:

- ofertas maduras
- bundles principais
- familias consolidadas

Regra:

- caminho comercial padrao
- menor atrito operacional

## O que entra em `entitlements por contrato`

Para o sistema, o contrato deveria controlar pelo menos:

- emissoes mensais
- admins cliente maximos
- inspetores maximos
- revisores maximos
- variantes ativas maximas
- integracoes maximas
- familias ou bundles liberados
- recursos premium incluidos

Recursos premium que fazem sentido como feature flag contratual:

- `advanced_preview`
- `anexo_pack`
- `family_memory`
- `governed_signatories`
- `mobile_autonomous`
- `mobile_review`
- `official_issue`
- `operational_memory`
- `priority_support`
- `public_verification`

## O que deve subir de plano

### Sinais para sair de Go e ir para Plus

- cliente atingindo limite de emissao;
- precisa abrir mais familias;
- ja exige mais de 1 ou 2 revisores;
- quer mais preview, memoria e produtividade.

### Sinais para sair de Plus e ir para Scale

- operacao com varios inspetores em paralelo;
- necessidade de autonomia mobile;
- maior uso de memoria por familia;
- comeco de integracoes e automacoes mais serias.

### Sinais para sair de Scale e ir para Enterprise

- pedido de customizacao de template;
- exigencia de SLA;
- integracao fora do padrao;
- bundles exclusivos;
- politica contratual muito especifica;
- governanca por tenant bem fora do default.

## O que nao prometer no Go

Para proteger margem e expectativa:

- nao prometer customizacao sob demanda;
- nao prometer autonomia total no mobile;
- nao prometer integracoes enterprise;
- nao prometer volume alto de IA sem limite;
- nao prometer evolucao dedicada de template por cliente sem contrapartida comercial.

## Estrategia de precificacao

O preco deve crescer mais por:

- governanca;
- automacao;
- capacidade;
- customizacao.

E menos por:

- detalhe tecnico isolado;
- numero de telas;
- nomenclatura interna do motor.

Regra pratica:

- `Go` vende entrada e seguranca;
- `Plus` vende produtividade;
- `Scale` vende autonomia com controle;
- `Enterprise` vende adaptacao e prioridade.

## Recomendacao final

Se o objetivo for vender com clareza e escalar com menos confusao, a divisao recomendada e:

- `Tariel Go`
- `Tariel Plus`
- `Tariel Scale`
- `Tariel Enterprise`

Se a marca quiser manter o nome `Tariel Plus+`, a estrutura comercial acima continua valida. A unica mudanca seria o nome da terceira camada.

## Decisao objetiva

- `sim`, vale ter 4 planos.
- `nao`, nao vale vender por `tokens` como linguagem principal.
- `sim`, vale limitar familias, variantes, usuarios, emissoes, integracoes e recursos premium.
- `sim`, `Enterprise` deve ficar como negociacao consultiva com maior preco e maior flexibilidade.

## Proximo passo recomendado

Transformar esta matriz em:

- tabela oficial de `entitlements por plano`;
- bundles oficiais do catalogo;
- politica de upgrade e excedente;
- copy comercial para site, proposta e contrato.
