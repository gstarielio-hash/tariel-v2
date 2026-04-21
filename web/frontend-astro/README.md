# Tariel Web Migration

Alvo de migracao para substituir o frontend atual por uma stack Node/TypeScript moderna:

- Astro 6
- `@astrojs/node`
- Tailwind CSS v4
- shadcn/ui
- React 19
- Lucide
- Prisma 7
- PostgreSQL
- Vite

## O que este workspace faz

Este workspace fica em `web/frontend-astro/` e foi preparado para:

- servir UI com Astro SSR em Node
- usar React 19 apenas nas ilhas interativas
- manter um design system editavel com `shadcn/ui`
- falar com o banco atual via Prisma
- introspectar o schema real do PostgreSQL existente

## Versoes atuais verificadas em 2026-04-20

- Astro `6.1.8`
- `@astrojs/react` `5.0.3`
- `@astrojs/node` `10.0.5`
- React / React DOM `19.2.5`
- Tailwind CSS / `@tailwindcss/vite` `4.2.3`
- Lucide React `1.8.0`
- Prisma / `@prisma/client` `7.7.0`

## Node 22 sem mexer no sistema

O Astro atual exige Node `>=22.12.0`.
Como a maquina local ainda esta em Node `20.20.2`, o workspace inclui o wrapper:

```bash
./bin/npm22
```

Ele executa `npm` usando Node `22.12.0` via `npx`, sem alterar a instalacao global.

## Bootstrap

```bash
cd web/frontend-astro
cp .env.example .env
./bin/npm22 install
./bin/npm22 run prisma:pull
./bin/npm22 run dev
```

## Banco local atual

O workspace aceita o mesmo shorthand usado hoje pelo backend Python:

```bash
DATABASE_URL="postgresql:///tariel_dev"
```

Internamente ele normaliza essa URL para socket local do PostgreSQL, usando o usuario do sistema operacional atual.

## Comandos principais

```bash
./bin/npm22 run dev
./bin/npm22 run build
./bin/npm22 run check
./bin/npm22 run prisma:pull
./bin/npm22 run prisma:generate
./bin/npm22 run prisma:studio
```

## Estrategia de migracao

O backend Python atual pode continuar vivo durante a transicao.
Este workspace abre a nova camada Node/TypeScript e Prisma ao redor do mesmo banco,
permitindo migrar telas e fluxos por fatias em vez de reescrever tudo de uma vez.
