# Tariel Control

Repositório principal do produto Tariel.

## Workspaces

- `web/`: aplicação FastAPI que roda em produção no Render
- `android/`: aplicativo mobile do inspetor
- `scripts/`: automações e comandos de suporte local

A Mesa Avaliadora oficial vive no portal web de revisão em `web/`.

## Deploy

O deploy de produção usa o blueprint da raiz em `render.yaml`.
Esse blueprint aponta para `web/` via `rootDir: web`, então:

- os comandos de build/start são executados no diretório da aplicação web
- os caminhos persistentes de upload ficam alinhados com `web/static/uploads`

## Documentação

- Contexto geral do produto: `docs/TARIEL_CONTEXT.md`
- Web: `web/README.md`
- Mobile: `android/README.md`
- Roadmap funcional unificado: `docs/roadmap_execucao_funcional_web_mobile.md`

## Qualidade Local

Comandos úteis na raiz:

```bash
make help
make hygiene-check
make web-ci
make mesa-smoke
make mobile-ci
make ci
```

Hooks opcionais:

```bash
python -m pip install -r web/requirements.txt
make hooks-install
```
