const { existsSync, readFileSync, writeFileSync } = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");
const {
  limparBuildsAndroidNoNodeModules,
  limparBuildsProjetoAndroid,
} = require("./cleanup-android-build-artifacts.cjs");
const { fixAndroidLauncherIcon } = require("./fix-android-launcher-icon.cjs");
const { fixLinuxNodeExecutables } = require("./fix-linux-node-executables.cjs");

function flagEnabled(value) {
  return ["1", "true", "yes", "on"].includes(
    String(value || "")
      .trim()
      .toLowerCase(),
  );
}

function shouldRunCleanPreviewBuild() {
  return (
    process.argv.includes("--clean") ||
    flagEnabled(process.env.ANDROID_PREVIEW_CLEAN) ||
    flagEnabled(process.env.TARIEL_ANDROID_PREVIEW_CLEAN)
  );
}

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

function findAdbPath(androidSdkPath) {
  const adbBinary = process.platform === "win32" ? "adb.exe" : "adb";
  return path.join(androidSdkPath, "platform-tools", adbBinary);
}

function parseAdbDevices(stdout) {
  return String(stdout || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.startsWith("List of devices attached"))
    .map((line) => line.split(/\s+/))
    .filter((parts) => parts.length >= 2 && parts[1] === "device")
    .map((parts) => parts[0]);
}

function listConnectedAdbDevices(adbPath, env) {
  const result = spawnSync(adbPath, ["devices"], {
    env,
    encoding: "utf8",
    shell: false,
  });
  if ((result.status ?? 0) !== 0) {
    throw new Error(result.stderr || "Falha ao listar devices ADB.");
  }
  return parseAdbDevices(result.stdout);
}

function waitForDeviceBoot(adbPath, serial, env) {
  const waitResult = spawnSync(adbPath, ["-s", serial, "wait-for-device"], {
    env,
    stdio: "inherit",
    shell: false,
    timeout: 30000,
  });
  if ((waitResult.status ?? 0) !== 0) {
    throw new Error(`Falha ao aguardar device ${serial}.`);
  }

  const deadline = Date.now() + 120000;
  let stablePasses = 0;
  while (Date.now() < deadline) {
    const sysBootProbe = spawnSync(
      adbPath,
      ["-s", serial, "shell", "getprop", "sys.boot_completed"],
      {
        env,
        encoding: "utf8",
        shell: false,
        timeout: 10000,
      },
    );
    const devBootProbe = spawnSync(
      adbPath,
      ["-s", serial, "shell", "getprop", "dev.bootcomplete"],
      {
        env,
        encoding: "utf8",
        shell: false,
        timeout: 10000,
      },
    );
    const bootAnimProbe = spawnSync(
      adbPath,
      ["-s", serial, "shell", "getprop", "init.svc.bootanim"],
      {
        env,
        encoding: "utf8",
        shell: false,
        timeout: 10000,
      },
    );
    const packageProbe = spawnSync(
      adbPath,
      [
        "-s",
        serial,
        "shell",
        "cmd",
        "package",
        "resolve-activity",
        "--brief",
        "com.android.settings",
      ],
      {
        env,
        encoding: "utf8",
        shell: false,
        timeout: 10000,
      },
    );
    const serviceListProbe = spawnSync(
      adbPath,
      ["-s", serial, "shell", "service", "list"],
      {
        env,
        encoding: "utf8",
        shell: false,
        timeout: 10000,
      },
    );

    const sysBoot = String(sysBootProbe.stdout || "").trim();
    const devBoot = String(devBootProbe.stdout || "").trim();
    const bootAnim = String(bootAnimProbe.stdout || "").trim();
    const packageOutput = `${packageProbe.stdout || ""}\n${packageProbe.stderr || ""}`;
    const serviceOutput = `${serviceListProbe.stdout || ""}\n${serviceListProbe.stderr || ""}`;
    const packageReady =
      (packageProbe.status ?? 0) === 0 &&
      packageOutput.includes("com.android.settings") &&
      packageOutput.includes("/");
    const criticalServicesReady =
      (serviceListProbe.status ?? 0) === 0 &&
      serviceOutput.includes("package:") &&
      serviceOutput.includes("activity:");
    const bootReady =
      (sysBootProbe.status ?? 0) === 0 &&
      sysBoot === "1" &&
      (!devBoot || devBoot === "1") &&
      (!bootAnim || bootAnim === "stopped") &&
      packageReady &&
      criticalServicesReady;

    if (bootReady) {
      stablePasses += 1;
      if (stablePasses >= 3) {
        return;
      }
    } else {
      stablePasses = 0;
    }

    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1500);
  }

  throw new Error(`Device ${serial} não concluiu boot completo a tempo.`);
}

function waitForCriticalSystemServices(
  adbPath,
  serial,
  env,
  timeoutMs = 60000,
) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const serviceListProbe = spawnSync(
      adbPath,
      ["-s", serial, "shell", "service", "list"],
      {
        env,
        encoding: "utf8",
        shell: false,
        timeout: 10000,
      },
    );
    const serviceOutput = `${serviceListProbe.stdout || ""}\n${serviceListProbe.stderr || ""}`;
    const servicesReady =
      (serviceListProbe.status ?? 0) === 0 &&
      serviceOutput.includes("package:") &&
      serviceOutput.includes("activity:");

    if (servicesReady) {
      return;
    }

    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1500);
  }

  throw new Error(
    `Device ${serial} permaneceu sem serviços críticos (package/activity).`,
  );
}

function resolveTargetSerial(adbPath, env) {
  const explicitSerial = String(env.ANDROID_SERIAL || "").trim();
  if (explicitSerial) {
    return explicitSerial;
  }

  const devices = listConnectedAdbDevices(adbPath, env);
  if (devices.length === 1) {
    return devices[0];
  }

  const emulators = devices.filter((device) => device.startsWith("emulator-"));
  if (emulators.length === 1) {
    return emulators[0];
  }

  throw new Error(
    `Não foi possível resolver um único device ADB. Devices visíveis: ${devices.join(", ") || "nenhum"}.`,
  );
}

function resolveReleaseApkPath(androidCwd) {
  return path.join(
    androidCwd,
    "app",
    "build",
    "outputs",
    "apk",
    "release",
    "app-release.apk",
  );
}

function installApkWithFallback(adbPath, serial, apkPath, env) {
  const installArgsPrimary = [
    "-s",
    serial,
    "install",
    "--no-streaming",
    "-r",
    apkPath,
  ];
  const primary = spawnSync(adbPath, installArgsPrimary, {
    env,
    stdio: "inherit",
    shell: false,
  });
  if ((primary.status ?? 0) === 0) {
    return;
  }

  waitForCriticalSystemServices(adbPath, serial, env);

  console.warn(
    "[devkit] adb install --no-streaming falhou; tentando fallback simples.",
  );
  const fallback = spawnSync(
    adbPath,
    ["-s", serial, "install", "-r", apkPath],
    {
      env,
      stdio: "inherit",
      shell: false,
    },
  );
  if ((fallback.status ?? 0) !== 0) {
    process.exit(fallback.status ?? 1);
  }
}

function launchPreviewApp(adbPath, serial, env) {
  const launchArgs = [
    "-s",
    serial,
    "shell",
    "monkey",
    "-p",
    "com.tarielia.inspetor",
    "-c",
    "android.intent.category.LAUNCHER",
    "1",
  ];
  const result = spawnSync(adbPath, launchArgs, {
    env,
    encoding: "utf8",
    shell: false,
    timeout: 15000,
  });

  if (result.stdout) {
    process.stdout.write(result.stdout);
  }
  if (result.stderr) {
    process.stderr.write(result.stderr);
  }

  if (result.error && result.error.code === "ETIMEDOUT") {
    console.warn(
      "[devkit] Launch do app preview excedeu timeout; seguindo com o app ja instalado.",
    );
    return;
  }

  if ((result.status ?? 0) !== 0) {
    console.warn(
      `[devkit] Launch do app preview retornou ${result.status ?? "desconhecido"}; seguindo mesmo assim.`,
    );
  }
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
    "Nao encontrei um JDK valido. Instale o Android Studio ou configure JAVA_HOME antes de gerar o APK preview.",
  );
  process.exit(1);
}

const androidSdk = findAndroidSdk();
if (!androidSdk) {
  console.error(
    "Nao encontrei o Android SDK. Abra o Android Studio e confirme se o SDK foi instalado antes de gerar o APK preview.",
  );
  process.exit(1);
}

const nodeBinary = findNodeBinary();
if (!nodeBinary) {
  console.error(
    "Nao encontrei um Node valido. Instale o Node.js ou configure NODE_BINARY antes de gerar o APK preview.",
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
const cleanPreviewBuild = shouldRunCleanPreviewBuild();

console.log(`Usando API mobile preview em ${apiBaseUrl}`);
console.log(
  `Usando Android V2 preview flag=${androidV2ReadContractsFlag || "<unset>"}`,
);
console.log(
  cleanPreviewBuild
    ? "Usando Android preview com limpeza fria de build."
    : "Usando Android preview incremental (sem limpeza fria).",
);

const env = {
  ...expoPublicEnv,
  ...process.env,
  JAVA_HOME: javaHome,
  ANDROID_HOME: androidSdk,
  ANDROID_SDK_ROOT: androidSdk,
  NODE_BINARY: nodeBinary,
  EXPO_PUBLIC_API_BASE_URL: apiBaseUrl,
  NODE_ENV: process.env.NODE_ENV || "production",
  RCT_NO_LAUNCH_PACKAGER: "1",
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
const adbPath = findAdbPath(androidSdk);
if (cleanPreviewBuild) {
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
}

const command = process.platform === "win32" ? "cmd.exe" : "./gradlew";
const args =
  process.platform === "win32"
    ? ["/d", "/s", "/c", "gradlew.bat assembleRelease"]
    : ["assembleRelease"];

const child = spawn(command, args, {
  cwd: androidCwd,
  env,
  stdio: "inherit",
  shell: false,
});

child.on("exit", (code) => {
  if ((code ?? 0) !== 0) {
    process.exit(code ?? 0);
    return;
  }
  const apkPath = resolveReleaseApkPath(androidCwd);
  if (!existsSync(apkPath)) {
    console.error(`Nao encontrei o APK preview gerado em ${apkPath}.`);
    process.exit(1);
    return;
  }

  let serial = "";
  try {
    serial = resolveTargetSerial(adbPath, env);
    waitForDeviceBoot(adbPath, serial, env);
  } catch (error) {
    console.error(
      error instanceof Error
        ? error.message
        : "Falha ao resolver o device ADB.",
    );
    process.exit(1);
    return;
  }

  console.log(`[devkit] Instalando APK preview em ${serial}`);
  installApkWithFallback(adbPath, serial, apkPath, env);
  launchPreviewApp(adbPath, serial, env);
  process.exit(0);
});
