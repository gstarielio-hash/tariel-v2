import { buildInspectorBaseDerivedStateInput } from "./buildInspectorBaseDerivedStateInput";
import type {
  BuildInspectorBaseDerivedStateInputParams,
  InspectorBaseDerivedStateInput,
} from "./inspectorDerivedStateTypes";

interface BuildInspectorRootBaseDerivedStateInputParams {
  chatState: BuildInspectorBaseDerivedStateInputParams["chat"];
  helperState: BuildInspectorBaseDerivedStateInputParams["helpers"];
  historyAndOfflineState: BuildInspectorBaseDerivedStateInputParams["historyAndOffline"];
  settingsState: BuildInspectorBaseDerivedStateInputParams["settingsAndAccount"];
  shellState: BuildInspectorBaseDerivedStateInputParams["shell"];
}

export function buildInspectorRootBaseDerivedStateInput({
  chatState,
  helperState,
  historyAndOfflineState,
  settingsState,
  shellState,
}: BuildInspectorRootBaseDerivedStateInputParams): InspectorBaseDerivedStateInput {
  return buildInspectorBaseDerivedStateInput({
    shell: shellState,
    chat: chatState,
    historyAndOffline: historyAndOfflineState,
    settingsAndAccount: settingsState,
    helpers: helperState,
  });
}
