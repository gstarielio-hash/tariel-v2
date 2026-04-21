import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

import {
  BATTERY_OPTIONS,
  DENSITY_OPTIONS,
  FONT_SIZE_OPTIONS,
  LOCK_TIMEOUT_OPTIONS,
} from "../InspectorMobileApp.constants";

export function ehOpcaoValida<T extends readonly string[]>(
  valor: unknown,
  opcoes: T,
): valor is T[number] {
  return (
    typeof valor === "string" && (opcoes as readonly string[]).includes(valor)
  );
}

export function construirUrlCanalSuporte(rawValue: string): string {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "";
  }
  if (/^(https?:\/\/|whatsapp:\/\/)/i.test(value)) {
    return value;
  }
  const digits = value.replace(/\D/g, "");
  return digits ? `https://wa.me/${digits}` : "";
}

export function serializarPayloadExportacao(payload: unknown): string {
  return JSON.stringify(payload, null, 2);
}

export async function compartilharTextoExportado(params: {
  extension: "json" | "txt";
  content: string;
  prefixo: string;
}): Promise<boolean> {
  try {
    const baseDir = `${FileSystem.cacheDirectory || FileSystem.documentDirectory || ""}tariel-exports`;
    await FileSystem.makeDirectoryAsync(baseDir, { intermediates: true });
    const carimbo = new Date().toISOString().replace(/[:.]/g, "-");
    const uri = `${baseDir}/${params.prefixo}-${carimbo}.${params.extension}`;
    await FileSystem.writeAsStringAsync(uri, params.content);
    const podeCompartilhar = await Sharing.isAvailableAsync();
    if (podeCompartilhar) {
      await Sharing.shareAsync(uri, {
        dialogTitle: "Exportar dados do Tariel Inspetor",
        mimeType:
          params.extension === "json" ? "application/json" : "text/plain",
      });
    }
    return true;
  } catch (error) {
    console.warn("Falha ao exportar dados do app.", error);
    return false;
  }
}

export function obterIntervaloMonitoramentoMs(
  economiaDados: boolean,
  usoBateria: (typeof BATTERY_OPTIONS)[number],
): number {
  if (economiaDados || usoBateria === "Econômico") {
    return 60_000;
  }
  if (usoBateria === "Otimizado") {
    return 40_000;
  }
  return 25_000;
}

export function obterEscalaFonte(
  tamanho: (typeof FONT_SIZE_OPTIONS)[number],
): number {
  if (tamanho === "pequeno") {
    return 0.94;
  }
  if (tamanho === "grande") {
    return 1.08;
  }
  return 1;
}

export function obterEscalaDensidade(
  densidade: (typeof DENSITY_OPTIONS)[number],
): number {
  return densidade === "compacta" ? 0.9 : 1;
}

export function erroSugereModoOffline(erro: unknown): boolean {
  const texto = String(erro instanceof Error ? erro.message : erro || "")
    .trim()
    .toLowerCase();
  if (!texto) {
    return false;
  }

  return [
    "network request failed",
    "network",
    "offline",
    "internet",
    "connection",
    "conex",
    "fetch",
    "timeout",
    "timed out",
  ].some((trecho) => texto.includes(trecho));
}

export function formatarHorarioAtividade(dataIso: string): string {
  const data = new Date(dataIso);
  if (Number.isNaN(data.getTime())) {
    return "agora";
  }
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function obterTimeoutBloqueioMs(
  value: (typeof LOCK_TIMEOUT_OPTIONS)[number],
): number | null {
  if (value === "imediatamente") {
    return 0;
  }
  if (value === "1 minuto") {
    return 60_000;
  }
  if (value === "5 minutos") {
    return 5 * 60_000;
  }
  if (value === "15 minutos") {
    return 15 * 60_000;
  }
  return null;
}
