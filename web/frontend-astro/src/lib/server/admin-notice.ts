export interface AdminNoticeCredential {
  label: string;
  portal?: string;
  email?: string;
  password?: string;
  notes?: string[];
}

export interface AdminNotice {
  tone: "success" | "error" | "info";
  title: string;
  message: string;
  details?: string[];
  credentials?: AdminNoticeCredential[];
}

const ADMIN_NOTICE_COOKIE = "tariel_admin_notice";
const ADMIN_NOTICE_OPTIONS = {
  path: "/",
  httpOnly: true,
  sameSite: "lax" as const,
  maxAge: 120,
};

export function setAdminNotice(cookies: any, notice: AdminNotice) {
  cookies.set(ADMIN_NOTICE_COOKIE, notice, ADMIN_NOTICE_OPTIONS);
}

export function consumeAdminNotice(cookies: any): AdminNotice | null {
  const rawNotice = cookies.get(ADMIN_NOTICE_COOKIE);

  if (!rawNotice) {
    return null;
  }

  cookies.delete(ADMIN_NOTICE_COOKIE, {
    path: "/",
  });

  try {
    const parsed = rawNotice.json() as AdminNotice;

    if (!parsed || typeof parsed !== "object") {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

export function safeAdminReturnPath(value: FormDataEntryValue | string | null | undefined, fallback: string) {
  const normalized = String(value ?? "").trim();

  if (!normalized.startsWith("/admin")) {
    return fallback;
  }

  return normalized;
}
