import { startTransition, useState, type ComponentProps } from "react";
import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";

interface AuthPreviewFormProps {
  portalLabel: string;
  submitLabel?: string;
  supportText: string;
  previewMessage: string;
  variant?: "portal" | "admin" | "mesa";
}

type SubmitHandler = NonNullable<ComponentProps<"form">["onSubmit"]>;

const variantStyles = {
  portal: {
    focus: "focus-visible:ring-sky-500",
    panel: "border-sky-500/15 bg-sky-500/6 text-sky-950",
    note: "border-sky-500/18 bg-sky-500/8 text-sky-800",
    button: "bg-slate-950 text-white hover:bg-slate-800",
  },
  admin: {
    focus: "focus-visible:ring-orange-500",
    panel: "border-orange-500/15 bg-orange-500/6 text-orange-950",
    note: "border-orange-500/18 bg-orange-500/8 text-orange-800",
    button: "bg-slate-950 text-white hover:bg-slate-800",
  },
  mesa: {
    focus: "focus-visible:ring-emerald-500",
    panel: "border-emerald-500/15 bg-emerald-500/6 text-emerald-950",
    note: "border-emerald-500/18 bg-emerald-500/8 text-emerald-800",
    button: "bg-slate-950 text-white hover:bg-slate-800",
  },
} as const;

export function AuthPreviewForm({
  portalLabel,
  submitLabel = "Acessar",
  supportText,
  previewMessage,
  variant = "portal",
}: AuthPreviewFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const styles = variantStyles[variant];

  const handleSubmit: SubmitHandler = (event) => {
    event.preventDefault();
    setSubmitting(true);

    startTransition(() => {
      setFeedback(previewMessage);
      setSubmitting(false);
    });
  };

  return (
    <div className="space-y-5">
      <div className={`rounded-[28px] border p-4 ${styles.panel}`}>
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-white/75 p-2 text-slate-950 shadow-sm">
            <ShieldCheck className="size-4" />
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em]">Primeira fatia migrada</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Este login ja esta em <strong>Astro + React 19</strong>. A integracao de autenticacao entra na proxima
              etapa do backend novo em Node/TypeScript.
            </p>
          </div>
        </div>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit} noValidate>
        <label className="block space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">E-mail</span>
          <input
            type="email"
            name="email"
            placeholder="voce@empresa.com"
            autoComplete="username"
            className={`w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 ${styles.focus}`}
          />
        </label>

        <label className="block space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Senha</span>
          <div className="relative">
            <input
              type="password"
              name="senha"
              placeholder="Digite sua senha"
              autoComplete="current-password"
              className={`w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 pr-12 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 ${styles.focus}`}
            />
            <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-slate-400">
              <LockKeyhole className="size-4" />
            </span>
          </div>
        </label>

        <Button
          type="submit"
          size="lg"
          className={`w-full rounded-2xl text-sm font-semibold shadow-[0_18px_40px_rgba(15,23,42,0.18)] ${styles.button}`}
          disabled={submitting}
        >
          {submitting ? "Preparando ambiente..." : submitLabel}
          <ArrowRight className="size-4" />
        </Button>
      </form>

      <div className={`rounded-[24px] border px-4 py-3 text-sm leading-6 ${styles.note}`}>
        <strong className="font-semibold">{portalLabel}</strong>
        <p className="mt-1">{supportText}</p>
      </div>

      {feedback ? (
        <div className="rounded-[24px] border border-slate-200 bg-slate-950 px-4 py-3 text-sm leading-6 text-slate-100">
          {feedback}
        </div>
      ) : null}
    </div>
  );
}
