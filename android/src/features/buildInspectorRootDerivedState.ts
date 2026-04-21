import { buildInspectorBaseDerivedState } from "./common/buildInspectorBaseDerivedState";
import {
  formatarHorarioAtividade,
  obterEscalaDensidade,
  obterEscalaFonte,
} from "./common/appSupportHelpers";
import { buildInspectorRootBaseDerivedStateInput } from "./common/buildInspectorRootBaseDerivedStateInput";
import { formatarTipoTemplateLaudo } from "./activity/activityNotificationHelpers";
import {
  podeEditarConversaNoComposer,
  previewChatLiberadoParaConversa,
} from "./chat/conversationHelpers";
import { buildHistorySections } from "./history/historyHelpers";
import {
  pendenciaFilaProntaParaReenvio,
  prioridadePendenciaOffline,
} from "./offline/offlineQueueHelpers";
import type { InspectorRootBootstrap } from "./useInspectorRootBootstrap";

export interface InspectorRootPresentationDerivedSnapshot {
  conversaAtiva: ReturnType<
    typeof buildInspectorBaseDerivedState
  >["conversaAtiva"];
  inspectorBaseDerivedState: ReturnType<typeof buildInspectorBaseDerivedState>;
  mesaDisponivel: ReturnType<
    typeof buildInspectorBaseDerivedState
  >["mesaDisponivel"];
  mesaTemMensagens: ReturnType<
    typeof buildInspectorBaseDerivedState
  >["mesaTemMensagens"];
  resumoFilaOffline: ReturnType<
    typeof buildInspectorBaseDerivedState
  >["resumoFilaOffline"];
  sessaoAtual: ReturnType<typeof buildInspectorBaseDerivedState>["sessaoAtual"];
  tipoTemplateAtivoLabel: ReturnType<
    typeof buildInspectorBaseDerivedState
  >["tipoTemplateAtivoLabel"];
  ultimoTicketSuporte: ReturnType<
    typeof buildInspectorBaseDerivedState
  >["ultimoTicketSuporte"];
  vendoFinalizacao: ReturnType<
    typeof buildInspectorBaseDerivedState
  >["vendoFinalizacao"];
  vendoMesa: ReturnType<typeof buildInspectorBaseDerivedState>["vendoMesa"];
}

export function buildInspectorRootDerivedState(
  bootstrap: InspectorRootBootstrap,
): InspectorRootPresentationDerivedSnapshot {
  const localState = bootstrap.localState;
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;
  const shellSupport = bootstrap.shellSupport;

  const inspectorBaseDerivedState = buildInspectorBaseDerivedState(
    buildInspectorRootBaseDerivedStateInput({
      shellState: {
        abaAtiva: localState.abaAtiva,
        buscaAjuda: settingsSupportState.presentationState.buscaAjuda,
        buscaConfiguracoes: localState.buscaConfiguracoes,
        colorScheme: bootstrap.colorScheme,
        filtroConfiguracoes: bootstrap.filtroConfiguracoes,
        keyboardHeight: shellSupport.keyboardHeight,
        session: sessionFlow.state.session,
        statusApi: sessionFlow.state.statusApi,
        statusAtualizacaoApp:
          settingsSupportState.presentationState.statusAtualizacaoApp,
        ultimaVerificacaoAtualizacao:
          settingsSupportState.presentationState.ultimaVerificacaoAtualizacao,
      },
      chatState: {
        anexoMesaRascunho: localState.anexoMesaRascunho,
        anexoRascunho: localState.anexoRascunho,
        carregandoConversa: localState.carregandoConversa,
        carregandoMesa: localState.carregandoMesa,
        conversa: localState.conversa,
        enviandoMensagem: localState.enviandoMensagem,
        enviandoMesa: localState.enviandoMesa,
        mensagem: localState.mensagem,
        mensagemMesa: localState.mensagemMesa,
        mensagensMesa: localState.mensagensMesa,
        preparandoAnexo: localState.preparandoAnexo,
      },
      historyAndOfflineState: {
        buscaHistorico: shellSupport.buscaHistorico,
        eventosSeguranca:
          settingsSupportState.presentationState.eventosSeguranca,
        filaOffline: localState.filaOffline,
        filaSuporteLocal:
          settingsSupportState.presentationState.filaSuporteLocal,
        filtroEventosSeguranca:
          settingsSupportState.presentationState.filtroEventosSeguranca,
        filtroFilaOffline: localState.filtroFilaOffline,
        filtroHistorico: localState.filtroHistorico,
        fixarConversas: settingsSupportState.presentationState.fixarConversas,
        historicoOcultoIds: localState.historicoOcultoIds,
        laudosDisponiveis: localState.laudosDisponiveis,
        notificacoes: localState.notificacoes,
        pendenciaFilaProntaParaReenvio,
        prioridadePendenciaOffline,
      },
      settingsState: {
        arquivosPermitidos: settingsBindings.security.arquivosPermitidos,
        biometriaPermitida: settingsBindings.security.biometriaPermitida,
        cameraPermitida: settingsBindings.security.cameraPermitida,
        codigosRecuperacao:
          settingsSupportState.presentationState.codigosRecuperacao,
        corDestaque: settingsBindings.appearance.corDestaque,
        contaTelefone: settingsBindings.account.contaTelefone,
        densidadeInterface: settingsBindings.appearance.densidadeInterface,
        email: sessionFlow.state.email,
        emailAtualConta: settingsBindings.account.emailAtualConta,
        estiloResposta: settingsBindings.ai.estiloResposta,
        idiomaResposta: settingsBindings.ai.idiomaResposta,
        integracoesExternas:
          settingsSupportState.presentationState.integracoesExternas,
        lockTimeout: settingsBindings.security.lockTimeout,
        microfonePermitido: settingsBindings.security.microfonePermitido,
        modeloIa: settingsBindings.ai.modeloIa,
        mostrarConteudoNotificacao:
          settingsBindings.notifications.mostrarConteudoNotificacao,
        mostrarSomenteNovaMensagem:
          settingsBindings.notifications.mostrarSomenteNovaMensagem,
        notificacoesPermitidas:
          settingsBindings.notifications.notificacoesPermitidas,
        ocultarConteudoBloqueado:
          settingsBindings.notifications.ocultarConteudoBloqueado,
        perfilExibicao: settingsBindings.account.perfilExibicao,
        perfilNome: settingsBindings.account.perfilNome,
        planoAtual: settingsSupportState.presentationState.planoAtual,
        provedoresConectados:
          settingsSupportState.presentationState.provedoresConectados,
        reautenticacaoStatus:
          settingsSupportState.presentationState.reautenticacaoStatus,
        recoveryCodesEnabled:
          settingsSupportState.presentationState.recoveryCodesEnabled,
        salvarHistoricoConversas:
          settingsBindings.dataControls.salvarHistoricoConversas,
        settingsDrawerPage:
          settingsSupportState.navigationState.settingsDrawerPage,
        settingsDrawerSection:
          settingsSupportState.navigationState.settingsDrawerSection,
        sessoesAtivas: settingsSupportState.presentationState.sessoesAtivas,
        somNotificacao: settingsBindings.notifications.somNotificacao,
        sincronizacaoDispositivos:
          settingsBindings.dataControls.sincronizacaoDispositivos,
        tamanhoFonte: settingsBindings.appearance.tamanhoFonte,
        temaApp: settingsBindings.appearance.temaApp,
        twoFactorEnabled:
          settingsSupportState.presentationState.twoFactorEnabled,
        twoFactorMethod: settingsSupportState.presentationState.twoFactorMethod,
        uploadArquivosAtivo: settingsBindings.attachments.uploadArquivosAtivo,
      },
      helperState: {
        buildHistorySections,
        formatarHorarioAtividade,
        formatarTipoTemplateLaudo,
        obterEscalaDensidade,
        obterEscalaFonte,
        podeEditarConversaNoComposer,
        previewChatLiberadoParaConversa,
      },
    }),
  );

  return {
    conversaAtiva: inspectorBaseDerivedState.conversaAtiva,
    inspectorBaseDerivedState,
    mesaDisponivel: inspectorBaseDerivedState.mesaDisponivel,
    mesaTemMensagens: inspectorBaseDerivedState.mesaTemMensagens,
    resumoFilaOffline: inspectorBaseDerivedState.resumoFilaOffline,
    sessaoAtual: inspectorBaseDerivedState.sessaoAtual,
    tipoTemplateAtivoLabel: inspectorBaseDerivedState.tipoTemplateAtivoLabel,
    ultimoTicketSuporte: inspectorBaseDerivedState.ultimoTicketSuporte,
    vendoFinalizacao: inspectorBaseDerivedState.vendoFinalizacao,
    vendoMesa: inspectorBaseDerivedState.vendoMesa,
  };
}
