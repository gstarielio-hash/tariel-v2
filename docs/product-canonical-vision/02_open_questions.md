# Dúvidas Abertas e Decisões Pendentes

Este documento registra perguntas que ainda precisam de resposta antes de mudanças maiores de produto, arquitetura ou operação.

O objetivo não é adiar trabalho indefinidamente. O objetivo é evitar que decisões técnicas virem substitutas informais de decisões de produto, jurídico, privacidade ou operação.

## Como interpretar estas pendências

- `Aberta`: não há decisão canônica suficiente para orientar implementação futura sem risco de retrabalho.
- `Parcial`: existe direção, mas faltam limites operacionais ou jurídicos.
- `Fechada`: a direção canônica já foi fixada e o trabalho restante é de implementação ou rollout.
- `Dependente de implementação`: a direção de produto existe, mas a viabilidade e o custo precisam ser detalhados tecnicamente.

## 1. Decisões que dependem de produto

| Tema | Pergunta aberta | Status |
| --- | --- | --- |
| Unidade canônica detalhada | A unidade principal foi fechada como `caso técnico` com três saídas canônicas: histórico simples, relatório genérico e laudo emitido. | Fechada |
| Ownership formal do caso | O ownership híbrido foi fechado: `Inspetor` e `Mesa Avaliadora` podem aprovar/emitir conforme grants e política do tenant; `Admin Cliente` supervisiona e pode intervir administrativamente sem virar signatário técnico por padrão. | Fechada |
| Estados do fluxo | O fluxo canônico foi fechado com ramificações por política do tenant, incluindo `analise_livre`, `relatorio_generico_em_preparo`, `pre_laudo`, `laudo_em_coleta`, `em_revisao_humana`, `devolvido_para_ajuste`, `aprovado_humano`, `emitido`, `encerrado_sem_documento` e `reaberto`. | Fechada |
| Papel do Admin Cliente | A coordenação operacional do `Admin Cliente` foi aceita e a estratégia cross-surface ficou fechada: a continuidade entre mobile, inspetor web e mesa web é governada por grants e links do tenant, sem depender de sessão realmente unificada por padrão. | Fechada |
| Papel do Admin Geral | O princípio de menor acesso com exceção auditada ficou formalizado: acesso excepcional só com aprovação, justificativa, step-up, janela temporária e escopo administrativo/diagnóstico do tenant, sem acesso técnico irrestrito por padrão. | Fechada |
| Escopo do Android | O núcleo obrigatório do mobile foi fechado: IA, histórico, configurações/personalização e geração de relatório genérico. Emissão, mesa nativa, templates extras e templates personalizados variam por pacote e política do tenant. | Fechada |
| Produto documental | O produto comercial foi fechado como combinação de conversa com IA, relatório genérico, laudo estruturado e revisão humana conforme pacote; templates governados continuam motor interno e não precisam ser a narrativa comercial principal. | Fechada |
| IA e automação | A IA pode preencher praticamente tudo no fluxo, incluindo campos, checklist, pré-laudo, conclusão preliminar e recomendação, mas nunca pode sozinha declarar que o laudo está pronto nem substituir a validação humana final. | Fechada |
| Governança de templates | O `Admin CEO` cria, edita e libera templates e pré-laudos; casos novos usam a versão liberada mais recente, enquanto casos em andamento e documentos emitidos preservam a versão com que começaram. Migração de versão exige ação explícita e auditável. | Fechada |

## 2. Decisões que dependem de jurídico, privacidade e compliance

| Tema | Pergunta aberta | Status |
| --- | --- | --- |
| Visibilidade entre empresas | Exceções de suporte ficaram fechadas: a operação da plataforma só atua com janela temporária auditada, aprovação, justificativa e escopo mínimo necessário por tenant. | Fechada |
| Retenção de dados | A retenção segue configurável por tenant, mas agora com mínimos canônicos: `365 dias` para timeline técnica do caso e `1825 dias` para documento emitido e trilha de auditoria. | Fechada |
| Registro de autoria | A responsabilidade técnica final do signatário humano ficou fechada, incluindo os campos mínimos obrigatórios de auditoria: ator, papel, tenant, caso, lifecycle, presença de IA, motivo de override, timestamp do override, signatário final, registro profissional e versão emitida. | Fechada |
| Conteúdo gerado por IA | A atuação da IA permanece no histórico interno e a trilha obrigatória de auditoria ficou fechada, inclusive para `override humano` com justificativa. O `PDF final` segue como documento validado por humano sem marcação explícita de IA por padrão. | Fechada |
| Evidências anexadas | A direção base foi fechada: foto é evidência padrão do chat; documento adicional pode ser habilitado por família, template e tenant; o PDF principal permanece limpo e o pacote final pode carregar anexos completos. Ainda falta detalhar a matriz por família e pacote. | Parcial |
| Consentimento e política | A direção canônica agora é `tenant terms + user notice`: a empresa contrata o uso e cada usuário precisa ser avisado de IA/OCR/geração documental nas superfícies do produto. | Fechada |

## 3. Decisões que dependem de arquitetura e implementação futura

| Tema | Pergunta aberta | Status |
| --- | --- | --- |
| Núcleo compartilhado | O produto já exige um módulo ou serviço explícito de `caso técnico` compartilhado entre chat, mesa, mobile e cliente. O lifecycle v1 já está exposto em contratos e ACL; ainda falta extrair isso de compat layers e consolidar persistência/serviços centrais. | Dependente de implementação |
| Pipeline documental | O formato-fonte deixou de ser decisão canônica de produto. Qual implementação interna melhor sustenta `PDF final` com governança e edição futura? | Dependente de implementação |
| Orquestração assíncrona | Quais partes do fluxo de IA, OCR, exportação e geração documental precisam sair do caminho síncrono para filas ou jobs? | Dependente de implementação |
| Desglobalização frontend | Qual estratégia será usada para reduzir a dependência de `window.*`, ordem manual de scripts e facades por portal sem quebrar os portais existentes? | Dependente de implementação |
| Contrato web/mobile | Como garantir evolução segura do domínio do inspetor sem quebrar o app Android, que consome o mesmo núcleo funcional? O contrato de lifecycle, owner, transições e ações já está compartilhado; ainda faltam disciplina de versionamento, fallback e rollout por superfície. | Parcial |
| Observabilidade de produto | Quais eventos, métricas e trilhas de auditoria precisam ser expostos por domínio para sustentar operação, suporte e governança? | Dependente de implementação |

## 4. Decisões que dependem de operação e modelo comercial

| Tema | Pergunta aberta | Status |
| --- | --- | --- |
| Planos e limites | A matriz comercial ficou fechada por eixos de capacidade configuráveis por tenant: `mesa`, `offline`, `retenção`, `SLA`, `branding`, profundidade do fluxo guiado e operador mobile unificado. | Fechada |
| Suporte operacional | O fluxo padrão de suporte ficou fechado: menor acesso por padrão e acesso excepcional só por aprovação, justificativa, janela temporária e escopo mínimo auditável. | Fechada |
| Escala de revisão | A mesa avaliadora foi fechada como capacidade da própria empresa/tenant. A Tariel pode atuar em suporte excepcional e auditado, mas isso não substitui a mesa do cliente como modelo padrão. | Fechada |
| Governança comercial | O `Admin Geral` deve operar por indicadores agregados e sinais administrativos; abrir conteúdo técnico continua exceção controlada, não visão padrão. | Fechada |

## Perguntas críticas que merecem decisão antes da próxima onda técnica grande

As pendências abaixo têm maior poder de gerar retrabalho estrutural se continuarem implícitas:

1. Como a política de evidências e anexos será detalhada por família, template e pacote?
2. Como os modelos operacionais do tenant (`operador único`, `time enxuto`, `operação separada`) serão materializados em grants, UX e cadastro?
3. Como a matriz comercial canônica por eixos será refletida no cadastro, nas projeções e nos entitlements operacionais?
4. Como o protocolo formal e auditável de acesso excepcional do `Admin Geral` será materializado nas superfícies administrativas e operacionais?
5. Qual implementação interna sustentará melhor o pipeline `document_view_model -> editor_document -> pdf_render -> delivery_package`?
6. Quais partes do fluxo de IA, OCR, exportação e geração documental precisam sair do caminho síncrono para filas ou jobs?

## Leitura prática destas pendências

Enquanto estas perguntas não forem fechadas, propostas futuras devem evitar:

- criar novos contratos públicos baseados em estados implícitos do caso;
- misturar governança administrativa com acesso técnico sem regra formal;
- consolidar o pipeline documental em torno de uma tecnologia intermediária tratada como definitiva de produto;
- remover trilhas mínimas de auditoria ou autoria em nome de simplificação operacional;
- ampliar a política de anexos sem separar claramente foto padrão de documento governado por família/template/tenant;
- ampliar o catálogo governado sem materializar tecnicamente versionamento, grants e migração explícita de template.

## Saída esperada de uma próxima etapa

Uma etapa seguinte de documentação deve transformar estas perguntas em:

- decisões canônicas aprovadas;
- mapa de domínios e capacidades;
- definição do núcleo compartilhado de caso técnico;
- política canônica de evidências por família, template e pacote;
- materialização dos modelos operacionais do tenant e dos grants acumuláveis;
- política de visibilidade e acesso por persona;
- direção oficial do pipeline documental futuro;
- matriz comercial canônica por eixos e modo de operação;
- lifecycle canônico de templates e pré-laudos.
