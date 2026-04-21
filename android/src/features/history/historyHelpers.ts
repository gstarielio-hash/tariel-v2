import type { MobileLaudoCard } from "../../types/mobile";
import { stripEmbeddedChatAiPreferences } from "../chat/preferences";

export interface HistorySection {
  key: string;
  title: string;
  items: MobileLaudoCard[];
}

const historySectionOrder = ["today", "yesterday", "week", "older"] as const;

export function filtrarThreadContextChips<T>(items: Array<T | null>): T[] {
  return items.filter((item): item is T => item !== null);
}

function startOfDay(date: Date): number {
  const clone = new Date(date);
  clone.setHours(0, 0, 0, 0);
  return clone.getTime();
}

function getHistorySectionKey(
  dataIso: string,
  referencia = new Date(),
): (typeof historySectionOrder)[number] {
  const alvo = new Date(dataIso);
  if (Number.isNaN(alvo.getTime())) {
    return "older";
  }

  const diffDays = Math.floor(
    (startOfDay(referencia) - startOfDay(alvo)) / 86_400_000,
  );

  if (diffDays <= 0) {
    return "today";
  }
  if (diffDays === 1) {
    return "yesterday";
  }
  if (diffDays < 7) {
    return "week";
  }
  return "older";
}

function getHistorySectionLabel(
  key: (typeof historySectionOrder)[number],
): string {
  switch (key) {
    case "today":
      return "Hoje";
    case "yesterday":
      return "Ontem";
    case "week":
      return "Esta semana";
    default:
      return "Mais antigos";
  }
}

export function buildHistorySections(
  items: MobileLaudoCard[],
): HistorySection[] {
  const fixados = items.filter((item) => item.pinado);
  const restantes = items.filter((item) => !item.pinado);
  const buckets = new Map<
    (typeof historySectionOrder)[number],
    MobileLaudoCard[]
  >();
  for (const item of restantes) {
    const key = getHistorySectionKey(item.data_iso);
    const current = buckets.get(key) || [];
    current.push(item);
    buckets.set(key, current);
  }

  const secoesCronologicas = historySectionOrder
    .map((key) => ({
      key,
      title: getHistorySectionLabel(key),
      items: buckets.get(key) || [],
    }))
    .filter((section) => section.items.length > 0);

  return fixados.length
    ? [
        { key: "pinned", title: "Fixadas", items: fixados },
        ...secoesCronologicas,
      ]
    : secoesCronologicas;
}

export function aplicarPreferenciasLaudos(
  itens: MobileLaudoCard[],
  fixadosIds: number[],
  ocultosIds: number[],
): MobileLaudoCard[] {
  const ocultos = new Set(ocultosIds);
  const fixados = new Set(fixadosIds);

  return itens
    .filter((item) => !ocultos.has(item.id))
    .map((item) => ({
      ...item,
      pinado: fixados.has(item.id),
      preview: stripEmbeddedChatAiPreferences(item.preview, {
        fallbackHiddenOnly: "Evidência enviada",
      }),
    }));
}
