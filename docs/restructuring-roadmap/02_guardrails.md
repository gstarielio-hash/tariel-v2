# 02. Guardrails da Reestruturação

Este documento estabelece as regras fortes da reestruturação. Ele define limites não negociáveis para que a reorganização do sistema não vire uma reescrita descontrolada.

## 1. Guardrails absolutos

Os itens abaixo valem para toda a trilha 0-90 dias.

1. Não alterar regras de negócio.
2. Não alterar backend funcional.
3. Não alterar frontend funcional.
4. Não alterar endpoints.
5. Não alterar contratos.
6. Não remover código.
7. Não misturar reestruturação com entrega de feature.
8. Não mexer em auth/session/multiportal sem fase dedicada e aprovação explícita fora deste roadmap.
9. Não mexer em API compartilhada com o mobile sem contrato congelado e revisão específica.
10. Não promover mudanças estruturais sem rollback claro.

## 2. Classes de mudança

Toda mudança futura de reestruturação deve ser classificada antes de abrir PR.

| Classe | Tipo | Permitida neste roadmap? | Exemplo |
| --- | --- | --- | --- |
| `G0` | Documentação apenas | Sim | roadmap, ADR, inventário, ledger |
| `G1` | Teste, CI, observabilidade, instrumentação | Sim | métricas, guards, coverage, profiling |
| `G2` | Modularização interna sem mudança de contrato | Sim, a partir da Fase 2 | extrair serviço, quebrar arquivo, criar adapter |
| `G3` | Mudança de contrato, endpoint, auth, negócio, UX funcional | Não | alterar payload, rota, sessão, fluxo do usuário |

Regra:

- Se houver dúvida entre `G2` e `G3`, classificar como `G3` e bloquear até decisão explícita.

## 3. Guardrails por superfície

## 3.1 Backend

Pode:

- extrair helpers e serviços internos;
- quebrar arquivos grandes;
- melhorar organização interna;
- adicionar instrumentação;
- ampliar testes.

Não pode:

- mudar resposta de rota;
- mudar nome ou formato de endpoint;
- alterar estado persistido de forma observável;
- alterar regras de transição de laudo;
- alterar fluxos de mesa, pendência, avaliação e templates do ponto de vista funcional.

## 3.2 Frontend web

Pode:

- mapear assets;
- instrumentar carregamento;
- modularizar internamente JS e CSS em fases futuras controladas;
- criar documentação de shell e runtime.

Não pode:

- alterar comportamento funcional percebido pelo usuário;
- mudar contrato DOM/API que já sustenta os fluxos atuais sem fase explícita;
- mudar navegação, rotas, estados ou fluxos de interação nesta trilha.

## 3.3 Auth, sessão e multiportal

Pode:

- documentar;
- testar melhor;
- medir;
- tornar observável.

Não pode:

- alterar cookie, token, sessão ou isolamento de portal;
- alterar política de login/troca de senha;
- alterar papéis e RBAC;
- alterar o comportamento que separa `/admin`, `/cliente`, `/app` e `/revisao`.

## 3.4 Mobile e shared API

Pode:

- documentar contratos usados pelo app;
- ampliar testes e monitors;
- tornar explícita a matriz de compatibilidade entre app e backend.

Não pode:

- alterar payloads usados pelo app;
- alterar semântica das rotas do inspetor que o mobile consome;
- introduzir mudança silenciosa que force atualização do app.

## 3.5 Banco e migração

Pode:

- documentar modelos, constraints e índices;
- medir custo de queries;
- preparar análise de schema.

Não pode:

- mudar schema funcional;
- criar migração estrutural;
- alterar comportamento persistido;
- remover tabelas, colunas, índices ou dados.

## 3.6 Código legado e compat layers

Pode:

- identificar;
- documentar;
- marcar como candidato a deprecação futura;
- encapsular melhor.

Não pode:

- remover;
- romper importadores existentes;
- eliminar fallback sem substituto validado.

## 4. Guardrails de escopo por PR

Todo PR futuro de reestruturação deve obedecer:

1. Uma fase declarada.
2. Uma classe de mudança declarada.
3. Uma superfície crítica dominante por PR.
4. Um rollback simples descrito.
5. Um conjunto explícito de invariantes preservados.

Exemplo de invariantes obrigatórios:

- mesmas rotas;
- mesmos payloads;
- mesmo fluxo de autenticação;
- mesma separação entre portais;
- mesma semântica operacional para inspetor, cliente, revisor e mobile.

## 5. Guardrails de merge

Não fazer merge se:

- o PR mistura reestruturação com regra de negócio;
- o PR mistura várias superfícies críticas ao mesmo tempo;
- o PR não consegue explicar o rollback;
- o PR não deixa claro o que não muda;
- o PR toca auth/session/multiportal sem aprovação explícita fora desta trilha;
- o PR pode afetar mobile/shared API sem matriz de compatibilidade;
- o PR reduz visibilidade de métricas ou testes.

## 6. Guardrails de pausa imediata

Pausar o trabalho se:

- surgir regressão em `/app/api/chat`;
- surgir regressão em `/revisao/painel` ou `/revisao/ws/whispers`;
- o portal cliente perder consistência entre Admin, Chat e Mesa;
- houver quebra de login, troca de senha ou isolamento de portal;
- o mobile parar de consumir a API compartilhada corretamente;
- uma extração interna começar a exigir mudança de contrato para continuar.

## 7. Guardrails para documentação de mudança

Toda iniciativa futura de reestruturação deve deixar escrito:

- `Fase`
- `Classe`
- `Objetivo`
- `Superfícies impactadas`
- `Invariantes`
- `Validação`
- `Rollback`
- `Critério de pausa`

## 8. Guardrails de estratégia

1. Medir antes de modularizar.
2. Modularizar antes de remover.
3. Isolar antes de modernizar.
4. Preservar fallback antes de desligar legado.
5. Fazer hardening antes de acelerar a fase seguinte.

## 9. Superfícies de risco máximo

Estas áreas sempre exigem revisão reforçada:

- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/cliente/portal_bridge.py`
- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/realtime.py`
- `web/app/shared/security.py`
- `web/app/shared/security_session_store.py`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `android/src/features/InspectorMobileApp.tsx`

## 10. Regra de não avanço automático

Completar uma fase não autoriza a próxima automaticamente. Cada transição exige nova decisão explícita após revisar:

- métricas;
- regressões;
- cobertura;
- rollback;
- custo cognitivo real das mudanças feitas.
