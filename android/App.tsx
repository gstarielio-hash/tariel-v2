import { StatusBar } from "expo-status-bar";

import { InspectorMobileApp } from "./src/features/InspectorMobileApp";
import { SettingsStoreProvider } from "./src/settings";

export default function App() {
  return (
    <SettingsStoreProvider>
      <StatusBar hidden style="light" translucent />
      <InspectorMobileApp />
    </SettingsStoreProvider>
  );
}
