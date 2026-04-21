import type {
  MobilePushRegistration,
  MobilePushRegistrationResponse,
} from "../types/mobile";
import {
  buildApiUrl,
  construirHeaders,
  extrairMensagemErro,
  fetchComObservabilidade,
  lerJsonSeguro,
} from "./apiCore";

function extrairRegistroPush(payload: unknown): MobilePushRegistration | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }
  const registration = (payload as { registration?: unknown }).registration;
  if (
    !registration ||
    typeof registration !== "object" ||
    Array.isArray(registration)
  ) {
    return null;
  }
  return registration as MobilePushRegistration;
}

export interface MobilePushRegistrationPayload {
  device_id: string;
  plataforma: "android" | "ios";
  provider: "expo" | "native";
  push_token: string;
  permissao_notificacoes: boolean;
  push_habilitado: boolean;
  token_status: string;
  canal_build: string;
  app_version: string;
  build_number: string;
  device_label: string;
  is_emulator: boolean;
  ultimo_erro: string;
}

export async function registrarDispositivoPushMobile(
  accessToken: string,
  payload: MobilePushRegistrationPayload,
): Promise<MobilePushRegistrationResponse> {
  const response = await fetchComObservabilidade(
    "mobile_push_register",
    buildApiUrl("/app/api/mobile/push/register"),
    {
      method: "POST",
      headers: construirHeaders(accessToken, {
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(payload),
    },
  );

  const body = await lerJsonSeguro<
    MobilePushRegistrationResponse | { detail?: string }
  >(response);
  const registration = extrairRegistroPush(body);
  if (!response.ok || !body || !registration) {
    throw new Error(
      extrairMensagemErro(
        body,
        "Nao foi possivel sincronizar o registro push do dispositivo.",
      ),
    );
  }

  return {
    ok: true,
    registration,
  };
}
