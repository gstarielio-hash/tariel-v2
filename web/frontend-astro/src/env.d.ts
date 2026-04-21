/// <reference types="astro/client" />

import type { AuthenticatedAdminRequest } from "@/lib/server/admin-auth";

declare global {
  namespace App {
    interface Locals {
      adminSession: AuthenticatedAdminRequest | null;
    }
  }
}

export {};
