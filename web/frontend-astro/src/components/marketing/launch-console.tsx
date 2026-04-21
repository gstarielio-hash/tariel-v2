import { useState } from "react";
import { ArrowRight, DatabaseZap, Layers3, Orbit, ShieldCheck, Sparkles, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const tracks = [
  {
    id: "astro",
    label: "Astro Shell",
    title: "Renderizacao rapida para telas publicas e shells de portal",
    description:
      "Use Astro para construir landing pages, areas institucionais e shells com baixo custo de JavaScript e grande controle de composicao.",
    icon: Orbit,
  },
  {
    id: "react",
    label: "React Islands",
    title: "Interacao localizada onde o produto realmente precisa",
    description:
      "Hydration seletiva permite encaixar ilhas React nos pontos de alta interacao sem transformar o portal inteiro em SPA.",
    icon: Layers3,
  },
  {
    id: "shadcn",
    label: "Design System",
    title: "Base reutilizavel com shadcn/ui e tokens sem acoplar a framework magico",
    description:
      "Os componentes entram como codigo do projeto, o que facilita ajustes visuais e governanca sem depender de uma black box externa.",
    icon: ShieldCheck,
  },
  {
    id: "prisma",
    label: "Prisma 7",
    title: "Node/TypeScript falando com o Postgres atual com tipagem forte",
    description:
      "O schema pode ser puxado do banco existente via introspeccao, o client e gerado no projeto e as consultas podem coexistir com a camada Python durante a migracao.",
    icon: DatabaseZap,
  },
] as const;

export function LaunchConsole() {
  const [activeId, setActiveId] = useState<(typeof tracks)[number]["id"]>("astro");
  const active = tracks.find((track) => track.id === activeId) ?? tracks[0];
  const ActiveIcon = active.icon;

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/15 bg-slate-950/85 p-6 text-slate-50 shadow-2xl shadow-orange-950/30 backdrop-blur-xl">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-300/70 to-transparent" />
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-orange-200/80">Frontend Lab</p>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-white">Astro + React 19 no mesmo fluxo</h2>
        </div>
        <div className="rounded-full border border-white/15 bg-white/10 p-3">
          <Sparkles className="size-5 text-orange-200" />
        </div>
      </div>

      <div className="mt-6 grid gap-3">
        {tracks.map((track) => {
          const Icon = track.icon;

          return (
            <button
              key={track.id}
              type="button"
              onClick={() => setActiveId(track.id)}
              className={cn(
                "flex items-center gap-3 rounded-2xl border px-4 py-3 text-left transition duration-200",
                activeId === track.id
                  ? "border-orange-300/60 bg-orange-300/12 text-white shadow-lg shadow-orange-950/30"
                  : "border-white/10 bg-white/5 text-slate-300 hover:border-white/20 hover:bg-white/8 hover:text-white",
              )}
            >
              <span className="rounded-xl bg-white/10 p-2">
                <Icon className="size-4" />
              </span>
              <span className="flex-1">
                <span className="block text-sm font-semibold">{track.label}</span>
                <span className="block text-xs text-slate-400">{track.title}</span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-6 rounded-[24px] border border-white/10 bg-white/[0.04] p-5">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-orange-300/15 p-3 text-orange-100">
            <ActiveIcon className="size-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">{active.label}</p>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Ponto de integracao</p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-slate-300">{active.description}</p>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-4">
            <div className="flex items-center gap-2 text-emerald-100">
              <Zap className="size-4" />
              <span className="text-sm font-semibold">Vite por baixo</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-emerald-50/85">
              Build rapido e dev server previsivel, mantendo o stack moderno sem reescrever o backend Python.
            </p>
          </div>
          <div className="rounded-2xl border border-sky-300/20 bg-sky-300/10 p-4">
            <div className="flex items-center gap-2 text-sky-100">
              <Layers3 className="size-4" />
              <span className="text-sm font-semibold">Lucide + UI code-first</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-sky-50/85">
              Icones tree-shakeable e componentes editaveis direto no repo, sem camada proprietaria.
            </p>
          </div>
          <div className="rounded-2xl border border-violet-300/20 bg-violet-300/10 p-4 sm:col-span-2">
            <div className="flex items-center gap-2 text-violet-100">
              <DatabaseZap className="size-4" />
              <span className="text-sm font-semibold">Prisma conectado a banco existente</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-violet-50/85">
              A migracao pode ler o schema atual do Postgres com <code>prisma db pull</code> e abrir uma camada Node/TS ao redor do banco sem
              desligar a aplicacao Python no primeiro passo.
            </p>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Button size="lg" className="bg-orange-500 text-white hover:bg-orange-400">
            Abrir piloto Astro
            <ArrowRight />
          </Button>
          <Button variant="outline" size="lg" className="border-white/15 bg-transparent text-white hover:bg-white/10">
            Ver componentes
          </Button>
        </div>
      </div>
    </div>
  );
}
