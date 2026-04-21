const { existsSync, readFileSync, writeFileSync } = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");
const {
  limparBuildsAndroidNoNodeModules,
  limparBuildsProjetoAndroid,
} = require("./cleanup-android-build-artifacts.cjs");
const { fixAndroidLauncherIcon } = require("./fix-android-launcher-icon.cjs");
const { fixLinuxNodeExecutables } = require("./fix-linux-node-executables.cjs");

function binJavaExists(javaHome) {
  if (!javaHome) {
    return false;
  }

  const javaBinary = process.platform === "win32" ? "java.exe" : "java";
  return existsSync(path.join(javaHome, "bin", javaBinary));
}

function findJavaHome() {
  const home = process.env.HOME || process.env.USERPROFILE || "";
  const candidates = [
    process.env.JAVA_HOME,
    process.env.ANDROID_STUDIO_JBR,
    "C:\\Program Files\\Android\\Android Studio\\jbr",
    path.join(
      process.env.LOCALAPPDATA || "",
      "Programs",
      "Android Studio",
      "jbr",
    ),
    home && path.join(home, "android-studio", "jbr"),
    "/opt/android-studio/jbr",
    "/usr/lib/jvm/default-java",
    "/usr/lib/jvm/java-17-openjdk-amd64",
    "/usr/lib/jvm/java-21-openjdk-amd64",
    "/Applications/Android Studio.app/Contents/jbr/Contents/Home",
    "/Applications/Android Studio.app/Contents/jbr",
  ].filter(Boolean);

  return candidates.find(binJavaExists) || null;
}

function findAndroidSdk() {
  const home = process.env.HOME || process.env.USERPROFILE || "";
  const candidates = [
    process.env.ANDROID_HOME,
    process.env.ANDROID_SDK_ROOT,
    path.join(process.env.LOCALAPPDATA || "", "Android", "Sdk"),
    home && path.join(home, "Android", "Sdk"),
    home && path.join(home, "Android", "sdk"),
    home && path.join(home, ".android", "sdk"),
  ].filter(Boolean);

  return (
    candidates.find((sdkPath) =>
      existsSync(path.join(sdkPath, "platform-tools")),
    ) || null
  );
}

function findNodeBinary() {
  const candidates = [
    process.execPath,
    process.env.NODE_BINARY,
    path.join(
      process.env.ProgramFiles || "C:\\Program Files",
      "nodejs",
      "node.exe",
    ),
    path.join(
      process.env["ProgramFiles(x86)"] || "C:\\Program Files (x86)",
      "nodejs",
      "node.exe",
    ),
  ].filter(Boolean);

  return candidates.find((nodePath) => existsSync(nodePath)) || null;
}

function ensureLocalProperties(androidSdkPath) {
  const localPropertiesPath = path.join(
    process.cwd(),
    "android",
    "local.properties",
  );
  const sdkDir =
    process.platform === "win32"
      ? androidSdkPath.replace(/\\/g, "\\\\")
      : androidSdkPath;
  writeFileSync(localPropertiesPath, `sdk.dir=${sdkDir}\n`, "utf8");
}

function lerApiBaseUrlDoEnv() {
  const envPath = path.join(process.cwd(), ".env");
  if (!existsSync(envPath)) {
    return "";
  }

  const content = readFileSync(envPath, "utf8");
  const match = content.match(/^\s*EXPO_PUBLIC_API_BASE_URL\s*=\s*(.+)\s*$/m);
  if (!match) {
    return "";
  }

  return match[1].trim().replace(/^['"]|['"]$/g, "");
}

function lerExpoPublicEnvDoArquivo() {
  const envPath = path.join(process.cwd(), ".env");
  if (!existsSync(envPath)) {
    return {};
  }

  const values = {};
  for (const rawLine of readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) {
      continue;
    }
    const [rawKey, ...rawValueParts] = line.split("=");
    const key = String(rawKey || "").trim();
    if (!key.startsWith("EXPO_PUBLIC_")) {
      continue;
    }
    values[key] = rawValueParts
      .join("=")
      .trim()
      .replace(/^['"]|['"]$/g, "");
  }

  return values;
}

const javaHome = findJavaHome();
if (!javaHome) {
  console.error(
    "Nao encontrei um JDK valido. Instale o Android Studio ou configure JAVA_HOME antes de rodar o app Android.",
  );
  process.exit(1);
}

const androidSdk = findAndroidSdk();
if (!androidSdk) {
  console.error(
    "Nao encontrei o Android SDK. Abra o Android Studio e confirme se o SDK foi instalado antes de rodar o app Android.",
  );
  process.exit(1);
}

const nodeBinary = findNodeBinary();
if (!nodeBinary) {
  console.error(
    "Nao encontrei um Node valido. Instale o Node.js ou configure NODE_BINARY antes de rodar o app Android.",
  );
  process.exit(1);
}

ensureLocalProperties(androidSdk);
fixAndroidLauncherIcon(process.cwd());
fixLinuxNodeExecutables(process.cwd());

const expoPublicEnv = lerExpoPublicEnvDoArquivo();
const apiBaseUrl =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  expoPublicEnv.EXPO_PUBLIC_API_BASE_URL ||
  lerApiBaseUrlDoEnv() ||
  "http://127.0.0.1:8000";
const androidV2ReadContractsFlag =
  process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED ||
  expoPublicEnv.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED ||
  "";

console.log(`Usando API mobile dev em ${apiBaseUrl}`);
console.log(
  `Usando Android V2 dev flag=${androidV2ReadContractsFlag || "<unset>"}`,
);

const env = {
  ...expoPublicEnv,
  ...process.env,
  JAVA_HOME: javaHome,
  ANDROID_HOME: androidSdk,
  ANDROID_SDK_ROOT: androidSdk,
  NODE_BINARY: nodeBinary,
  EXPO_PUBLIC_API_BASE_URL: apiBaseUrl,
  PATH: [
    path.dirname(nodeBinary),
    path.join(javaHome, "bin"),
    path.join(androidSdk, "platform-tools"),
    path.join(androidSdk, "emulator"),
    process.env.PATH || "",
  ].join(path.delimiter),
};

if (process.platform === "win32") {
  env.PATHEXT =
    process.env.PATHEXT && process.env.PATHEXT.includes(".EXE")
      ? process.env.PATHEXT
      : ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC";
}

const androidCwd = path.join(process.cwd(), "android");
const gradleStopCommand =
  process.platform === "win32" ? "cmd.exe" : "./gradlew";
const gradleStopArgs =
  process.platform === "win32"
    ? ["/d", "/s", "/c", "gradlew.bat --stop"]
    : ["--stop"];

spawnSync(gradleStopCommand, gradleStopArgs, {
  cwd: androidCwd,
  env,
  stdio: "ignore",
  shell: false,
});

limparBuildsAndroidNoNodeModules(process.cwd());
limparBuildsProjetoAndroid(process.cwd());

const command = process.platform === "win32" ? "npx.cmd" : "npx";
const child = spawn(command, ["expo", "run:android"], {
  cwd: process.cwd(),
  env,
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
