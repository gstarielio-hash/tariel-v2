# Prompt Genérico Baseado no Esqueleto do Projeto

Use este arquivo quando a IA externa nao tiver acesso ao repositório, ao visual atual ou ao código-fonte.

Ideia:
- em vez de pedir para "preservar o que já existe"
- você entrega para a IA o esqueleto funcional da área
- e pede um redesign visual novo em cima dessa estrutura

## Como usar

1. Escolha a área que quer redesenhar.
2. Copie o prompt-base no final deste arquivo.
3. Cole junto a seção `Esqueleto da área` correspondente.
4. Se quiser, adicione screenshots apenas como referência estrutural, não estética.

## Mapa Geral do Produto

Produto:
- `Tariel.ia`

Tipo de produto:
- SaaS B2B para operação técnica, inspeção, revisão, gestão documental e administração de empresas

Perfis principais:
- `Admin-Geral`
- `Admin-Cliente`
- `Inspetor`
- `Mesa Avaliadora / Revisor`

Tom do produto:
- corporativo
- operacional
- técnico
- sem marketing excessivo
- sem linguagem promocional de landing page

Regras visuais globais:
- a interface deve parecer software profissional, não template genérico
- priorizar clareza operacional, densidade controlada e hierarquia forte
- evitar excesso de cards repetidos sem função
- evitar visual de CRM genérico ou dashboard de bootstrap
- evitar look de app casual, chat casual ou plataforma “startup brinquedo”
- a interface deve funcionar desktop-first, mas com resposta coerente no mobile

## Esqueleto da Área: Admin-Geral

Usuário:
- Admin-Geral / Admin-CEO

Objetivo principal:
- controlar empresas assinantes, planos, acessos e visão macro da operação

Blocos funcionais típicos:
- dashboard executivo
- KPIs principais
- gráficos ou leitura de tendência
- alertas operacionais
- lista/tabela de empresas
- busca e filtros
- ações por empresa
- CTA para criar nova empresa
- comparação ou gestão de planos

Ações críticas:
- criar empresa
- ver detalhe de empresa
- bloquear/desbloquear
- alterar plano
- acompanhar capacidade e risco operacional

Sensação desejada:
- comando
- visão estratégica
- operação multiempresa

## Esqueleto da Área: Admin-Cliente

Usuário:
- administrador da empresa cliente

Objetivo principal:
- operar a empresa em um portal unificado, incluindo equipe, plano, auditoria, chat e mesa

Blocos funcionais típicos:
- identificação da empresa
- resumo da conta/plano
- visão de saúde operacional
- navegação entre `Admin`, `Chat` e `Mesa`
- gestão de usuários
- onboarding da equipe
- auditoria recente
- leitura de prioridades

Ações críticas:
- criar usuário
- alterar perfil/papel
- bloquear/desbloquear usuário
- trocar plano
- acompanhar gargalos da operação

Sensação desejada:
- workspace unificado da empresa
- gestão + operação no mesmo ambiente

## Esqueleto da Área: Portal do Inspetor / Chat

Usuário:
- inspetor em campo

Objetivo principal:
- conduzir inspeção ativa com apoio de IA, contexto do laudo e comunicação com a mesa avaliadora

Blocos funcionais típicos:
- cabeçalho com status e ações principais
- sidebar/histórico
- área principal de conversa
- barra de status da inspeção ativa
- ações rápidas
- widget ou painel da mesa avaliadora
- painel de pendências
- estados de laudo bloqueado, leitura ou reabertura
- banner ou alerta de resposta da mesa

Ações críticas:
- iniciar nova inspeção
- continuar inspeção ativa
- enviar mensagem
- finalizar e enviar para a mesa
- visualizar pendências
- acompanhar resposta da mesa

Sensação desejada:
- ferramenta operacional de campo
- fluxo contínuo de trabalho
- IA como assistente técnica, não chatbot casual

## Esqueleto da Área: Mesa Avaliadora

Usuário:
- revisor técnico / mesa avaliadora

Objetivo principal:
- receber laudos, responder o campo, validar aprendizados, tratar pendências e concluir revisões

Blocos funcionais típicos:
- topbar funcional
- fila lateral
- métricas operacionais
- whispers urgentes
- filtros da fila
- listas de laudos por estado
- área principal de detalhe do laudo
- mensagens e histórico
- contexto técnico / pacote / anexos
- ações finais de revisão

Ações críticas:
- priorizar item
- responder inspetor
- abrir pacote técnico
- marcar pendência
- validar aprendizado
- devolver ou concluir revisão

Sensação desejada:
- inbox técnica
- workbench de revisão
- alta responsabilidade operacional

## Esqueleto da Área: Biblioteca de Templates

Usuário:
- mesa avaliadora / time documental

Objetivo principal:
- gerenciar templates técnicos de laudo e seu ciclo de vida

Blocos funcionais típicos:
- hero funcional da biblioteca
- busca
- filtros
- ordenação
- overview com métricas
- lista ou grid de templates
- seleção em lote
- comparação entre versões
- auditoria/histórico da biblioteca

Ações críticas:
- abrir template
- filtrar por status
- comparar versões
- mudar ciclo de vida
- arquivar
- excluir

Sensação desejada:
- operação documental séria
- catálogo vivo de ativos técnicos

## Esqueleto da Área: Editor Word de Templates

Usuário:
- mesa avaliadora / editor técnico

Objetivo principal:
- criar, editar, revisar e publicar templates técnicos com placeholders e blocos estruturados

Blocos funcionais típicos:
- barra superior com ações principais
- abertura de template
- salvar
- publicar versão
- preview PDF
- folha A4 central
- lateral de ferramentas
- presets rápidos
- blocos prontos
- placeholders e tokens
- inspector editorial

Ações críticas:
- abrir template
- editar conteúdo
- inserir bloco
- inserir placeholder
- salvar
- publicar
- gerar preview

Sensação desejada:
- ferramenta editorial profissional
- produção documental técnica
- desktop-first

## Esqueleto da Área: Login de Portal Corporativo

Usuário:
- qualquer perfil do sistema, dependendo do portal

Objetivo principal:
- entrar rapidamente no ambiente correto com foco total na autenticação

Blocos funcionais típicos:
- painel esquerdo de contexto curto
- card de login
- título objetivo
- subtítulo operacional
- campo de e-mail
- campo de senha
- lembrar-me
- recuperar senha
- CTA principal
- divisor
- botões SSO

Ações críticas:
- autenticar
- acionar recuperação
- usar SSO

Sensação desejada:
- enterprise
- limpa
- sem onboarding excessivo
- foco total em acesso

## Prompt-Base Para Colar em Outra IA

```text
Você não tem acesso ao repositório, ao código-fonte ou ao visual atual do produto.

Considere como fonte de verdade apenas o esqueleto funcional abaixo.

Quero que você crie uma nova proposta visual para uma área do produto Tariel.ia.

Contexto do produto:
- SaaS B2B para operação técnica, inspeção, revisão, documentação e administração corporativa
- o produto é corporativo, técnico e orientado a operação
- a interface não deve parecer landing page, CRM genérico, template de dashboard ou app casual

Regra principal:
- não tente “adivinhar” um visual existente
- use apenas a estrutura funcional fornecida
- proponha um redesign visual do zero em cima desse esqueleto

Área alvo:
- [PREENCHER AQUI]

Tela alvo:
- [PREENCHER AQUI]

Objetivo primário da tela:
- [PREENCHER AQUI]

Esqueleto funcional da área:
- [COLE AQUI UMA DAS SEÇÕES DE ESQUELETO DESTE ARQUIVO]

Restrições:
- mantenha os blocos funcionais essenciais
- você pode reorganizar a hierarquia visual
- você pode mudar completamente layout, componentes, grid, tipografia, espaçamentos e direção estética
- a interface precisa continuar parecendo software enterprise
- a solução deve funcionar bem em desktop e de forma coerente em mobile
- menos marketing e mais operação

O que eu quero que você entregue:
1. conceito visual da tela
2. estrutura do layout
3. hierarquia dos blocos
4. proposta de componentes
5. HTML/CSS ou mockup textual detalhado
6. justificativa curta do porquê essa direção visual funciona para essa área

Evite:
- dashboard genérico
- cards repetitivos sem função
- visual de template pronto
- excesso de efeitos decorativos
- cara de app casual ou consumer
```
