# Refatoração Frontend do Portal do Inspetor

## Objetivo

Organizar o frontend do portal do inspetor para ficar mais limpo, previsível e visualmente consistente, reduzindo redundâncias estruturais e preparando o projeto para uma evolução estética profissional sem regressão funcional.

## Princípios

- Uma responsabilidade por arquivo.
- Um componente visual, uma fonte de verdade.
- Home e workspace com identidades visuais distintas, mas coesas.
- Refatorar primeiro a estrutura, depois a superfície visual.
- Não misturar compatibilidade legada com markup principal.
- Manter cobertura de testes e comportamento estável a cada fase.

## Ordem de Execução

### Fase 1. Estrutura de Templates

Status: `concluída`

Objetivo:
- transformar o template monolítico do portal do inspetor em um compositor;
- extrair sidebar, home, workspace, widget da mesa e modais para parciais;
- preservar IDs, classes, atributos e semântica atuais.

Arquivos alvo:
- `templates/index.html`
- `templates/inspetor/_portal_main.html`
- `templates/inspetor/_sidebar.html`
- `templates/inspetor/_portal_home.html`
- `templates/inspetor/_workspace.html`
- `templates/inspetor/_mesa_widget.html`
- `templates/inspetor/_macros.html`
- `templates/inspetor/modals/_nova_inspecao.html`
- `templates/inspetor/modals/_gate_qualidade.html`
- `templates/inspetor/modals/_perfil.html`

Critérios de aceite:
- `index.html` deixa de concentrar o markup inteiro;
- o portal continua carregando sem alteração funcional;
- os testes de smoke e acesso crítico seguem verdes.

### Fase 2. Sistema Visual do Inspetor

Status: `concluída`

Objetivo:
- consolidar tokens de cor, espaçamento, tipografia, borda, sombra e estados;
- eliminar variações visuais redundantes de cards, botões, badges e modais;
- reforçar hierarquia visual entre home, sidebar e workspace.

Arquivos alvo:
- `static/css/shared/global.css`
- `static/css/shared/layout.css`
- `static/css/shared/app_shell.css`
- nova família `static/css/inspetor/`

Estrutura alvo:
- `static/css/inspetor/tokens.css`
- `static/css/inspetor/shell.css`
- `static/css/inspetor/home.css`
- `static/css/inspetor/workspace.css`
- `static/css/inspetor/mesa.css`
- `static/css/inspetor/modals.css`
- `static/css/inspetor/profile.css`
- `static/css/inspetor/responsive.css`

Critérios de aceite:
- botões, badges, chips e cards seguem padrões únicos;
- a home fica mais respirada e editorial;
- o workspace fica mais técnico, focado e menos ruidoso;
- não existe CSS duplicado entre home e workspace sem motivo explícito.

Entrega executada:
- criação da árvore `static/css/inspetor/`;
- separação em `tokens`, `shell`, `home`, `workspace`, `modals`, `profile`, `mesa` e `responsive`;
- atualização do `base.html` para carregar a família nova em ordem explícita;
- extensão da smoke suite para validar os assets novos.

### Fase 3. Modularização do JavaScript

Status: `concluída`

Objetivo:
- quebrar o arquivo principal do portal em módulos por feature;
- separar boot, estado, home, workspace, pendências, mesa, perfil e notificações;
- reduzir o risco de regressão ao editar uma única área.

Arquivos alvo:
- `static/js/chat/chat_index_page.js`

Estrutura aplicada nesta fase:
- `static/js/chat/chat_index_page.js` como runtime compartilhado e bootstrap
- `static/js/inspetor/modals.js`
- `static/js/inspetor/pendencias.js`
- `static/js/inspetor/mesa_widget.js`
- `static/js/inspetor/notifications_sse.js`

Critérios de aceite:
- `chat_index_page.js` deixa de concentrar modal, pendências, mesa e SSE em um único corpo;
- cada módulo expõe uma responsabilidade clara por `ctx.actions`;
- o boot passa a compor as features carregadas em `templates/index.html`.

### Fase 4. Limpeza de Compatibilidade e Redundâncias

Status: `concluída`

Objetivo:
- remover blocos de compatibilidade escondidos do DOM principal;
- consolidar helpers e evitar múltiplas formas de representar o mesmo estado;
- reduzir dependências implícitas entre template, CSS e JS.

Alvos prioritários:
- blocos `inspetor-runtime-compat`
- blocos `modal-runtime-compat`
- trechos duplicados de estado em `chat_*`
- markup e estilos que existem apenas para legados internos

Critérios de aceite:
- o DOM final reflete a interface real, não artefatos de transição;
- os estados de laudo, mesa e home possuem um caminho único de leitura.

Entrega executada:
- remoção dos blocos `inspetor-runtime-compat` do workspace e da sidebar;
- remoção do bloco `modal-runtime-compat` do modal de nova inspeção;
- promoção de controles reais para mesa, contexto do rodapé e nome da inspeção;
- simplificação do bootstrap para usar o estado vazio real da sidebar e parar de depender de IDs extintos.

### Fase 5. Polimento Visual e Consistência Final

Status: `concluída`

Objetivo:
- revisar ritmo visual, alinhamento, contraste, vazios, responsividade e microinterações;
- garantir uma estética mais organizada, limpa e profissional;
- padronizar a percepção de qualidade entre login, home e workspace.

Entregáveis:
- revisão final de grid e spacing;
- padronização de cabeçalhos, vazios e estados de loading;
- refinamento do modo foco;
- revisão de acessibilidade visual.

Entrega executada:
- reorganização visual da home com hero editorial, superfícies de seção e sinais operacionais;
- refinamento do workspace com cabeçalho mais claro, mensagens mais legíveis e cards laterais mais consistentes;
- revisão da responsividade para preservar a leitura do workspace sem padding improvisado em breakpoints menores;
- consolidação do contrato visual dark premium em `tokens.css`, com base alinhada ao design system e ajuste intencional de alvos secundários para `40px` no runtime do inspetor.

### Fase 6. Isolamento Visual do Portal

Status: `concluída`

Objetivo:
- remover o portal do inspetor da cascata visual antiga;
- concentrar a aparência ativa do portal em uma camada própria;
- parar de carregar CSS legado desnecessário no runtime do inspetor.

Entrega executada:
- criação de `templates/inspetor/base.html` como base dedicada do portal;
- remoção de `shared/layout.css`, `chat/chat_base.css` e `chat/chat_mobile.css` do pipeline visual do inspetor;
- ativação de `static/css/inspetor/reboot.css` como camada visual principal do portal;
- remoção da família `inspetor/{shell,home,workspace,modals,profile,mesa,responsive}.css` do carregamento em runtime e do pre-cache do service worker;
- manutenção dos arquivos antigos apenas como referência de migração até a exclusão definitiva.

## Backlog Executivo

### Alta prioridade

- decompor `index.html`;
- reduzir acoplamento do portal a um único JS gigante;
- consolidar tokens e componentes visuais;
- remover compatibilidade escondida do template principal.

### Média prioridade

- reorganizar CSS do inspetor em árvore dedicada;
- separar home e workspace em estilos independentes;
- revisar estados vazios, fallbacks e banners.

### Baixa prioridade

- criar catálogo visual interno de componentes do inspetor;
- documentar guidelines visuais para futuras telas do portal.

## Riscos Controlados

- mover estrutura cedo demais sem validar smoke pode quebrar IDs usados no JS;
- modularizar JS antes de estabilizar os templates aumenta retrabalho;
- mexer em visual sem tokens consolidados tende a gerar nova redundância.

## Estratégia de Validação

- `node --check static/js/chat/chat_index_page.js`
- `python -m pytest tests/test_smoke.py -q`
- `python -m pytest tests/test_portais_acesso_critico.py -q`
- suíte dirigida do inspetor em `tests/test_regras_rotas_criticas.py`

## Resultado Esperado

Ao final da refatoração, o portal do inspetor deve ter:

- estrutura de templates legível;
- fronteiras claras entre home, workspace, mesa e perfil;
- sistema visual uniforme;
- frontend sem redundâncias óbvias;
- base pronta para evolução estética de alto nível sem fragilidade operacional.
