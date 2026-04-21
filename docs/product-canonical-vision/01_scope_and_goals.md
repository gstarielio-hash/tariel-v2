# Escopo e Metas do Produto

## Objetivo do sistema

O sistema Tariel existe para permitir que inspeções técnicas sejam conduzidas com apoio de IA, governadas por fluxos humanos de revisão e convertidas em documentação técnica rastreável, sem perder responsabilidade profissional, isolamento entre empresas e auditabilidade operacional.

Em termos de produto, o sistema deve reduzir atrito entre coleta técnica, análise, construção do laudo, revisão e aprovação, mas sem transformar esse processo em uma automação opaca ou juridicamente frágil.

## Visão geral do produto

O Tariel é um produto multiportal orientado a casos técnicos.

O centro funcional do sistema é um mesmo `caso técnico`, que pode conter `thread`, `laudo`, anexos, revisão e artefatos derivados. Esse caso precisa ser visível de forma consistente por superfícies diferentes, cada uma com um papel distinto:

1. `Chat Inspetor`
   Papel: condução operacional da inspeção, conversa com IA, anexos, evidências, rascunhos e progressão do laudo.
2. `Mesa Avaliadora`
   Papel: leitura crítica do mesmo caso, comentários, validações, cobranças de ajuste e aprovação final humana.
3. `Admin Cliente`
   Papel: gestão de usuários, acompanhamento da operação da própria empresa, visibilidade gerencial e controle restrito à empresa cliente.
4. `Admin Geral`
   Papel: operação da plataforma SaaS, gestão de empresas, planos, billing, saúde operacional e políticas gerais.
5. `App Android`
   Papel: cliente operacional principal do ecossistema do `Chat Inspetor`, centrado em conversa com IA, uso móvel e continuidade do mesmo contrato funcional.

6. `Inspetor Web`
   Papel: cliente operacional oficial complementar do mesmo domínio do inspetor, mantido para clientes que prefiram operar pela web.

## O que o sistema é

- Um sistema multiportal de inspeção técnica assistida por IA.
- Um produto centrado em continuidade entre conversa, análise, revisão e documento final.
- Uma plataforma com separação explícita entre trabalho técnico do cliente e governança SaaS.
- Um ambiente em que IA ajuda a produzir rascunhos, estruturar respostas e acelerar o preenchimento do laudo.
- Um fluxo em que a aprovação final do engenheiro continua sendo mandatória.
- Um ecossistema em que web e Android compartilham o mesmo núcleo de negócio do `Chat Inspetor`.
- Um produto em que o foco estratégico principal atual é `mobile-first`.
- Um produto em que a experiência principal do mobile é um chat com IA que pode ou não virar laudo.
- Um produto em que o inspetor pode operar em análise livre, laudo guiado ou laudo com mesa.
- Um produto em que o mesmo caso pode terminar como histórico simples, relatório genérico ou laudo emitido, conforme o fluxo e a política do tenant.
- Um produto em que a mesa pode existir no mobile como fluxo nativo, inclusive para o mesmo usuário quando o pacote e a permissão permitirem.
- Um produto em que o mesmo usuário pode acumular papéis operacionais quando o modelo do tenant permitir.
- Um produto em que templates e pré-laudos são governados centralmente pelo `Admin CEO`.

## O que o sistema não é

- Não é um chatbot genérico sem compromisso com caso técnico, laudo e rastreabilidade.
- Não é uma ferramenta de aprovação automática de laudos por IA.
- Não é um ERP completo do cliente nem um BI universal da empresa.
- Não é um painel único em que todas as personas devam ver o mesmo conteúdo técnico.
- Não é um produto em que `Admin Geral` tenha visibilidade automática sobre todo conteúdo técnico privado de cada cliente.
- Não é um fluxo documental em que o formato-fonte do template já esteja fechado como decisão definitiva de produto.

## Domínios canônicos do produto

### 1. Operação de inspeção

Domínio responsável por captura de contexto, conversa operacional, anexos, evidências, progresso do laudo e interação com IA.

O ponto de entrada preferencial deste domínio é um chat com IA que pode ficar em análise livre ou subir para laudo.

Superfícies principais:

- `Chat Inspetor` web
- `App Android`

### 2. Avaliação e aprovação técnica

Domínio responsável por revisão humana, comentários, pendências, avaliação de qualidade e aprovação final do caso técnico.

Superfícies principais:

- `Mesa Avaliadora`
- fluxo nativo de mesa no `App Android`, quando o pacote permitir

### 3. Governança operacional do cliente

Domínio responsável por gestão de usuários, acompanhamento gerencial da empresa, visibilidade restrita à própria empresa e administração do uso interno do sistema.

Superfície principal:

- `Admin Cliente`

### 4. Governança de plataforma

Domínio responsável por operação da plataforma SaaS, billing, planos, gestão de empresas, políticas comerciais e monitoramento operacional agregado.

Esta camada também abriga a governança central de templates e pré-laudos por `Admin CEO`.

Superfície principal:

- `Admin Geral`

### 5. Núcleo documental e de caso técnico

Domínio transversal responsável pelo vínculo entre conversa, revisões, anexos, templates, versões e artefatos finais do laudo.

Este domínio é compartilhado pelos demais e não deve ficar implícito dentro de apenas um portal.
Os templates estruturais desse domínio são liberados centralmente e consumidos pelas camadas operacionais.

## Arquitetura-alvo em alto nível

Do ponto de vista de produto, a arquitetura-alvo desejada é:

1. Um `núcleo de caso técnico` compartilhado entre `Chat Inspetor` e `Mesa Avaliadora`.
2. Fronteiras claras entre `operação técnica`, `governança do cliente` e `governança da plataforma`.
3. Contratos consistentes entre web e Android no que diz respeito ao `Chat Inspetor`.
4. Um `núcleo de modos operacionais` que suporte análise livre, pré-laudo, laudo guiado e laudo com mesa sem recriar o caso.
5. Uma trilha explícita de responsabilidade humana em todas as etapas críticas: revisão, aprovação, publicação e auditoria.
6. Um catálogo governado de templates e pré-laudos com autoria central e consumo controlado pelas demais personas.

## Metas de produto

### Metas funcionais

- Permitir que o inspetor conduza um caso técnico com assistência de IA sem perder contexto.
- Garantir que a mesa acompanhe o mesmo caso técnico com visibilidade suficiente para comentar, validar e aprovar.
- Permitir que o cliente gerencie sua operação sem cruzar indevidamente fronteiras de conteúdo técnico.
- Permitir que a operação da plataforma administre empresas, planos e billing sem depender de acesso irrestrito ao conteúdo técnico.
- Suportar continuidade entre web e Android no fluxo operacional do inspetor.

### Metas de qualidade

- Rastreabilidade de todas as ações críticas sobre o caso técnico.
- Isolamento confiável entre empresas, usuários e portais.
- Clareza sobre quem gerou, revisou, aprovou e publicou cada artefato.
- Redução de retrabalho entre conversa, análise e geração documental.
- Preparação para escalabilidade do fluxo documental e de revisão.

### Metas de evolução

- Sair de uma arquitetura mental centrada em telas para uma arquitetura centrada em domínios e capacidades.
- Tratar `caso técnico` como unidade canônica de continuidade entre portais.
- Preparar o sistema para pipeline documental mais robusto sem travar prematuramente o formato-fonte dos templates.
- Criar base para reduzir acoplamentos históricos entre frontends, bridges globais e controladores monolíticos.
- Priorizar o mobile como principal diferencial sem descontinuar o inspetor web.

## Restrições obrigatórias

- A aprovação final do engenheiro permanece obrigatória.
- IA pode sugerir, estruturar, resumir e preencher rascunhos, mas não substituir a autoridade técnica final.
- O mesmo caso técnico deve poder ser acompanhado por `Chat Inspetor` e `Mesa Avaliadora`.
- O acesso a dados técnicos precisa respeitar escopo de empresa e papel do usuário.
- `Admin Geral` não deve ter acesso automático ao conteúdo técnico detalhado do cliente como comportamento padrão.
- O sistema deve manter compatibilidade entre web e Android quando ambos atuarem no fluxo do inspetor.
- O roadmap técnico futuro não pode quebrar contratos de negócio sem decisão explícita de produto.
- O produto deve suportar operação com mesa obrigatória, mesa opcional ou sem mesa conforme pacote ou política do tenant.
- A política do tenant deve governar quem pode aprovar e emitir: `Inspetor`, `Mesa Avaliadora` ou ambos, sempre com validação humana.
- Casos em andamento não podem trocar silenciosamente de versão de template ou pré-laudo.
- Fotos são a evidência padrão do chat; documentos adicionais dependem de família, template e política do tenant.
- Apenas o `Admin CEO` pode criar, editar e liberar templates e pré-laudos.
- As personas operacionais podem usar e escolher templates liberados, mas não editar sua estrutura.
- Em fluxo guiado, a correção deve ocorrer por checkpoints e campos, e não por um segundo chat redundante.

## Princípios do produto

1. `Continuidade de caso antes de continuidade de tela`
   A experiência deve preservar o mesmo caso técnico ao longo dos portais, em vez de criar cópias desconectadas por interface.

2. `IA como assistente, humano como autoridade final`
   O sistema deve amplificar produtividade e qualidade, não terceirizar responsabilidade profissional.

3. `Revisão explícita é parte do produto`
   A mesa não é um acessório operacional; ela é parte constitutiva do fluxo de confiança do sistema.

4. `Governança não é visibilidade irrestrita`
   Camadas administrativas precisam de controle e métricas, mas não de acesso automático a tudo.

5. `Documento final exige trilha de origem`
   Todo laudo precisa preservar vínculo entre contexto, rascunho, revisão, aprovação e artefato final.

6. `Multiportal com fronteiras claras`
   O produto pode ter múltiplos portais, mas cada um precisa ter responsabilidade, escopo e linguagem de uso próprios.

7. `Compatibilidade operacional entre clientes do mesmo domínio`
   Web e Android devem ser tratados como clientes distintos do mesmo domínio operacional, não como negócios separados.

8. `Produto guiando arquitetura`
   Refatoração, modularização e evolução de frontend/backend precisam seguir os domínios do produto, não apenas hotspots acidentais do código.

## Decisões já suficientemente estáveis para orientar arquitetura futura

- `Chat Inspetor` e `Mesa Avaliadora` fazem parte do mesmo fluxo de caso técnico.
- `App Android` é foco estratégico principal, enquanto o inspetor web continua superfície oficial complementar.
- O `App Android` é centrado em um chat com IA que pode ou não virar laudo.
- O núcleo obrigatório do mobile para qualquer tenant inclui IA, histórico, configurações/personalização e geração de relatório genérico.
- Direitos de emissão, mesa nativa, templates avançados e templates personalizados variam por política e pacote do tenant.
- Quando a mesa existir no mobile, ela deve existir como fluxo nativo do app e pode ser acessada pelo mesmo usuário, se o pacote e a permissão permitirem.
- `Admin Cliente` e `Admin Geral` têm funções diferentes e não devem colapsar em uma só camada administrativa.
- O mesmo tenant pode operar com `Admin Cliente` dedicado ou com um usuário acumulando esse grant, conforme o modelo operacional contratado.
- Templates e pré-laudos governados pertencem à camada central de `Admin CEO`.
- Casos novos usam a versão mais recente liberada do template; casos em andamento e documentos emitidos preservam a versão com que nasceram.
- A entrega documental final precisa ser `PDF`; o formato-fonte dos templates continua sendo decisão técnica e não requisito estável de produto neste momento.
- A separação entre apoio da IA e aprovação humana não é opcional; é estrutural.

## Limites desta definição

Este documento define escopo, metas e princípios. Ele não fecha sozinho:

- o modelo final de permissões detalhadas;
- o nível exato de visibilidade do `Admin Geral` em cenários excepcionais;
- o desenho final do pipeline documental;
- a futura estratégia de desglobalização total dos frontends;
- a decomposição técnica definitiva em serviços, módulos ou bounded contexts.
