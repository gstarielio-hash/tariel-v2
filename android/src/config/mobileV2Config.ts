export const ANDROID_V2_READ_CONTRACTS_FLAG =
  "EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED";

export interface AndroidV2ReadContractsRuntimeSnapshot {
  envKey: typeof ANDROID_V2_READ_CONTRACTS_FLAG;
  rawValue: string | null;
  normalizedValue: string;
  enabled: boolean;
  parser: "truthy_string_v1";
  source: "expo_public_env";
}

function normalizarFlagBoolean(rawValue: string | undefined): boolean {
  const value = String(rawValue || "")
    .trim()
    .toLowerCase();
  return value === "1" || value === "true" || value === "on" || value === "yes";
}

function readAndroidV2ReadContractsRawValue(): string | undefined {
  const directRuntimeValue =
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED;
  if (typeof directRuntimeValue === "string") {
    return directRuntimeValue;
  }
  return process.env[ANDROID_V2_READ_CONTRACTS_FLAG];
}

export function getAndroidV2ReadContractsRuntimeSnapshot(): AndroidV2ReadContractsRuntimeSnapshot {
  const runtimeValue = readAndroidV2ReadContractsRawValue();
  const normalizedValue = String(runtimeValue || "")
    .trim()
    .toLowerCase();

  return {
    envKey: ANDROID_V2_READ_CONTRACTS_FLAG,
    rawValue:
      runtimeValue === undefined || runtimeValue === null
        ? null
        : String(runtimeValue).trim() || null,
    normalizedValue,
    enabled: normalizarFlagBoolean(runtimeValue),
    parser: "truthy_string_v1",
    source: "expo_public_env",
  };
}

export function androidV2ReadContractsEnabled(): boolean {
  return getAndroidV2ReadContractsRuntimeSnapshot().enabled;
}
