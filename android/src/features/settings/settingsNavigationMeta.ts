import { MaterialCommunityIcons } from "@expo/vector-icons";

export type SettingsSectionKey =
  | "prioridades"
  | "conta"
  | "preferenciasIa"
  | "aparencia"
  | "notificacoes"
  | "contasConectadas"
  | "sessoes"
  | "twofa"
  | "protecaoDispositivo"
  | "verificacaoIdentidade"
  | "atividadeSeguranca"
  | "dadosConversas"
  | "permissoes"
  | "segurancaArquivos"
  | "privacidadeNotificacoes"
  | "excluirConta"
  | "recursosAvancados"
  | "sistema"
  | "suporte";

export type SettingsDrawerPage =
  | "overview"
  | "prioridades"
  | "contaAcesso"
  | "experiencia"
  | "seguranca"
  | "sistemaSuporte";

interface SettingsSectionMeta {
  title: string;
  subtitle: string;
  icon: keyof typeof MaterialCommunityIcons.glyphMap;
}

interface SettingsPageMeta {
  title: string;
  subtitle: string;
  icon: keyof typeof MaterialCommunityIcons.glyphMap;
  sections: SettingsSectionKey[];
}

export const SETTINGS_DRAWER_SECTION_META: Record<
  SettingsSectionKey,
  SettingsSectionMeta
> = {
  prioridades: {
    title: "Ações prioritárias",
    subtitle: "O que pede atenção primeiro.",
    icon: "flash-outline",
  },
  conta: {
    title: "Conta",
    subtitle: "Perfil, contato e senha.",
    icon: "account-circle-outline",
  },
  preferenciasIa: {
    title: "Preferências da IA",
    subtitle: "Modelo, idioma e estilo.",
    icon: "robot-outline",
  },
  aparencia: {
    title: "Aparência",
    subtitle: "Tema, densidade e destaque.",
    icon: "palette-outline",
  },
  notificacoes: {
    title: "Notificações",
    subtitle: "Alertas, push e vibração.",
    icon: "bell-outline",
  },
  contasConectadas: {
    title: "Contas conectadas",
    subtitle: "Identidades vinculadas ao acesso.",
    icon: "account-outline",
  },
  sessoes: {
    title: "Sessões e dispositivos",
    subtitle: "Dispositivos ativos e logout remoto.",
    icon: "devices",
  },
  twofa: {
    title: "Verificação em duas etapas",
    subtitle: "2FA e códigos de recuperação.",
    icon: "shield-key-outline",
  },
  protecaoDispositivo: {
    title: "Proteção no dispositivo",
    subtitle: "Biometria e bloqueio local.",
    icon: "cellphone-lock",
  },
  verificacaoIdentidade: {
    title: "Verificação de identidade",
    subtitle: "Reautenticação para ações sensíveis.",
    icon: "shield-account-outline",
  },
  atividadeSeguranca: {
    title: "Atividade de segurança",
    subtitle: "Eventos e logins recentes.",
    icon: "history",
  },
  dadosConversas: {
    title: "Controles de dados",
    subtitle: "Histórico, retenção e sincronização.",
    icon: "database-outline",
  },
  permissoes: {
    title: "Permissões",
    subtitle: "Câmera, arquivos, microfone e notificações.",
    icon: "shield-sync-outline",
  },
  segurancaArquivos: {
    title: "Segurança de arquivos enviados",
    subtitle: "Formatos, limites e proteção dos uploads.",
    icon: "file-lock-outline",
  },
  privacidadeNotificacoes: {
    title: "Privacidade em notificações",
    subtitle: "Controle das prévias.",
    icon: "bell-cog-outline",
  },
  excluirConta: {
    title: "Excluir conta",
    subtitle: "Remoção permanente da conta.",
    icon: "alert-outline",
  },
  recursosAvancados: {
    title: "Fala",
    subtitle: "Voz, transcrição e leitura.",
    icon: "microphone-message",
  },
  sistema: {
    title: "Sistema",
    subtitle: "Idioma, versão e manutenção.",
    icon: "cellphone-cog",
  },
  suporte: {
    title: "Suporte",
    subtitle: "Ajuda, feedback e diagnóstico.",
    icon: "lifebuoy",
  },
};

export const SETTINGS_DRAWER_PAGE_META: Record<
  Exclude<SettingsDrawerPage, "overview">,
  SettingsPageMeta
> = {
  prioridades: {
    title: "Ações prioritárias",
    subtitle: "O que pede atenção primeiro.",
    icon: "flash-outline",
    sections: ["prioridades"],
  },
  contaAcesso: {
    title: "Conta e acesso",
    subtitle: "Perfil, contato e senha.",
    icon: "account-circle-outline",
    sections: ["conta"],
  },
  experiencia: {
    title: "Experiência do app",
    subtitle: "IA, aparência e notificações.",
    icon: "palette-outline",
    sections: ["preferenciasIa", "aparencia", "notificacoes"],
  },
  seguranca: {
    title: "Segurança e privacidade",
    subtitle: "Permissões, dados locais e proteção.",
    icon: "shield-lock-outline",
    sections: [
      "protecaoDispositivo",
      "permissoes",
      "privacidadeNotificacoes",
      "dadosConversas",
      "segurancaArquivos",
    ],
  },
  sistemaSuporte: {
    title: "Sistema e suporte",
    subtitle: "Fala, manutenção e ajuda.",
    icon: "cellphone-cog",
    sections: ["sistema", "recursosAvancados", "suporte"],
  },
};
