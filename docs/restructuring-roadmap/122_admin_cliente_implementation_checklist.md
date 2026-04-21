# Admin-Cliente - checklist pratico de implementacao

Criado em `2026-03-31`.

## Contexto

Este documento transforma a trilha de produto consolidada em `Tarie 2/docs/65_MATRIZ_RESPONSABILIDADE_ADMIN_CLIENTE.md`, `66_GAP_ANALISE_ADMIN_CLIENTE.md` e `67_ORDEM_DE_EXECUCAO_ADMIN_CLIENTE_INSPETOR_MESA_E_SUPORTE.md` em um checklist executavel no repositorio principal.

Ele parte de um estado em que a `Fase 07 - Cliente e admin` ja foi promovida em `docs/restructuring-roadmap/116_phase7_cliente_admin_closure.md`, mas ainda restam lacunas de governanca, auth, semantica e UX no portal `admin-cliente`.

## Objetivo

Fechar o portal `admin-cliente` como superficie canonica da empresa cliente, sem misturar:

- governanca comercial da Tariel;
- governanca do tenant;
- operacao do tenant;
- suporte excepcional do `admin-geral`.

## Invariantes

Estas regras nao devem mudar durante a execucao do checklist:

- `tenant boundary` continua rigido em `/cliente`, `/admin`, `/app` e `/revisao`;
- `chat` e `mesa` continuam company-scoped no portal cliente;
- `/cliente/api/diagnostico` e `/cliente/api/suporte/report` continuam operacionais;
- `RBAC`, `CSRF` e trilha de auditoria continuam obrigatorios nas mutacoes;
- mudanca comercial efetiva de plano continua pertencendo ao `admin-geral`;
- o portal cliente continua sendo consumidor do bootstrap existente, sem troca big bang de payload.

## Premissa operacional recomendada

Assumir `hierarquia estrita` como padrao de implementacao, porque essa e a direcao mais coerente na documentacao atual:

- `admin-geral` cria e governa contas `admin_cliente`;
- `admin-cliente` governa apenas `inspetor` e `revisor`.

Se houver decisao explicita futura para suportar multiplos `admin_cliente` por tenant, reabrir apenas os itens marcados como `decision gate`, sem desfazer os demais cortes.

## Hotspots reais no codigo

### Backend

- `web/app/domains/cliente/management_routes.py`
- `web/app/domains/cliente/dashboard.py`
- `web/app/domains/cliente/dashboard_bootstrap_support.py`
- `web/app/domains/cliente/dashboard_bootstrap.py`

### Frontend e templates

- `web/templates/cliente_portal.html`
- `web/templates/login_cliente.html`
- `web/static/js/cliente/portal.js`
- `web/static/js/cliente/portal_admin.js`
- `web/static/js/cliente/portal_bindings.js`
- `web/static/js/cliente/portal_chat.js`
- `web/static/js/cliente/portal_shared_helpers.js`
- `web/static/css/cliente/portal.css`
- `web/static/css/shared/auth_shell.css`

### Gates existentes de teste

- `web/tests/test_cliente_portal_critico.py`
- `web/tests/test_portais_acesso_critico.py`
- `web/tests/test_tenant_boundary_matrix.py`
- `web/tests/test_session_auth_audit_matrix.py`
- `web/tests/test_cliente_route_support.py`
- `web/tests/test_smoke.py`
- `web/tests/test_v2_tenant_admin_projection.py`
- `web/tests/e2e/test_portais_playwright.py`

## Ordem executavel

### Fase A - governanca e escopo do tenant

Objetivo:

- retirar governanca comercial direta do portal cliente;
- alinhar a gestao de usuarios ao papel real do tenant.

Checklist:

- substituir a mutacao direta `PATCH /cliente/api/empresa/plano` por trilha de `preview + solicitacao/interesse`;
- manter `POST /cliente/api/empresa/plano/interesse` como trilha auditavel do tenant;
- reescrever a UI de plano para remover `Salvar plano` e comunicar `Solicitar mudanca` ou `Registrar interesse`;
- remover `admin_cliente` do formulario de criacao de usuario no portal cliente;
- remover `admin_cliente` dos filtros e textos que sugerem autoprovisionamento no mesmo nivel;
- preservar gestao de `inspetor` e `revisor`, incluindo bloqueio, reset e edicao;
- revisar qualquer mensagem de auditoria que ainda descreva alteracao comercial imediata pelo tenant.

Arquivos-alvo:

- `web/app/domains/cliente/management_routes.py`
- `web/templates/cliente_portal.html`
- `web/static/js/cliente/portal_admin.js`
- `web/static/js/cliente/portal_bindings.js`
- `web/static/js/cliente/portal_chat.js`
- `web/static/js/cliente/portal_shared_helpers.js`

Ponto de decisao:

- se o produto insistir em multiplos `admin_cliente`, manter apenas o backend/UX de criacao de pares; todo o resto da fase continua igual.

Validacao minima:

- reescrever `test_admin_cliente_altera_plano_apenas_da_propria_empresa` para refletir bloqueio ou desvio para interesse;
- manter verde `test_admin_cliente_registra_interesse_em_upgrade_no_historico`;
- adicionar cobertura garantindo que `/cliente/api/usuarios` rejeita `nivel_acesso=admin_cliente` quando a hierarquia estrita estiver ativa;
- revalidar `tenant boundary` e a impossibilidade de o portal cliente gerir `admin-geral`.

Critico para concluir:

- nenhum caminho do portal cliente conclui troca comercial de plano;
- nenhum CTA do portal cliente sugere que o tenant cria novo `admin_cliente` por padrao;
- a auditoria do tenant registra interesse comercial, nao alteracao comercial efetiva.

### Fase B - honestidade de produto no auth

Objetivo:

- parar de prometer fluxos que ainda nao existem.

Checklist:

- remover ou implementar de verdade o CTA de `Esqueceu a senha?`;
- remover ou implementar de verdade os botoes de login com `Google` e `Microsoft`;
- manter a tela de login restrita ao que o ambiente realmente suporta hoje;
- revisar os textos que mandam o tenant escalar tudo ao `Admin-CEO`, evitando vazamento de semantica de plataforma dentro da experiencia principal do cliente.

Arquivos-alvo:

- `web/templates/login_cliente.html`
- `web/app/domains/cliente/route_support.py`
- `web/tests/test_cliente_route_support.py`
- `web/tests/test_smoke.py`

Validacao minima:

- testar `GET /cliente/login` para garantir que a pagina nao exibe CTAs stubados;
- manter login, logout e troca obrigatoria de senha funcionando;
- garantir que a remocao dos stubs nao quebre CSP, nonce ou o fluxo de erro do formulario.

Critico para concluir:

- a tela de login so anuncia o que existe de verdade no produto;
- o tenant nao encontra CTA falso para social login ou recuperacao ainda nao implementada.

### Fase C - isolamento semantico e drenagem de compatibilidade

Objetivo:

- limpar residuos conceituais do `admin-geral` do portal cliente;
- reduzir o peso da camada `temporaryCompat` sem trocar o bootstrap em big bang.

Checklist:

- remover a observacao de compatibilidade que ancora `Admin-CEO` em `web/app/domains/cliente/dashboard.py`;
- eliminar rotulagem residual de `Admin-CEO` em `ROLE_LABELS` do portal cliente quando ela nao for mais necessaria ao payload;
- revisar o bootstrap para que a superficie cliente exponha apenas os papeis que o tenant realmente governa;
- inventariar os modulos marcados com `temporaryCompat: true` em `web/static/js/cliente/portal.js`;
- promover a primeira rodada de drenagem para reduzir bridges globais, preservando o contrato de boot;
- evitar recentralizar logica em `portal.js`; a reducao de compatibilidade deve mover responsabilidade para modulos canonicos, nao para o shell.

Arquivos-alvo:

- `web/app/domains/cliente/dashboard.py`
- `web/app/domains/cliente/dashboard_bootstrap_support.py`
- `web/app/domains/cliente/dashboard_bootstrap.py`
- `web/static/js/cliente/portal.js`
- `web/static/js/cliente/portal_admin.js`
- `web/static/js/cliente/portal_chat.js`
- `web/static/js/cliente/portal_bindings.js`

Validacao minima:

- manter `test_v2_tenant_admin_projection.py` verde para garantir que o bootstrap nao quebrou;
- manter `test_smoke.py` verde no recorte de portais;
- rodar smoke focal do portal cliente e, se houver mudanca de boot, executar tambem o recorte Playwright do portal.

Critico para concluir:

- o portal cliente deixa de carregar semantica de governanca Tariel como parte normal da experiencia;
- a camada de compatibilidade fica menor e explicitamente mapeada.

### Fase D - auth proprio, simplificacao de UX e acabamento

Objetivo:

- isolar visual e assets do portal cliente;
- reduzir densidade e ruido sem reabrir redesign premium amplo.

Checklist:

- separar o login cliente do `shared/auth_shell.css` se isso ainda o mantiver acoplado ao shell compartilhado;
- reduzir estilos inline em `cliente_portal.html`;
- simplificar a secao administrativa para comunicar claramente:
  - empresa;
  - equipe;
  - chat;
  - mesa;
  - suporte e diagnostico;
- rever microcopy para reforcar que a empresa administra os servicos contratados, nao a plataforma Tariel;
- manter a ergonomia atual de suporte e diagnostico, mas reduzir altura e densidade excessivas.

Arquivos-alvo:

- `web/templates/login_cliente.html`
- `web/templates/cliente_portal.html`
- `web/static/css/cliente/portal.css`
- `web/static/css/cliente/` se nascer auth proprio
- `web/static/js/cliente/portal_admin.js`

Validacao minima:

- smoke HTML do portal cliente;
- recorte visual/e2e do cliente em `web/tests/e2e/test_portais_playwright.py` se houver alteracao estrutural de layout ou seletores;
- revalidar acessibilidade basica de formulario e tab principal.

Critico para concluir:

- a UI comunica o papel correto do `admin-cliente`;
- o portal parece console administrativo de tenant, nao painel de governanca global.

## Sequencia recomendada de commits

1. `admin-cliente: trocar mutacao de plano por trilha de interesse`
2. `admin-cliente: restringir criacao de usuarios a inspetor e revisor`
3. `admin-cliente: remover stubs de auth nao implementados`
4. `admin-cliente: limpar semantica residual e reduzir temporaryCompat`
5. `admin-cliente: isolar auth e simplificar UX`

## Pacote minimo de validacao por rodada

Rodar no minimo:

```bash
pytest web/tests/test_cliente_portal_critico.py -q
pytest web/tests/test_portais_acesso_critico.py -q
pytest web/tests/test_tenant_boundary_matrix.py -q
pytest web/tests/test_session_auth_audit_matrix.py -q
pytest web/tests/test_cliente_route_support.py -q
pytest web/tests/test_smoke.py -q
pytest web/tests/test_v2_tenant_admin_projection.py -q
```

Se houver mudanca estrutural no frontend do portal cliente, complementar com:

```bash
pytest web/tests/e2e/test_portais_playwright.py -q
```

## Rollback

Se alguma rodada abrir regressao, reverter primeiro por slice:

- backend de plano/interesse;
- gestao de usuarios do tenant;
- login/auth cliente;
- boot do portal cliente;
- UX do painel.

Nao misturar rollback de governanca com rollback visual no mesmo commit.

## Definicao de pronto

O trabalho pode ser considerado fechado quando:

- `admin-cliente` opera apenas o escopo correto do tenant;
- `admin-geral` permanece como dono de plano, billing e governanca superior;
- login e UX do portal cliente nao prometem fluxos inexistentes;
- residuos semanticos de `Admin-CEO` saem do portal cliente;
- `temporaryCompat` deixa de ser pilar estrutural do boot do portal cliente;
- o pacote focal de testes permanece verde.

## Proximo passo direto

Executar a `Fase A` primeiro, porque ela corrige a governanca do tenant sem depender de redesign visual amplo e desbloqueia o resto do fechamento do portal `admin-cliente`.
