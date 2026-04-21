import type { ActiveThread, ChatState } from "./types";

export type AttachmentPickerOptionKey = "camera" | "galeria" | "documento";

export interface AttachmentPickerOptionDescriptor {
  key: AttachmentPickerOptionKey;
  title: string;
  detail: string;
  icon: "camera-outline" | "image-outline" | "file-document-outline";
  enabled: boolean;
}

function readRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function readBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function normalizarCategoria(value: string): string {
  return value.trim().toLowerCase();
}

function policySupportsCategory(
  conversation: ChatState | null | undefined,
  category: "imagem" | "documento",
): boolean | null {
  const supportedCategories =
    conversation?.attachmentPolicy?.supported_categories;
  if (!supportedCategories?.length) {
    return null;
  }

  return supportedCategories.some(
    (item) => normalizarCategoria(item) === category,
  );
}

export function isImageAttachmentAllowed(params: {
  conversation?: ChatState | null;
}): boolean {
  const policy = params.conversation?.attachmentPolicy;
  if (!policy) {
    return true;
  }

  return (
    policy.upload_allowed &&
    policySupportsCategory(params.conversation, "imagem") !== false
  );
}

export function resolveImageAttachmentPolicyLabel(params: {
  conversation?: ChatState | null;
}): string {
  const policy = params.conversation?.attachmentPolicy;
  if (!policy) {
    return "";
  }

  if (!policy.upload_allowed) {
    return "Uploads bloqueados pela politica ativa deste caso.";
  }

  if (policySupportsCategory(params.conversation, "imagem") === false) {
    return "Captura e galeria nao fazem parte da politica ativa deste caso.";
  }

  return "";
}

export function isDocumentAttachmentAllowed(params: {
  activeThread: ActiveThread;
  conversation?: ChatState | null;
}): boolean {
  const policy = params.conversation?.attachmentPolicy;
  const hasActiveCase = Boolean(params.conversation?.laudoId);
  if (!hasActiveCase) {
    return false;
  }

  if (policy) {
    return (
      policy.upload_allowed &&
      policySupportsCategory(params.conversation, "documento") !== false
    );
  }

  const tenantEntitlements = readRecord(
    readRecord(params.conversation?.reviewPackage)?.tenant_entitlements,
  );
  const uploadDocAllowed = readBoolean(tenantEntitlements?.upload_doc);
  if (uploadDocAllowed === false) {
    return false;
  }

  return true;
}

export function resolveDocumentAttachmentPolicyLabel(params: {
  activeThread: ActiveThread;
  conversation?: ChatState | null;
}): string {
  const policy = params.conversation?.attachmentPolicy;
  const hasActiveCase = Boolean(params.conversation?.laudoId);
  if (!hasActiveCase) {
    return "Documentos liberam quando o caso ja estiver em coleta ou laudo.";
  }

  if (policy) {
    if (!policy.upload_allowed) {
      return "Uploads bloqueados pela politica ativa deste caso.";
    }

    if (policySupportsCategory(params.conversation, "documento") === false) {
      return "Este caso aceita somente imagens no app; documento nao faz parte da politica ativa.";
    }

    return params.activeThread === "mesa"
      ? "Envie base documental rastreavel para apoiar a revisao humana."
      : "Documentos seguem a politica canonica de anexos deste caso.";
  }

  const tenantEntitlements = readRecord(
    readRecord(params.conversation?.reviewPackage)?.tenant_entitlements,
  );
  const uploadDocAllowed = readBoolean(tenantEntitlements?.upload_doc);
  if (uploadDocAllowed === false) {
    return "Upload documental bloqueado pela politica ativa deste cliente.";
  }

  return params.activeThread === "mesa"
    ? "Envie base documental rastreavel para apoiar a revisao humana."
    : "Documentos seguem a politica do caso, do template e do plano contratado.";
}

export function buildAttachmentPickerOptions(params: {
  activeThread: ActiveThread;
  conversation?: ChatState | null;
}): AttachmentPickerOptionDescriptor[] {
  const imageAllowed = isImageAttachmentAllowed(params);
  const imagePolicyLabel = resolveImageAttachmentPolicyLabel(params);
  const documentAllowed = isDocumentAttachmentAllowed(params);
  const documentDetail = resolveDocumentAttachmentPolicyLabel(params);

  return [
    {
      key: "camera",
      title: "Camera",
      detail:
        imagePolicyLabel ||
        "Capture a evidencia na hora e siga no mesmo fluxo do caso.",
      icon: "camera-outline",
      enabled: imageAllowed,
    },
    {
      key: "galeria",
      title: "Galeria",
      detail:
        imagePolicyLabel ||
        "Use foto ja registrada sem sair da conversa atual.",
      icon: "image-outline",
      enabled: imageAllowed,
    },
    {
      key: "documento",
      title: "Documento",
      detail: documentDetail,
      icon: "file-document-outline",
      enabled: documentAllowed,
    },
  ];
}
