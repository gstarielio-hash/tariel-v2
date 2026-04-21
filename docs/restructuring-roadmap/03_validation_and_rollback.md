# 03. Validação, Merge e Rollback

Este documento define como cada mudança futura de reestruturação deve ser validada, quando deve ser pausada, quando pode ser mergeada e como deve ser revertida.

## 1. Critério de aceite macro da reestruturação

Uma mudança de reestruturação só é aceitável se:

- não alterar regra de negócio;
- não alterar backend funcional;
- não alterar frontend funcional;
- não alterar endpoints;
- não alterar contratos;
- não remover código;
- melhorar governança, observabilidade ou modularidade interna;
- preservar rollback claro.

## 2. Matriz de validação por classe de mudança

| Classe | Tipo | Validação mínima | Rollback mínimo |
| --- | --- | --- | --- |
| `G0` | Documentação apenas | revisão de coerência e vínculo com a fase | revert simples |
| `G1` | Teste/CI/observabilidade | checks locais/CI + evidência de não impacto funcional | revert simples ou desligar flag |
| `G2` | Modularização interna sem mudança de contrato | testes existentes + testes novos na fronteira + comparação de comportamento + plano de rollback | revert simples, fallback ou flag |
| `G3` | Mudança de contrato/comportamento | bloqueada por este roadmap | não aplicável nesta trilha |

## 3. Critérios mínimos de merge

Nenhuma mudança futura ligada à reestruturação deve ser mergeada sem:

1. Fase declarada.
2. Classe declarada.
3. Invariantes declarados.
4. Superfícies afetadas declaradas.
5. Validação executada e registrada.
6. Rollback descrito.
7. Critério de pausa descrito.

## 4. Invariantes obrigatórios por superfície

## 4.1 Backend

- mesmas rotas;
- mesmos métodos HTTP;
- mesmos formatos de resposta;
- mesma semântica operacional.

## 4.2 Frontend web

- mesma navegação funcional;
- mesma semântica de interação;
- mesma ligação com APIs;
- mesma separação entre portais.

## 4.3 Auth/session/multiportal

- mesmo fluxo de login;
- mesma política de troca de senha;
- mesmo isolamento entre portais;
- mesma semântica de sessão e perfil.

## 4.4 Mobile/shared API

- mesmos contratos de rota usados pelo app;
- mesma semântica de login, bootstrap, chat e mesa;
- mesma compatibilidade entre versões atuais de app e backend.

## 5. Checklist mínimo antes do merge

### Para `G0`

- documentação revisada;
- sem alteração de código;
- referências corretas à fase e aos guardrails.

### Para `G1`

- nenhuma mudança de comportamento observável;
- métricas ou guards documentados;
- testes e CI não enfraquecidos;
- rollback simples definido.

### Para `G2`

- escopo pequeno e isolado;
- testes existentes continuam válidos;
- testes adicionais cobrem a fronteira extraída;
- invariantes declarados;
- comparação clara entre “antes” e “depois”;
- rollback rápido possível;
- superfícies de alto risco tiveram revisão explícita.

## 6. Critérios de pausa

Pausar a iniciativa imediatamente se ocorrer qualquer um destes sinais:

- falha em fluxo crítico de inspetor, cliente, revisor ou templates;
- comportamento divergente em laudo, mesa ou pendência;
- quebra de autenticação, sessão ou multiportal;
- quebra de contrato percebida pelo mobile;
- piora mensurável e relevante em `/app/api/chat`;
- piora mensurável e relevante em `/revisao/painel`;
- perda de clareza de rollback;
- PRs começando a depender de exceções ao roadmap para continuar.

## 7. Critérios de rollback

Executar rollback se:

- o comportamento funcional mudou sem autorização;
- houve quebra de contrato;
- houve regressão de auth/session;
- houve regressão de mobile/shared API;
- houve piora operacional relevante sem mitigação;
- o fallback planejado não funcionou como esperado.

## 8. Estratégias de rollback aceitáveis

| Estratégia | Quando usar | Observação |
| --- | --- | --- |
| Revert simples do PR | `G0`, `G1` e `G2` pequenos | Estratégia preferencial |
| Desligar feature flag | observabilidade ou modularização protegida por flag | A flag deve manter comportamento anterior |
| Voltar para facade/adapter anterior | extrações internas da Fase 2 ou 3 | O caminho antigo deve continuar preservado |
| Rollback do deploy | somente se a reversão por código não bastar | Deve ser acompanhado de análise de causa |

## 9. Critérios de “merge seguro”

Uma mudança é considerada “merge seguro” quando:

- o comportamento antigo continua demonstrável;
- o caminho de fallback é conhecido;
- a superfície tocada cabe em um PR pequeno;
- o time consegue explicar a mudança sem recorrer ao arquivo monolítico antigo para tudo;
- a mudança reduz ambiguidade ou melhora rastreabilidade.

## 10. Critérios de “merge perigoso”

Bloquear merge se o PR:

- toca `chat_stream_routes.py` e `portal_bridge.py` e `revisor/panel.py` ao mesmo tempo;
- mistura backend, frontend web e mobile em uma refatoração única;
- tenta limpar legado e modularizar ao mesmo tempo;
- muda contrato “sem querer” por efeito colateral;
- toca auth/session sem fase dedicada;
- depende de suposições não medidas sobre performance.

## 11. Validações específicas por área de risco

## 11.1 Chat do inspetor

Exigir:

- mesma resposta funcional;
- mesmo comportamento de laudo ativo;
- mesmo contrato em `/app/api/chat`;
- mesmas integrações com pendências, mesa e citações.

## 11.2 Revisor e mesa

Exigir:

- mesma fila operacional;
- mesmas respostas, avaliações e pendências;
- mesmo comportamento de whispers;
- mesma integridade de `/revisao/ws/whispers`.

## 11.3 Portal cliente

Exigir:

- mesma consistência entre abas Admin, Chat e Mesa;
- mesmo contrato das rotas `/cliente/api/*`;
- nenhum vazamento de regra entre empresa, inspetor e revisor.

## 11.4 Auth/session/multiportal

Exigir:

- login intacto em todos os portais;
- troca de senha intacta;
- isolamento intacto entre perfis;
- nenhuma mudança silenciosa em cookie, token ou sessão.

## 11.5 Mobile/shared API

Exigir:

- compatibilidade preservada nas rotas usadas pelo app;
- sem alteração de payload consumido por `chatApi.ts`, `mesaApi.ts` e `authApi.ts`;
- nenhuma exigência implícita de atualização do app.

## 12. Validações de saída por fase

| Fase | Para considerar a fase concluída |
| --- | --- |
| Fase 0 | governança aprovada e compreendida |
| Fase 1 | métricas e inventários suficientes para modularizar com segurança |
| Fase 2 | hotspots reduzidos internamente sem quebra de contrato |
| Fase 3 | fronteiras consolidadas e deprecações futuras preparadas sem remoção |

## 13. Regra final de governança

Se uma mudança futura não consegue provar claramente:

- o que não muda;
- como será validada;
- como será revertida;

então ela ainda não está pronta para merge.
