# 09. Dívida Técnica e Riscos

Este documento faz uma leitura franca do estado técnico do sistema: o que está bom, o que está apenas administrável e o que já parece frágil ou arriscado.

## 1. O que está bom

## 1.1 Organização macro do backend

Pontos positivos confirmados:

- backend organizado por domínio em `web/app/domains/`;
- camada compartilhada explícita em `web/app/shared/`;
- bootstrap centralizado em `web/main.py`;
- configuração e segurança HTTP separadas em `web/app/core/`.

Leitura:

- a base não é caótica no nível macro;
- existe intenção arquitetural clara de monólito modular.

## 1.2 Multiportal tratado como requisito real

Pontos positivos:

- o sistema isola estado por portal;
- autenticação e sessão conhecem o contexto `/admin`, `/cliente`, `/app` e `/revisao`;
- há testes cobrindo acesso crítico aos portais.

Leitura:

- essa é uma parte madura e importante, porque evita mistura de perfis em uma app única.

## 1.3 Banco e migrações

Pontos positivos:

- Alembic versionado;
- modelos consistentes;
- índices relevantes em entidades críticas;
- separação razoável entre auth/empresa e laudo/operação.

## 1.4 Cobertura de qualidade

Pontos positivos:

- CI web com Ruff, mypy, pytest e Playwright;
- CI mobile com typecheck, lint, format e Jest;
- testes de realtime, websocket, portais e regras críticas.

Leitura:

- a dívida técnica do projeto não decorre de ausência total de processo.

## 2. O que está “mais ou menos”

## 2.1 Modularidade interna desigual

O projeto está bem separado em nível de pasta, mas de forma desigual em nível de arquivo.

Sinais:

- alguns domínios são relativamente bem recortados;
- outros ainda concentram fluxos demais em arquivos muito grandes;
- o frontend web segue mais “modularidade por convenção” do que encapsulamento real.

## 2.2 Portal cliente

Leitura:

- o portal cliente é uma boa ideia de produto;
- tecnicamente, ele depende fortemente de bridges para `chat` e `revisor`;
- isso reduz duplicação, mas aumenta acoplamento.

Conclusão:

- solução pragmaticamente boa, mas não barata de manter.

## 2.3 Biblioteca de templates

Leitura:

- parece ser um subsistema relevante e bem encaminhado;
- ao mesmo tempo, já se espalhou por vários arquivos grandes;
- pode crescer mais rápido do que a estrutura atual comporta com conforto.

## 3. O que está perigoso

## 3.1 Arquivos grandes demais

Exemplos críticos:

- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/admin/services.py`
- `web/app/domains/revisor/templates_laudo_support.py`
- `web/app/domains/revisor/templates_laudo_management_routes.py`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `android/src/features/InspectorMobileApp.tsx`

Risco:

- alteração pequena tende a ter raio de impacto amplo;
- leitura e revisão ficam caras;
- testes ajudam, mas não resolvem a dificuldade de raciocínio local.

## 3.2 Compatibilidade legada ainda visível

Evidências:

- wrappers legados na raiz de `web/`;
- fachadas compatíveis como `chat/routes.py`, `chat/auth.py`, `revisor/routes.py`;
- comentários e camadas de compatibilidade no frontend shared.

Risco:

- aumenta ambiguidade sobre a fonte de verdade;
- dificulta saber o que ainda é contrato ativo e o que é apenas ponte de migração.

## 3.3 Frontend web global demais

Evidências:

- uso de `window.*` em módulos compartilhados;
- ordem de `<script>` importa;
- ausência de bundler moderno;
- JS de portal muito centralizado.

Risco:

- manutenção mais frágil;
- bugs de inicialização e acoplamento implícito;
- custo alto para modernizar incrementalmente.

## 3.4 Fluxos críticos muito orquestrados dentro do request

Evidências:

- chat do inspetor integra validação, persistência, IA, commands e mesa;
- geração de documentos segue no caminho síncrono;
- painel do revisor monta muita coisa em tempo de request.

Risco:

- latência variável;
- debugging difícil em cenários mistos;
- risco de regressão funcional e de performance ao mesmo tempo.

## 4. O que parece legado

### Backend

- `web/banco_dados.py`
- `web/seguranca.py`
- `web/rotas_admin.py`
- `web/rotas_inspetor.py`
- `web/servicos_saas.py`
- scripts CLI antigos na raiz de `web/`

### Frontend web

- base genérica antiga e parte dos componentes históricos;
- CSS antigos mantidos como referência de migração;
- aliases/event bridges em módulos shared.

Leitura:

- o legado não domina o sistema inteiro;
- ele aparece como camada residual em torno do núcleo atual.

## 5. O que parece duplicado ou próximo disso

### Autenticação por portal

Cada portal tem suas telas e fluxos próprios de login/troca de senha. Isso é coerente com UX e isolamento, mas gera repetição estrutural controlada.

### Portais com shell própria

- inspetor
- cliente
- revisor
- admin

Isso é natural do produto, mas implica menos compartilhamento de frontend do que um design system mais formal permitiria.

### Lógicas similares de chat/mesa em várias superfícies

O código tenta evitar duplicação total via bridge, mas o custo é:

- wrappers;
- adaptadores;
- múltiplos pontos de entrada para as mesmas regras.

## 6. Onde o acoplamento é mais forte

| Área | Tipo de acoplamento | Comentário |
| --- | --- | --- |
| `shared.database` | estrutural | Hub de importação para o backend inteiro. |
| `shared.security` | transversal | Quase toda superfície autenticada depende dela. |
| `chat` + `nucleo/cliente_ia.py` | funcional | Fluxo principal depende de integração externa. |
| `cliente` + `chat` + `revisor` | composicional | O portal cliente reaproveita ambos. |
| frontend inspetor | client-side | Muitos módulos interdependentes na mesma página. |
| revisor templates | documental | CRUD, diff, preview, status e publicação no mesmo subsistema. |

## 7. O que depende de decisão de produto

- Quanto do portal cliente deve continuar sendo “portal unificado” em uma única tela.
- Quanto da biblioteca de templates vai crescer em poder de edição e workflow.
- Qual o papel de “aprendizado visual” na operação futura.
- Se o mobile continuará sendo apenas do inspetor ou ganhará mais escopo.

## 8. O que depende de decisão de backend

- Se o fluxo de IA e exportações deve ganhar fila assíncrona dedicada.
- Se o portal cliente deve seguir com bridges ou receber serviços próprios mais claros.
- Se o realtime continuará restrito ao revisor ou será expandido.
- Se a camada compartilhada precisa de contratos mais explícitos e menores.

## 9. O que deveria ser priorizado primeiro em futura refatoração

### Prioridade técnica alta

- reduzir responsabilidade do fluxo central de chat;
- quebrar os maiores controllers JS;
- tornar mais explícitos os contratos internos entre `cliente`, `chat` e `revisor`;
- mapear com instrumentação as consultas do painel revisor.

### Prioridade técnica média

- reduzir compat layers ainda visíveis;
- limpar a fronteira entre CSS ativo e CSS legado;
- formalizar melhor o inventário de endpoints consumidos pelo mobile.

## 10. Áreas com maior chance de bug ou regressão

- transições de estado do laudo;
- mesa avaliadora e whispers;
- portal cliente por acoplamento cruzado;
- templates de laudo e publicação;
- frontend inspetor no primeiro carregamento e troca de contexto;
- sessão e autenticação multiportal.

## 11. Arquivos que merecem cautela extra em qualquer mudança futura

- `web/main.py`
- `web/app/shared/database.py`
- `web/app/shared/security.py`
- `web/app/shared/security_session_store.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/cliente/portal_bridge.py`
- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/realtime.py`
- `web/app/domains/revisor/templates_laudo_support.py`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `android/src/features/InspectorMobileApp.tsx`

## Confirmado no código

- A arquitetura macro é melhor do que a modularidade interna dos maiores arquivos.
- O sistema tem qualidade e cobertura relevantes, mas concentra demais em hotspots específicos.
- Há legado residual e compatibilidade histórica ainda presentes.
- Frontend web e backend compartilham o mesmo problema estrutural: alguns arquivos viraram “centros de gravidade”.

## Inferência provável

- O principal risco do projeto não é colapso total de arquitetura, e sim erosão gradual de mantenibilidade.
- Sem uma estratégia deliberada de contenção, novos recursos tenderão a continuar entrando nos mesmos hotspots já saturados.
- Parte da dívida técnica atual é consequência de sucesso de produto e expansão funcional em cima de um monólito que ainda segura bem a operação.

## Dúvida aberta

- Não está claro se a equipe já possui métricas internas que sustentem uma priorização objetiva dessas dívidas. O código evidencia os hotspots, mas não mostra a ordem real de dor em produção.
