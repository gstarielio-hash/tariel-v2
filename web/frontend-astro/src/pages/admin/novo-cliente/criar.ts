import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  requireAdminStepUp,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { createCompany } from "@/lib/server/admin-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const errorReturnTo = "/admin/novo-cliente";
  const adminSession = await requireAdminStepUp(context, {
    returnTo: errorReturnTo,
    message: "Reautenticação necessária para provisionar uma nova empresa.",
  });

  if (adminSession instanceof Response) {
    return adminSession;
  }

  try {
    const result = await createCompany(
      {
        nome: String(formData.get("nome") ?? ""),
        cnpj: String(formData.get("cnpj") ?? ""),
        emailAdmin: String(formData.get("emailAdmin") ?? ""),
        plano: String(formData.get("plano") ?? ""),
        segmento: String(formData.get("segmento") ?? ""),
        cidadeEstado: String(formData.get("cidadeEstado") ?? ""),
        nomeResponsavel: String(formData.get("nomeResponsavel") ?? ""),
        observacoes: String(formData.get("observacoes") ?? ""),
        provisionarInspetor: formData.has("provisionarInspetor"),
        inspetorNome: String(formData.get("inspetorNome") ?? ""),
        inspetorEmail: String(formData.get("inspetorEmail") ?? ""),
        inspetorTelefone: String(formData.get("inspetorTelefone") ?? ""),
        provisionarRevisor: formData.has("provisionarRevisor"),
        revisorNome: String(formData.get("revisorNome") ?? ""),
        revisorEmail: String(formData.get("revisorEmail") ?? ""),
        revisorTelefone: String(formData.get("revisorTelefone") ?? ""),
        revisorCrea: String(formData.get("revisorCrea") ?? ""),
      },
      adminSession.user.id,
    );

    return redirectWithAdminNotice(
      context,
      `/admin/clientes/${result.companyId}`,
      {
        tone: "success",
        title: "Cliente provisionado",
        message: `${result.companyName} foi criada na nova stack e já pode entrar em operação.`,
        details: [
          `Tenant #${result.companyId} provisionado no PostgreSQL atual.`,
          "As credenciais abaixo aparecem apenas nesta navegação.",
        ],
        credentials: result.credentials.map((credential) => ({
          ...credential,
          notes: ["Senha temporária: forçar atualização no primeiro acesso."],
        })),
      },
    );
  } catch (error) {
    return redirectWithAdminNotice(context, errorReturnTo, {
      tone: "error",
      title: "Falha no onboarding",
      message: getAdminErrorMessage(
        error,
        "Não foi possível criar a empresa e os usuários iniciais.",
      ),
    });
  }
};
