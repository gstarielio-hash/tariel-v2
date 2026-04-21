import type { ComponentProps } from "react";

import { LoginScreen } from "./LoginScreen";

interface InspectorLoginShellProps {
  loginScreenProps: ComponentProps<typeof LoginScreen>;
}

export function InspectorLoginShell({
  loginScreenProps,
}: InspectorLoginShellProps) {
  return <LoginScreen {...loginScreenProps} />;
}
