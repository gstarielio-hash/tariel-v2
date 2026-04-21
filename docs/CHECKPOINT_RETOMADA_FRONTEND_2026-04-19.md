# Checkpoint de Retomada do Frontend

Data de referência: 2026-04-19
Objetivo: permitir retomada exata do trabalho a partir do mesmo ponto, sem depender do contexto da conversa.

## 1. Projeto oficial

- Repositório local oficial:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- Backend oficial:
  - o backend ativo do produto também vive neste mesmo repositório, dentro de `web/`
- Frontend oficial:
  - `web/templates`
  - `web/static`
- Não usar `/tmp` como base de código do produto
- Todo o trabalho recente foi feito no projeto oficial acima

## 2. Git atual

- Branch operacional atual:
  - `checkpoint/20260331-current-worktree`
- HEAD local no momento deste checkpoint:
  - `5aea5f41f9fae77a20fc79e89ea221e3eed3e933`
- HEAD remoto confirmado para a mesma branch:
  - `5aea5f41f9fae77a20fc79e89ea221e3eed3e933`
- Estado do worktree:
  - limpo

## 3. GitHub oficial

- Remoto oficial em uso:
  - `origin -> git@github.com:gstarielio-hash/tariel-web.git`
- Remoto antigo ainda presente no repo, mas não usado como oficial:
  - `github-antigo -> https://github.com/gabrisantoss/tariel-control.git`
- Perfil GitHub oficial considerado nesta frente:
  - `gstarielio-hash`

## 4. Render oficial

### 4.1 Blueprint versionado no repo

Arquivo:

- [render.yaml](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/render.yaml)

Configuração relevante encontrada no arquivo:

- serviço web:
  - `name: tarie-ia`
- `rootDir: web`
- `autoDeploy: true`
- `healthCheckPath: /health`
- runtime:
  - `python`

### 4.2 URL documentada do serviço online

Referência já documentada no próprio repositório:

- `https://tariel-web-free.onrender.com`

### 4.3 Estado operacional verificado agora

Foi feita uma tentativa de probe direta em:

- `https://tariel-web-free.onrender.com/health`

Resultado desta checagem agora:

- `curl --max-time 20` terminou com timeout
- código HTTP retornado:
  - `000`

Leitura prática:

- o endpoint documentado continua sendo este;
- neste instante ele não respondeu em 20s;
- isso é compatível com cold start, wake-up lento ou indisponibilidade temporária;
- o repositório confirma a configuração do deploy, mas o mapeamento exato da branch ativa no dashboard Render não fica versionado no repo.

## 5. Rotas web principais para retomada de teste

### Relativas

- Admin CEO:
  - `/admin/login`
- Portal da Empresa:
  - `/cliente/login`
- Inspetor Web:
  - `/app/login`
- Revisão Técnica:
  - `/revisao/login`

### Absolutas, usando a URL documentada do Render

- `https://tariel-web-free.onrender.com/admin/login`
- `https://tariel-web-free.onrender.com/cliente/login`
- `https://tariel-web-free.onrender.com/app/login`
- `https://tariel-web-free.onrender.com/revisao/login`

## 6. Estado do loop de refatoração do frontend

Arquivo âncora do loop:

- [LOOP_REFATORACAO_FRONTEND.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/docs/LOOP_REFATORACAO_FRONTEND.md)

Esse arquivo é a memória operacional principal do loop.
Ele foi atualizado para sobreviver à compactação de contexto.

### Regras do loop

Cada ciclo segue:

1. reanalisar o maior hotspot seguro;
2. escolher um corte pequeno e coeso;
3. refatorar sem alterar regra de negócio;
4. validar;
5. commit;
6. push;
7. registrar o próximo hotspot.

## 7. Ciclos concluídos nesta fase

### Ciclo 0

- commit:
  - `a621c34`
- mensagem:
  - `fix(web): restore critical branch health`

### Ciclo 1

- commit:
  - `b875502`
- mensagem:
  - `refactor(web): extract inspector ui bindings`
- entrega principal:
  - extração dos bindings de UI do inspetor para módulo próprio

### Ajuste de teste entre ciclos

- commit:
  - `59eb93d`
- mensagem:
  - `test(web): align smoke check with ui bindings module`
- motivo:
  - um smoke test ainda assumia wiring preso ao arquivo monolítico antigo

### Ciclo 2

- commit:
  - `8c8e6af`
- mensagem:
  - `refactor(web): extract inspector domain events`
- entrega principal:
  - eventos de domínio do inspetor saíram do arquivo principal

### Ciclo 3

- commit:
  - `2e34d94`
- mensagem:
  - `refactor(web): extract inspector bootstrap flow`
- entrega principal:
  - boot/orquestração do inspetor saiu para módulo próprio

### Ciclo 4

- commit:
  - `3ea6792`
- mensagem:
  - `refactor(web): extract inspector observers`
- entrega principal:
  - observers de sidebar e workspace saíram do arquivo principal

### Ciclo 5

- commit:
  - `5aea5f4`
- mensagem:
  - `refactor(web): extract inspector workspace derivatives`
- entrega principal:
  - derivadas do workspace saíram do arquivo principal

### Ciclo 6

- commit:
  - `4e5c8c3`
- mensagem:
  - `refactor(web): extract inspector governance module`
- entrega principal:
  - governança documental do inspetor saiu para módulo próprio

### Ciclo 7

- commit:
  - `pendente no momento deste checkpoint`
- mensagem:
  - `refactor(web): extract inspector workspace overview`
- entrega principal:
  - resumo executivo, navegação e cards documentais do workspace saíram para módulo próprio

## 8. Arquivos novos criados nesta fase do loop

- [ui_bindings.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/ui_bindings.js)
- [system_events.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/system_events.js)
- [bootstrap.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/bootstrap.js)
- [observers.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/observers.js)
- [workspace_derivatives.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/workspace_derivatives.js)
- [governance.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/governance.js)
- [workspace_overview.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/workspace_overview.js)

## 9. Redução real do hotspot principal

Arquivo principal atacado:

- [chat_index_page.js](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_index_page.js)

Estado atual:

- linhas atuais:
  - `7058`

Leitura prática:

- o arquivo continua grande;
- mas já perdeu blocos centrais de UI, eventos, bootstrap, observers, derivadas do workspace, governança e overview do workspace;
- a direção estrutural está correta;
- ainda não terminou.

## 10. Validações que vêm sendo usadas e passaram nos ciclos recentes

### Checagens estáticas

- `git diff --check`
- `node --check web/static/js/chat/chat_index_page.js`
- `node --check web/static/js/inspetor/*.js` no arquivo alterado do ciclo

### Smoke local

- `pytest -q web/tests/test_smoke.py`

### Auditoria visual do inspetor

- `python3 web/scripts/inspecao_visual_inspetor.py`

### E2E real do inspetor

- `RUN_E2E=1 AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py`

### Hook crítico no push

- `web critical pytest`

## 11. Capturas geradas nesta fase

Diretório base:

- `web/artifacts/visual/inspetor/`

Capturas relevantes mais recentes:

- [20260419-164640](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/artifacts/visual/inspetor/20260419-164640/index.html)
- [20260419-165926](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/artifacts/visual/inspetor/20260419-165926/index.html)
- [20260419-170731](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/artifacts/visual/inspetor/20260419-170731/index.html)
- [20260419-171340](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/artifacts/visual/inspetor/20260419-171340/index.html)
- [20260419-172458](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/artifacts/visual/inspetor/20260419-172458/index.html)
- [20260419-183729](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/artifacts/visual/inspetor/20260419-183729/index.html)
- [20260419-184957](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/artifacts/visual/inspetor/20260419-184957/index.html)

## 12. Próximo ponto exato de retomada

O loop deve retomar daqui:

1. revisar extrações restantes do fluxo de mesa;
2. separar mais blocos de contexto IA e ações do workspace;
3. só depois decidir se continua no inspetor ou passa para hotspots grandes de template/CSS do admin e revisão.

Leitura prática:

- ainda estamos na refatoração estrutural do frontend web;
- o foco principal continua sendo o inspetor web;
- a próxima extração segura ficou mais próxima do fluxo de mesa e do contexto IA do workspace do que do núcleo de regras.
- o mobile ainda não entrou na frente de corte grande nesta rodada;
- a estratégia continua sendo pequenos cortes com commit e push a cada ciclo.

## 13. Comandos recomendados para retomar depois

### Entrar no projeto

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
```

### Confirmar branch e limpeza

```bash
git status --short --branch
git log --oneline -8
```

### Ler o estado operacional

```bash
sed -n '1,260p' docs/CHECKPOINT_RETOMADA_FRONTEND_2026-04-19.md
sed -n '1,260p' docs/LOOP_REFATORACAO_FRONTEND.md
```

### Reabrir o hotspot atual

```bash
sed -n '1,260p' web/static/js/inspetor/workspace_derivatives.js
rg -n "mesa|governanca|resumo executivo|workspace" web/static/js/chat/chat_index_page.js web/static/js/inspetor
```

### Validar antes do próximo commit

```bash
git diff --check
pytest -q web/tests/test_smoke.py
python3 web/scripts/inspecao_visual_inspetor.py
RUN_E2E=1 AMBIENTE=dev pytest -q web/tests/e2e/test_inspetor_visual_playwright.py
```

## 14. Resumo operacional curto

Se precisar retomar sem reler tudo:

- projeto oficial:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- GitHub oficial:
  - `gstarielio-hash/tariel-web`
- branch:
  - `checkpoint/20260331-current-worktree`
- HEAD:
  - `5aea5f4`
- worktree:
  - limpo
- Render:
  - blueprint versionado em `render.yaml`
  - `rootDir: web`
  - `autoDeploy: true`
  - URL documentada: `https://tariel-web-free.onrender.com`
  - probe agora: timeout em 20s
- loop atual:
  - 5 ciclos concluídos
- próximo alvo:
  - fluxo de mesa + governança/resumo executivo do inspetor
