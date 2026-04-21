import type {
  BuildThreadContextStateInput,
  ThreadContextStateResult,
} from "../common/inspectorDerivedStateTypes";
import {
  descricaoCaseLifecycle,
  hasFormalCaseWorkflow,
  hasCaseSurfaceAction,
  resolverCaseLifecycleStatus,
  resolverCaseOwnerRole,
  rotuloCaseLifecycle,
} from "./caseLifecycle";
import { getGuidedInspectionProgress } from "../inspection/guidedInspection";
import {
  reasonLabelForInspectionEntryMode,
  resolveInspectionEntryMode,
} from "../inspection/inspectionEntryMode";
import { buildThreadContextActions } from "./buildThreadContextActions";
import { buildReportPackDraftSummary } from "./reportPackHelpers";
import {
  detalharReemissaoRecomendada,
  detalheMotivoHandoffMesa,
  resumirContextoFinalizacao,
  resumirReemissaoRecomendada,
  rotuloModoHandoffMesa,
  rotuloUltimaEvidenciaGuiada,
  tomResumoReportPack,
} from "./threadContextFinalization";

export function buildThreadContextState(
  input: BuildThreadContextStateInput,
): ThreadContextStateResult {
  const {
    caseCreationError,
    caseCreationState = "idle",
    conversaAtiva,
    entryModePreference,
    filtrarThreadContextChips,
    guidedInspectionDraft,
    laudosDisponiveis,
    mapearStatusLaudoVisual,
    mesaDisponivel,
    mesaTemMensagens,
    mensagensMesa,
    notificacoesMesaLaudoAtual,
    onAdvanceGuidedInspection,
    onOpenMesaTab,
    onOpenQualityGate,
    onResumeGuidedInspection,
    onStartFreeChat,
    onStartGuidedInspection,
    onStopGuidedInspection,
    rememberLastCaseMode,
    resumoFilaOffline,
    statusApi,
    threadHomeVisible,
    tipoTemplateAtivoLabel,
    vendoFinalizacao,
    vendoMesa,
  } = input;
  const guidedProgress = guidedInspectionDraft
    ? getGuidedInspectionProgress(guidedInspectionDraft)
    : null;
  const reemissoesRecomendadasTotal = laudosDisponiveis.filter(
    (item) => item.official_issue_summary?.primary_pdf_diverged,
  ).length;
  const resumoReemissaoRecomendada = resumirReemissaoRecomendada(
    reemissoesRecomendadasTotal,
  );
  const modoGuiadoAtivo = Boolean(guidedInspectionDraft) && !vendoMesa;
  const entryMode = resolveInspectionEntryMode({
    activeCase: conversaAtiva?.laudoCard,
    cards: laudosDisponiveis,
    preference: entryModePreference,
    rememberLastCaseMode,
  });
  const blankEntryModeIsEvidence =
    !modoGuiadoAtivo &&
    !vendoMesa &&
    !conversaAtiva?.laudoId &&
    entryMode.effective === "evidence_first";
  const blankCaseCreationInProgress =
    !modoGuiadoAtivo &&
    !vendoMesa &&
    !conversaAtiva?.laudoId &&
    caseCreationState === "creating";
  const blankCaseCreationQueuedOffline =
    !modoGuiadoAtivo &&
    !vendoMesa &&
    !conversaAtiva?.laudoId &&
    caseCreationState === "queued_offline";
  const blankCaseCreationError =
    !modoGuiadoAtivo &&
    !vendoMesa &&
    !conversaAtiva?.laudoId &&
    caseCreationState === "error";
  const activeCaseEntryModeIsEvidence =
    !modoGuiadoAtivo &&
    !vendoMesa &&
    Boolean(conversaAtiva?.laudoId) &&
    entryMode.effective === "evidence_first";
  const activeCaseJustCreated =
    !modoGuiadoAtivo &&
    !vendoMesa &&
    Boolean(conversaAtiva?.laudoId) &&
    caseCreationState === "created";
  const blankCaseCreationActive =
    blankCaseCreationInProgress ||
    blankCaseCreationQueuedOffline ||
    blankCaseCreationError;
  const entryModeReasonLabel = reasonLabelForInspectionEntryMode(
    entryMode.reason,
  );
  const chatVazioInicial =
    threadHomeVisible &&
    !vendoMesa &&
    !conversaAtiva?.laudoId &&
    !conversaAtiva?.mensagens?.length &&
    !resumoFilaOffline;
  const caseLifecycleStatus = resolverCaseLifecycleStatus({
    conversation: conversaAtiva,
  });
  const activeCaseFormalWorkflow =
    Boolean(conversaAtiva?.laudoId) &&
    hasFormalCaseWorkflow({
      allowedSurfaceActions: conversaAtiva?.allowedSurfaceActions,
      conversation: conversaAtiva,
      entryModeEffective: conversaAtiva?.laudoCard?.entry_mode_effective,
      lifecycleStatus: caseLifecycleStatus,
      workflowMode: conversaAtiva?.caseWorkflowMode,
    });
  const activeCaseVisualFree =
    Boolean(conversaAtiva?.laudoId) &&
    !activeCaseFormalWorkflow &&
    !activeCaseEntryModeIsEvidence;
  const activeOwnerRole = resolverCaseOwnerRole({
    conversation: conversaAtiva,
    lifecycleStatus: caseLifecycleStatus,
  });
  const canChatFinalize = hasCaseSurfaceAction({
    conversation: conversaAtiva,
    lifecycleStatus: caseLifecycleStatus,
    ownerRole: activeOwnerRole,
    action: "chat_finalize",
  });
  const canChatReopen = hasCaseSurfaceAction({
    conversation: conversaAtiva,
    lifecycleStatus: caseLifecycleStatus,
    ownerRole: activeOwnerRole,
    action: "chat_reopen",
  });
  const lifecycleLabel = rotuloCaseLifecycle(caseLifecycleStatus);
  const lifecycleDescription = descricaoCaseLifecycle(caseLifecycleStatus);
  const reportPackSummary = buildReportPackDraftSummary(
    conversaAtiva?.reportPackDraft,
  );
  const finalizationSummary = vendoFinalizacao
    ? resumirContextoFinalizacao({
        canChatFinalize,
        canChatReopen,
        caseLifecycleStatus,
        conversaAtiva,
        lifecycleDescription,
        reportPackSummary,
        tipoTemplateAtivoLabel,
      })
    : null;
  const ultimaEvidenciaGuiada =
    guidedInspectionDraft?.evidenceRefs[
      Math.max((guidedInspectionDraft?.evidenceRefs.length || 1) - 1, 0)
    ] || null;

  const statusVisualLaudo = mapearStatusLaudoVisual(
    conversaAtiva?.caseLifecycleStatus ||
      conversaAtiva?.laudoCard?.case_lifecycle_status ||
      conversaAtiva?.laudoCard?.status_card ||
      conversaAtiva?.statusCard ||
      "aberto",
  );
  const laudoContextTitle = modoGuiadoAtivo
    ? guidedInspectionDraft?.templateLabel || "Inspecao guiada"
    : vendoMesa
      ? conversaAtiva?.laudoCard?.titulo ||
        (conversaAtiva?.laudoId
          ? `Laudo #${conversaAtiva.laudoId}`
          : "Mesa avaliadora")
      : vendoFinalizacao
        ? finalizationSummary?.title ||
          conversaAtiva?.laudoCard?.titulo ||
          (conversaAtiva?.laudoId
            ? `Caso #${conversaAtiva.laudoId}`
            : "Fechamento do caso")
        : conversaAtiva?.laudoCard?.titulo ||
          (conversaAtiva?.laudoId
            ? `Laudo #${conversaAtiva.laudoId}`
            : blankCaseCreationInProgress
              ? "Criando caso..."
              : blankCaseCreationQueuedOffline
                ? "Caso aguardando sincronização"
                : blankCaseCreationError
                  ? "Falha ao criar caso"
                  : "Por onde começar?");
  const laudoContextDescription = modoGuiadoAtivo
    ? guidedProgress?.isComplete
      ? "Checklist base concluido. Revise as evidencias e envie para a IA consolidar o rascunho do laudo."
      : "A IA guia a coleta no chat enquanto voce confirma as evidencias obrigatorias do template."
    : vendoMesa
      ? !mesaDisponivel
        ? "A mesa fica disponível após o primeiro laudo."
        : activeOwnerRole === "mesa"
          ? lifecycleDescription
          : mesaTemMensagens
            ? conversaAtiva?.permiteEdicao
              ? "Use esta aba apenas para tratativas da mesa."
              : "Acompanhe os retornos técnicos sem misturar com o chat principal."
            : "Retornos técnicos da mesa aparecem aqui, separados do chat principal."
      : conversaAtiva?.laudoId
        ? activeCaseJustCreated
          ? activeCaseEntryModeIsEvidence
            ? "Caso criado no primeiro envio. A coleta guiada continua sendo a origem preferida deste laudo."
            : "Caso criado no primeiro envio. Continue a coleta no mesmo laudo sem abrir uma thread paralela."
          : canChatReopen
            ? lifecycleDescription
            : activeCaseEntryModeIsEvidence
              ? "Este caso prioriza coleta guiada. Retome o checklist do caso ou siga no chat sem abrir um novo laudo."
              : activeCaseVisualFree
                ? "Continue no chat livre deste caso. Se quiser começar outra conversa, toque em Novo chat."
                : "Registre achado, contexto e evidências com clareza."
        : blankCaseCreationInProgress
          ? "O primeiro envio já saiu do app. Aguarde a IA devolver o número do caso e o contexto inicial antes de enviar outra abertura."
          : blankCaseCreationQueuedOffline
            ? `${resumoFilaOffline ? `${resumoFilaOffline}. ` : ""}O primeiro envio ficou guardado localmente. O laudo será criado quando a sincronização voltar ao servidor.`
            : blankCaseCreationError
              ? caseCreationError?.trim() ||
                "O primeiro envio falhou antes de criar o caso. Revise a conexão e tente novamente."
              : "Escolha um modo para iniciar.";
  const laudoContextDescriptionFinal = vendoFinalizacao
    ? finalizationSummary?.description || laudoContextDescription
    : laudoContextDescription;
  const threadSpotlight = vendoFinalizacao
    ? finalizationSummary?.spotlight || {
        label: "Fechamento governado",
        tone: "accent" as const,
        icon: "clipboard-clock-outline" as const,
      }
    : modoGuiadoAtivo
      ? guidedProgress?.isComplete
        ? {
            label: "Checklist base concluido",
            tone: "success" as const,
            icon: "check-decagram-outline" as const,
          }
        : {
            label: "IA conduzindo coleta",
            tone: "accent" as const,
            icon: "robot-outline" as const,
          }
      : vendoMesa
        ? !mesaDisponivel
          ? {
              label: "Sem laudo",
              tone: "muted" as const,
              icon: "clipboard-clock-outline" as const,
            }
          : mesaTemMensagens
            ? conversaAtiva?.permiteEdicao
              ? {
                  label: "Mesa ativa",
                  tone: "accent" as const,
                  icon: "message-reply-text-outline" as const,
                }
              : {
                  label: "Modo leitura",
                  tone: "muted" as const,
                  icon: "lock-outline" as const,
                }
            : {
                label: "Sem retorno",
                tone: "muted" as const,
                icon: "clock-outline" as const,
              }
        : conversaAtiva?.laudoId
          ? activeCaseJustCreated
            ? {
                label: "Caso criado",
                tone: "success" as const,
                icon: "check-decagram-outline" as const,
              }
            : activeCaseVisualFree
              ? {
                  label: "Chat livre ativo",
                  tone: "success" as const,
                  icon: "message-processing-outline" as const,
                }
              : activeOwnerRole === "mesa"
                ? {
                    label: lifecycleLabel,
                    tone: "accent" as const,
                    icon: "clipboard-clock-outline" as const,
                  }
                : caseLifecycleStatus === "devolvido_para_correcao"
                  ? {
                      label: "Correção pendente",
                      tone: "danger" as const,
                      icon: "alert-circle-outline" as const,
                    }
                  : caseLifecycleStatus === "emitido"
                    ? {
                        label: "Documento emitido",
                        tone: "success" as const,
                        icon: "check-decagram-outline" as const,
                      }
                    : canChatReopen
                      ? {
                          label: "Modo leitura",
                          tone: "muted" as const,
                          icon: "lock-outline" as const,
                        }
                      : activeCaseEntryModeIsEvidence
                        ? {
                            label: "Coleta guiada preferida",
                            tone: "accent" as const,
                            icon: "robot-outline" as const,
                          }
                        : {
                            label: lifecycleLabel,
                            tone: statusVisualLaudo.tone,
                            icon: statusVisualLaudo.icon,
                          }
          : blankCaseCreationInProgress
            ? {
                label: "Criando caso",
                tone: "accent" as const,
                icon: "progress-clock" as const,
              }
            : blankCaseCreationQueuedOffline
              ? {
                  label: "Aguardando rede",
                  tone:
                    statusApi === "offline"
                      ? ("danger" as const)
                      : ("accent" as const),
                  icon:
                    statusApi === "offline"
                      ? ("cloud-off-outline" as const)
                      : ("cloud-upload-outline" as const),
                }
              : blankCaseCreationError
                ? {
                    label: "Falha no 1º envio",
                    tone: "danger" as const,
                    icon: "alert-circle-outline" as const,
                  }
                : {
                    label: blankEntryModeIsEvidence
                      ? "IA recomenda guiado"
                      : "Chat livre como padrão",
                    tone: blankEntryModeIsEvidence
                      ? ("accent" as const)
                      : ("success" as const),
                    icon: blankEntryModeIsEvidence
                      ? ("robot-outline" as const)
                      : ("message-processing-outline" as const),
                  };
  const mostrarContextoThread =
    vendoMesa ||
    Boolean(conversaAtiva?.laudoId) ||
    Boolean(resumoFilaOffline) ||
    Boolean(modoGuiadoAtivo) ||
    blankCaseCreationActive ||
    chatVazioInicial;
  const mesaContextChips = [
    mesaDisponivel
      ? {
          key: "status",
          label: lifecycleLabel,
          tone: "accent" as const,
          icon: "clipboard-text-outline" as const,
        }
      : null,
    notificacoesMesaLaudoAtual
      ? {
          key: "naolidas",
          label: `${notificacoesMesaLaudoAtual} nova${notificacoesMesaLaudoAtual === 1 ? "" : "s"}`,
          tone: "danger" as const,
          icon: "bell-ring-outline" as const,
        }
      : null,
    mesaDisponivel && !notificacoesMesaLaudoAtual && mesaTemMensagens
      ? {
          key: "modo",
          label: conversaAtiva?.permiteEdicao
            ? "Resposta liberada"
            : "Modo leitura",
          tone: conversaAtiva?.permiteEdicao
            ? ("success" as const)
            : ("muted" as const),
          icon: conversaAtiva?.permiteEdicao
            ? ("reply-outline" as const)
            : ("lock-outline" as const),
        }
      : null,
  ];
  const chatContextChips = modoGuiadoAtivo
    ? [
        {
          key: "checklist",
          label: `${guidedProgress?.completedCount || 0}/${guidedProgress?.totalCount || 0} etapas`,
          tone: guidedProgress?.isComplete
            ? ("success" as const)
            : ("accent" as const),
          icon: guidedProgress?.isComplete
            ? ("check-decagram-outline" as const)
            : ("clipboard-text-search-outline" as const),
        },
        guidedInspectionDraft?.mesaHandoff?.required
          ? {
              key: "mesa-handoff",
              label: "Mesa requerida",
              tone: "danger" as const,
              icon: "clipboard-alert-outline" as const,
            }
          : null,
        {
          key: "template",
          label: guidedInspectionDraft?.templateLabel || "Template guiado",
          tone: "muted" as const,
          icon: "shape-outline" as const,
        },
        guidedProgress?.currentItem
          ? {
              key: "etapa",
              label: guidedProgress.currentItem.title,
              tone: "muted" as const,
              icon: "arrow-right-circle-outline" as const,
            }
          : null,
      ]
    : [
        conversaAtiva?.laudoId
          ? {
              key: "status",
              label: activeCaseVisualFree
                ? "Chat livre"
                : conversaAtiva?.laudoCard?.status_card_label || "Em andamento",
              tone: activeCaseVisualFree
                ? ("success" as const)
                : ("accent" as const),
              icon: activeCaseVisualFree
                ? ("message-processing-outline" as const)
                : ("file-document-edit-outline" as const),
            }
          : blankCaseCreationInProgress
            ? {
                key: "creation-state",
                label: "1º envio em processamento",
                tone: "accent" as const,
                icon: "progress-clock" as const,
              }
            : blankCaseCreationQueuedOffline
              ? {
                  key: "creation-state",
                  label: "Caso no próximo sync",
                  tone:
                    statusApi === "offline"
                      ? ("danger" as const)
                      : ("accent" as const),
                  icon:
                    statusApi === "offline"
                      ? ("cloud-off-outline" as const)
                      : ("cloud-upload-outline" as const),
                }
              : blankCaseCreationError
                ? {
                    key: "creation-state",
                    label: "Falha no 1º envio",
                    tone: "danger" as const,
                    icon: "alert-circle-outline" as const,
                  }
                : {
                    key: "nova",
                    label: blankEntryModeIsEvidence
                      ? "Entrada guiada"
                      : "Chat livre",
                    tone: blankEntryModeIsEvidence
                      ? ("accent" as const)
                      : ("success" as const),
                    icon: blankEntryModeIsEvidence
                      ? ("robot-outline" as const)
                      : ("message-processing-outline" as const),
                  },
        activeCaseJustCreated
          ? {
              key: "creation-success",
              label: "Caso criado",
              tone: "success" as const,
              icon: "check-decagram-outline" as const,
            }
          : null,
        blankCaseCreationInProgress
          ? {
              key: "creation",
              label: "Aguarde a IA",
              tone: "muted" as const,
              icon: "timer-sand" as const,
            }
          : null,
        blankCaseCreationQueuedOffline
          ? {
              key: "offline",
              label: resumoFilaOffline || "Fila offline ativa",
              tone:
                statusApi === "offline"
                  ? ("danger" as const)
                  : ("muted" as const),
              icon:
                statusApi === "offline"
                  ? ("cloud-off-outline" as const)
                  : ("cloud-upload-outline" as const),
            }
          : null,
        blankCaseCreationError
          ? {
              key: "creation",
              label: "Rascunho restaurado",
              tone: "muted" as const,
              icon: "history" as const,
            }
          : null,
        !conversaAtiva?.laudoId &&
        blankEntryModeIsEvidence &&
        !blankCaseCreationActive
          ? {
              key: "origem",
              label: "IA recomenda guiado",
              tone: "accent" as const,
              icon: "robot-outline" as const,
            }
          : activeCaseEntryModeIsEvidence
            ? {
                key: "origem",
                label: "Coleta guiada",
                tone: "accent" as const,
                icon: "robot-outline" as const,
              }
            : null,
        canChatReopen
          ? {
              key: "reabrir",
              label:
                caseLifecycleStatus === "emitido"
                  ? "Reabra para novo ciclo"
                  : "Reabra para corrigir",
              tone: "danger" as const,
              icon: "history" as const,
            }
          : null,
        resumoFilaOffline && !blankCaseCreationQueuedOffline
          ? {
              key: "offline",
              label: resumoFilaOffline,
              tone:
                statusApi === "offline"
                  ? ("danger" as const)
                  : ("muted" as const),
              icon:
                statusApi === "offline"
                  ? ("cloud-off-outline" as const)
                  : ("cloud-upload-outline" as const),
            }
          : null,
        conversaAtiva?.laudoId
          ? {
              key: "template",
              label: tipoTemplateAtivoLabel,
              tone: "muted" as const,
              icon: "shape-outline" as const,
            }
          : null,
      ];
  const finalizationContextChips = finalizationSummary?.chips || [];
  const entryChooserContextChips =
    reemissoesRecomendadasTotal > 0
      ? [
          {
            key: "governance-reissue",
            label: resumoReemissaoRecomendada,
            tone: "danger" as const,
            icon: "alert-circle-outline" as const,
          },
        ]
      : [];
  const entryChooserLayout =
    threadHomeVisible &&
    !vendoMesa &&
    !conversaAtiva?.laudoId &&
    !modoGuiadoAtivo &&
    !blankCaseCreationActive;
  const chipsContextoThread = entryChooserLayout
    ? filtrarThreadContextChips(entryChooserContextChips)
    : filtrarThreadContextChips(
        vendoFinalizacao
          ? finalizationContextChips
          : vendoMesa
            ? mesaContextChips
            : chatContextChips,
      ).slice(0, vendoFinalizacao ? 3 : 2);
  const threadInsights = modoGuiadoAtivo
    ? [
        {
          key: "progresso",
          label: "Progresso",
          value: `${guidedProgress?.completedCount || 0}/${guidedProgress?.totalCount || 0}`,
          detail: guidedProgress?.isComplete
            ? "Checklist base pronto para consolidacao."
            : `${guidedProgress?.remainingCount || 0} etapa${guidedProgress?.remainingCount === 1 ? "" : "s"} restante${guidedProgress?.remainingCount === 1 ? "" : "s"}.`,
          tone: guidedProgress?.isComplete
            ? ("success" as const)
            : ("accent" as const),
          icon: guidedProgress?.isComplete
            ? ("check-decagram-outline" as const)
            : ("timeline-outline" as const),
        },
        {
          key: "etapa-atual",
          label: guidedProgress?.isComplete ? "Pronto" : "Etapa atual",
          value:
            guidedProgress?.currentItem?.title || "Revise e gere o rascunho",
          detail:
            guidedProgress?.currentItem?.evidenceHint ||
            "Use o chat para complementar evidencias antes do rascunho.",
          tone: "muted" as const,
          icon: guidedProgress?.currentItem
            ? ("clipboard-text-search-outline" as const)
            : ("file-document-check-outline" as const),
        },
        {
          key: "bundle",
          label: "Bundle do caso",
          value: `${guidedInspectionDraft?.evidenceRefs.length || 0} evid.`,
          detail: guidedInspectionDraft?.evidenceRefs.length
            ? "Evidencias guiadas vinculadas a mensagens da thread do laudo."
            : "As proximas evidencias guiadas entram na mesma thread canonica do caso.",
          tone: "success" as const,
          icon: "link-variant" as const,
        },
        ultimaEvidenciaGuiada
          ? {
              key: "ultima-evidencia",
              label: "Ultima evidencia",
              value: ultimaEvidenciaGuiada.stepTitle,
              detail: rotuloUltimaEvidenciaGuiada(
                ultimaEvidenciaGuiada.attachmentKind,
              ),
              tone: "muted" as const,
              icon: "camera-plus-outline" as const,
            }
          : null,
        reportPackSummary
          ? {
              key: "report-pack",
              label: "Pre-laudo",
              value: reportPackSummary.totalBlocks
                ? `${reportPackSummary.readyBlocks}/${reportPackSummary.totalBlocks} blocos`
                : reportPackSummary.readinessLabel,
              detail: `${reportPackSummary.readinessLabel}. ${reportPackSummary.readinessDetail}`,
              tone: tomResumoReportPack(
                reportPackSummary.pendingBlocks,
                reportPackSummary.attentionBlocks,
              ),
              icon: "file-document-outline" as const,
            }
          : null,
        reportPackSummary?.inspectionContextLabel
          ? {
              key: "inspection-context",
              label: "Ativo",
              value: reportPackSummary.inspectionContextLabel,
              detail:
                reportPackSummary.inspectionContextDetail ||
                "Contexto principal do ativo reaproveitado do pre-laudo.",
              tone: "muted" as const,
              icon: "map-marker-outline" as const,
            }
          : null,
        guidedInspectionDraft?.mesaHandoff?.required
          ? {
              key: "mesa",
              label: "Revisao",
              value: rotuloModoHandoffMesa(
                guidedInspectionDraft.mesaHandoff.reviewMode,
              ),
              detail:
                `Registrado a partir da etapa ${guidedInspectionDraft.mesaHandoff.stepTitle}. ` +
                detalheMotivoHandoffMesa(
                  guidedInspectionDraft.mesaHandoff.reasonCode,
                ),
              tone: "danger" as const,
              icon: "clipboard-alert-outline" as const,
            }
          : null,
      ].filter((item): item is Exclude<typeof item, null> => item !== null)
    : vendoFinalizacao
      ? finalizationSummary?.insights || []
      : conversaAtiva?.laudoCard
        ? vendoMesa
          ? [
              activeCaseJustCreated
                ? {
                    key: "case-creation",
                    label: "Criação",
                    value:
                      conversaAtiva.laudoId != null
                        ? `Laudo #${conversaAtiva.laudoId}`
                        : "Caso criado",
                    detail:
                      "O primeiro envio abriu o caso com sucesso. Agora toda nova evidência entra no mesmo trilho canônico.",
                    tone: "success" as const,
                    icon: "check-decagram-outline" as const,
                  }
                : null,
              {
                key: "status",
                label: "Lifecycle",
                value: lifecycleLabel,
                detail:
                  activeOwnerRole === "mesa"
                    ? "A mesa está conduzindo esta etapa do caso."
                    : conversaAtiva.permiteEdicao
                      ? "Resposta liberada no app"
                      : lifecycleDescription,
                tone: statusVisualLaudo.tone,
                icon: statusVisualLaudo.icon,
              },
              {
                key: mesaTemMensagens ? "retornos" : "template",
                label: mesaTemMensagens ? "Mesa" : "Fluxo",
                value: mesaTemMensagens
                  ? `${mensagensMesa.length} retorno${mensagensMesa.length === 1 ? "" : "s"}`
                  : tipoTemplateAtivoLabel,
                detail: mesaTemMensagens
                  ? "Retornos técnicos separados do chat."
                  : "A mesa será usada quando houver retorno técnico.",
                tone: mesaTemMensagens
                  ? ("muted" as const)
                  : ("muted" as const),
                icon: mesaTemMensagens
                  ? ("message-reply-text-outline" as const)
                  : ("shape-outline" as const),
              },
            ].filter(
              (item): item is Exclude<typeof item, null> => item !== null,
            )
          : [
              {
                key: activeCaseVisualFree ? "mode" : "status",
                label: activeCaseVisualFree ? "Modo" : "Lifecycle",
                value: activeCaseVisualFree ? "Chat livre" : lifecycleLabel,
                detail: activeCaseVisualFree
                  ? "Sem trilho canônico visível no chat. A conversa segue livre até você decidir abrir outro fluxo."
                  : canChatReopen
                    ? lifecycleDescription
                    : activeCaseEntryModeIsEvidence
                      ? "Modo preferido deste caso: coleta guiada."
                      : lifecycleDescription,
                tone: activeCaseVisualFree
                  ? ("success" as const)
                  : statusVisualLaudo.tone,
                icon: activeCaseVisualFree
                  ? ("message-processing-outline" as const)
                  : statusVisualLaudo.icon,
              },
              {
                key: activeCaseEntryModeIsEvidence ? "origem" : "ultima",
                label: activeCaseEntryModeIsEvidence
                  ? "Origem"
                  : "Última atividade",
                value: activeCaseEntryModeIsEvidence
                  ? entryModeReasonLabel
                  : conversaAtiva.laudoCard.hora_br ||
                    conversaAtiva.laudoCard.data_br,
                detail: activeCaseEntryModeIsEvidence
                  ? "Voce pode retomar a coleta guiada ou manter o chat livre no mesmo caso."
                  : [
                      conversaAtiva.laudoCard.data_br,
                      conversaAtiva.laudoCard.tipo_template,
                    ]
                      .filter(Boolean)
                      .join(" • "),
                tone: "muted" as const,
                icon: activeCaseEntryModeIsEvidence
                  ? ("history" as const)
                  : ("calendar-clock-outline" as const),
              },
              activeCaseFormalWorkflow && reportPackSummary
                ? {
                    key: "report-pack",
                    label: "Pre-laudo",
                    value: reportPackSummary.totalBlocks
                      ? `${reportPackSummary.readyBlocks}/${reportPackSummary.totalBlocks} blocos`
                      : reportPackSummary.readinessLabel,
                    detail: `${reportPackSummary.readinessLabel}. ${reportPackSummary.readinessDetail}`,
                    tone: tomResumoReportPack(
                      reportPackSummary.pendingBlocks,
                      reportPackSummary.attentionBlocks,
                    ),
                    icon: "file-document-outline" as const,
                  }
                : null,
              activeCaseFormalWorkflow &&
              reportPackSummary?.inspectionContextLabel
                ? {
                    key: "inspection-context",
                    label: "Ativo",
                    value: reportPackSummary.inspectionContextLabel,
                    detail:
                      reportPackSummary.inspectionContextDetail ||
                      "Contexto principal do ativo reaproveitado do pre-laudo.",
                    tone: "muted" as const,
                    icon: "map-marker-outline" as const,
                  }
                : null,
            ].filter(
              (item): item is Exclude<typeof item, null> => item !== null,
            )
        : !vendoMesa && !conversaAtiva?.laudoId
          ? blankCaseCreationInProgress
            ? [
                {
                  key: "case-creation",
                  label: "Criação",
                  value: "Em processamento",
                  detail:
                    "O primeiro envio está tentando abrir o caso no backend. Aguarde a devolutiva da IA antes de reenviar a abertura.",
                  tone: "accent" as const,
                  icon: "progress-clock" as const,
                },
              ]
            : blankCaseCreationQueuedOffline
              ? [
                  {
                    key: "case-creation",
                    label: "Criação",
                    value: "Na fila local",
                    detail: `${resumoFilaOffline ? `${resumoFilaOffline}. ` : ""}O caso só será criado no servidor quando a sincronização voltar.`,
                    tone:
                      statusApi === "offline"
                        ? ("danger" as const)
                        : ("accent" as const),
                    icon:
                      statusApi === "offline"
                        ? ("cloud-off-outline" as const)
                        : ("cloud-upload-outline" as const),
                  },
                ]
              : blankCaseCreationError
                ? [
                    {
                      key: "case-creation",
                      label: "Criação",
                      value: "Falhou",
                      detail:
                        caseCreationError?.trim() ||
                        "O primeiro envio não conseguiu abrir o caso. Revise a conexão e tente novamente.",
                      tone: "danger" as const,
                      icon: "alert-circle-outline" as const,
                    },
                  ]
                : reemissoesRecomendadasTotal > 0
                  ? [
                      {
                        key: "governance-reissue",
                        label: "Governança",
                        value: resumoReemissaoRecomendada,
                        detail: detalharReemissaoRecomendada(
                          reemissoesRecomendadasTotal,
                        ),
                        tone: "danger" as const,
                        icon: "alert-circle-outline" as const,
                      },
                    ]
                  : []
          : [];
  const threadActions = buildThreadContextActions({
    activeCaseEntryModeIsEvidence,
    activeCaseFormalWorkflow,
    activeOwnerRole,
    blankCaseCreationInProgress,
    blankCaseCreationQueuedOffline,
    canChatFinalize,
    conversaAtiva,
    guidedInspectionDraft,
    guidedProgress,
    mesaDisponivel,
    modoGuiadoAtivo,
    onAdvanceGuidedInspection,
    onOpenMesaTab,
    onOpenQualityGate,
    onResumeGuidedInspection,
    onStartFreeChat,
    onStartGuidedInspection,
    onStopGuidedInspection,
    reportPackSummary,
    vendoFinalizacao,
    vendoMesa,
  });

  return {
    chipsContextoThread,
    laudoContextDescription: laudoContextDescriptionFinal,
    laudoContextTitle,
    mostrarContextoThread,
    statusVisualLaudo,
    threadContextLayout: vendoFinalizacao
      ? "finalization"
      : entryChooserLayout
        ? "entry_chooser"
        : "default",
    threadActions,
    threadInsights,
    threadSpotlight,
  };
}
