# Pacote Canônico de Visão de Produto e Arquitetura-Alvo

Este pacote consolida a visão de produto que deve orientar decisões futuras de arquitetura, modularização, priorização e governança do sistema Tariel.

O objetivo desta etapa não é propor refatoração imediata nem autorizar mudanças funcionais. O objetivo é estabelecer uma linguagem canônica sobre o que o produto é, quais domínios o compõem, quais limites não podem ser violados e quais decisões ainda dependem de alinhamento de produto, operação, jurídico e implementação.

## Resumo executivo

O Tariel é um sistema multiportal para inspeções técnicas assistidas por IA, revisão técnica humana e governança operacional por empresa.

O núcleo do produto não é apenas um chat, nem apenas um gerador de laudos. O núcleo é a gestão de um mesmo caso técnico ao longo de quatro camadas:

1. `Chat Inspetor`: espaço operacional em que a inspeção acontece, com conversa, evidências, contexto normativo e construção assistida do laudo.
2. `Mesa Avaliadora`: espaço de revisão, comentário, validação, ajustes e aprovação do mesmo caso técnico.
3. `Admin Cliente`: espaço de gestão restrita à própria empresa para usuários, operação e acompanhamento da empresa cliente.
4. `Admin Geral`: espaço de operação da plataforma, empresas, planos, billing e governança SaaS.

O app Android faz parte do mesmo ecossistema e deve ser tratado como um cliente de primeira classe do fluxo do `Chat Inspetor`, não como um produto paralelo desconectado. A direção estratégica atual é `mobile-first`.

A visão-alvo do sistema é operar um mesmo caso técnico com continuidade entre conversa, análise, revisão, documentação e aprovação final, preservando:

- aprovação final obrigatória do engenheiro;
- isolamento entre empresas e entre portais;
- rastreabilidade de ações humanas e artefatos gerados;
- fronteira clara entre operação técnica do cliente e governança da plataforma;
- PDF como artefato final obrigatório de entrega, sem fixar neste momento um único formato-fonte canônico de template.

## Índice do pacote

- `README.md`: visão geral, resumo executivo e forma de uso do pacote.
- `01_scope_and_goals.md`: escopo do produto, metas, princípios e arquitetura-alvo em alto nível.
- `02_open_questions.md`: dúvidas abertas e decisões pendentes antes de mudanças técnicas ou de produto maiores.
- `03_foundational_decisions_2026-04-12.md`: decisões fundamentais normalizadas a partir das respostas diretas do produto.

## Como usar estes documentos

Use este pacote antes de qualquer discussão sobre:

- refatoração estrutural;
- novos módulos ou portais;
- mudanças de ownership entre `chat`, `mesa`, `cliente` e `admin`;
- evolução do fluxo de laudo, templates e aprovação;
- expansão do app Android;
- desenho de integrações, permissões e fronteiras de visibilidade.

Sequência recomendada de leitura:

1. Ler este `README.md` para alinhar vocabulário e objetivos.
2. Ler `01_scope_and_goals.md` para fixar o escopo canônico do produto.
3. Ler `03_foundational_decisions_2026-04-12.md` para entender as decisões já fechadas.
4. Ler `02_open_questions.md` para identificar o que ainda não está encerrado.
5. Só então abrir propostas de arquitetura, refatoração ou roadmap técnico.

## Regras de uso deste pacote

- Estes documentos são canônicos até que outro pacote os substitua explicitamente.
- Mudanças técnicas futuras devem declarar aderência ou exceção explícita a esta visão.
- Se uma proposta conflitar com estes documentos, o conflito deve ser resolvido como decisão de produto e arquitetura, não apenas como decisão de implementação.
- Este pacote não substitui a auditoria técnica em `docs/full-system-audit/`; ele organiza a leitura dela sob uma ótica de produto e arquitetura-alvo.

## Invariantes que já ficam estabelecidos aqui

- O sistema não pode tratar a IA como aprovadora final de laudos.
- `Chat Inspetor` e `Mesa Avaliadora` precisam operar sobre o mesmo caso técnico, com continuidade de contexto.
- `Admin Cliente` gerencia a operação da própria empresa, mas não substitui a camada técnica de inspeção e revisão.
- `Admin Geral` gerencia a plataforma, mas não deve ter acesso automático e irrestrito ao conteúdo técnico dos clientes.
- O app Android participa do ecossistema do `Chat Inspetor`, precisa respeitar os mesmos contratos de negócio e hoje é prioridade estratégica do produto.
- O requisito estável de documento é `PDF como artefato final`; o formato-fonte permanece decisão de implementação.

## Limite desta fase

Este pacote inicia a visão canônica do produto. Ele ainda não detalha todas as capacidades por domínio, nem fecha todas as decisões de privacidade, workflow e arquitetura técnica futura. Esses pontos aparecem como pendências explícitas em `02_open_questions.md`.
