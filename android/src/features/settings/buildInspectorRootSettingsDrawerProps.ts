import type { InspectorBaseDerivedState } from "../common/buildInspectorBaseDerivedState";
import { buildInspectorSettingsDrawerInput } from "./buildInspectorSettingsDrawerInput";
import { buildInspectorSettingsDrawerPanelProps } from "./buildInspectorSettingsDrawerPanelProps";
import type { InspectorSettingsDrawerPanelBuilderInput } from "./settingsDrawerBuilderTypes";

type InspectorSettingsDrawerBaseState = Pick<
  InspectorBaseDerivedState,
  | "artigosAjudaFiltrados"
  | "contaEmailLabel"
  | "contaTelefoneLabel"
  | "conversasOcultasTotal"
  | "conversasVisiveisTotal"
  | "corDestaqueResumoConfiguracao"
  | "detalheGovernancaConfiguracao"
  | "eventosSegurancaFiltrados"
  | "existeProvedorDisponivel"
  | "iniciaisPerfilConfiguracao"
  | "integracoesConectadasTotal"
  | "integracoesDisponiveisTotal"
  | "mostrarGrupoContaAcesso"
  | "mostrarGrupoExperiencia"
  | "mostrarGrupoSeguranca"
  | "mostrarGrupoSistema"
  | "nomeUsuarioExibicao"
  | "outrasSessoesAtivas"
  | "perfilExibicaoLabel"
  | "perfilNomeCompleto"
  | "permissoesNegadasTotal"
  | "planoResumoConfiguracao"
  | "previewPrivacidadeNotificacao"
  | "provedoresConectadosTotal"
  | "provedorPrimario"
  | "reemissoesRecomendadasTotal"
  | "resumo2FAFootnote"
  | "resumo2FAStatus"
  | "resumoAlertaMetodosConta"
  | "resumoBlindagemSessoes"
  | "resumoCodigosRecuperacao"
  | "resumoContaAcesso"
  | "resumoDadosConversas"
  | "resumoExcluirConta"
  | "resumoFilaOffline"
  | "resumoFilaSuporteLocal"
  | "resumoGovernancaConfiguracao"
  | "resumoMetodosConta"
  | "resumoPermissoes"
  | "resumoPermissoesCriticas"
  | "resumoPrivacidadeNotificacoes"
  | "resumoSessaoAtual"
  | "resumoSuporteApp"
  | "settingsDrawerInOverview"
  | "settingsDrawerMatchesPage"
  | "settingsDrawerMatchesSection"
  | "settingsDrawerPageSections"
  | "settingsDrawerSectionMenuAtiva"
  | "settingsDrawerSubtitle"
  | "settingsDrawerTitle"
  | "settingsPrintDarkMode"
  | "sessoesSuspeitasTotal"
  | "temaResumoConfiguracao"
  | "temPrioridadesConfiguracao"
  | "ticketsBugTotal"
  | "ticketsFeedbackTotal"
  | "totalSecoesConfiguracaoVisiveis"
  | "ultimaVerificacaoAtualizacaoLabel"
  | "ultimoEventoProvedor"
  | "ultimoEventoSessao"
  | "ultimoTicketSuporteResumo"
  | "workspaceResumoConfiguracao"
>;

interface BuildInspectorRootSettingsDrawerPropsInput {
  accountState: Pick<
    InspectorSettingsDrawerPanelBuilderInput,
    | "email"
    | "emailAtualConta"
    | "handleAlterarEmail"
    | "handleAlterarSenha"
    | "handleEditarPerfil"
    | "handleSolicitarLogout"
    | "handleUploadFotoPerfil"
    | "perfilFotoHint"
    | "perfilFotoUri"
  >;
  baseState: InspectorSettingsDrawerBaseState;
  experienceState: Pick<
    InspectorSettingsDrawerPanelBuilderInput,
    | "aprendizadoIa"
    | "animacoesAtivas"
    | "chatCategoryEnabled"
    | "corDestaque"
    | "criticalAlertsEnabled"
    | "densidadeInterface"
    | "entryModePreference"
    | "emailsAtivos"
    | "entradaPorVoz"
    | "estiloResposta"
    | "handleAbrirAjudaDitado"
    | "handleAbrirModeloIa"
    | "handleToggleEntradaPorVoz"
    | "handleToggleNotificaPush"
    | "handleToggleRespostaPorVoz"
    | "handleToggleSpeechEnabled"
    | "handleToggleVibracao"
    | "idiomaResposta"
    | "mediaCompression"
    | "memoriaIa"
    | "mesaCategoryEnabled"
    | "mostrarCategoriaMesa"
    | "microfonePermitido"
    | "modeloIa"
    | "nomeAutomaticoConversas"
    | "notificaPush"
    | "notificaRespostas"
    | "notificacoesPermitidas"
    | "onAbrirPermissaoNotificacoes"
    | "onCyclePreferredVoice"
    | "preferredVoiceLabel"
    | "rememberLastCaseMode"
    | "respostaPorVoz"
    | "setAnimacoesAtivas"
    | "setAprendizadoIa"
    | "setChatCategoryEnabled"
    | "setCorDestaque"
    | "setCriticalAlertsEnabled"
    | "setDensidadeInterface"
    | "setEntryModePreference"
    | "setEmailsAtivos"
    | "setEstiloResposta"
    | "setIdiomaResposta"
    | "setMemoriaIa"
    | "setMesaCategoryEnabled"
    | "setNotificaRespostas"
    | "setRememberLastCaseMode"
    | "setSomNotificacao"
    | "setSpeechRate"
    | "setSystemCategoryEnabled"
    | "setTamanhoFonte"
    | "setTemperaturaIa"
    | "setTemaApp"
    | "setTomConversa"
    | "setVoiceLanguage"
    | "somNotificacao"
    | "speechEnabled"
    | "speechRate"
    | "sttSupported"
    | "systemCategoryEnabled"
    | "tamanhoFonte"
    | "temperaturaIa"
    | "temaApp"
    | "tomConversa"
    | "ttsSupported"
    | "vibracaoAtiva"
    | "voiceLanguage"
  >;
  navigationState: Pick<
    InspectorSettingsDrawerPanelBuilderInput,
    | "appBuildChannel"
    | "appVersionLabel"
    | "configuracoesDrawerX"
    | "fecharConfiguracoes"
    | "handleAbrirPaginaConfiguracoes"
    | "handleAbrirSecaoConfiguracoes"
    | "handleVoltarResumoConfiguracoes"
    | "onAbrirFilaOffline"
    | "settingsDrawerPage"
    | "settingsDrawerPanResponder"
  >;
  securityState: Pick<
    InspectorSettingsDrawerPanelBuilderInput,
    | "analyticsOptIn"
    | "arquivosPermitidos"
    | "autoUploadAttachments"
    | "backupAutomatico"
    | "biometriaPermitida"
    | "cameraPermitida"
    | "codigo2FA"
    | "codigosRecuperacao"
    | "compartilharMelhoriaIa"
    | "crashReportsOptIn"
    | "deviceBiometricsEnabled"
    | "filtroEventosSeguranca"
    | "fixarConversas"
    | "handleApagarHistoricoConfiguracoes"
    | "handleCompartilharCodigosRecuperacao"
    | "handleConfirmarCodigo2FA"
    | "handleDetalhesSegurancaArquivos"
    | "handleEncerrarOutrasSessoes"
    | "handleEncerrarSessao"
    | "handleEncerrarSessaoAtual"
    | "handleEncerrarSessoesSuspeitas"
    | "handleExcluirConta"
    | "handleExportarAntesDeExcluirConta"
    | "handleExportarDados"
    | "handleGerarCodigosRecuperacao"
    | "handleGerenciarConversasIndividuais"
    | "handleLogout"
    | "handleGerenciarPermissao"
    | "handleLimparCache"
    | "handleLimparTodasConversasConfig"
    | "handleMudarMetodo2FA"
    | "handleReautenticacaoSensivel"
    | "handleReportarAtividadeSuspeita"
    | "handleRevisarPermissoesCriticas"
    | "handleRevisarSessao"
    | "handleToggle2FA"
    | "handleToggleBackupAutomatico"
    | "handleToggleBiometriaNoDispositivo"
    | "handleToggleMostrarConteudoNotificacao"
    | "handleToggleMostrarSomenteNovaMensagem"
    | "handleToggleOcultarConteudoBloqueado"
    | "handleToggleProviderConnection"
    | "handleToggleSincronizacaoDispositivos"
    | "hideInMultitask"
    | "limpandoCache"
    | "lockTimeout"
    | "mediaCompression"
    | "mostrarConteudoNotificacao"
    | "mostrarSomenteNovaMensagem"
    | "nomeAutomaticoConversas"
    | "ocultarConteudoBloqueado"
    | "provedoresConectados"
    | "reautenticacaoStatus"
    | "recoveryCodesEnabled"
    | "requireAuthOnOpen"
    | "resumoCache"
    | "retencaoDados"
    | "salvarHistoricoConversas"
    | "setAnalyticsOptIn"
    | "setAutoUploadAttachments"
    | "setCodigo2FA"
    | "setCompartilharMelhoriaIa"
    | "setCrashReportsOptIn"
    | "setFiltroEventosSeguranca"
    | "setFixarConversas"
    | "setHideInMultitask"
    | "setLockTimeout"
    | "setMediaCompression"
    | "setNomeAutomaticoConversas"
    | "setRecoveryCodesEnabled"
    | "setRequireAuthOnOpen"
    | "setRetencaoDados"
    | "setSalvarHistoricoConversas"
    | "setWifiOnlySync"
    | "sessoesAtivas"
    | "sincronizacaoDispositivos"
    | "twoFactorEnabled"
    | "twoFactorMethod"
    | "wifiOnlySync"
  >;
  supportAndSystemState: Pick<
    InspectorSettingsDrawerPanelBuilderInput,
    | "economiaDados"
    | "filaSuporteLocal"
    | "handleAbrirAjustesDoSistema"
    | "handleAbrirCanalSuporte"
    | "handleAbrirCentralAtividade"
    | "handleAbrirSobreApp"
    | "handleCentralAjuda"
    | "handleEnviarFeedback"
    | "handleExportarDiagnosticoApp"
    | "handleLicencas"
    | "handleLimparCache"
    | "handleLimparFilaSuporteLocal"
    | "handlePermissoes"
    | "handlePoliticaPrivacidade"
    | "handleRefresh"
    | "handleReportarProblema"
    | "handleTermosUso"
    | "handleVerificarAtualizacoes"
    | "idiomaApp"
    | "regiaoApp"
    | "resumoCache"
    | "resumoCentralAtividade"
    | "setEconomiaDados"
    | "setIdiomaApp"
    | "setRegiaoApp"
    | "setUsoBateria"
    | "sincronizandoDados"
    | "supportChannelLabel"
    | "usoBateria"
    | "verificandoAtualizacoes"
  >;
}

export function buildInspectorRootSettingsDrawerProps({
  accountState,
  baseState,
  experienceState,
  navigationState,
  securityState,
  supportAndSystemState,
}: BuildInspectorRootSettingsDrawerPropsInput): ReturnType<
  typeof buildInspectorSettingsDrawerPanelProps
> {
  return buildInspectorSettingsDrawerPanelProps(
    buildInspectorSettingsDrawerInput({
      account: {
        contaEmailLabel: baseState.contaEmailLabel,
        contaTelefoneLabel: baseState.contaTelefoneLabel,
        email: accountState.email,
        emailAtualConta: accountState.emailAtualConta,
        handleAlterarEmail: accountState.handleAlterarEmail,
        handleAlterarSenha: accountState.handleAlterarSenha,
        handleEditarPerfil: accountState.handleEditarPerfil,
        handleSolicitarLogout: accountState.handleSolicitarLogout,
        handleUploadFotoPerfil: accountState.handleUploadFotoPerfil,
        iniciaisPerfilConfiguracao: baseState.iniciaisPerfilConfiguracao,
        nomeUsuarioExibicao: baseState.nomeUsuarioExibicao,
        perfilExibicaoLabel: baseState.perfilExibicaoLabel,
        perfilFotoHint: accountState.perfilFotoHint,
        perfilFotoUri: accountState.perfilFotoUri,
        perfilNomeCompleto: baseState.perfilNomeCompleto,
        planoResumoConfiguracao: baseState.planoResumoConfiguracao,
        provedorPrimario: baseState.provedorPrimario,
        reemissoesRecomendadasTotal: baseState.reemissoesRecomendadasTotal,
        resumoContaAcesso: baseState.resumoContaAcesso,
        resumoGovernancaConfiguracao: baseState.resumoGovernancaConfiguracao,
        resumoMetodosConta: baseState.resumoMetodosConta,
        workspaceResumoConfiguracao: baseState.workspaceResumoConfiguracao,
        detalheGovernancaConfiguracao: baseState.detalheGovernancaConfiguracao,
      },
      experience: {
        aprendizadoIa: experienceState.aprendizadoIa,
        animacoesAtivas: experienceState.animacoesAtivas,
        artigosAjudaFiltrados: baseState.artigosAjudaFiltrados,
        chatCategoryEnabled: experienceState.chatCategoryEnabled,
        corDestaque: experienceState.corDestaque,
        criticalAlertsEnabled: experienceState.criticalAlertsEnabled,
        densidadeInterface: experienceState.densidadeInterface,
        entryModePreference: experienceState.entryModePreference,
        emailsAtivos: experienceState.emailsAtivos,
        entradaPorVoz: experienceState.entradaPorVoz,
        estiloResposta: experienceState.estiloResposta,
        handleAbrirAjudaDitado: experienceState.handleAbrirAjudaDitado,
        handleAbrirModeloIa: experienceState.handleAbrirModeloIa,
        handleToggleEntradaPorVoz: experienceState.handleToggleEntradaPorVoz,
        handleToggleNotificaPush: experienceState.handleToggleNotificaPush,
        handleToggleRespostaPorVoz: experienceState.handleToggleRespostaPorVoz,
        handleToggleSpeechEnabled: experienceState.handleToggleSpeechEnabled,
        handleToggleVibracao: experienceState.handleToggleVibracao,
        idiomaResposta: experienceState.idiomaResposta,
        mediaCompression: experienceState.mediaCompression,
        memoriaIa: experienceState.memoriaIa,
        mesaCategoryEnabled: experienceState.mesaCategoryEnabled,
        mostrarCategoriaMesa: experienceState.mostrarCategoriaMesa,
        microfonePermitido: experienceState.microfonePermitido,
        modeloIa: experienceState.modeloIa,
        nomeAutomaticoConversas: experienceState.nomeAutomaticoConversas,
        notificaPush: experienceState.notificaPush,
        notificaRespostas: experienceState.notificaRespostas,
        notificacoesPermitidas: experienceState.notificacoesPermitidas,
        onAbrirPermissaoNotificacoes:
          experienceState.onAbrirPermissaoNotificacoes,
        onCyclePreferredVoice: experienceState.onCyclePreferredVoice,
        preferredVoiceLabel: experienceState.preferredVoiceLabel,
        rememberLastCaseMode: experienceState.rememberLastCaseMode,
        respostaPorVoz: experienceState.respostaPorVoz,
        setAnimacoesAtivas: experienceState.setAnimacoesAtivas,
        setAprendizadoIa: experienceState.setAprendizadoIa,
        setChatCategoryEnabled: experienceState.setChatCategoryEnabled,
        setCorDestaque: experienceState.setCorDestaque,
        setCriticalAlertsEnabled: experienceState.setCriticalAlertsEnabled,
        setDensidadeInterface: experienceState.setDensidadeInterface,
        setEntryModePreference: experienceState.setEntryModePreference,
        setEmailsAtivos: experienceState.setEmailsAtivos,
        setEstiloResposta: experienceState.setEstiloResposta,
        setIdiomaResposta: experienceState.setIdiomaResposta,
        setMemoriaIa: experienceState.setMemoriaIa,
        setMesaCategoryEnabled: experienceState.setMesaCategoryEnabled,
        setNotificaRespostas: experienceState.setNotificaRespostas,
        setRememberLastCaseMode: experienceState.setRememberLastCaseMode,
        setSomNotificacao: experienceState.setSomNotificacao,
        setSpeechRate: experienceState.setSpeechRate,
        setSystemCategoryEnabled: experienceState.setSystemCategoryEnabled,
        setTamanhoFonte: experienceState.setTamanhoFonte,
        setTemperaturaIa: experienceState.setTemperaturaIa,
        setTemaApp: experienceState.setTemaApp,
        setTomConversa: experienceState.setTomConversa,
        setVoiceLanguage: experienceState.setVoiceLanguage,
        somNotificacao: experienceState.somNotificacao,
        speechEnabled: experienceState.speechEnabled,
        speechRate: experienceState.speechRate,
        sttSupported: experienceState.sttSupported,
        systemCategoryEnabled: experienceState.systemCategoryEnabled,
        tamanhoFonte: experienceState.tamanhoFonte,
        temperaturaIa: experienceState.temperaturaIa,
        temaApp: experienceState.temaApp,
        tomConversa: experienceState.tomConversa,
        ttsSupported: experienceState.ttsSupported,
        vibracaoAtiva: experienceState.vibracaoAtiva,
        voiceLanguage: experienceState.voiceLanguage,
      },
      navigation: {
        appBuildChannel: navigationState.appBuildChannel,
        appVersionLabel: navigationState.appVersionLabel,
        configuracoesDrawerX: navigationState.configuracoesDrawerX,
        fecharConfiguracoes: navigationState.fecharConfiguracoes,
        handleAbrirPaginaConfiguracoes:
          navigationState.handleAbrirPaginaConfiguracoes,
        handleAbrirSecaoConfiguracoes:
          navigationState.handleAbrirSecaoConfiguracoes,
        handleVoltarResumoConfiguracoes:
          navigationState.handleVoltarResumoConfiguracoes,
        mostrarGrupoContaAcesso: baseState.mostrarGrupoContaAcesso,
        mostrarGrupoExperiencia: baseState.mostrarGrupoExperiencia,
        mostrarGrupoSeguranca: baseState.mostrarGrupoSeguranca,
        mostrarGrupoSistema: baseState.mostrarGrupoSistema,
        onAbrirFilaOffline: navigationState.onAbrirFilaOffline,
        settingsDrawerInOverview: baseState.settingsDrawerInOverview,
        settingsDrawerMatchesPage: baseState.settingsDrawerMatchesPage,
        settingsDrawerMatchesSection: baseState.settingsDrawerMatchesSection,
        settingsDrawerPage: navigationState.settingsDrawerPage,
        settingsDrawerPageSections: baseState.settingsDrawerPageSections,
        settingsDrawerPanResponder: navigationState.settingsDrawerPanResponder,
        settingsDrawerSectionMenuAtiva:
          baseState.settingsDrawerSectionMenuAtiva,
        settingsDrawerSubtitle: baseState.settingsDrawerSubtitle,
        settingsDrawerTitle: baseState.settingsDrawerTitle,
        settingsPrintDarkMode: baseState.settingsPrintDarkMode,
        temaResumoConfiguracao: baseState.temaResumoConfiguracao,
        temPrioridadesConfiguracao: baseState.temPrioridadesConfiguracao,
        totalSecoesConfiguracaoVisiveis:
          baseState.totalSecoesConfiguracaoVisiveis,
      },
      security: {
        analyticsOptIn: securityState.analyticsOptIn,
        arquivosPermitidos: securityState.arquivosPermitidos,
        autoUploadAttachments: securityState.autoUploadAttachments,
        backupAutomatico: securityState.backupAutomatico,
        biometriaPermitida: securityState.biometriaPermitida,
        cameraPermitida: securityState.cameraPermitida,
        codigo2FA: securityState.codigo2FA,
        codigosRecuperacao: securityState.codigosRecuperacao,
        compartilharMelhoriaIa: securityState.compartilharMelhoriaIa,
        conversasOcultasTotal: baseState.conversasOcultasTotal,
        conversasVisiveisTotal: baseState.conversasVisiveisTotal,
        crashReportsOptIn: securityState.crashReportsOptIn,
        deviceBiometricsEnabled: securityState.deviceBiometricsEnabled,
        eventosSegurancaFiltrados: baseState.eventosSegurancaFiltrados,
        filtroEventosSeguranca: securityState.filtroEventosSeguranca,
        fixarConversas: securityState.fixarConversas,
        handleApagarHistoricoConfiguracoes:
          securityState.handleApagarHistoricoConfiguracoes,
        handleCompartilharCodigosRecuperacao:
          securityState.handleCompartilharCodigosRecuperacao,
        handleConfirmarCodigo2FA: securityState.handleConfirmarCodigo2FA,
        handleDetalhesSegurancaArquivos:
          securityState.handleDetalhesSegurancaArquivos,
        handleEncerrarOutrasSessoes: securityState.handleEncerrarOutrasSessoes,
        handleEncerrarSessao: securityState.handleEncerrarSessao,
        handleEncerrarSessaoAtual: securityState.handleEncerrarSessaoAtual,
        handleEncerrarSessoesSuspeitas:
          securityState.handleEncerrarSessoesSuspeitas,
        handleExcluirConta: securityState.handleExcluirConta,
        handleExportarAntesDeExcluirConta:
          securityState.handleExportarAntesDeExcluirConta,
        handleExportarDados: securityState.handleExportarDados,
        handleGerarCodigosRecuperacao:
          securityState.handleGerarCodigosRecuperacao,
        handleGerenciarConversasIndividuais:
          securityState.handleGerenciarConversasIndividuais,
        handleLogout: securityState.handleLogout,
        handleGerenciarPermissao: securityState.handleGerenciarPermissao,
        handleLimparCache: securityState.handleLimparCache,
        handleLimparTodasConversasConfig:
          securityState.handleLimparTodasConversasConfig,
        handleMudarMetodo2FA: securityState.handleMudarMetodo2FA,
        handleReautenticacaoSensivel:
          securityState.handleReautenticacaoSensivel,
        handleReportarAtividadeSuspeita:
          securityState.handleReportarAtividadeSuspeita,
        handleRevisarPermissoesCriticas:
          securityState.handleRevisarPermissoesCriticas,
        handleRevisarSessao: securityState.handleRevisarSessao,
        handleToggle2FA: securityState.handleToggle2FA,
        handleToggleBackupAutomatico:
          securityState.handleToggleBackupAutomatico,
        handleToggleBiometriaNoDispositivo:
          securityState.handleToggleBiometriaNoDispositivo,
        handleToggleMostrarConteudoNotificacao:
          securityState.handleToggleMostrarConteudoNotificacao,
        handleToggleMostrarSomenteNovaMensagem:
          securityState.handleToggleMostrarSomenteNovaMensagem,
        handleToggleOcultarConteudoBloqueado:
          securityState.handleToggleOcultarConteudoBloqueado,
        handleToggleProviderConnection:
          securityState.handleToggleProviderConnection,
        handleToggleSincronizacaoDispositivos:
          securityState.handleToggleSincronizacaoDispositivos,
        hideInMultitask: securityState.hideInMultitask,
        limpandoCache: securityState.limpandoCache,
        lockTimeout: securityState.lockTimeout,
        mediaCompression: securityState.mediaCompression,
        mostrarConteudoNotificacao: securityState.mostrarConteudoNotificacao,
        mostrarSomenteNovaMensagem: securityState.mostrarSomenteNovaMensagem,
        nomeAutomaticoConversas: securityState.nomeAutomaticoConversas,
        outrasSessoesAtivas: baseState.outrasSessoesAtivas,
        ocultarConteudoBloqueado: securityState.ocultarConteudoBloqueado,
        permissoesNegadasTotal: baseState.permissoesNegadasTotal,
        previewPrivacidadeNotificacao: baseState.previewPrivacidadeNotificacao,
        provedoresConectados: securityState.provedoresConectados,
        provedoresConectadosTotal: baseState.provedoresConectadosTotal,
        provedorPrimario: baseState.provedorPrimario,
        reautenticacaoStatus: securityState.reautenticacaoStatus,
        recoveryCodesEnabled: securityState.recoveryCodesEnabled,
        requireAuthOnOpen: securityState.requireAuthOnOpen,
        resumo2FAFootnote: baseState.resumo2FAFootnote,
        resumo2FAStatus: baseState.resumo2FAStatus,
        resumoAlertaMetodosConta: baseState.resumoAlertaMetodosConta,
        resumoBlindagemSessoes: baseState.resumoBlindagemSessoes,
        resumoCache: securityState.resumoCache,
        resumoCodigosRecuperacao: baseState.resumoCodigosRecuperacao,
        resumoDadosConversas: baseState.resumoDadosConversas,
        resumoExcluirConta: baseState.resumoExcluirConta,
        resumoPermissoes: baseState.resumoPermissoes,
        resumoPermissoesCriticas: baseState.resumoPermissoesCriticas,
        resumoPrivacidadeNotificacoes: baseState.resumoPrivacidadeNotificacoes,
        resumoSessaoAtual: baseState.resumoSessaoAtual,
        retencaoDados: securityState.retencaoDados,
        salvarHistoricoConversas: securityState.salvarHistoricoConversas,
        setAnalyticsOptIn: securityState.setAnalyticsOptIn,
        setAutoUploadAttachments: securityState.setAutoUploadAttachments,
        setCodigo2FA: securityState.setCodigo2FA,
        setCompartilharMelhoriaIa: securityState.setCompartilharMelhoriaIa,
        setCrashReportsOptIn: securityState.setCrashReportsOptIn,
        setFiltroEventosSeguranca: securityState.setFiltroEventosSeguranca,
        setFixarConversas: securityState.setFixarConversas,
        setHideInMultitask: securityState.setHideInMultitask,
        setLockTimeout: securityState.setLockTimeout,
        setMediaCompression: securityState.setMediaCompression,
        setNomeAutomaticoConversas: securityState.setNomeAutomaticoConversas,
        setRecoveryCodesEnabled: securityState.setRecoveryCodesEnabled,
        setRequireAuthOnOpen: securityState.setRequireAuthOnOpen,
        setRetencaoDados: securityState.setRetencaoDados,
        setSalvarHistoricoConversas: securityState.setSalvarHistoricoConversas,
        setWifiOnlySync: securityState.setWifiOnlySync,
        sessoesAtivas: securityState.sessoesAtivas,
        sessoesSuspeitasTotal: baseState.sessoesSuspeitasTotal,
        sincronizacaoDispositivos: securityState.sincronizacaoDispositivos,
        twoFactorEnabled: securityState.twoFactorEnabled,
        twoFactorMethod: securityState.twoFactorMethod,
        ultimoEventoProvedor: baseState.ultimoEventoProvedor,
        ultimoEventoSessao: baseState.ultimoEventoSessao,
        wifiOnlySync: securityState.wifiOnlySync,
      },
      supportAndSystem: {
        contaEmailLabel: baseState.contaEmailLabel,
        contaTelefoneLabel: baseState.contaTelefoneLabel,
        corDestaqueResumoConfiguracao: baseState.corDestaqueResumoConfiguracao,
        economiaDados: supportAndSystemState.economiaDados,
        existeProvedorDisponivel: baseState.existeProvedorDisponivel,
        fecharConfiguracoes: navigationState.fecharConfiguracoes,
        filaSuporteLocal: supportAndSystemState.filaSuporteLocal,
        handleAbrirAjustesDoSistema:
          supportAndSystemState.handleAbrirAjustesDoSistema,
        handleAbrirCanalSuporte: supportAndSystemState.handleAbrirCanalSuporte,
        handleAbrirCentralAtividade:
          supportAndSystemState.handleAbrirCentralAtividade,
        handleAbrirSobreApp: supportAndSystemState.handleAbrirSobreApp,
        handleCentralAjuda: supportAndSystemState.handleCentralAjuda,
        handleEnviarFeedback: supportAndSystemState.handleEnviarFeedback,
        handleExportarDiagnosticoApp:
          supportAndSystemState.handleExportarDiagnosticoApp,
        handleLicencas: supportAndSystemState.handleLicencas,
        handleLimparCache: supportAndSystemState.handleLimparCache,
        handleLimparFilaSuporteLocal:
          supportAndSystemState.handleLimparFilaSuporteLocal,
        handlePermissoes: supportAndSystemState.handlePermissoes,
        handlePoliticaPrivacidade:
          supportAndSystemState.handlePoliticaPrivacidade,
        handleRefresh: supportAndSystemState.handleRefresh,
        handleReportarProblema: supportAndSystemState.handleReportarProblema,
        handleTermosUso: supportAndSystemState.handleTermosUso,
        handleVerificarAtualizacoes:
          supportAndSystemState.handleVerificarAtualizacoes,
        idiomaApp: supportAndSystemState.idiomaApp,
        integracoesConectadasTotal: baseState.integracoesConectadasTotal,
        integracoesDisponiveisTotal: baseState.integracoesDisponiveisTotal,
        regiaoApp: supportAndSystemState.regiaoApp,
        resumoCache: supportAndSystemState.resumoCache,
        resumoCentralAtividade: supportAndSystemState.resumoCentralAtividade,
        resumoFilaOffline: baseState.resumoFilaOffline,
        resumoFilaSuporteLocal: baseState.resumoFilaSuporteLocal,
        resumoPermissoes: baseState.resumoPermissoes,
        resumoSuporteApp: baseState.resumoSuporteApp,
        setEconomiaDados: supportAndSystemState.setEconomiaDados,
        setIdiomaApp: supportAndSystemState.setIdiomaApp,
        setRegiaoApp: supportAndSystemState.setRegiaoApp,
        setUsoBateria: supportAndSystemState.setUsoBateria,
        sincronizandoDados: supportAndSystemState.sincronizandoDados,
        supportChannelLabel: supportAndSystemState.supportChannelLabel,
        ticketsBugTotal: baseState.ticketsBugTotal,
        ticketsFeedbackTotal: baseState.ticketsFeedbackTotal,
        ultimaVerificacaoAtualizacaoLabel:
          baseState.ultimaVerificacaoAtualizacaoLabel,
        ultimoTicketSuporteResumo: baseState.ultimoTicketSuporteResumo,
        usoBateria: supportAndSystemState.usoBateria,
        verificandoAtualizacoes: supportAndSystemState.verificandoAtualizacoes,
      },
    }),
  );
}
