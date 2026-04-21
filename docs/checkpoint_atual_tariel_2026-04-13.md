# Checkpoint Atual Tariel

Data: 2026-04-13
Horario de referencia: 16:35 -03

## Estado atual

- Branch atual: `feature/canonical-case-lifecycle-v1`
- HEAD base ao iniciar este checkpoint: `771e3f5`
- Repositório remoto: `gstarielio-hash/tariel-web`
- Fase atual: consolidação da plataforma canônica entre tenant, web, mobile e documento

## Onde parou de verdade

O núcleo do produto já mudou de patamar.

O projeto agora tem em produção local de código:

- `caso técnico` como unidade canônica;
- lifecycle compartilhado entre backend, inspetor web, portal cliente e Android;
- grants multiportal governados por tenant;
- pacote operacional por empresa definido no `Admin CEO`;
- quality gate, override humano e trilha auditável;
- app Android mais próximo de uma jornada nativa real.

O ciclo mais recente foi centrado em duas frentes:

- consolidar governança, grants, mesa, quality gate e offline no app Android;
- corrigir problemas reais do mobile em aparelho, incluindo fullscreen, bootstrap, rede local em dev e vazamento de `preferencias_ia_mobile` no chat visível.

## O que entrou neste corte

- saneamento de `preferencias_ia_mobile` no backend, no cache local, no histórico e na renderização do chat;
- envio das preferências da IA como contexto interno, não mais como texto visível para o usuário;
- correção do runtime de env e da leitura da `API_BASE_URL` no dev client Android;
- correção de loop de render ligado à persistência/configurações no app;
- navegação de caso reorganizada com `Chat`, `Mesa` condicional e `Finalizar`;
- remoção de parte relevante da poluição visual do topo do chat;
- checkpoint canônico atualizado em `STATUS_CANONICO.md`.

## O que já está sólido

- grants e pacote operacional por tenant;
- lifecycle e ações canônicas do caso;
- mesa mobile e finalização governada;
- quality gate com justificativa humana;
- offline/caching por identidade de conta;
- contratos compartilhados entre backend, web e Android;
- sanitização estrutural de dados internos antes de render em chat e histórico.

## O problema atual mais importante

O principal gargalo desta fase não é mais regra de negócio.

O gargalo agora é:

- acabamento de UX do app Android;
- simplificação de telas carregadas;
- redução de respostas longas e genéricas da IA;
- continuidade da limpeza arquitetural do backend/web sem perder a direção canônica já conquistada.

## Próxima sequência recomendada

1. limpar visualmente `Finalizar`, `Configurações` e `Histórico` no Android;
2. validar no aparelho login, anexos, offline e mesa depois do ajuste visual;
3. continuar extraindo o núcleo compartilhado de `caso técnico`;
4. reduzir compat layers e globals do frontend web;
5. retomar o pipeline documental premium.
