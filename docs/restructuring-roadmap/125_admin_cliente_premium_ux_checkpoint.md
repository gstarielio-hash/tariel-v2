# Admin-Cliente - checkpoint de UX premium

Criado em `2026-04-01`.

## Objetivo

Fechar o pacote de acabamento premium do `admin-cliente` sem reabrir auth, sessao, contratos sensiveis do backend ou a fronteira de governanca ja consolidada do tenant.

## O que entrou

- a shell do portal cliente ganhou hero executivo, CTA dominante, faixa de KPIs e leitura mais clara do foco atual do tenant;
- o painel `admin` passou a ter briefs por secao, subnavegacao com hierarquia mais forte e cards com peso visual melhor calibrado;
- a area de `support` passou a exibir politica de suporte, protocolo recente, resumo executivo da timeline, busca textual e filtros operacionais;
- `chat` e `mesa` ganharam fallbacks SSR mais fortes para `?sec=`, com textos iniciais coerentes para deep link, reload e historico;
- a navegacao do `admin` foi endurecida como URL-first nas subabas, preservando back/forward e reload sem estado hibrido fragil;
- o tema do portal cliente recebeu refinamento de tipografia, espacamento, contraste, superficies, motion e mobile para deixar a experiencia mais madura.

## Hotspots desta rodada

- `web/templates/cliente/_shell_header.html`
- `web/templates/cliente/painel/_content.html`
- `web/templates/cliente/painel/_overview.html`
- `web/templates/cliente/painel/_capacity.html`
- `web/templates/cliente/painel/_team.html`
- `web/templates/cliente/painel/_support.html`
- `web/templates/cliente/chat/_content.html`
- `web/templates/cliente/mesa/_content.html`
- `web/static/js/cliente/portal_shell.js`
- `web/static/js/cliente/portal_admin_surface.js`
- `web/static/js/cliente/painel_page.js`
- `web/static/js/cliente/portal.js`
- `web/static/css/cliente/portal_admin_theme.css`

## Validacao executada

Checks de sintaxe:

```bash
node --check web/static/js/cliente/portal.js
node --check web/static/js/cliente/portal_shell.js
node --check web/static/js/cliente/portal_admin_surface.js
node --check web/static/js/cliente/painel_page.js
```

Recortes focais:

```bash
pytest tests/test_smoke.py -q -k 'templates_cliente_explicitam_abas_e_formularios_principais or test_portais_principais_referenciam_marca_nos_templates_de_login'
pytest tests/test_portais_acesso_critico.py -q -k 'admin_cliente_login_funciona_e_painel_abre or admin_cliente_links_diretos_por_secao_resolvem_alias_e_fallback'
pytest tests/test_cliente_portal_critico.py -q -k 'exporta_diagnostico_e_registra_suporte or filtra_auditoria_por_superficie_operacional'
```

Resultado:

- `6 passed`

Recorte browser:

```bash
env RUN_E2E=1 pytest tests/e2e/test_portais_playwright.py -q -k 'admin_cliente_deep_links_por_secao_preservam_shell_e_historico' -rs
```

Resultado:

- `1 passed, 36 deselected`

## O que isso fecha

- o `admin-cliente` deixa de dever acabamento premium local;
- a shell administrativa do tenant passa a ter leitura mais clara, mais cara e mais estavel sem sacrificar progressividade;
- o pacote premium do portal cliente deixa de ser apenas proposta e vira checkpoint verificavel.

## O que continua fora

- redesign premium amplo do produto inteiro fora do `admin-cliente`;
- reabertura de auth, sessao, contratos do chat ou contrato tecnico bruto por causa de UX;
- expansao cross-tenant dentro do papel `admin-cliente`.

## Leitura final

O `admin-cliente` agora fica fechado em tres camadas: estrutura, governanca residual e acabamento premium local. O que sobra daqui para frente ja nao e “arrumar o portal cliente”, e sim evolucao de outras superficies ou linguagem premium mais ampla do produto.
