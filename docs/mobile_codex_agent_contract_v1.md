# Mobile Codex Agent Contract v1

Status: draft ativo
Data de referência: 2026-04-14

## Objetivo principal

Concluir a frente mobile Android do Tariel com foco em qualidade profissional do produto, priorizando:

- geração de laudos e PDFs no mobile com resultado técnico, organizado e visualmente profissional;
- pipeline confiável de `chat -> fotos -> análise -> relatório -> PDF`;
- aderência dos fluxos guiados aos templates e NRs já documentados no Tariel;
- estabilidade geral do app, eliminação de regressões móveis e redução de bugs silenciosos;
- evolução visual do app para um padrão premium, sem aparência de MVP inicial.

## Escopo permitido

O agente pode atuar em:

- `android/`
- `web/`, quando a mudança for necessária para suportar ou corrigir o mobile
- `scripts/`, quando a mudança for necessária para suportar validação ou operação da frente mobile
- `docs/`, para registrar ideias, critérios, pendências e checkpoints

## Escopo proibido

O agente não deve:

- inventar regras funcionais que entrem em conflito com a documentação já consolidada do Tariel;
- alterar arbitrariamente a lógica do produto fora do eixo mobile sem necessidade comprovada;
- impor ideias novas de produto sem registrar antes para aprovação humana;
- tratar iOS, produção real ou tenants reais como frente principal desta etapa;
- declarar o app concluído apenas por aparência visual ou testes unitários isolados.

## Princípios de execução

- preservar o comportamento central já bom do chat livre;
- priorizar qualidade de laudo e PDF antes de polimento periférico;
- priorizar estabilidade antes de refatorações grandes;
- corrigir backend/web sempre que o mobile depender disso para fechar contrato ou fluxo;
- usar os documentos já existentes do Tariel como base de verdade;
- registrar ideias novas separadamente para aprovação humana posterior.

## Fluxo central do produto

O fluxo central e inegociável nesta etapa é:

- o app funcionar como um chat com IA;
- o usuário poder enviar fotos para a IA;
- a IA analisar as evidências recebidas;
- a IA gerar um laudo técnico;
- o laudo virar um PDF profissional dentro do app.

### Chat livre

Objetivo:

- aceitar até 10 fotos por fluxo, com bloqueio rígido acima disso;
- analisar todas as fotos recebidas;
- fazer leitura individual das evidências;
- responder com coerência técnica, sem texto solto ou sem sentido;
- gerar um PDF com estrutura profissional, incluindo capa e sumário;
- agrupar os achados por tema no relatório final.

Regras atuais:

- o estilo atual de resposta da IA no chat livre deve ser preservado como base;
- mudanças de prompt/comportamento textual só devem ser propostas com cautela;
- o relatório deve ser gerado com o que existe no chat, sem bloquear por falta de informação adicional.
- quando várias fotos forem iguais ou muito similares, a IA deve explicitar que não há elementos suficientemente diferentes entre elas e tratá-las como ângulos complementares da mesma evidência, enriquecendo a análise de forma consolidada e não repetitiva.

### Chat guiado

Objetivo:

- usar os templates já existentes e documentados no Tariel;
- respeitar as NRs e a estrutura esperada de cada template;
- gerar laudos organizados, padronizados e profissionais;
- garantir que as fotos/evidências estejam coerentes com os campos pedidos pelo template.

Regra atual:

- o fluxo guiado já exige evidência mínima; portanto o foco é qualidade e coerência do preenchimento, não flexibilizar o gate.
- quando a foto não corresponder ao campo esperado, o sistema deve avisar e marcar pendência, em vez de aprovar silenciosamente.
- o rótulo visual recomendado para esse caso é `incompatível`.

## Famílias e frentes prioritárias

A primeira onda de trabalho deve concentrar as famílias já consideradas prioritárias pelo operador:

- `NR10`
- `NR12`
- `NR13`
- `NR35`

As demais famílias permanecem no backlog estruturado e podem entrar em ondas futuras:

- `NR10`
- `NR12`
- `NR13`
- `NR11`
- `NR20`
- `NR33`
- `NR35`

Subfrentes mencionadas como relevantes:

- `RTI`
- `SPDA`
- `PIE`
- `LOTO`
- levantamento em campo;
- diagnóstico dos itens normativos;
- avaliação de dispositivos de segurança;
- avaliação de segurança elétrica;
- identificação de zonas de risco;
- documentos com `ART`;
- inspeções iniciais, periódicas e extraordinárias;
- ultrassom / espessura;
- calibração de válvulas e manômetros;
- emissão de laudos técnicos;
- emissão de livros de registro;
- testes hidrostáticos e de estanqueidade;
- projeto de instalação;
- plano de inspeções e manutenções;
- análise de risco;
- prevenção e controle;
- espaço confinado;
- planos de resgate;
- linhas de vida, pontos de ancoragem e montagem.

## Prioridades operacionais

Prioridade sugerida a partir das respostas do operador:

1. geração de laudo/PDF e finalização;
2. estabilidade e eliminação de bugs silenciosos;
3. pipeline de fotos e anexos;
4. templates guiados e aderência às NRs;
5. UX visual premium;
6. configurações e preferências funcionando;
7. mesa;
8. offline;
9. performance fina;
10. publicação/distribuição.

## Visual e UX

Objetivo visual:

- o app não deve parecer app inicial ou MVP cru;
- o acabamento deve ser premium;
- o visual pode evoluir de forma superficial mesmo sem seguir literalmente cada detalhe da documentação, desde que isso melhore a experiência e não quebre o comportamento esperado;
- referências externas de mercado podem inspirar o visual, mas sem descaracterizar o comportamento central do Tariel.

### Referências visuais consolidadas

O operador forneceu referências visuais derivadas de uma biblioteca de UI no Figma, com o seguinte enquadramento:

- login: aproveitar apenas a limpeza visual e a hierarquia; não copiar provedores sociais como Apple, Google ou Microsoft, porque o acesso do Tariel é governado pelo `AdminCEO`;
- chat: usar como referência principal de layout, respiro, composer e hierarquia visual;
- interior do chat: usar como referência para mensagens, anexos, ações contextuais e clareza da superfície;
- histórico/perfil/menu lateral: usar como referência para navegação compacta e limpa;
- configurações/planos: usar como referência de organização visual, mas sem replicar conceitos de assinatura incompatíveis com o produto.

Arquivos de referência registrados:

- `/home/gabriel/Área de trabalho/TARIEL/prints/imagem1.png`
- `/home/gabriel/Área de trabalho/TARIEL/prints/imagem2.png`
- `/home/gabriel/Área de trabalho/TARIEL/prints/imagem3.png`
- `/home/gabriel/Área de trabalho/TARIEL/prints/imagem4.png`
- `/home/gabriel/Área de trabalho/TARIEL/prints/imagem5.png`
- `/home/gabriel/Área de trabalho/TARIEL/prints/imagem6.png`

## Configurações

Meta:

- todas as opções atualmente existentes em Configurações devem funcionar corretamente;
- preferências, modos e personalizações não podem falhar silenciosamente;
- alterações devem persistir quando aplicável;
- a tela não deve conter inconsistências visuais ou ações “mortas”.

### Ordem recomendada para a primeira rodada

Como nem tudo está pronto ainda, a rodada 1 deve priorizar:

1. `perfil e conta operacional`
   campos visíveis do usuário, tenant, identidade e consistência de sessão
2. `preferências da IA e do relatório`
   tudo que influencia comportamento, geração de saída, modos e personalização
3. `segurança, sessão e permissões`
   reautenticação, logout, permissões de câmera/galeria/documento e fluxo seguro
4. `exportação, downloads e histórico documental`
   PDFs, anexos, compartilhamento e reabertura autenticada
5. `diagnóstico e suporte operacional`
   sinais úteis para triagem de falha, estado do app, fila local e feedback técnico

Itens de menor prioridade imediata:

- modos cosméticos sem impacto operacional;
- telas de planos/assinatura que não fazem parte do modelo governado do Tariel.

## Definição de pronto sugerida

Uma versão pode ser considerada pronta para esta etapa quando:

- `make mobile-ci` estiver verde;
- o recorte web/mobile crítico estiver verde;
- `make smoke-mobile` estiver verde quando a lane estiver disponível;
- o fluxo central `chat -> foto -> análise -> relatório -> PDF` estiver validado no emulador;
- quando o aparelho físico estiver disponível, o mesmo fluxo estiver confirmado manualmente;
- o chat guiado estiver operacional nas famílias prioritárias do lote atual;
- configurações estiverem funcionando sem erro silencioso;
- não houver bug crítico conhecido em login, upload, geração de PDF, abertura de PDF, histórico, finalização ou persistência de estado;
- riscos residuais estiverem documentados explicitamente.

### Checklist manual mínimo no celular físico

Quando o aparelho físico estiver disponível, o aceite manual mínimo deve confirmar:

1. login funcionando corretamente;
2. envio de fotos no chat funcionando;
3. geração de PDF concluindo no fluxo principal;
4. abertura do PDF dentro do app / via fluxo autenticado;
5. histórico reabrindo a conversa e o documento gerado.

### Seções obrigatórias do PDF livre

Para esta etapa, o PDF do chat livre deve conter no mínimo:

- capa;
- sumário;
- contexto;
- evidências fotográficas;
- análise técnica;
- achados / não conformidades;
- recomendações;
- conclusão.

## Definição de bug silencioso

Para esta frente, considerar como bug silencioso qualquer situação em que:

- um botão não faz nada e não informa erro;
- uma ação aparenta sucesso, mas o estado não persiste;
- upload some, trava ou não entra no fluxo sem feedback;
- o PDF não gera ou não abre sem mensagem clara;
- uma configuração pode ser alterada na UI, mas não muda comportamento real;
- a finalização retorna sucesso visual, mas o backend não consolidou o estado esperado;
- o histórico perde anexos, contexto ou documento sem aviso.

## Comportamentos que devem ser preservados

Até nova aprovação, o agente deve preservar:

- o tom/base atual das respostas do chat livre, salvo ajuste pontual claramente melhor;
- a governança central já definida no Tariel;
- as regras documentadas de templates e NRs;
- o lifecycle canônico e a integração web/mobile existente;
- os gates mínimos de evidência do fluxo guiado.

## Evidências visuais recomendadas

Para orientar o agente e a revisão humana, organizar prints em grupos como:

- `prints/01_referencias_premium`
- `prints/02_chat_livre_atual`
- `prints/03_chat_guiado_templates`
- `prints/04_pdf_laudos`
- `prints/05_configuracoes`
- `prints/06_historico_finalizar`
- `prints/07_bugs_criticos`
- `prints/08_fluxos_bons_para_preservar`

Idealmente cada pasta deve vir com uma nota curta dizendo:

- o que está certo;
- o que está errado;
- o que precisa parecer ou funcionar melhor.

## Pendências de definição

Ainda falta confirmar com o operador:

1. como a UI deve exibir agrupamentos consolidados de fotos redundantes no chat livre sem poluir a conversa;
2. qual mecânica visual detalhada deve ser usada para o selo `incompatível` no guiado;
3. qual lote 2 de famílias entra após estabilizar `NR10`, `NR12`, `NR13` e `NR35`.
