import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  requireAdminSession,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { updateCompanyCatalogFamilyRelease } from "@/lib/server/admin-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const familyKey = String(context.params.familyKey ?? "").trim();
  const tenantId = Number(formData.get("tenant_id") ?? "");
  const defaultReturnTo =
    Number.isInteger(tenantId) && tenantId > 0
      ? `/admin/clientes/${tenantId}`
      : familyKey
        ? `/admin/catalogo-laudos/familias/${familyKey}?tab=liberacao`
        : "/admin/catalogo-laudos";
  const returnTo = getAdminReturnPath(formData, defaultReturnTo);
  const adminSession = requireAdminSession(context);

  try {
    if (!familyKey) {
      throw new Error("Família inválida.");
    }

    if (!Number.isInteger(tenantId) || tenantId <= 0) {
      throw new Error("Empresa inválida.");
    }

    const result = await updateCompanyCatalogFamilyRelease({
      companyId: tenantId,
      familyKey,
      releaseStatus: String(formData.get("release_status") ?? ""),
      defaultTemplateCode: String(formData.get("default_template_code") ?? ""),
      observacoes: String(formData.get("observacoes") ?? ""),
      allowedTemplates: formData
        .getAll("allowed_templates")
        .map((value) => String(value ?? "").trim())
        .filter(Boolean),
      allowedVariants: formData
        .getAll("allowed_variants")
        .map((value) => String(value ?? "").trim())
        .filter(Boolean),
      actorUserId: adminSession.user.id,
    });

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: "Liberação atualizada",
      message: `${result.familyLabel} foi atualizada para ${result.companyName}.`,
      details: [
        `Status: ${result.releaseStatus}`,
        `Variantes ativas: ${result.selectedCount}`,
        `Ativadas: ${result.activated.length}`,
        `Reativadas: ${result.reactivated.length}`,
        `Desativadas: ${result.deactivated.length}`,
      ],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao salvar liberação",
      message: getAdminErrorMessage(
        error,
        "Não foi possível atualizar a liberação desta família para a empresa.",
      ),
    });
  }
};
