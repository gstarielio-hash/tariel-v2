# Decisões Fundamentais de Produto

Data de referência: 2026-04-13
Origem: respostas diretas do decisor do produto e consolidação canônica
Status: canônico

## Objetivo

Fixar as decisões de produto que já estão claras o suficiente para orientar:

- arquitetura;
- backlog;
- fronteiras entre portais;
- estratégia mobile e web;
- fluxo de inspeção e laudo;
- políticas de revisão, retenção e entrega.

## Resumo executivo

O Tariel passa a ser lido assim:

1. a unidade principal do produto é o `caso técnico`;
2. o caso pode começar livre e nem sempre precisa virar laudo;
3. quando necessário, o caso sobe de nível para laudo estruturado;
4. o ownership do caso é híbrido e muda por estado;
5. o produto opera em modos claros de trabalho, com ou sem mesa;
6. o foco principal é `mobile-first`, mas o inspetor web continua oficial;
7. a IA pode preparar quase tudo, mas nunca validar sozinha o laudo final;
8. o requisito estável de entrega é `PDF final`, não um formato-fonte específico;
9. retenção, mesa e profundidade do fluxo podem variar por pacote comercial;
10. o app mobile tem como centro um chat com IA que pode ou não virar laudo, conforme a intenção do usuário;
11. quando a mesa existir no mobile, ela deve existir como fluxo nativo do app, e não como um site aberto dentro dele;
12. depois da aprovação humana, o sistema gera o PDF final, marca o caso como `emitido` e permite reabertura para um novo ciclo quando o laudo precisar ser refeito;
13. na reabertura de um caso emitido, o usuário pode escolher manter o PDF anterior visível no caso ou retirá-lo da superfície ativa, preservando trilha interna quando fizer sentido.
14. quando a IA sugerir texto ou correção, a trilha principal disso deve ficar no histórico interno, enquanto o PDF final continua sendo tratado como documento validado por humano;
15. se o humano insistir em manter algo fora do padrão da NR ou do template, o sistema deve alertar a divergência, mostrar a orientação correta e pedir confirmação explícita antes de continuar;
16. depois da validação humana, o laudo passa a compor o histórico da empresa para consulta futura e acompanhamento operacional.
17. quando o pacote contratado for `mobile principal com operador único`, essa regra deve nascer no cadastro da empresa pelo `Admin CEO`, e não como exceção solta por usuário.

## 1. Unidade canônica do produto

### Decisão

A unidade principal do produto é o `caso técnico`.

### Definições práticas

- `caso técnico`: trabalho iniciado pelo inspetor no web ou mobile;
- `thread`: conversa operacional dentro do caso;
- `laudo`: artefato estruturado derivado do caso quando o fluxo exigir formalização.

### Regra

O sistema não deve tratar todo começo de conversa como laudo.

Um caso pode:

- permanecer como análise livre;
- subir para um estado de intenção documental;
- virar laudo formal;
- seguir para revisão humana;
- terminar aprovado, devolvido ou encerrado sem laudo final.

## 2. Modos canônicos de trabalho

### Decisão

O produto opera em três modos principais:

1. `análise livre`
2. `laudo guiado`
3. `laudo com mesa`

### Análise livre

Uso:

- conversa com IA;
- análise de foto;
- apoio técnico rápido;
- sem obrigação imediata de gerar laudo final.

### Regra de entrada

O foco principal do app mobile é esse modo:

- um chat com IA que pode ajudar o usuário;
- pode permanecer como análise livre;
- pode evoluir para laudo quando o usuário quiser formalizar.

### Laudo guiado

Uso:

- inspeção iniciada já com template ou família definida;
- checklist e checkpoints explícitos;
- progressão orientada para saída documental.

### Regra de correção

Quando o fluxo estiver guiado por NR ou template:

- o sistema deve mostrar checkpoints claros;
- o usuário deve conseguir se autocorrigir pelo próprio fluxo;
- o produto deve evitar um "chat para corrigir o próprio chat", porque isso é redundante.

### Laudo com mesa

Uso:

- o caso ou laudo segue para revisão humana;
- a mesa avalia, devolve, aprova ou aprova com ressalva;
- a conclusão final depende de validação humana.

### Regra adicional

`mesa` deve ser tratada como capacidade funcional do produto, não apenas como portal web separado.

## 3. Escalada do caso até laudo

### Decisão

O caso pode começar livre e subir de nível sem recriação.

### Regra prática

O sistema deve aceitar:

- conversa livre que nunca vira laudo;
- conversa livre que depois vira laudo;
- inspeção guiada que já nasce orientada a laudo.

### Estado intermediário recomendado

Entre caso livre e laudo formal, existe um estado canônico útil:

- `pré-laudo`

Leitura:

- já existe intenção de formalizar;
- ainda faltam dados, checklist ou coerência mínima;
- o caso ainda não deve ser tratado como laudo pronto.

### Saídas canônicas do caso

O caso técnico pode terminar de três formas oficiais:

- `histórico simples`: conversa e análises da IA ficam só como histórico operacional, sem documento final;
- `relatório genérico`: o chat livre com IA e fotos gera um relatório genérico, que pode ser compartilhado ou emitido conforme a política do tenant;
- `laudo formal`: template ou pré-laudo estruturado é preenchido, validado por humano e emitido.

## 4. Ownership híbrido por estado

### Decisão

O ownership do caso não é fixo.
Ele muda por estado.

### Regra operacional

- o owner ativo obedece o estado do caso e a política operacional do tenant;
- `Inspetor` comanda durante análise livre, geração de relatório genérico, coleta e preenchimento guiado;
- `Mesa Avaliadora` comanda quando o caso é enviado para revisão humana;
- se a mesa devolver, o caso volta para o `Inspetor`;
- `Inspetor`, `Mesa Avaliadora` ou ambos podem aprovar e emitir, desde que isso esteja liberado no tenant e o usuário tenha o grant correspondente;
- o mesmo usuário pode acumular grants de `Inspetor`, `Mesa Avaliadora` e `Admin Cliente` quando o modelo operacional do tenant permitir;
- `Admin Cliente` supervisiona e pode intervir administrativamente, mas não vira autor técnico nem signatário final por padrão;
- o sistema precisa registrar explicitamente o owner ativo do caso em cada estado.

### Implicação arquitetural

O núcleo do produto não pode ser modelado como:

- "chat manda sempre"; ou
- "mesa manda sempre".

O produto exige um `núcleo de caso técnico` com transição formal de ownership.

## 5. Fluxo canônico do caso

### Decisão

O fluxo oficial parte do web do inspetor ou do mobile e aceita variações comerciais sem perder a unidade do caso.

### Fluxo base

1. caso iniciado no mobile ou no inspetor web;
2. o caso segue por `chat livre` ou por `análise guiada/checklist`;
3. no `chat livre`, a IA pode apenas analisar, produzir histórico simples ou gerar relatório genérico;
4. no trilho documental, o caso sobe para `pré-laudo` ou já nasce como `laudo guiado`;
5. inspetor completa dados, evidências e checkpoints quando houver exigência documental;
6. a política do tenant decide se o caso segue sem mesa, com mesa opcional ou com mesa obrigatória;
7. quando vai para revisão humana, a mesa avalia, aprova, aprova com ressalva ou devolve;
8. se devolvido, o caso retorna ao inspetor;
9. só após validação humana o documento pode ser tratado como concluído;
10. a aprovação humana pode ser feita por `Inspetor`, `Mesa Avaliadora` ou ambos, conforme grants e política do tenant;
11. após a aprovação, o sistema gera o PDF final e fecha o ciclo como `emitido`;
12. o caso também pode ser encerrado sem documento final, preservando o histórico operacional, ou terminar como relatório genérico;
13. se o laudo emitido precisar ser refeito, ele pode ser reaberto para nova edição, nova revisão e nova finalização;
14. quando o caso emitido for reaberto, o sistema deve oferecer uma escolha explícita sobre o PDF anterior: manter visível no caso ou ocultar da superfície ativa;
15. independentemente da visibilidade ativa, o documento anterior pode permanecer como trilha histórica e item de aprendizado interno.

### Máquina de estados canônica

Os nomes canônicos do lifecycle passam a ser:

- `analise_livre`
- `relatorio_generico_em_preparo`
- `pre_laudo`
- `laudo_em_coleta`
- `em_revisao_humana`
- `devolvido_para_ajuste`
- `aprovado_humano`
- `emitido`
- `encerrado_sem_documento`
- `reaberto`

Leitura prática:

- `analise_livre` pode terminar em `encerrado_sem_documento` ou subir para `relatorio_generico_em_preparo`, `pre_laudo` ou `laudo_em_coleta`;
- `relatorio_generico_em_preparo` pode seguir direto para aprovação humana e emissão, ou ir para `em_revisao_humana` quando a política exigir;
- `laudo_em_coleta` pode ir direto para `aprovado_humano` e `emitido`, ou passar por `em_revisao_humana`, conforme a política do tenant;
- `em_revisao_humana` pode seguir para `aprovado_humano` ou `devolvido_para_ajuste`;
- `devolvido_para_ajuste` retorna o caso a `laudo_em_coleta` ou `relatorio_generico_em_preparo`, dependendo do trilho;
- `emitido` pode ir para `reaberto`, voltando a `laudo_em_coleta` ou `em_revisao_humana`.

### Handoff para mesa

Direção canônica:

quando o inspetor envia o caso para mesa, o sistema deve montar automaticamente um pacote de handoff com:

- resumo do caso;
- fotos principais;
- pendências visíveis;
- versão atual do laudo;
- sinais de cobertura e bloqueios.

## 6. Modelos de mesa avaliadora

### Decisão

O produto deve suportar três modelos de revisão:

1. `sem mesa`
2. `mesa opcional`
3. `mesa obrigatória`

### Implicação comercial e operacional

- isso pode variar por empresa;
- isso pode variar por pacote vendido;
- isso pode variar por criticidade do caso.
- a mesa pode existir no web, no mobile ou em ambos;
- em certos pacotes, a mesma pessoa que opera o mobile pode também validar no mobile.
- a mesa padrão pertence ao próprio tenant/empresa;
- a Tariel pode prestar suporte excepcional e auditado, mas isso não transforma a plataforma em pool compartilhado de revisão por padrão.

### Fila da mesa

Direção canônica:

a fila da mesa não deve ser apenas por ordem de chegada.
Ela deve poder considerar:

- prioridade;
- prazo;
- criticidade;
- tipo de caso;
- SLA contratado.

### Decisões simples da mesa

A mesa deve operar, no mínimo, com estes resultados claros:

- `corrigir e reenviar`
- `aprovado`
- `aprovado com ressalva`

### Regra de superfície

Quando a mesa existir no mobile, isso significa:

- ver templates liberados;
- escolher o template aplicável;
- validar o caso;
- aprovar ou devolver dentro do app.

Isso não significa:

- abrir um site externo da mesa dentro do mobile;
- espelhar um portal web sem adaptação.

## 7. Visibilidade por persona

### Admin Cliente

### Decisão

O `Admin Cliente` pode ver integralmente o que está acontecendo entre inspetor, mesa e mobile dentro da própria empresa e, quando o tenant permitir, agir operacionalmente sobre o caso.

### Leitura prática

- conversa;
- andamento;
- pendências;
- anexos;
- decisões da mesa.
- histórico por usuário;
- laudos emitidos.

### Papel esperado

O `Admin Cliente` é principalmente camada de:

- acompanhamento;
- visibilidade gerencial;
- gestão de assinatura e operação da própria empresa;
- cadastro e coordenação de inspetores e avaliadores da mesa;
- controle operacional do tenant.

Ele não é a camada principal de autoria técnica do laudo.
Ele também não cria nem edita templates estruturais.

### Governança de superfície e ação

O nível de exposição operacional do `Admin Cliente` não precisa ser igual em todos os tenants.

Direção canônica:

- a empresa pode operar apenas com resumos e indicadores agregados; ou
- a empresa pode liberar visão caso a caso no portal do `Admin Cliente`; ou
- a empresa pode liberar também ações operacionais por caso, quando isso fizer parte do serviço contratado.

Essa escolha:

- depende do desenho operacional combinado na contratação;
- deve ficar vinculada ao cadastro governado do tenant;
- deve ser configurável pela camada central do `Admin CEO`;
- não deve virar comportamento implícito decidido apenas pela interface ou por atalho técnico local.

### Ações administrativas aceitáveis

Quando o tenant liberar ação operacional ao `Admin Cliente`, as ações mínimas aceitáveis são:

- solicitar nova avaliação da mesa;
- pedir correção ao inspetor ou ao operador que finalizou;
- reabrir o caso;
- bloquear emissão ou publicação;
- cancelar ou redirecionar o fluxo operacional do caso.

Essas ações:

- são administrativas e auditáveis;
- não transformam automaticamente o `Admin Cliente` em signatário técnico;
- precisam respeitar grants e política do tenant.

### Pacote mobile principal com operador único

### Decisão

Quando o cliente contratar o modo `mobile principal com operador único`, isso deve ser definido no cadastro da empresa em `Admin CEO`.

### Regra prática

- o tenant pode ou não ter um `Admin Cliente` dedicado;
- o operador principal continua focado no app mobile;
- esse mesmo operador pode ter continuidade no `inspetor web` e na `mesa web`, conforme a política do tenant;
- em tenant pequeno, o mesmo usuário pode acumular `Admin Cliente`, `Inspetor` e `Mesa Avaliadora`;
- a regra comercial desse pacote é de operador operacional único;
- os demais tenants e pacotes continuam seguindo a operação padrão.

### Implicação técnica

Essa decisão já vale como política contratual do tenant.

Direção fechada:

- por padrão, a continuidade entre `mobile`, `inspetor web` e `mesa web` acontece por `grants + links governados do tenant`;
- isso não exige sessão realmente unificada entre superfícies neste momento;
- uma sessão única real pode existir futuramente, mas não é pré-requisito da regra comercial nem do lifecycle canônico.

### Modelos operacionais do tenant

Para reduzir ambiguidade comercial e operacional, o tenant pode nascer em três modelos:

1. `operador_unico_mobile`
   Um único usuário acumula operação mobile, inspetor web, mesa e administração do tenant, se contratado.
2. `time_enxuto`
   O tenant tem poucos usuários e pelo menos um acumula grant de `Admin Cliente`, sem exigir separação rígida entre papéis.
3. `operacao_separada`
   `Admin Cliente`, `Inspetor` e `Mesa Avaliadora` existem como usuários ou equipes distintas.

### Admin Geral

### Decisão

`Admin Geral` não deve ter acesso técnico irrestrito por padrão.

### Regra prática

- opera a plataforma;
- corrige bug, código e operação;
- deve evitar abrir conteúdo técnico privado quando isso não for necessário;
- acesso técnico deve ser excepcional e orientado a suporte ou incidente real.

### Protocolo formal de exceção

Quando houver acesso excepcional, a regra canônica é:

- exigir aprovação explícita;
- exigir justificativa registrada;
- exigir step-up de segurança;
- limitar a janela temporal da exceção;
- limitar o escopo ao mínimo necessário;
- deixar trilha auditável do começo ao fim.

Escopo padrão aceitável:

- `metadata_only`;
- `administrative`;
- `tenant_diagnostic`.

Escopo não aceito por padrão:

- acesso técnico irrestrito e permanente ao conteúdo privado do cliente.

### Admin CEO

### Decisão

A criação, edição e liberação de templates e pré-laudos é exclusiva do `Admin CEO`.

### Regra prática

- `Inspetor`, `Mesa Avaliadora`, `Admin Cliente`, `App Mobile` e `Inspetor Web` usam templates já liberados;
- essas camadas podem escolher o template aplicável ao caso;
- essas camadas podem pedir ajuste de template;
- essas camadas não podem editar a estrutura canônica do template.

## 8. Estratégia de canal: mobile-first com web oficial

### Decisão

O foco principal do produto é `mobile-first`.

O `inspetor web` continua existindo como canal oficial, porque pode haver clientes que prefiram operar pela web.

### Regra canônica

- `mobile` é o principal diferencial competitivo;
- `web` continua sendo produto oficial e não legado;
- ambos participam do mesmo núcleo de caso técnico;
- o desenho do produto não deve depender de pensar primeiro no web.

### Consequências

O app mobile pode ser:

- fluxo livre;
- fluxo guiado por template;
- canal que fecha o laudo sozinho;
- canal que inclui validação nativa, inclusive pelo mesmo usuário mobile, quando o pacote e a permissão permitirem;
- canal que depende de web e/ou mesa, conforme o pacote vendido.

Também pode existir venda:

- com `Admin Cliente`;
- sem `Admin Cliente`, quando o modelo comercial não exigir essa camada.

## 9. Direção do mobile

### Decisão

O mobile deve ser tratado como principal superfície de captura e conclusão, centrado em um chat com IA que pode ou não virar laudo.

### Direções canônicas

- a experiência principal começa por conversa com IA;
- o caso pode permanecer como análise livre ou subir para laudo quando o usuário quiser formalizar;
- o núcleo obrigatório do mobile para qualquer tenant inclui IA, histórico, configurações/personalização e geração de relatório genérico;
- missões guiadas por tipo de inspeção;
- reuso de contexto do ativo, NR, planta e inspeções anteriores;
- continuidade entre fotos, checklist, chat, histórico e conclusão;
- possibilidade de a mesma experiência mobile incluir escolha de template, emissão e validação;
- possibilidade de operação independente da web, quando o pacote permitir.

### Capacidades que variam por pacote

Os pontos que variam por política do tenant e pacote contratado são:

- limite de uso;
- direito de emissão pelo mobile/inspetor;
- presença de mesa nativa no app;
- acesso a templates adicionais;
- acesso a templates personalizados;
- uso offline e sincronização posterior.

### Regra de mesa no mobile

Quando a mesa existir no mobile:

- ela deve existir como fluxo nativo do app;
- pode ser acessada pelo mesmo usuário autenticado no mobile, se o pacote e a permissão permitirem;
- deve permitir ver templates liberados, escolher o template correto e validar no próprio app;
- não deve depender de abrir um site externo.

## 10. Papel comercial do produto

### Decisão

O produto vendido é principalmente:

- geração de laudo;
- conversa com IA para análise e organização;
- transformação de conversa + fotos + contexto em relatório estruturado;
- revisão humana antes da conclusão final.

### Regra sobre templates

Templates são motor interno de aceleração, padronização e preenchimento.
Eles não precisam ser a narrativa comercial principal.

### Direção de empacotamento

A oferta comercial deve poder combinar:

- volume;
- retenção;
- mesa;
- SLA;
- offline;
- branding;
- entrega final;
- profundidade do fluxo.

Pacotes exemplares aceitáveis:

- análise rápida;
- laudo assistido;
- laudo com validação humana;
- plano enterprise mobile.

## 11. Limite de autonomia da IA

### Decisão

A IA pode preparar praticamente todo o trabalho, mas nunca validar sozinha o laudo final.

### IA pode

- analisar imagens;
- organizar dados;
- sugerir texto;
- preencher rascunho;
- preencher campos e checklist;
- preencher pré-laudo para apoio à mesa ou ao validador no mobile;
- preparar conclusão preliminar e recomendação;
- montar relatório;
- sugerir correções;
- apoiar coerência entre conteúdo, fotos e campos.

### IA não pode

- declarar autonomamente que o laudo está pronto;
- substituir a aprovação humana final.
- impor uma correção final contra a decisão humana validada.

### Direção funcional

O produto deve caminhar para duas camadas de IA:

- IA operacional do inspetor;
- IA de pré-revisão para apoiar a mesa.

Também faz sentido manter:

- checagem automática antes do envio à mesa;
- score interno de confiança apenas para priorização;
- correção guiada por checklist, campos e checkpoints, em vez de um segundo chat para corrigir o primeiro;
- sugestão de correção baseada no motivo da devolução.

### Regra de divergência com norma

Quando o conteúdo humano divergir do padrão esperado da NR, do template ou do checkpoint:

- o sistema deve sinalizar onde está a divergência;
- o sistema deve mostrar qual seria a orientação correta esperada;
- o sistema deve pedir confirmação explícita para continuar mesmo assim;
- a decisão final continua sendo humana;
- o override precisa ficar preservado em trilha interna de auditoria.

### Regra de autoria visível

Direção atual:

- a participação da IA deve ficar registrada no histórico interno do caso e na trilha operacional;
- o `PDF final` não precisa carregar marcação explícita de "trecho gerado por IA" por padrão;
- o documento final continua sendo lido como laudo validado por humano.

### Regra de responsabilidade técnica

Quando o laudo for validado e assinado:

- a responsabilidade técnica final é do humano que aprovou e assinou;
- a assinatura profissional aplicável, como `CREA`, é a referência principal de autoria e validação do documento final;
- se o sistema tiver alertado divergência com NR, template ou checkpoint e o humano ainda assim confirmar o conteúdo, a decisão final passa a ficar registrada como override humano explícito;
- a pré-montagem pela IA não desloca a responsabilidade do signatário humano.

## 12. Política documental

### Decisão

O formato-fonte principal do documento não é requisito estável de produto neste momento.

### Invariante

O que importa para o produto é:

- entrega final em `PDF`;
- PDF apto para impressão e envio;
- possibilidade de distribuição por e-mail, WhatsApp ou link.

### Direção de entrega

A entrega final pode evoluir para pacote mais rico, por exemplo:

- PDF final;
- resumo executivo;
- hash ou ID de verificação;
- anexos selecionados;
- versão cliente final e versão interna técnica, quando fizer sentido.

### Pipeline canônico de implementação

Enquanto o formato-fonte interno continua decisão de implementação, o pipeline canônico passa a ser lido assim:

- `document_view_model`;
- `editor_document`;
- `pdf_render`;
- `delivery_package`.

O pacote final de entrega deve carregar contexto suficiente para auditoria e governança, mesmo quando a distribuição pública continue centrada no `PDF final`.

### Política de anexos e evidências

Direção canônica:

- no chat, `texto + foto` é a evidência padrão;
- `documento` ou `PDF` adicional pode ser habilitado por família, template e política do tenant;
- o `PDF final` principal pode carregar fotos e referências documentais selecionadas;
- o `delivery_package` pode carregar anexos completos quando isso fizer sentido para a família ou para o serviço contratado.

### Versionamento de template e pré-laudo

Direção canônica:

- caso novo usa a versão mais recente liberada do template ou pré-laudo;
- caso em andamento preserva a versão com que começou;
- documento emitido preserva para sempre a versão usada na emissão;
- migração de caso em andamento para versão nova exige ação explícita e trilha auditável.

## 13. Histórico, retenção e exclusão

### Decisão

O histórico do caso deve preservar:

- conversa;
- anexos;
- conteúdos enviados pelo usuário.
- sugestões e preenchimentos relevantes produzidos pela IA no fluxo interno;
- decisões humanas de validação, correção e override.

### Regra comercial

A retenção deve ser configurável por tenant.

Modos aceitáveis:

- curto;
- operacional;
- anual;
- arquivo permanente.

### Direção operacional

- depois da validação humana, o laudo passa a compor o histórico da empresa;
- a empresa deve conseguir consultar esse histórico quando precisar rever o caso, sustentar reunião futura ou entender o contexto do laudo;
- a política precisa deixar explícito o efeito da exclusão de empresa e de inspetor sobre o histórico;
- quando a empresa é excluída, o conteúdo da empresa deixa de existir conforme a política do produto;
- quando o inspetor é excluído, o efeito sobre seu histórico precisa seguir a política comercial e de auditabilidade do tenant;
- considerar arquivamento frio antes de apagar em definitivo, quando fizer sentido para o pacote.

### Mínimos canônicos de retenção

Mesmo com configuração por tenant, os mínimos canônicos passam a ser:

- `365 dias` para timeline técnica do caso;
- `1825 dias` para documento emitido;
- `1825 dias` para trilha de auditoria e autoria;
- exclusão definitiva só depois de respeitar esses mínimos e a política contratual ativa.

### Autoria e auditoria obrigatórias

Campos mínimos obrigatórios de trilha:

- usuário ator;
- papel do ator;
- tenant;
- caso técnico;
- lifecycle do caso;
- presença de conteúdo assistido por IA;
- motivo do `override humano`, quando existir;
- timestamp do `override humano`, quando existir;
- nome do signatário final;
- registro profissional aplicável, como `CREA`;
- versão emitida do documento.

### Consentimento operacional

O uso de IA, OCR e geração documental passa a seguir esta regra:

- a contratação e o tenant aceitam o serviço;
- o usuário final precisa receber aviso claro nas superfícies do produto;
- a trilha pública continua focada no documento validado por humano;
- a trilha interna preserva o uso da IA para auditoria e suporte.

### Restrição importante

O detalhamento restante daqui em diante é de implementação e rollout, não mais de direção canônica.

## 14. Matriz comercial canônica

### Decisão

Os pacotes comerciais não diferenciam só volume.
Eles combinam eixos de capacidade por tenant.

### Eixos mínimos

- `mesa`;
- `direito de emissão`;
- `offline`;
- `limites de uso`;
- `retenção`;
- `SLA`;
- `branding`;
- `acesso a templates padrão`;
- `acesso a templates personalizados`;
- profundidade do fluxo guiado;
- operador mobile unificado.

### Regra

- a combinação desses eixos nasce no cadastro da empresa pelo `Admin CEO`;
- um tenant não interfere nas regras do outro;
- os grants por usuário sempre respeitam primeiro o que o tenant comprou.

## 15. Consequências imediatas para arquitetura

Estas decisões implicam:

1. o núcleo do sistema deve ser modelado em torno de `caso técnico`;
2. `thread` e `laudo` são componentes do caso, não a unidade primária;
3. o sistema deve suportar `análise livre`, `laudo guiado` e `laudo com mesa`;
4. precisa existir owner ativo do caso por estado;
5. o mobile deve ser pensado como principal superfície operacional;
6. o inspetor web permanece oficial e compatível com o mesmo domínio;
7. o `Admin Cliente` precisa de visão ampla sobre a operação do próprio tenant;
8. o `Admin Geral` precisa operar por menor acesso ao conteúdo técnico;
9. a mesa pode ser opcional ou obrigatória conforme a venda;
10. a conclusão final continua dependente de validação humana;
11. o documento final entregue é PDF, sem travar agora o formato-fonte interno;
12. o mobile precisa suportar fluxo nativo de validação quando a mesa existir no app;
13. o mesmo usuário mobile pode acumular captura e validação quando o pacote e a permissão permitirem;
14. templates e pré-laudos governados só podem ser criados, editados e liberados pelo `Admin CEO`.

## 16. O que ainda exige detalhamento posterior

Mesmo com esta decisão canônica, ainda falta detalhar:

- nomenclatura comercial final dos pacotes;
- matriz detalhada de anexos e documentos por família/template/pacote;
- materialização técnica dos modelos operacionais do tenant e dos grants acumuláveis;
- solicitação de ajuste e rollout operacional de templates e pré-laudos;
- desenho técnico final do pipeline documental e do `delivery_package`.

## Decisão final deste documento

Até nova revisão explícita:

- o produto é `caso-técnico-first`;
- a estratégia é `mobile-first`;
- o inspetor web continua oficial;
- o mobile é centrado em um chat com IA que pode ou não virar laudo;
- o fluxo é multi-modo;
- a mesa pode ser configurável por pacote;
- a mesa pode existir nativamente no mobile;
- o mesmo usuário mobile pode validar no app quando o pacote e a permissão permitirem;
- templates e pré-laudos governados são exclusivos do `Admin CEO`;
- a aprovação final humana continua obrigatória;
- `PDF final` é o requisito estável de entrega.
