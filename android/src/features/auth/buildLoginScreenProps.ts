import type { Dispatch, RefObject, SetStateAction } from "react";
import type { TextInput } from "react-native";

import type { LoginScreenProps } from "./LoginScreen";

function sanitizeProbeValue(value: string, fallback = "none"): string {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return fallback;
  }
  return normalized.replace(/[;\n\r]+/g, ",").slice(0, 180);
}

export interface BuildLoginScreenPropsInput {
  accentColor: string;
  animacoesAtivas: boolean;
  automationDiagnosticsEnabled?: boolean;
  appGradientColors: readonly [string, string, ...string[]];
  carregando: boolean;
  email: string;
  emailInputRef: RefObject<TextInput | null>;
  entrando: boolean;
  erro: string;
  fontScale: number;
  handleEsqueciSenha: () => void | Promise<void>;
  handleLogin: () => void | Promise<void>;
  handleLoginSocial: (provider: "Google" | "Microsoft") => void | Promise<void>;
  introVisivel: boolean;
  keyboardAvoidingBehavior: LoginScreenProps["keyboardAvoidingBehavior"];
  keyboardVisible: boolean;
  loginStage:
    | "idle"
    | "authenticating"
    | "loading_bootstrap"
    | "persisting_session"
    | "error";
  statusApi: "checking" | "online" | "offline";
  loginKeyboardBottomPadding: number;
  loginKeyboardVerticalOffset: number;
  mostrarSenha: boolean;
  senha: string;
  senhaInputRef: RefObject<TextInput | null>;
  setEmail: Dispatch<SetStateAction<string>>;
  setIntroVisivel: Dispatch<SetStateAction<boolean>>;
  setMostrarSenha: Dispatch<SetStateAction<boolean>>;
  setSenha: Dispatch<SetStateAction<string>>;
}

export function buildLoginScreenProps(
  input: BuildLoginScreenPropsInput,
): LoginScreenProps {
  const {
    accentColor,
    animacoesAtivas,
    automationDiagnosticsEnabled,
    appGradientColors,
    carregando,
    email,
    emailInputRef,
    entrando,
    erro,
    fontScale,
    handleEsqueciSenha,
    handleLogin,
    handleLoginSocial,
    introVisivel,
    keyboardAvoidingBehavior,
    keyboardVisible,
    loginStage,
    statusApi,
    loginKeyboardBottomPadding,
    loginKeyboardVerticalOffset,
    mostrarSenha,
    senha,
    senhaInputRef,
    setEmail,
    setIntroVisivel,
    setMostrarSenha,
    setSenha,
  } = input;
  const loginAutomationProbeLabel = automationDiagnosticsEnabled
    ? [
        "pilot_login_probe",
        `stage=${sanitizeProbeValue(loginStage, "idle")}`,
        `status_api=${sanitizeProbeValue(statusApi, "checking")}`,
        `entrando=${entrando ? "1" : "0"}`,
        `carregando=${carregando ? "1" : "0"}`,
        `erro=${sanitizeProbeValue(erro)}`,
      ].join(";")
    : "";
  const loginAutomationMarkerIds = automationDiagnosticsEnabled
    ? [
        `login-stage-${sanitizeProbeValue(loginStage, "idle")}`,
        entrando ? "login-stage-entrando" : "login-stage-idle",
        erro.trim() ? "login-error-visible" : "login-error-hidden",
      ]
    : [];

  return {
    accentColor,
    animacoesAtivas,
    automationDiagnosticsEnabled: Boolean(automationDiagnosticsEnabled),
    appGradientColors,
    carregando,
    email,
    emailInputRef,
    entrando,
    erro,
    fontScale,
    introVisivel,
    keyboardAvoidingBehavior,
    keyboardVisible,
    loginAutomationMarkerIds,
    loginAutomationProbeLabel,
    loginKeyboardBottomPadding,
    loginKeyboardVerticalOffset,
    mostrarSenha,
    onEmailChange: setEmail,
    onEmailSubmit: () => senhaInputRef.current?.focus(),
    onEsqueciSenha: () => {
      void handleEsqueciSenha();
    },
    onIntroDone: () => setIntroVisivel(false),
    onLogin: () => {
      void handleLogin();
    },
    onLoginSocial: (provider: "Google" | "Microsoft") => {
      void handleLoginSocial(provider);
    },
    onSenhaChange: setSenha,
    onSenhaSubmit: () => {
      if (entrando) {
        return;
      }
      void handleLogin();
    },
    onToggleMostrarSenha: () => setMostrarSenha((current: boolean) => !current),
    senha,
    senhaInputRef,
  };
}
