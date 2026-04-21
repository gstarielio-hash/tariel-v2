export interface ReviewerNoticeCredential {
  label: string;
  portal?: string;
  email?: string;
  password?: string;
  notes?: string[];
}

export interface ReviewerNotice {
  tone: "success" | "error" | "info";
  title: string;
  message: string;
  details?: string[];
  credentials?: ReviewerNoticeCredential[];
}

const REVIEWER_NOTICE_COOKIE = "tariel_reviewer_notice";
const REVIEWER_NOTICE_OPTIONS = {
  path: "/",
  httpOnly: true,
  sameSite: "lax" as const,
  maxAge: 120,
};

export function setReviewerNotice(cookies: any, notice: ReviewerNotice) {
  cookies.set(REVIEWER_NOTICE_COOKIE, notice, REVIEWER_NOTICE_OPTIONS);
}

export function consumeReviewerNotice(cookies: any): ReviewerNotice | null {
  const rawNotice = cookies.get(REVIEWER_NOTICE_COOKIE);

  if (!rawNotice) {
    return null;
  }

  cookies.delete(REVIEWER_NOTICE_COOKIE, {
    path: "/",
  });

  try {
    const parsed = rawNotice.json() as ReviewerNotice;

    if (!parsed || typeof parsed !== "object") {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}
