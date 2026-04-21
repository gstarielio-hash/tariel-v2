# Roadmap Premium de Memoria Operacional

Documento de decisao para transformar a memoria operacional governada em uma frente premium de produto, sem abrir uma frente grande demais cedo demais.

Complementa:

- `web/docs/memoria_operacional_governada.md`
- `web/docs/wave_1_memoria_operacional_governada.md`
- `web/docs/mobile_review_operating_model.md`
- `web/docs/direcao_operacional_mesa.md`
- `web/docs/waves_a_b_c_produto_vendavel.md`
- `docs/backlog_evolucao_produto_governado.md`

## O que significa "premium" no Tariel

No Tariel, "premium" nao e:

- colocar mais IA generica no fluxo;
- deixar a Mesa virar digitadora de laudo;
- fazer autoaprendizado sem governanca;
- criar dashboards bonitos sem aumentar confianca operacional.

"Premium" significa:

- prevenir erro de campo antes da Mesa;
- guiar o inspetor com clareza sobre o que falta;
- mostrar para a Mesa uma previa tecnicamente explicada;
- acumular memoria forte a partir de casos aprovados;
- detectar irregularidade operacional cedo;
- explicar por que uma sugestao existe;
- reduzir retrabalho e aumentar padronizacao ao longo do tempo.

## Tese de produto

Se o Tariel quiser parecer um sistema realmente especialista, ele precisa transmitir tres sensacoes:

1. o inspetor sente que o sistema sabe conduzir a captura;
2. a Mesa sente que esta revisando com memoria, nao do zero;
3. a empresa percebe que cada caso validado fortalece os proximos.

Essa e a frente mais forte para diferenciar o produto no medio prazo.

## Como ler este roadmap junto com as ideias adicionais

As ideias adicionais recomendadas abaixo fazem sentido e reforcam a linha premium.

A regra correta, porem, e:

- nao abrir 15 frentes de uma vez;
- tratar as ideias como modulos acoplados a um tronco principal;
- priorizar primeiro o que fortalece o ciclo `campo -> Mesa -> memoria -> produto`;
- puxar governanca comercial e rollout de catalogo depois que a espinha operacional estiver madura.

Isso significa:

- varias ideias da lista ja entram no tronco premium;
- outras rodam bem como trilha paralela curta;
- outras dependem da memoria operacional existir antes de valer a pena.

## Os seis pilares premium

### 1. Evidence Radar

Painel vivo de cobertura operacional no caso atual.

Deve mostrar:

- evidencias ja coletadas;
- evidencias aceitas;
- evidencias rejeitadas;
- angulos obrigatorios faltantes;
- qualidade insuficiente;
- conflito entre preenchimento e imagem;
- itens bloqueantes para subir a Mesa.

Valor premium:

- reduz retrabalho;
- aumenta clareza de campo;
- tira ambiguidade do inspetor.

### 2. Quality Gate Operacional

Camada automatica de verificacao antes da Mesa.

Deve detectar pelo menos:

- foto borrada;
- foto escura;
- foto cortada;
- foto duplicada;
- imagem incompativel com a familia;
- imagem incompativel com o ativo ou componente;
- evidencia declarada sem suporte visivel minimo;
- conclusao rascunho incoerente com evidencias.

Valor premium:

- evita que a Mesa seja a primeira linha de controle de qualidade;
- aumenta a confianca no caso antes da revisao humana.

### 3. Revisao por bloco com `refazer_inspetor`

A Mesa nao devolve o laudo inteiro quando o problema e localizado.

Ela devolve:

- o bloco;
- o motivo;
- a evidencia faltante ou ruim;
- o nivel de bloqueio;
- o caminho claro de correcao.

Valor premium:

- reduz friccao;
- reduz retrabalho total;
- aumenta rastreabilidade de revisao.

### 4. Family Memory Index

Memoria consolidada por familia para chat, previa e geracao.

Deve recuperar:

- linguagem tecnica recorrente aprovada;
- padroes de achado;
- componentes frequentes;
- angulos mais uteis;
- conflitos recorrentes;
- recomendacoes tecnicas aprovadas;
- distribuicao de status final por contexto parecido.

Valor premium:

- cada laudo novo parte de uma base melhor;
- a IA deixa de responder de forma generica.

### 5. Golden References

Biblioteca aprovada de referencias visuais e documentais por familia, componente e angulo.

Exemplos:

- vista geral valida;
- placa valida;
- manometro legivel;
- ponto de corrosao bem enquadrado;
- nao conformidade classica por familia.

Valor premium:

- eleva qualidade de captura;
- acelera treinamento operacional;
- padroniza criterio entre inspetor e Mesa.

### 6. Promotion Desk Governado

Quando a memoria detectar padrao forte, o sistema abre sugestao formal, nao muda a regra sozinho.

Tipos de promocao:

- novo angulo recomendado;
- novo angulo obrigatorio;
- nova red flag;
- reforco de evidencia minima;
- sugestao de checklist;
- snippet tecnico recorrente;
- regra de coerencia entre achado e conclusao.

Valor premium:

- o sistema melhora sem perder governanca;
- o produto fica mais forte de forma auditavel.

## Catalogo ampliado de iniciativas

As ideias abaixo sao todas validas. O ponto aqui e enquadrar cada uma no lugar certo.

### A. Nucleo operacional e memoria

Itens que fortalecem diretamente a espinha premium:

- `coverage map de evidencia`
- `revisao por bloco`
- `red flags por familia`
- `clone from last inspection`
- `fit score de familia e variante`
- `diff entre emissoes`
- `anexo pack automatico`

Leitura:

- estes itens melhoram o trabalho do inspetor, a decisao da Mesa e a memoria futura;
- alguns podem entrar cedo, outros dependem de memoria aprovada mais madura.

### B. Confianca documental e entrega premium

Itens que melhoram autenticidade, confianca e apresentacao profissional:

- `QR Code ou hash publico de verificacao`
- `signatarios governados`

Leitura:

- estes itens aumentam percepcao de produto serio e auditavel;
- `QR/hash` vale entrar cedo;
- `signatarios` vale mais quando a emissao estiver mais madura.

### C. Governanca comercial e rollout

Itens que fortalecem operacao SaaS, contrato e liberacao controlada:

- `entitlements por contrato`
- `release channels do catalogo`
- `tenant policy profile`
- `pacotes comerciais`

Leitura:

- fazem muito sentido;
- mas nao deveriam ser a primeira frente se o objetivo agora e robustecer o nucleo tecnico e operacional.

### D. Recorrencia e verticalizacao

Itens que ampliam valor operacional e valor comercial depois do nucleo:

- `renewal engine`
- `biblioteca de linguagem por setor`

Leitura:

- ambos podem gerar valor forte;
- mas dependem de familias mais maduras e memoria mais limpa para ficarem premium de verdade.

## O que eu faria agora

Sim, vale a pena ir para esse lado.

Mas vale a pena ir para esse lado do jeito certo:

- nao como frente gigante;
- nao tentando resolver toda a memoria de uma vez;
- nao com embeddings, CV pesado e analytics avancado ja no primeiro corte.

O corte certo agora e:

### Fase A. Fundacao que ja entrega valor

1. `coverage map` de evidencia por familia
2. quality gate operacional simples
3. revisao por bloco
4. estado `refazer_inspetor`
5. persistencia de `approved_case_snapshot`
6. persistencia de `operational_event`
7. esqueleto de `clone from last inspection`

Esse recorte ja entrega valor real e conversa diretamente com o backlog atual.

### Fase B. Inteligencia operacional visivel

1. `family_memory_index`
2. consulta de casos aprovados parecidos
3. golden references
4. previa enriquecida da Mesa
5. alertas de conflito entre caso atual e memoria aprovada
6. `fit score` inicial de familia e variante
7. `red flags` por familia

### Fase C. Premium maduro

1. promotion desk
2. analytics operacionais
3. deduplicacao e clusters de novidade
4. busca semantica e visual mais forte
5. sugestoes governadas de familia e overlay
6. `diff entre emissoes`
7. `anexo pack automatico`
8. `biblioteca de linguagem por setor`

## O que eu nao faria agora

Mesmo sendo valioso, eu nao abriria agora:

- autoaprendizado amplo em producao;
- mudanca automatica de regra oficial;
- CV pesado e caro antes do gate simples;
- busca semantica sofisticada antes de ter memoria limpa;
- dashboards gigantes antes de ter eventos canonicos;
- autonomia sem Mesa.

Esses itens sao premium tardio, nao premium inicial.

## Como isso conversa com o backlog atual

Esse lado e compativel com o backlog e nao exige reabrir arquitetura base.

Conexoes diretas:

- `coverage map` de evidencia
- revisao por bloco
- `clone from last inspection`
- `red flags` por familia
- diff entre emissoes
- biblioteca de linguagem por setor

Ou seja:

- e uma frente forte;
- mas ela precisa ser fatiada em camadas que o backlog atual ja suporta.

## Como eu encaixaria as 15 ideias na ordem correta

### Rodar agora

Itens que eu colocaria no corte ativo:

1. `coverage map de evidencia`
2. `revisao por bloco`
3. quality gate operacional
4. `refazer_inspetor`
5. `approved_case_snapshot`
6. `operational_event`
7. `clone from last inspection`

Motivo:

- esses itens formam a espinha dorsal;
- eles aumentam qualidade de campo, poder da Mesa e base futura de memoria.

### Rodar em paralelo como trilha curta

Item que pode entrar em paralelo sem competir com a espinha:

1. `QR Code ou hash publico de verificacao`

Motivo:

- melhora autenticidade documental;
- gera percepcao premium externa;
- tem valor comercial alto sem depender de toda a memoria pronta.

### Rodar logo depois da espinha

Itens que eu puxaria assim que Onda 1 e Onda 2 estiverem de pe:

1. `red flags por familia`
2. `fit score de familia e variante`
3. `diff entre emissoes`
4. `signatarios governados`
5. `anexo pack automatico`

Motivo:

- todos ganham muito mais valor quando ja existe memoria, revisao por bloco e trilha operacional consistente;
- antes disso, alguns deles ficam com cara de camada bonita por cima de base fraca.

### Rodar depois como governanca comercial e rollout

Itens que eu deixaria para uma fase seguinte:

1. `entitlements por contrato`
2. `release channels do catalogo`
3. `tenant policy profile`
4. `pacotes comerciais`
5. `renewal engine`
6. `biblioteca de linguagem por setor`

Motivo:

- sao valiosos;
- mas entram melhor quando o nucleo operacional e a memoria premium ja estao fortes;
- assim voce comercializa um produto que realmente entrega o diferencial prometido.

## Ordem premium recomendada

### Onda 1. Premium operacional minimo

- `coverage_snapshot`
- quality gate de foto e coerencia
- `refazer_inspetor`
- revisao por bloco
- base de `clone from last inspection`

Resultado esperado:

- menos lixo chega na Mesa;
- a Mesa para de corrigir erro obvio de campo.

### Onda 2. Premium de memoria aprovada

- `approved_case_snapshot`
- `operational_event`
- `family_memory_index`
- consulta de casos similares aprovados
- `coverage map` visivel para Mesa e inspetor

Resultado esperado:

- melhor previa;
- melhor chat;
- melhor reaproveitamento.

### Onda 3. Premium de referencia guiada

- golden references
- angulos por familia
- exemplos de nao conformidade aprovados
- score operacional por evidencia
- `fit score` inicial
- `red flags` iniciais

Resultado esperado:

- o inspetor sabe melhor o que capturar;
- o sistema consegue cobrar melhor a qualidade.

### Onda 4. Premium governado

- promotion desk
- candidatos de overlay
- candidatos de evidencia minima
- candidatos de red flag
- `diff entre emissoes`
- `anexo pack automatico`
- linguagem controlada por setor

Resultado esperado:

- o produto evolui com base na operacao validada.

## Sinais de que vale ir por este lado agora

Vale muito a pena se o objetivo atual for:

- aumentar confianca do produto;
- reduzir retrabalho entre inspetor e Mesa;
- criar diferencial tecnico real;
- fortalecer a IA com base auditavel;
- construir um moat de dados operacionais aprovados.

Vale menos a pena como primeira frente se o objetivo imediato for:

- abrir distribuicao comercial muito rapido;
- melhorar onboarding superficial;
- mexer primeiro em branding e apresentacao;
- empurrar novas familias antes de amadurecer a operacao.

## Recomendacao objetiva

Minha recomendacao hoje e:

- sim, esse lado vale a pena;
- eu entraria primeiro pela Onda 1 e Onda 2;
- eu rodaria `QR/hash` em paralelo como trilha curta de valor externo;
- eu nao tentaria implementar o "premium total" de uma vez.

## Quando vale rodar dois lados ao mesmo tempo

Vale rodar duas trilhas quando elas se complementam sem competir pelo mesmo nucleo:

- `premium operacional`
- `QR/hash publico`

Essa combinacao e boa porque:

- uma fortalece o produto por dentro;
- a outra melhora autenticidade e percepcao por fora.

Eu nao rodaria em paralelo agora:

- `premium operacional` + governanca comercial grande;
- `premium operacional` + rollout complexo de catalogo;
- `premium operacional` + renewal engine completo.

Isso aumentaria dispersao cedo demais.

Se a outra direcao que voce mandar em seguida competir diretamente com isso, a comparacao certa deve ser:

- qual frente gera mais confianca real no produto;
- qual frente reduz mais retrabalho operacional;
- qual frente cria base de dados reaproveitavel de longo prazo;
- qual frente depende menos de trabalho manual externo.

Regra pratica:

- se a outra frente for mais cosmetica que estrutural, eu ficaria com esta;
- se a outra frente desbloquear venda imediata sem comprometer a arquitetura, pode valer rodar antes;
- se a outra frente conflitar com esta, a escolha deve priorizar aquilo que fortalece o ciclo `campo -> Mesa -> memoria -> produto`.

## Frase de produto

O Tariel premium nao e o sistema que escreve mais bonito.

E o sistema que:

- captura melhor;
- revisa melhor;
- explica melhor;
- aprende melhor;
- e fica mais confiavel a cada caso validado.
