# Regressao Integral Operacional

Runner unico para validar o produto em camadas e registrar bugs, acertos e o manifesto real de cobertura de cada rodada.

## Objetivo

Evitar depender de varios comandos soltos quando a meta e responder:

- criacao de contas ainda funciona?
- portais continuam isolados?
- inspetor continua criando e finalizando laudo?
- mesa continua operando, exportando e emitindo?
- o ambiente online hospedado continua coerente?
- quais bugs ficaram abertos nesta rodada?

## Perfis

- `critical`: rodada menor, focada no que mais quebra venda e operacao.
- `broad`: rodada ampla para dia a dia, incluindo backend, gates auxiliares, mobile baseline e E2E principal.
- `exhaustive`: varredura mais completa disponivel hoje, incluindo descoberta de testes backend restantes, E2E local mais amplo, stress local e jornada online quando houver base URL.

## Comandos principais

Local amplo:

```bash
make full-regression-audit
```

Local critico:

```bash
make full-regression-audit-critical
```

Local exaustivo:

```bash
make full-regression-audit-exhaustive
```

Amplo + online hospedado:

```bash
make full-regression-audit-hosted
```

Exaustivo + online hospedado:

```bash
make full-regression-audit-exhaustive-hosted
```

Modo mais humano, lento e visual, no perfil exaustivo:

```bash
make full-regression-audit-human
```

Tambem e possivel rodar direto:

```bash
python3 scripts/run_full_regression_audit.py --profile exhaustive --base-url https://tariel-web-free.onrender.com
```

## O que o runner cobre

Perfil `critical`:

- criacao e acesso multiportal
- portal admin-cliente
- fluxo critico do inspetor
- fluxo critico da mesa
- contrato documental e catalogo
- E2E Playwright multiportal focado nos fluxos mais caros

Perfil `broad` adiciona:

- catalogo, ondas, overlays e governanca de templates
- policy, tenant, auth, hygiene e operacao
- fases de entry mode
- matriz V2 core e V2 android
- runners auxiliares de documento, observabilidade, higiene e V2
- mobile baseline
- E2E local mais amplo dos portais

Perfil `exhaustive` adiciona:

- testes backend descobertos que nao estavam em grupos manuais
- E2E local de stress e stress paralelo
- manifesto de cobertura da rodada para mostrar exatamente o que entrou

Suite online opcional:

- jornada real no Render via `web/scripts/render_ui_user_journey.py`

## Artefatos gerados

Em `artifacts/full_regression_audit/<timestamp>/`:

- `summary.json`
- `summary.md`
- `coverage_manifest.md`
- `bug_registry.json`
- `bug_registry.md`
- `success_registry.md`
- `logs/*.txt`
- `online_journey/*` quando houver base URL hospedada

## Como usar a saida

1. abrir `bug_registry.md`
2. abrir `success_registry.md` para ver o que realmente funcionou
3. abrir `coverage_manifest.md` para confirmar o escopo real da rodada
4. ordenar `bug_registry.md` por severidade
5. corrigir primeiro bugs que quebram:
   - login
   - criacao de empresa/usuarios
   - coleta do inspetor
   - operacao da mesa
   - emissao e verificacao documental
6. rodar o mesmo runner de novo

## Limite importante

Esse runner agora tenta cobrir praticamente toda a automacao existente do repositório quando usado em `exhaustive`, mas isso ainda nao equivale a "todo comportamento possivel do sistema".

Ele cobre o que ja esta automatizado ou empacotado como gate/runner. O que ainda nao tem automacao dedicada continua aparecendo como lacuna de cobertura, nao como falsa promessa de que foi testado.

Se algum modulo novo virar critico, ele deve entrar explicitamente no runner para passar a fazer parte da definicao de pronto.

## Modo humano

Quando usar `make full-regression-audit-human`, o runner:

- usa o perfil `exhaustive`
- desacelera a jornada hospedada
- abre a auditoria hospedada em modo visual quando houver sessao grafica disponivel
- usa pausas maiores entre acoes e observacao de tela
- preserva o foco em clique real e observacao contextual

Ele continua automatizado, mas fica mais proximo de uma sessao de exploracao humana do que de um smoke rapido.
