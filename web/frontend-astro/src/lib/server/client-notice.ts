export interface ClientNoticeCredential {
  label: string;
  portal?: string;
  email?: string;
  password?: string;
  notes?: string[];
}

export interface ClientNotice {
  tone: "success" | "error" | "info";
  title: string;
  message: string;
  details?: string[];
  credentials?: ClientNoticeCredential[];
}

const CLIENT_NOTICE_COOKIE = "tariel_client_notice";
const CLIENT_NOTICE_OPTIONS = {
  path: "/",
  httpOnly: true,
  sameSite: "lax" as const,
  maxAge: 120,
};

export function setClientNotice(cookies: any, notice: ClientNotice) {
  cookies.set(CLIENT_NOTICE_COOKIE, notice, CLIENT_NOTICE_OPTIONS);
}

export function consumeClientNotice(cookies: any): ClientNotice | null {
  const rawNotice = cookies.get(CLIENT_NOTICE_COOKIE);

  if (!rawNotice) {
    return null;
  }

  cookies.delete(CLIENT_NOTICE_COOKIE, {
    path: "/",
  });

  try {
    const parsed = rawNotice.json() as ClientNotice;

    if (!parsed || typeof parsed !== "object") {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}
