import {
  AI_MODEL_OPTIONS,
  CONVERSATION_TONE_OPTIONS,
  RESPONSE_LANGUAGE_OPTIONS,
  RESPONSE_STYLE_OPTIONS,
  TEMPERATURE_STEPS,
} from "../InspectorMobileApp.constants";
import type { SettingsEntryModePreference } from "../../settings/schema/types";
import {
  SettingsPressRow,
  SettingsScaleRow,
  SettingsSection,
  SettingsSegmentedRow,
  SettingsSwitchRow,
} from "./SettingsPrimitives";

type ModeloIa = (typeof AI_MODEL_OPTIONS)[number];
type EstiloResposta = (typeof RESPONSE_STYLE_OPTIONS)[number];
type IdiomaResposta = (typeof RESPONSE_LANGUAGE_OPTIONS)[number];
type TomConversa = (typeof CONVERSATION_TONE_OPTIONS)[number];
const ENTRY_MODE_PREFERENCE_OPTIONS = [
  "chat_first",
  "evidence_first",
  "auto_recommended",
] as const satisfies readonly SettingsEntryModePreference[];

function formatEntryModePreference(
  value: SettingsEntryModePreference | undefined,
): string {
  switch (value) {
    case "chat_first":
      return "Chat primeiro";
    case "evidence_first":
      return "Coleta guiada primeiro";
    default:
      return "Auto recomendado";
  }
}

function describeEntryModePreference(
  value: SettingsEntryModePreference,
): string {
  switch (value) {
    case "chat_first":
      return "O caso novo abre em chat livre. O primeiro texto, foto ou documento enviado cria o laudo.";
    case "evidence_first":
      return "O caso novo prioriza a coleta guiada. A primeira evidência ou mensagem enviada cria o laudo.";
    default:
      return "O app decide entre chat livre e coleta guiada sem abrir caso vazio antes do primeiro envio real.";
  }
}

function formatCaseCreationValue(
  value: SettingsEntryModePreference,
  rememberLastCaseMode: boolean,
): string {
  switch (value) {
    case "chat_first":
      return "Chat no 1º envio";
    case "evidence_first":
      return "Guiado no 1º envio";
    default:
      return rememberLastCaseMode ? "Auto + último modo" : "Auto recomendado";
  }
}

function describeCaseCreation(
  value: SettingsEntryModePreference,
  rememberLastCaseMode: boolean,
): string {
  if (value === "chat_first") {
    return "Nenhum chat vazio vira caso por si só. O laudo só nasce quando o primeiro envio real entra na thread.";
  }

  if (value === "evidence_first") {
    return "A coleta guiada prepara o caso, mas a criação continua lazy: o backend só abre o laudo na primeira evidência ou mensagem enviada.";
  }

  return rememberLastCaseMode
    ? "No automático, o app reaproveita o último modo efetivo do inspetor quando isso fizer sentido. Mesmo assim, o caso só nasce no primeiro envio real."
    : "No automático, o produto escolhe o melhor modo de entrada para o caso novo. Em todos os cenários, o laudo só nasce no primeiro envio real.";
}

function describeRememberLastCaseMode(value: boolean): string {
  return value
    ? "Quando o modo estiver em automático, o próximo caso novo tenta repetir o modo efetivo do caso anterior."
    : "Quando o modo estiver em automático, o próximo caso novo volta para a recomendação padrão do produto.";
}

interface SettingsExperienceAiSectionProps {
  modeloIa: ModeloIa;
  estiloResposta: EstiloResposta;
  idiomaResposta: IdiomaResposta;
  memoriaIa: boolean;
  aprendizadoIa: boolean;
  entryModePreference?: SettingsEntryModePreference;
  rememberLastCaseMode?: boolean;
  tomConversa: TomConversa;
  temperaturaIa: number;
  onAbrirMenuModeloIa: () => void;
  onSetEstiloResposta: (value: EstiloResposta) => void;
  onSetIdiomaResposta: (value: IdiomaResposta) => void;
  onSetMemoriaIa: (value: boolean) => void;
  onSetAprendizadoIa: (value: boolean) => void;
  onSetEntryModePreference: (value: SettingsEntryModePreference) => void;
  onSetRememberLastCaseMode: (value: boolean) => void;
  onSetTomConversa: (value: TomConversa) => void;
  onSetTemperaturaIa: (value: number) => void;
}

function nextOptionValue<T extends string>(
  current: T,
  options: readonly T[],
): T {
  const currentIndex = options.indexOf(current);
  if (currentIndex === -1) {
    return options[0];
  }
  return options[(currentIndex + 1) % options.length];
}

export function SettingsExperienceAiSection({
  modeloIa,
  estiloResposta,
  idiomaResposta,
  memoriaIa,
  aprendizadoIa,
  entryModePreference,
  rememberLastCaseMode,
  tomConversa,
  temperaturaIa,
  onAbrirMenuModeloIa,
  onSetEstiloResposta,
  onSetIdiomaResposta,
  onSetMemoriaIa,
  onSetAprendizadoIa,
  onSetEntryModePreference,
  onSetRememberLastCaseMode,
  onSetTomConversa,
  onSetTemperaturaIa,
}: SettingsExperienceAiSectionProps) {
  const entryModeValue = entryModePreference || "chat_first";
  const rememberLastModeValue = Boolean(rememberLastCaseMode);
  return (
    <SettingsSection
      icon="robot-outline"
      subtitle="Ajuste o comportamento da inteligência artificial nas conversas."
      title="Preferências da IA"
    >
      <SettingsPressRow
        icon="brain"
        onPress={onAbrirMenuModeloIa}
        testID="settings-ai-model-row"
        title="Modelo de IA"
        value={modeloIa}
      />
      <SettingsPressRow
        icon="message-text-outline"
        onPress={() =>
          onSetEstiloResposta(
            nextOptionValue(estiloResposta, RESPONSE_STYLE_OPTIONS),
          )
        }
        title="Estilo de resposta"
        value={estiloResposta}
      />
      <SettingsPressRow
        icon="translate"
        onPress={() =>
          onSetIdiomaResposta(
            nextOptionValue(idiomaResposta, RESPONSE_LANGUAGE_OPTIONS),
          )
        }
        title="Idioma da resposta"
        value={idiomaResposta}
      />
      <SettingsSwitchRow
        description="Permite lembrar preferências entre conversas."
        icon="memory"
        onValueChange={onSetMemoriaIa}
        title="Memória da IA"
        value={memoriaIa}
      />
      <SettingsPressRow
        description={describeEntryModePreference(entryModeValue)}
        icon="transit-connection-variant"
        onPress={() =>
          onSetEntryModePreference(
            nextOptionValue(entryModeValue, ENTRY_MODE_PREFERENCE_OPTIONS),
          )
        }
        testID="settings-ai-entry-mode-row"
        title="Modo inicial do caso"
        value={formatEntryModePreference(entryModeValue)}
      />
      <SettingsPressRow
        description={describeCaseCreation(
          entryModeValue,
          rememberLastModeValue,
        )}
        icon="flash-outline"
        title="Criação do caso"
        value={formatCaseCreationValue(entryModeValue, rememberLastModeValue)}
      />
      <SettingsSwitchRow
        description={describeRememberLastCaseMode(rememberLastModeValue)}
        icon="history"
        onValueChange={onSetRememberLastCaseMode}
        testID="settings-ai-remember-last-mode-row"
        title="Lembrar modo do último caso"
        value={rememberLastModeValue}
      />
      <SettingsSwitchRow
        description="Consentimento para melhoria contínua do modelo."
        icon="school-outline"
        onValueChange={onSetAprendizadoIa}
        title="Permitir aprendizado da IA"
        value={aprendizadoIa}
      />
      <SettingsSegmentedRow
        description="Tom principal do assistente durante a conversa."
        icon="account-voice"
        onChange={onSetTomConversa}
        options={CONVERSATION_TONE_OPTIONS}
        title="Tom da conversa"
        value={tomConversa}
      />
      <SettingsScaleRow
        description="Mais baixo para precisão, mais alto para criatividade."
        icon="tune-variant"
        maxLabel="Criativa"
        minLabel="Precisa"
        onChange={onSetTemperaturaIa}
        title="Temperatura da resposta"
        value={temperaturaIa}
        values={TEMPERATURE_STEPS}
      />
    </SettingsSection>
  );
}
