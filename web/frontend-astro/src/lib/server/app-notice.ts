export interface AppNotice {
  tone: "success" | "error" | "info";
  title: string;
  message: string;
  details?: string[];
}

const APP_NOTICE_COOKIE = "tariel_app_notice";
const APP_NOTICE_OPTIONS = {
  path: "/",
  httpOnly: true,
  sameSite: "lax" as const,
  maxAge: 120,
};

export function setAppNotice(cookies: any, notice: AppNotice) {
  cookies.set(APP_NOTICE_COOKIE, notice, APP_NOTICE_OPTIONS);
}

export function consumeAppNotice(cookies: any): AppNotice | null {
  const rawNotice = cookies.get(APP_NOTICE_COOKIE);

  if (!rawNotice) {
    return null;
  }

  cookies.delete(APP_NOTICE_COOKIE, { path: "/" });

  try {
    const parsed = rawNotice.json() as AppNotice;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}
