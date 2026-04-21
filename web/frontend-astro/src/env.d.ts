/// <reference types="astro/client" />

import type { AuthenticatedAdminRequest } from "@/lib/server/admin-auth";
import type {
  AuthenticatedClientPasswordResetRequest,
  AuthenticatedClientRequest,
} from "@/lib/server/client-auth";
import type {
  AuthenticatedReviewerPasswordResetRequest,
  AuthenticatedReviewerRequest,
} from "@/lib/server/reviewer-auth";

declare global {
  namespace App {
    interface Locals {
      adminSession: AuthenticatedAdminRequest | null;
      clientSession: AuthenticatedClientRequest | null;
      clientPasswordResetSession: AuthenticatedClientPasswordResetRequest | null;
      reviewerSession: AuthenticatedReviewerRequest | null;
      reviewerPasswordResetSession: AuthenticatedReviewerPasswordResetRequest | null;
    }
  }
}

export {};
