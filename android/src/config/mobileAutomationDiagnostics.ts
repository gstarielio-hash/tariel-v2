const DISABLED_AUTOMATION_VALUES = new Set(["0", "false", "no", "off"]);

export function isMobileAutomationDiagnosticsEnabled(): boolean {
  const rawValue = String(
    process.env.EXPO_PUBLIC_MOBILE_AUTOMATION_DIAGNOSTICS || "",
  )
    .trim()
    .toLowerCase();

  return !DISABLED_AUTOMATION_VALUES.has(rawValue);
}
