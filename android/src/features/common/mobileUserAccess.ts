import type {
  MobileCommercialOperatingModel,
  MobilePortalSwitchLink,
  MobileUser,
  MobileUserPortal,
} from "../../types/mobile";
import {
  DEFAULT_API_BASE_URL,
  normalizarApiBaseUrl,
  readRuntimeEnv,
} from "../../config/apiCore";
import type {
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import type { MobileReadCache } from "./readCacheTypes";

const MOBILE_USER_PORTAL_LABELS: Record<MobileUserPortal, string> = {
  cliente: "Admin-Cliente",
  inspetor: "Inspetor web/mobile",
  revisor: "Mesa Avaliadora",
};

const MOBILE_OPERATING_MODEL_LABELS: Record<
  MobileCommercialOperatingModel,
  string
> = {
  standard: "Operação padrão",
  mobile_single_operator: "Mobile principal com operador único",
};

const ACCESS_LEVEL_BASE_PORTALS: Record<number, MobileUserPortal> = {
  1: "inspetor",
  50: "revisor",
  80: "cliente",
};

export interface MobileResolvedPortalSwitchLink {
  portal: MobileUserPortal;
  label: string;
  url: string;
  destinationPath: string;
}

function joinHumanReadableList(items: string[]): string {
  if (!items.length) {
    return "";
  }
  if (items.length === 1) {
    return items[0];
  }
  if (items.length === 2) {
    return `${items[0]} e ${items[1]}`;
  }
  return `${items.slice(0, -1).join(", ")} e ${items[items.length - 1]}`;
}

function isMobileUserPortal(value: unknown): value is MobileUserPortal {
  return value === "cliente" || value === "inspetor" || value === "revisor";
}

function isMobileOperatingModel(
  value: unknown,
): value is MobileCommercialOperatingModel {
  return value === "standard" || value === "mobile_single_operator";
}

function basePublicaPortalWeb(): string {
  const rawBase =
    readRuntimeEnv("EXPO_PUBLIC_AUTH_WEB_BASE_URL") ||
    readRuntimeEnv("EXPO_PUBLIC_API_BASE_URL") ||
    DEFAULT_API_BASE_URL;
  return normalizarApiBaseUrl(
    String(rawBase || "")
      .trim()
      .replace(/\/+$/, ""),
  );
}

function normalizarUrlPortalWeb(rawValue: string): string {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "";
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  if (value.startsWith("//")) {
    return `https:${value}`;
  }
  return `${basePublicaPortalWeb()}${value.startsWith("/") ? "" : "/"}${value}`;
}

function extrairCaminhoDestinoPortal(rawValue: string): string {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "";
  }
  if (value.startsWith("/")) {
    return value;
  }
  try {
    const parsed = new URL(value);
    return parsed.pathname || parsed.href;
  } catch {
    return value;
  }
}

function notificationUsesMesaSurface(
  item: MobileActivityNotification,
): boolean {
  return (
    item.targetThread === "mesa" ||
    item.kind === "mesa_nova" ||
    item.kind === "mesa_resolvida" ||
    item.kind === "mesa_reaberta"
  );
}

export function resolveMobileUserPortals(
  user: MobileUser | null | undefined,
): MobileUserPortal[] {
  const normalized: MobileUserPortal[] = [];
  const rawPortals = Array.isArray(user?.allowed_portals)
    ? user.allowed_portals
    : [];
  rawPortals.forEach((item) => {
    if (isMobileUserPortal(item) && !normalized.includes(item)) {
      normalized.push(item);
    }
  });

  if (!normalized.length) {
    const fallbackPortal = ACCESS_LEVEL_BASE_PORTALS[user?.nivel_acesso ?? -1];
    if (fallbackPortal) {
      normalized.push(fallbackPortal);
    }
  }

  return normalized;
}

export function hasMobileUserPortal(
  user: MobileUser | null | undefined,
  portal: MobileUserPortal,
): boolean {
  return resolveMobileUserPortals(user).includes(portal);
}

export function resolveMobileUserPortalLabels(
  user: MobileUser | null | undefined,
): string[] {
  const rawLabels = Array.isArray(user?.allowed_portal_labels)
    ? user.allowed_portal_labels
        .map((item) => String(item || "").trim())
        .filter(Boolean)
    : [];
  if (rawLabels.length) {
    return rawLabels;
  }
  return resolveMobileUserPortals(user).map(
    (portal) => MOBILE_USER_PORTAL_LABELS[portal],
  );
}

export function resolveMobileUserOperatingModelLabel(
  user: MobileUser | null | undefined,
): string {
  const explicitLabel = String(
    user?.commercial_operating_model_label || "",
  ).trim();
  if (explicitLabel) {
    return explicitLabel;
  }
  const model = user?.commercial_operating_model;
  if (isMobileOperatingModel(model)) {
    return MOBILE_OPERATING_MODEL_LABELS[model];
  }
  return "";
}

export function buildMobileWorkspaceSummary(
  user: MobileUser | null | undefined,
): string {
  const companyName = String(user?.empresa_nome || "").trim() || "Pessoal";
  const operatingModelLabel = resolveMobileUserOperatingModelLabel(user);
  return operatingModelLabel
    ? `${companyName} • ${operatingModelLabel}`
    : companyName;
}

export function buildMobileAccessSummary(
  user: MobileUser | null | undefined,
): string {
  const parts: string[] = [];
  if (typeof user?.empresa_id === "number") {
    parts.push(`Empresa #${user.empresa_id}`);
  }

  const portalLabels = resolveMobileUserPortalLabels(user);
  if (portalLabels.length) {
    parts.push(portalLabels.join(" + "));
  }

  const operatingModelLabel = resolveMobileUserOperatingModelLabel(user);
  if (operatingModelLabel) {
    parts.push(operatingModelLabel);
  } else if (typeof user?.nivel_acesso === "number") {
    parts.push(`Nível ${user.nivel_acesso}`);
  }

  return parts.join(" • ") || "Conta corporativa autenticada";
}

export function buildMobileSupportAccessLabel(
  user: MobileUser | null | undefined,
): string {
  const portalLabels = resolveMobileUserPortalLabels(user);
  if (portalLabels.length) {
    return portalLabels.join(" + ");
  }

  const operatingModelLabel = resolveMobileUserOperatingModelLabel(user);
  if (operatingModelLabel) {
    return operatingModelLabel;
  }

  if (typeof user?.nivel_acesso === "number") {
    return `Nível ${user.nivel_acesso}`;
  }

  return "Conta autenticada";
}

export function buildMobileIdentityRuntimeNote(
  user: MobileUser | null | undefined,
): string {
  return String(user?.identity_runtime_note || "").trim();
}

export function resolveMobilePortalSwitchLinks(
  user: MobileUser | null | undefined,
): MobileResolvedPortalSwitchLink[] {
  const rawLinks = Array.isArray(user?.portal_switch_links)
    ? user.portal_switch_links
    : [];
  const normalized: MobileResolvedPortalSwitchLink[] = [];
  rawLinks.forEach((item) => {
    if (!item || typeof item !== "object") {
      return;
    }
    const raw = item as MobilePortalSwitchLink;
    const portal = isMobileUserPortal(raw.portal) ? raw.portal : null;
    const label = String(raw.label || "").trim();
    const destinationPath = extrairCaminhoDestinoPortal(raw.url);
    const resolvedUrl = normalizarUrlPortalWeb(String(raw.url || ""));
    if (!portal || !label || !destinationPath || !resolvedUrl) {
      return;
    }
    if (
      normalized.some(
        (existing) =>
          existing.portal === portal &&
          existing.destinationPath === destinationPath,
      )
    ) {
      return;
    }
    normalized.push({
      portal,
      label,
      url: resolvedUrl,
      destinationPath,
    });
  });
  return normalized;
}

export function buildMobilePortalSwitchSummary(
  user: MobileUser | null | undefined,
): string {
  const links = resolveMobilePortalSwitchLinks(user);
  if (!links.length) {
    return "";
  }
  return links
    .map((item) => `${item.label} (${item.destinationPath})`)
    .join(" • ");
}

export function buildMobileOperationalFootprintSummary(
  user: MobileUser | null | undefined,
): string {
  const surfaces: string[] = [];

  if (hasMobileUserPortal(user, "cliente")) {
    surfaces.push("Admin-Cliente da empresa");
  }
  if (hasMobileUserPortal(user, "inspetor")) {
    surfaces.push("chat do inspetor");
  }
  if (hasMobileUserPortal(user, "revisor")) {
    surfaces.push("mesa avaliadora");
  }

  surfaces.push("histórico", "fila offline", "configurações do app");

  return `${joinHumanReadableList(Array.from(new Set(surfaces)))}.`;
}

export function buildMobileHelpTopicsSummary(
  user: MobileUser | null | undefined,
): string {
  const topics: string[] = [];

  if (hasMobileUserPortal(user, "cliente")) {
    topics.push("acesso");
  }
  if (hasMobileUserPortal(user, "inspetor")) {
    topics.push("inspeção");
  }
  if (hasMobileUserPortal(user, "revisor")) {
    topics.push("mesa");
  }

  topics.push("offline", "segurança");

  return joinHumanReadableList(Array.from(new Set(topics)).slice(0, 4));
}

export function filterHelpArticlesByMobileAccess<T extends object>(
  items: readonly T[],
  user: MobileUser | null | undefined,
): T[] {
  return items.filter((item) => {
    const requiredPortals = Array.isArray(
      (
        item as T & {
          requiredPortals?: readonly MobileUserPortal[] | MobileUserPortal[];
        }
      ).requiredPortals,
    )
      ? (
          item as T & {
            requiredPortals?: readonly MobileUserPortal[] | MobileUserPortal[];
          }
        ).requiredPortals!.filter((portal): portal is MobileUserPortal =>
          isMobileUserPortal(portal),
        )
      : [];

    if (!requiredPortals.length) {
      return true;
    }

    return requiredPortals.every((portal) => hasMobileUserPortal(user, portal));
  });
}

export function filterOfflineQueueByMobileAccess(
  items: OfflinePendingMessage[],
  user: MobileUser | null | undefined,
): OfflinePendingMessage[] {
  if (hasMobileUserPortal(user, "revisor")) {
    return items;
  }
  return items.filter((item) => item.channel !== "mesa");
}

export function filterNotificationsByMobileAccess(
  items: MobileActivityNotification[],
  user: MobileUser | null | undefined,
): MobileActivityNotification[] {
  if (hasMobileUserPortal(user, "revisor")) {
    return items;
  }
  return items.filter((item) => !notificationUsesMesaSurface(item));
}

export function sanitizeReadCacheByMobileAccess(
  cache: MobileReadCache,
  user: MobileUser | null | undefined,
): MobileReadCache {
  if (hasMobileUserPortal(user, "revisor")) {
    return cache;
  }

  const hasMesaData =
    Object.keys(cache.mesaPorLaudo).length > 0 ||
    Object.keys(cache.mesaDrafts).length > 0 ||
    Object.keys(cache.mesaAttachmentDrafts).length > 0;

  if (!hasMesaData) {
    return cache;
  }

  return {
    ...cache,
    mesaPorLaudo: {},
    mesaDrafts: {},
    mesaAttachmentDrafts: {},
    updatedAt: new Date().toISOString(),
  };
}
