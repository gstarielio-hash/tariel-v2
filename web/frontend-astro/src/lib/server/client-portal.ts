import { getAdminClientDetail } from "@/lib/server/admin-clients";

export async function getClientPortalOverview(companyId: number) {
  return getAdminClientDetail(companyId);
}
