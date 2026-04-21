import type {
  MobileLifecycleTransition,
  MobileSurfaceAction,
} from "../../types/mobile";

import {
  normalizarCaseLifecycleStatus,
  resolverCaseLifecycleStatusFallback,
} from "./caseLifecycleNormalization";
import type {
  CanonicalCaseLifecycleStatus,
  CanonicalCaseOwnerRole,
  CaseVisualIcon,
  CaseVisualTone,
} from "./caseLifecycleTypes";

export function rotuloCaseLifecycle(
  lifecycleStatus: CanonicalCaseLifecycleStatus,
): string {
  switch (lifecycleStatus) {
    case "analise_livre":
      return "Análise livre";
    case "pre_laudo":
      return "Pré-laudo";
    case "laudo_em_coleta":
      return "Laudo em coleta";
    case "aguardando_mesa":
      return "Aguardando mesa";
    case "em_revisao_mesa":
      return "Mesa em revisão";
    case "devolvido_para_correcao":
      return "Devolvido para correção";
    case "aprovado":
      return "Aprovado";
    case "emitido":
      return "Documento emitido";
  }
}

export function rotuloCaseOwnerRole(ownerRole: CanonicalCaseOwnerRole): string {
  switch (ownerRole) {
    case "mesa":
      return "Mesa avaliadora";
    case "none":
      return "Ciclo concluído";
    default:
      return "Inspetor";
  }
}

export function rotuloCaseSurfaceAction(action: MobileSurfaceAction): string {
  switch (action) {
    case "chat_finalize":
      return "Finalizar no chat";
    case "chat_reopen":
      return "Reabrir no chat";
    case "mesa_approve":
      return "Aprovar no mobile";
    case "mesa_return":
      return "Devolver no mobile";
    case "system_issue":
      return "Emitir documento";
  }
}

export function resumirCaseSurfaceActions(
  actions: MobileSurfaceAction[],
  maxItems = 3,
): string {
  return actions
    .map((item) => rotuloCaseSurfaceAction(item))
    .filter(Boolean)
    .slice(0, maxItems)
    .join(" · ");
}

export function resumirLifecycleTransitions(
  transitions: MobileLifecycleTransition[],
  maxItems = 3,
): string {
  return transitions
    .map((item) => item.label || rotuloCaseLifecycle(item.target_status))
    .filter(Boolean)
    .slice(0, maxItems)
    .join(" · ");
}

export function descricaoCaseLifecycle(
  lifecycleStatus: CanonicalCaseLifecycleStatus,
): string {
  switch (lifecycleStatus) {
    case "analise_livre":
      return "Chat com IA ativo, sem obrigação de laudo final.";
    case "pre_laudo":
      return "O caso já aponta para laudo, mas ainda sem coleta completa.";
    case "laudo_em_coleta":
      return "O inspetor ainda está coletando ou consolidando evidências.";
    case "aguardando_mesa":
      return "O caso foi enviado e aguarda entrada da mesa avaliadora.";
    case "em_revisao_mesa":
      return "A mesa está revisando o caso neste momento.";
    case "devolvido_para_correcao":
      return "O caso voltou para correção antes da conclusão final.";
    case "aprovado":
      return "A validação humana já aprovou o caso e resta emitir o documento final.";
    case "emitido":
      return "O PDF final já foi emitido e está pronto para entrega.";
  }
}

export function targetThreadCaseLifecycle(
  lifecycleStatus: CanonicalCaseLifecycleStatus,
): "chat" | "mesa" {
  if (
    lifecycleStatus === "aguardando_mesa" ||
    lifecycleStatus === "em_revisao_mesa"
  ) {
    return "mesa";
  }
  return "chat";
}

export function mapearLifecycleVisual(lifecycleOrStatus: string): {
  tone: CaseVisualTone;
  icon: CaseVisualIcon;
} {
  const lifecycle =
    normalizarCaseLifecycleStatus(lifecycleOrStatus) ||
    resolverCaseLifecycleStatusFallback({ statusCard: lifecycleOrStatus });
  switch (lifecycle) {
    case "devolvido_para_correcao":
      return {
        tone: "danger",
        icon: "alert-circle-outline",
      };
    case "aguardando_mesa":
    case "em_revisao_mesa":
      return {
        tone: "accent",
        icon: "clipboard-clock-outline",
      };
    case "aprovado":
      return {
        tone: "success",
        icon: "check-decagram-outline",
      };
    case "emitido":
      return {
        tone: "success",
        icon: "file-document-check-outline",
      };
    case "pre_laudo":
    case "laudo_em_coleta":
      return {
        tone: "success",
        icon: "file-document-edit-outline",
      };
    default:
      return {
        tone: "muted",
        icon: "message-processing-outline",
      };
  }
}
