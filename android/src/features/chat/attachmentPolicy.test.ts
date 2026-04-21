import {
  buildAttachmentPickerOptions,
  isDocumentAttachmentAllowed,
  resolveDocumentAttachmentPolicyLabel,
} from "./attachmentPolicy";

describe("attachmentPolicy", () => {
  it("prioriza a politica canonica quando ela libera documento", () => {
    const conversation = {
      laudoId: 77,
      attachmentPolicy: {
        policy_name: "android_attachment_sync_policy" as const,
        upload_allowed: true,
        download_allowed: true,
        inline_preview_allowed: true,
        supported_categories: ["imagem", "documento"],
        supported_mime_types: ["image/png", "application/pdf"],
      },
      reviewPackage: {
        tenant_entitlements: {
          upload_doc: false,
        },
      },
    } as const;

    expect(
      isDocumentAttachmentAllowed({
        activeThread: "chat",
        conversation: conversation as never,
      }),
    ).toBe(true);
    expect(
      resolveDocumentAttachmentPolicyLabel({
        activeThread: "chat",
        conversation: conversation as never,
      }),
    ).toBe("Documentos seguem a politica canonica de anexos deste caso.");
  });

  it("bloqueia documento quando a politica canonica remove a categoria documental", () => {
    const options = buildAttachmentPickerOptions({
      activeThread: "chat",
      conversation: {
        laudoId: 77,
        attachmentPolicy: {
          policy_name: "android_attachment_sync_policy",
          upload_allowed: true,
          download_allowed: true,
          inline_preview_allowed: true,
          supported_categories: ["imagem"],
          supported_mime_types: ["image/png"],
        },
      } as never,
    });

    expect(options.find((item) => item.key === "documento")).toMatchObject({
      enabled: false,
      detail:
        "Este caso aceita somente imagens no app; documento nao faz parte da politica ativa.",
    });
  });

  it("bloqueia camera e galeria quando a politica canonica fecha uploads", () => {
    const options = buildAttachmentPickerOptions({
      activeThread: "mesa",
      conversation: {
        laudoId: 77,
        attachmentPolicy: {
          policy_name: "android_attachment_sync_policy",
          upload_allowed: false,
          download_allowed: true,
          inline_preview_allowed: true,
          supported_categories: ["imagem", "documento"],
          supported_mime_types: ["image/png", "application/pdf"],
        },
      } as never,
    });

    expect(options.find((item) => item.key === "camera")).toMatchObject({
      enabled: false,
      detail: "Uploads bloqueados pela politica ativa deste caso.",
    });
    expect(options.find((item) => item.key === "galeria")).toMatchObject({
      enabled: false,
      detail: "Uploads bloqueados pela politica ativa deste caso.",
    });
  });
});
