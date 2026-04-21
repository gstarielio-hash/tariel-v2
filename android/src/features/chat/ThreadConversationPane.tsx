import { type RefObject } from "react";
import {
  ScrollView,
  type ImageSourcePropType,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";

import type {
  MobileAttachment,
  MobileChatMessage,
  MobileLifecycleTransition,
  MobileMesaMessage,
  MobileMesaReviewCommandPayload,
  MobileReportPackDraft,
  MobileReviewPackage,
  MobileSurfaceAction,
} from "../../types/mobile";
import { hasFormalCaseWorkflow } from "./caseLifecycle";
import { ThreadConversationChatSurface } from "./ThreadConversationChatSurface";
import { ThreadConversationMesaSurface } from "./ThreadConversationMesaSurface";

export interface ThreadConversationPaneProps {
  vendoMesa: boolean;
  carregandoMesa: boolean;
  mensagensMesa: MobileMesaMessage[];
  reportPackDraft?: MobileReportPackDraft | null;
  reviewPackage?: MobileReviewPackage | null;
  caseLifecycleStatus?: string;
  caseWorkflowMode?: string;
  entryModeEffective?: string;
  activeOwnerRole?: string;
  allowedNextLifecycleStatuses?: string[];
  allowedLifecycleTransitions?: MobileLifecycleTransition[];
  allowedSurfaceActions?: MobileSurfaceAction[];
  mesaAcessoPermitido: boolean;
  mesaDisponivel: boolean;
  mesaIndisponivelDescricao: string;
  mesaIndisponivelTitulo: string;
  scrollRef: RefObject<ScrollView | null>;
  keyboardVisible: boolean;
  threadKeyboardPaddingBottom: number;
  nomeUsuarioExibicao: string;
  mensagensVisiveis: MobileChatMessage[];
  obterResumoReferenciaMensagem: (
    referenciaId: number | null,
    mensagensVisiveis: MobileChatMessage[],
    mensagensMesa: MobileMesaMessage[],
  ) => string;
  onAbrirReferenciaNoChat: (id: number) => void;
  onAbrirMesaTab?: () => void;
  onAbrirQualityGate?: () => void | Promise<void>;
  onUsarPerguntaPreLaudo?: (value: string) => void;
  sessionAccessToken: string | null;
  onAbrirAnexo: (attachment: MobileAttachment) => void;
  anexoAbrindoChave: string;
  toAttachmentKey: (attachment: MobileAttachment, fallback: string) => string;
  conversaPermiteEdicao: boolean;
  onDefinirReferenciaMesaAtiva: (item: MobileMesaMessage) => void;
  accentColor: string;
  carregandoConversa: boolean;
  conversaVazia: boolean;
  mensagemChatDestacadaId: number | null;
  onRegistrarLayoutMensagemChat: (id: number | null, y: number) => void;
  onExecutarComandoRevisaoMobile?: (
    payload: MobileMesaReviewCommandPayload,
  ) => Promise<void>;
  dynamicMessageBubbleStyle: StyleProp<ViewStyle>;
  dynamicMessageTextStyle: StyleProp<TextStyle>;
  enviandoMensagem: boolean;
  reviewCommandBusy?: boolean;
  brandMarkSource: ImageSourcePropType;
}

export function ThreadConversationPane({
  vendoMesa,
  carregandoMesa,
  mensagensMesa,
  reportPackDraft,
  reviewPackage,
  caseLifecycleStatus,
  caseWorkflowMode,
  entryModeEffective,
  activeOwnerRole,
  allowedNextLifecycleStatuses,
  allowedLifecycleTransitions,
  allowedSurfaceActions,
  mesaAcessoPermitido,
  mesaDisponivel,
  mesaIndisponivelDescricao,
  mesaIndisponivelTitulo,
  scrollRef,
  keyboardVisible,
  threadKeyboardPaddingBottom,
  nomeUsuarioExibicao,
  mensagensVisiveis,
  obterResumoReferenciaMensagem,
  onAbrirReferenciaNoChat,
  onAbrirMesaTab,
  onAbrirQualityGate,
  onUsarPerguntaPreLaudo,
  sessionAccessToken,
  onAbrirAnexo,
  anexoAbrindoChave,
  toAttachmentKey,
  conversaPermiteEdicao,
  onDefinirReferenciaMesaAtiva,
  onExecutarComandoRevisaoMobile,
  accentColor,
  carregandoConversa,
  conversaVazia,
  mensagemChatDestacadaId,
  onRegistrarLayoutMensagemChat,
  dynamicMessageBubbleStyle,
  dynamicMessageTextStyle,
  enviandoMensagem,
  reviewCommandBusy = false,
}: ThreadConversationPaneProps) {
  const fluxoFormalAtivo = hasFormalCaseWorkflow({
    allowedSurfaceActions,
    entryModeEffective,
    lifecycleStatus: caseLifecycleStatus,
    reportPackDraft,
    workflowMode: caseWorkflowMode,
  });

  if (vendoMesa) {
    return (
      <ThreadConversationMesaSurface
        accentColor={accentColor}
        activeOwnerRole={activeOwnerRole}
        allowedLifecycleTransitions={allowedLifecycleTransitions}
        allowedNextLifecycleStatuses={allowedNextLifecycleStatuses}
        allowedSurfaceActions={allowedSurfaceActions}
        anexoAbrindoChave={anexoAbrindoChave}
        carregandoMesa={carregandoMesa}
        caseLifecycleStatus={caseLifecycleStatus}
        conversaPermiteEdicao={conversaPermiteEdicao}
        dynamicMessageBubbleStyle={dynamicMessageBubbleStyle}
        dynamicMessageTextStyle={dynamicMessageTextStyle}
        keyboardVisible={keyboardVisible}
        mesaAcessoPermitido={mesaAcessoPermitido}
        mesaDisponivel={mesaDisponivel}
        mesaIndisponivelDescricao={mesaIndisponivelDescricao}
        mesaIndisponivelTitulo={mesaIndisponivelTitulo}
        mensagensMesa={mensagensMesa}
        mensagensVisiveis={mensagensVisiveis}
        nomeUsuarioExibicao={nomeUsuarioExibicao}
        obterResumoReferenciaMensagem={obterResumoReferenciaMensagem}
        onAbrirAnexo={onAbrirAnexo}
        onAbrirReferenciaNoChat={onAbrirReferenciaNoChat}
        onDefinirReferenciaMesaAtiva={onDefinirReferenciaMesaAtiva}
        onExecutarComandoRevisaoMobile={onExecutarComandoRevisaoMobile}
        reportPackDraft={reportPackDraft}
        reviewCommandBusy={reviewCommandBusy}
        reviewPackage={reviewPackage}
        scrollRef={scrollRef}
        sessionAccessToken={sessionAccessToken}
        threadKeyboardPaddingBottom={threadKeyboardPaddingBottom}
        toAttachmentKey={toAttachmentKey}
      />
    );
  }

  return (
    <ThreadConversationChatSurface
      allowedSurfaceActions={allowedSurfaceActions}
      anexoAbrindoChave={anexoAbrindoChave}
      carregandoConversa={carregandoConversa}
      caseLifecycleStatus={caseLifecycleStatus}
      conversaVazia={conversaVazia}
      dynamicMessageBubbleStyle={dynamicMessageBubbleStyle}
      dynamicMessageTextStyle={dynamicMessageTextStyle}
      enviandoMensagem={enviandoMensagem}
      fluxoFormalAtivo={fluxoFormalAtivo}
      keyboardVisible={keyboardVisible}
      mensagemChatDestacadaId={mensagemChatDestacadaId}
      mensagensMesa={mensagensMesa}
      mensagensVisiveis={mensagensVisiveis}
      obterResumoReferenciaMensagem={obterResumoReferenciaMensagem}
      onAbrirAnexo={onAbrirAnexo}
      onAbrirMesaTab={onAbrirMesaTab}
      onAbrirQualityGate={onAbrirQualityGate}
      onAbrirReferenciaNoChat={onAbrirReferenciaNoChat}
      onRegistrarLayoutMensagemChat={onRegistrarLayoutMensagemChat}
      onUsarPerguntaPreLaudo={onUsarPerguntaPreLaudo}
      reportPackDraft={reportPackDraft}
      reviewPackage={reviewPackage}
      scrollRef={scrollRef}
      sessionAccessToken={sessionAccessToken}
      threadKeyboardPaddingBottom={threadKeyboardPaddingBottom}
      toAttachmentKey={toAttachmentKey}
    />
  );
}
