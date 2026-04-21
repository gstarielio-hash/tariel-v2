#!/usr/bin/env node

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const DEFAULT_FLOW = "android/maestro/login-smoke.yaml";
const DEFAULT_APP_MODE = "dev-client";
const PREVIEW_APP_MODE = "preview";
const DEFAULT_HEALTH_TIMEOUT_SECONDS = 45;
const DEFAULT_METRO_TIMEOUT_SECONDS = 45;
const HEALTH_URL = "http://127.0.0.1:8000/health";
const METRO_URL = "http://127.0.0.1:8081";
const LOCAL_MOBILE_API_BASE_URL = "http://127.0.0.1:8000";
const ADB_AUTH_LOGIN_TIMEOUT_MS = 150000;
const DEFAULT_MAESTRO_LOGIN_EMAIL = "inspetor@tariel.ia";
const DEFAULT_MAESTRO_LOGIN_PASSWORD = "Dev@123456";
const ADB_AUTH_FLOW_ANCHORS = new Map([
  ["android/maestro/login-smoke.yaml", "open-history-button"],
  ["android/maestro/history-smoke.yaml", "open-history-button"],
  ["android/maestro/settings-smoke.yaml", "open-settings-button"],
  ["android/maestro/chat-smoke.yaml", "free-chat-start-button"],
  ["android/maestro/pre-laudo-canonical-smoke.yaml", "guided-entry-open-button"],
  ["android/maestro/pre-laudo-canonical-finalize-smoke.yaml", "guided-entry-open-button"],
]);
const CANONICAL_PRE_LAUDO_SEED_SCRIPT = path.join(
  "web",
  "scripts",
  "seed_mobile_canonical_pre_laudo_data.py",
);

function hasGraphicalDisplay() {
  if (process.platform === "linux") {
    return Boolean((process.env.DISPLAY || "").trim() || (process.env.WAYLAND_DISPLAY || "").trim());
  }
  return true;
}

function runningInCi() {
  return ["1", "true", "yes", "on"].includes(String(process.env.CI || "").trim().toLowerCase());
}

function mobileVisualEnabled() {
  const raw = String(process.env.MOBILE_VISUAL || "").trim().toLowerCase();
  if (["0", "false", "no", "off"].includes(raw)) {
    return false;
  }
  if (["1", "true", "yes", "on"].includes(raw)) {
    return hasGraphicalDisplay();
  }
  if (runningInCi()) {
    return false;
  }
  return hasGraphicalDisplay();
}

function printHelp() {
  console.log(`
Uso:
  node scripts/run_mobile_maestro_smoke.cjs [--device <id>] [--flow <arquivo>] [--skip-api-start] [--app-mode <modo>]

Opcoes:
  --device, --device-id, --udid  Serial/UDID do dispositivo Android (opcional).
  --flow                         Fluxo Maestro relativo a raiz do repo.
  --skip-api-start               Nao tenta subir a API local do mobile.
  --preview                      Atalho para --app-mode preview.
  --app-mode                     dev-client (padrao) ou preview.
  -h, --help                     Mostra esta ajuda.

Exemplos:
  node scripts/run_mobile_maestro_smoke.cjs
  node scripts/run_mobile_maestro_smoke.cjs --device emulator-5554
  node scripts/run_mobile_maestro_smoke.cjs --flow android/maestro/settings-smoke.yaml
  node scripts/run_mobile_maestro_smoke.cjs --preview --flow android/maestro/pre-laudo-canonical-finalize-smoke.yaml

Credenciais padrao do smoke:
  MAESTRO_LOGIN_EMAIL=${DEFAULT_MAESTRO_LOGIN_EMAIL}
  MAESTRO_LOGIN_PASSWORD=${DEFAULT_MAESTRO_LOGIN_PASSWORD}
`);
}

function parseArgs(argv) {
  const options = {
    deviceId: process.env.ANDROID_SERIAL || "",
    flow: DEFAULT_FLOW,
    skipApiStart: false,
    appMode: String(process.env.MOBILE_MAESTRO_APP_MODE || DEFAULT_APP_MODE)
      .trim()
      .toLowerCase(),
    help: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "-h" || arg === "--help") {
      options.help = true;
      continue;
    }

    if (arg === "--skip-api-start") {
      options.skipApiStart = true;
      continue;
    }

    if (arg === "--preview") {
      options.appMode = PREVIEW_APP_MODE;
      continue;
    }

    if (arg.startsWith("--device=")) {
      options.deviceId = arg.slice("--device=".length).trim();
      continue;
    }

    if (arg === "--device" || arg === "--device-id" || arg === "--udid") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error(`Valor ausente para ${arg}`);
      }
      options.deviceId = value.trim();
      index += 1;
      continue;
    }

    if (arg.startsWith("--flow=")) {
      options.flow = arg.slice("--flow=".length).trim();
      continue;
    }

    if (arg === "--flow") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error("Valor ausente para --flow");
      }
      options.flow = value.trim();
      index += 1;
      continue;
    }

    if (arg.startsWith("--app-mode=")) {
      options.appMode = arg.slice("--app-mode=".length).trim().toLowerCase();
      continue;
    }

    if (arg === "--app-mode") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error("Valor ausente para --app-mode");
      }
      options.appMode = value.trim().toLowerCase();
      index += 1;
      continue;
    }

    throw new Error(`Argumento nao reconhecido: ${arg}`);
  }

  if (!options.flow) {
    throw new Error("Flow nao pode ser vazio.");
  }

  if (![DEFAULT_APP_MODE, PREVIEW_APP_MODE].includes(options.appMode)) {
    throw new Error(
      `Modo de app invalido: ${options.appMode}. Use ${DEFAULT_APP_MODE} ou ${PREVIEW_APP_MODE}.`,
    );
  }

  return options;
}

function candidateExists(candidate) {
  return Boolean(candidate) && fs.existsSync(candidate);
}

function commandWorks(command, args) {
  const probe = spawnSync(command, args, {
    stdio: "ignore",
    shell: false,
  });
  return !probe.error && probe.status === 0;
}

function findAdbBinary() {
  const home = process.env.HOME || os.homedir() || "";
  const adbBinary = process.platform === "win32" ? "adb.exe" : "adb";
  const fileCandidates = [
    process.env.ADB_PATH,
    process.env.ANDROID_HOME && path.join(process.env.ANDROID_HOME, "platform-tools", adbBinary),
    process.env.ANDROID_SDK_ROOT && path.join(process.env.ANDROID_SDK_ROOT, "platform-tools", adbBinary),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, "Android", "Sdk", "platform-tools", "adb.exe"),
    home && path.join(home, "Android", "Sdk", "platform-tools", adbBinary),
    home && path.join(home, "Android", "sdk", "platform-tools", adbBinary),
  ].filter(Boolean);

  for (const candidate of fileCandidates) {
    if (candidateExists(candidate)) {
      return candidate;
    }
  }

  if (commandWorks(adbBinary, ["version"])) {
    return adbBinary;
  }

  throw new Error(
    "adb nao encontrado. Configure ANDROID_HOME/ANDROID_SDK_ROOT ou adicione platform-tools no PATH.",
  );
}

function findMaestroRunner() {
  const windowsMaestroExe =
    process.env.LOCALAPPDATA &&
    path.join(process.env.LOCALAPPDATA, "Programs", "maestro", "maestro", "bin", "maestro.exe");

  const explicit = process.env.MAESTRO_BIN;
  if (candidateExists(explicit)) {
    return { command: explicit, prefixArgs: [] };
  }

  if (candidateExists(windowsMaestroExe)) {
    return { command: windowsMaestroExe, prefixArgs: [] };
  }

  if (commandWorks("maestro", ["--version"])) {
    return { command: "maestro", prefixArgs: [] };
  }

  if (commandWorks("npx", ["--yes", "maestro", "--version"])) {
    return { command: "npx", prefixArgs: ["--yes", "maestro"] };
  }

  throw new Error(
    "maestro nao encontrado. Instale via curl/get.maestro.mobile.dev ou expo toolchain equivalente.",
  );
}

function findExpoRunner(repoRoot) {
  const androidRoot = path.join(repoRoot, "android");
  const expoBinary = process.platform === "win32" ? "expo.cmd" : "expo";
  const explicit = process.env.EXPO_BIN;
  const fileCandidates = [
    explicit,
    path.join(androidRoot, "node_modules", ".bin", expoBinary),
  ].filter(Boolean);

  for (const candidate of fileCandidates) {
    if (candidateExists(candidate)) {
      return { command: candidate, prefixArgs: [] };
    }
  }

  if (commandWorks(expoBinary, ["--version"])) {
    return { command: expoBinary, prefixArgs: [] };
  }

  if (commandWorks("npx", ["--yes", "expo", "--version"])) {
    return { command: "npx", prefixArgs: ["--yes", "expo"] };
  }

  throw new Error(
    "Expo CLI nao encontrada. Rode npm install em android/ antes do smoke mobile.",
  );
}

function previewMobileApiBaseUrl() {
  return (
    String(process.env.MOBILE_MAESTRO_API_BASE_URL || "").trim() ||
    LOCAL_MOBILE_API_BASE_URL
  );
}

function findPythonBinary(repoRoot) {
  const webRoot = path.join(repoRoot, "web");
  const exeName = process.platform === "win32" ? "python.exe" : "python";
  const home = process.env.HOME || os.homedir() || "";

  const fileCandidates = [
    process.env.PYTHON_BIN,
    path.join(repoRoot, ".venv-linux", "bin", "python"),
    path.join(repoRoot, ".venv", "bin", "python"),
    path.join(repoRoot, "venv", "bin", "python"),
    path.join(webRoot, ".venv-linux", "bin", "python"),
    path.join(webRoot, ".venv", "bin", "python"),
    path.join(webRoot, "venv", "bin", "python"),
    path.join(repoRoot, ".venv", "Scripts", exeName),
    path.join(repoRoot, "venv", "Scripts", exeName),
    path.join(webRoot, ".venv", "Scripts", exeName),
    path.join(webRoot, "venv", "Scripts", exeName),
    home && path.join(home, ".pyenv", "shims", "python"),
  ].filter(Boolean);

  for (const candidate of fileCandidates) {
    if (candidateExists(candidate)) {
      return candidate;
    }
  }

  if (commandWorks("python3", ["--version"])) {
    return "python3";
  }

  if (commandWorks("python", ["--version"])) {
    return "python";
  }

  throw new Error(
    "Python nao encontrado. Configure PYTHON_BIN ou crie uma venv em .venv-linux/.venv.",
  );
}

function runCommand(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    env: options.env,
    stdio: options.stdio || "inherit",
    shell: false,
  });

  if (result.error) {
    throw new Error(`Falha ao executar comando: ${command} (${result.error.message})`);
  }

  if ((result.status ?? 0) !== 0) {
    throw new Error(`Comando retornou erro (${result.status ?? 1}): ${command} ${args.join(" ")}`);
  }

  return result;
}

function runTextCommand(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    env: options.env,
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf8",
    shell: false,
  });

  if (result.error) {
    throw new Error(`Falha ao executar comando: ${command} (${result.error.message})`);
  }

  if ((result.status ?? 0) !== 0) {
    const stderr = String(result.stderr || "").trim();
    throw new Error(stderr || `Comando retornou erro (${result.status ?? 1}): ${command} ${args.join(" ")}`);
  }

  return String(result.stdout || "");
}

function runJsonCommand(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    env: options.env,
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf8",
    shell: false,
  });

  if (result.error) {
    throw new Error(`Falha ao executar comando: ${command} (${result.error.message})`);
  }

  if ((result.status ?? 0) !== 0) {
    const stderr = String(result.stderr || "").trim();
    throw new Error(stderr || `Comando retornou erro (${result.status ?? 1}): ${command} ${args.join(" ")}`);
  }

  try {
    return JSON.parse(String(result.stdout || ""));
  } catch (error) {
    throw new Error(
      `Nao foi possivel ler JSON de ${command}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

function parseConnectedDevices(adbBinary) {
  const result = spawnSync(adbBinary, ["devices"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
  });

  if (result.error || result.status !== 0) {
    throw new Error("Nao foi possivel listar dispositivos com adb devices.");
  }

  const lines = String(result.stdout || "")
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter(Boolean);

  const devices = [];
  for (const line of lines) {
    if (line.startsWith("List of devices attached")) {
      continue;
    }
    const [serial, state] = line.split(/\s+/);
    if (serial && state === "device") {
      devices.push(serial);
    }
  }

  return devices;
}

async function testHttpHealth(url = HEALTH_URL) {
  return new Promise((resolve) => {
    const request = http.get(url, { timeout: 3000 }, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });

    request.on("error", () => resolve(false));
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
  });
}

async function testHttpReachable(url) {
  return new Promise((resolve) => {
    const request = http.get(url, { timeout: 3000 }, (response) => {
      response.resume();
      resolve(Boolean(response.statusCode));
    });

    request.on("error", () => resolve(false));
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
  });
}

async function waitForHealth(timeoutSeconds = DEFAULT_HEALTH_TIMEOUT_SECONDS) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  while (Date.now() < deadline) {
    if (await testHttpHealth()) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  return false;
}

async function waitForReachableUrl(url, timeoutSeconds = DEFAULT_METRO_TIMEOUT_SECONDS) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  while (Date.now() < deadline) {
    if (await testHttpReachable(url)) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  return false;
}

function startMobileApiInBackground(repoRoot) {
  const webRoot = path.join(repoRoot, "web");
  if (!fs.existsSync(webRoot)) {
    throw new Error(`Pasta web nao encontrada em ${webRoot}`);
  }

  const pythonBinary = findPythonBinary(repoRoot);
  const logPath = path.join(repoRoot, "local-mobile-api.log");
  const errorLogPath = path.join(repoRoot, "local-mobile-api.error.log");

  fs.writeFileSync(logPath, "", "utf8");
  fs.writeFileSync(errorLogPath, "", "utf8");

  const outFd = fs.openSync(logPath, "a");
  const errFd = fs.openSync(errorLogPath, "a");

  const child = spawn(
    pythonBinary,
    ["-m", "uvicorn", "main:app", "--app-dir", ".", "--host", "0.0.0.0", "--port", "8000"],
    {
      cwd: webRoot,
      env: {
        ...process.env,
        AMBIENTE: process.env.AMBIENTE || "dev",
        SEED_DEV_BOOTSTRAP: "1",
        SEED_DEV_SENHA_PADRAO: process.env.SEED_DEV_SENHA_PADRAO || DEFAULT_MAESTRO_LOGIN_PASSWORD,
      },
      stdio: ["ignore", outFd, errFd],
      detached: process.platform !== "win32",
      shell: false,
      windowsHide: true,
    },
  );

  child.unref();
}

function killProcessIfRunning(pid) {
  if (!pid || Number.isNaN(Number(pid))) {
    return;
  }
  try {
    process.kill(Number(pid), "SIGTERM");
  } catch (_error) {
    return;
  }
  sleepSync(1200);
  try {
    process.kill(Number(pid), 0);
    process.kill(Number(pid), "SIGKILL");
  } catch (_error) {
    // Processo ja encerrou.
  }
}

function killMetroFromPidFile(pidPath) {
  if (!candidateExists(pidPath)) {
    return;
  }
  const rawPid = String(fs.readFileSync(pidPath, "utf8") || "").trim();
  if (rawPid) {
    killProcessIfRunning(rawPid);
  }
  fs.rmSync(pidPath, { force: true });
}

function killProcessesListeningOnPort(port) {
  const lsofResult = spawnSync("lsof", ["-ti", `:${port}`], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
    shell: false,
  });
  if (lsofResult.error || (lsofResult.status !== 0 && !String(lsofResult.stdout || "").trim())) {
    return;
  }
  const pids = String(lsofResult.stdout || "")
    .split(/\r?\n/g)
    .map((value) => value.trim())
    .filter(Boolean);
  for (const pid of pids) {
    killProcessIfRunning(pid);
  }
}

function startMobileMetroInBackground(repoRoot) {
  const androidRoot = path.join(repoRoot, "android");
  if (!fs.existsSync(androidRoot)) {
    throw new Error(`Pasta android nao encontrada em ${androidRoot}`);
  }

  const expo = findExpoRunner(repoRoot);
  const pidPath = path.join(androidRoot, "expo-mobile.pid");
  const logPath = path.join(androidRoot, "expo-mobile.log");
  const errorLogPath = path.join(androidRoot, "expo-mobile.error.log");
  const mobileApiBaseUrl = previewMobileApiBaseUrl();

  killMetroFromPidFile(pidPath);
  killProcessesListeningOnPort(8081);

  fs.writeFileSync(logPath, "", "utf8");
  fs.writeFileSync(errorLogPath, "", "utf8");

  const outFd = fs.openSync(logPath, "a");
  const errFd = fs.openSync(errorLogPath, "a");
  const child = spawn(
    expo.command,
    [
      ...expo.prefixArgs,
      "start",
      "--dev-client",
      "--host",
      "localhost",
      "--port",
      "8081",
      "--non-interactive",
    ],
    {
      cwd: androidRoot,
      env: {
        ...process.env,
        EXPO_PUBLIC_API_BASE_URL: mobileApiBaseUrl,
        EXPO_PUBLIC_AUTH_WEB_BASE_URL: mobileApiBaseUrl,
        EXPO_NO_TELEMETRY: "1",
      },
      stdio: ["ignore", outFd, errFd],
      detached: process.platform !== "win32",
      shell: false,
      windowsHide: true,
    },
  );

  if (child.pid) {
    fs.writeFileSync(pidPath, `${child.pid}\n`, "utf8");
  }
  child.unref();
}

function buildPreviewEnv(deviceId) {
  const mobileApiBaseUrl = previewMobileApiBaseUrl();
  return {
    ...process.env,
    ANDROID_SERIAL: deviceId,
    EXPO_PUBLIC_API_BASE_URL: mobileApiBaseUrl,
    EXPO_PUBLIC_AUTH_WEB_BASE_URL:
      String(process.env.MOBILE_MAESTRO_AUTH_WEB_BASE_URL || "").trim() ||
      mobileApiBaseUrl,
  };
}

function installPreviewBuild(repoRoot, deviceId) {
  const androidRoot = path.join(repoRoot, "android");
  const previewEnv = buildPreviewEnv(deviceId);

  console.log(
    `Gerando e instalando APK preview local com API ${previewEnv.EXPO_PUBLIC_API_BASE_URL}...`,
  );
  runCommand(process.execPath, ["scripts/fix-gradle-wrapper.cjs"], {
    cwd: androidRoot,
    env: previewEnv,
  });
  runCommand(process.execPath, ["scripts/run-android-preview.cjs"], {
    cwd: androidRoot,
    env: previewEnv,
  });
}

function buildMaestroEnv() {
  return {
    ...process.env,
    MAESTRO_LOGIN_EMAIL: process.env.MAESTRO_LOGIN_EMAIL || DEFAULT_MAESTRO_LOGIN_EMAIL,
    MAESTRO_LOGIN_PASSWORD: process.env.MAESTRO_LOGIN_PASSWORD || DEFAULT_MAESTRO_LOGIN_PASSWORD,
  };
}

function flowRequiresCanonicalLaudo(flowPath) {
  const normalized = String(flowPath || "").replace(/\\/g, "/");
  return (
    normalized.endsWith("/pre-laudo-canonical-smoke.yaml") ||
    normalized.endsWith("/pre-laudo-canonical-finalize-smoke.yaml") ||
    normalized.endsWith("/mobile-v2-pilot-run.yaml")
  );
}

function seedCanonicalPreLaudoCase(repoRoot) {
  const pythonBinary = findPythonBinary(repoRoot);
  const seedScriptPath = path.join(repoRoot, CANONICAL_PRE_LAUDO_SEED_SCRIPT);
  return runJsonCommand(pythonBinary, [seedScriptPath], { cwd: repoRoot });
}

function enrichMaestroEnvForFlow(repoRoot, flowPath, maestroEnv) {
  if (
    !flowRequiresCanonicalLaudo(flowPath) ||
    String(maestroEnv.MAESTRO_TARGET_LAUDO_ID || "").trim()
  ) {
    return maestroEnv;
  }

  const seedPayload = seedCanonicalPreLaudoCase(repoRoot);
  console.log(
    `Seed canônico pronto: laudo ${seedPayload.laudo_id} (${seedPayload.template_key || "padrao"}).`,
  );
  return {
    ...maestroEnv,
    MAESTRO_LOGIN_EMAIL:
      String(maestroEnv.MAESTRO_LOGIN_EMAIL || "").trim() ||
      seedPayload.inspetor_email ||
      DEFAULT_MAESTRO_LOGIN_EMAIL,
    MAESTRO_TARGET_LAUDO_ID: String(seedPayload.laudo_id),
  };
}

function resolveFlowPath(repoRoot, flow) {
  const normalizedFlow = flow.replace(/\\/g, path.sep);
  const fullPath = path.isAbsolute(normalizedFlow) ? normalizedFlow : path.join(repoRoot, normalizedFlow);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Flow do Maestro nao encontrado em ${fullPath}`);
  }
  return fullPath;
}

function resolveDeviceId(adbBinary, preferredDevice) {
  if (preferredDevice) {
    return preferredDevice;
  }

  const connectedDevices = parseConnectedDevices(adbBinary);
  const emulators = connectedDevices.filter((serial) => /^emulator-\d+$/.test(serial));
  if (emulators.length > 0) {
    return emulators[0];
  }
  if (connectedDevices.length === 1) {
    return connectedDevices[0];
  }

  if (connectedDevices.length === 0) {
    throw new Error("Nenhum dispositivo Android conectado. Conecte um aparelho ou suba um emulador.");
  }

  throw new Error(
    `Mais de um dispositivo detectado (${connectedDevices.join(", ")}). Informe --device <id>.`,
  );
}

function shouldEnsureLocalEmulator(adbBinary, preferredDevice) {
  const connectedDevices = parseConnectedDevices(adbBinary);
  if (preferredDevice) {
    return /^emulator-\d+$/.test(preferredDevice) && !connectedDevices.includes(preferredDevice);
  }
  return !connectedDevices.some((serial) => /^emulator-\d+$/.test(serial));
}

function ensureLocalEmulator(repoRoot) {
  if (process.platform === "win32") {
    return;
  }

  const scriptPath = path.join(repoRoot, "scripts", "dev", "run_android_emulator_stack.sh");
  if (!fs.existsSync(scriptPath)) {
    return;
  }

  const visualMode = mobileVisualEnabled();
  const args = ["--mode", "boot"];
  if (!visualMode) {
    args.push("--headless");
  }
  console.log(`Garantindo emulador Android ${visualMode ? "visível" : "headless"}...`);
  runCommand(scriptPath, args, { stdio: "inherit" });
}

function prepareVisibleDevice(adbBinary, deviceId) {
  runCommand(adbBinary, ["start-server"], { stdio: "ignore" });
  runCommand(adbBinary, ["-s", deviceId, "wait-for-device"]);
  runCommand(adbBinary, ["-s", deviceId, "reverse", "tcp:8000", "tcp:8000"]);
  runCommand(adbBinary, ["-s", deviceId, "shell", "svc", "power", "stayon", "true"], { stdio: "ignore" });
  runCommand(adbBinary, ["-s", deviceId, "shell", "input", "keyevent", "KEYCODE_WAKEUP"], { stdio: "ignore" });
  runCommand(adbBinary, ["-s", deviceId, "shell", "wm", "dismiss-keyguard"], { stdio: "ignore" });
  try {
    runCommand(adbBinary, ["-s", deviceId, "reverse", "tcp:8081", "tcp:8081"], { stdio: "ignore" });
  } catch (_error) {
    // Preview builds nao precisam do Metro; ignoramos se a porta nao existir.
  }
}

function sleepSync(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizeFlowForLookup(repoRoot, flowPath) {
  return path.relative(repoRoot, flowPath).replace(/\\/g, "/");
}

function shouldUseAdbAuthenticatedFlow(repoRoot, flowPath, appMode) {
  if (appMode === PREVIEW_APP_MODE) {
    return false;
  }
  const envValue = String(process.env.MAESTRO_USE_ADB_AUTH || "").trim().toLowerCase();
  if (["0", "false", "no", "off"].includes(envValue)) {
    return false;
  }
  return ADB_AUTH_FLOW_ANCHORS.has(normalizeFlowForLookup(repoRoot, flowPath));
}

function resolveAdbAuthAnchor(repoRoot, flowPath) {
  return ADB_AUTH_FLOW_ANCHORS.get(normalizeFlowForLookup(repoRoot, flowPath)) || "";
}

function dumpUiHierarchy(adbBinary, deviceId) {
  runCommand(adbBinary, ["-s", deviceId, "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], {
    stdio: "ignore",
  });
  return runTextCommand(adbBinary, ["-s", deviceId, "shell", "cat", "/sdcard/window_dump.xml"]);
}

function parseBoundsFromHierarchy(hierarchyXml, resourceId) {
  const pattern = new RegExp(
    `resource-id="(?:[^"]+:id/)?${escapeRegex(resourceId)}"[^>]*bounds="\\[(\\d+),(\\d+)\\]\\[(\\d+),(\\d+)\\]"`,
  );
  const match = hierarchyXml.match(pattern);
  if (!match) {
    return null;
  }
  return {
    left: Number(match[1]),
    top: Number(match[2]),
    right: Number(match[3]),
    bottom: Number(match[4]),
  };
}

function waitForResourceId(adbBinary, deviceId, resourceId, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const hierarchyXml = dumpUiHierarchy(adbBinary, deviceId);
    const bounds = parseBoundsFromHierarchy(hierarchyXml, resourceId);
    if (bounds) {
      return bounds;
    }
    sleepSync(1000);
  }
  throw new Error(`Elemento ${resourceId} nao apareceu no emulador a tempo.`);
}

function tapBoundsCenter(adbBinary, deviceId, bounds) {
  const centerX = Math.round((bounds.left + bounds.right) / 2);
  const centerY = Math.round((bounds.top + bounds.bottom) / 2);
  runCommand(adbBinary, [
    "-s",
    deviceId,
    "shell",
    "input",
    "tap",
    String(centerX),
    String(centerY),
  ], { stdio: "ignore" });
}

function readDisplaySize(adbBinary, deviceId) {
  const output = runTextCommand(adbBinary, ["-s", deviceId, "shell", "wm", "size"], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  const match = output.match(/Physical size:\s*(\d+)x(\d+)/i);
  if (!match) {
    return { width: 1080, height: 2400 };
  }
  return {
    width: Number(match[1]),
    height: Number(match[2]),
  };
}

function tapRelativePosition(adbBinary, deviceId, xRatio, yRatio) {
  const { width, height } = readDisplaySize(adbBinary, deviceId);
  const x = Math.round(width * xRatio);
  const y = Math.round(height * yRatio);
  runCommand(adbBinary, ["-s", deviceId, "shell", "input", "tap", String(x), String(y)], {
    stdio: "ignore",
  });
}

function encodeTextForAdb(text) {
  return String(text).replace(/ /g, "%s");
}

function inputTextWithAdb(adbBinary, deviceId, text) {
  runCommand(adbBinary, [
    "-s",
    deviceId,
    "shell",
    "input",
    "text",
    encodeTextForAdb(text),
  ], { stdio: "ignore" });
}

function buildDevClientLaunchUrl() {
  const baseUrl = String(process.env.MOBILE_MAESTRO_DEV_CLIENT_URL || "").trim() || METRO_URL;
  return `tarielinspetor://expo-development-client/?url=${encodeURIComponent(baseUrl)}`;
}

function launchDevClientExperience(adbBinary, deviceId) {
  runCommand(adbBinary, [
    "-s",
    deviceId,
    "shell",
    "am",
    "start",
    "-W",
    "-a",
    "android.intent.action.VIEW",
    "-d",
    buildDevClientLaunchUrl(),
    "com.tarielia.inspetor",
  ], { stdio: "ignore" });
}

function authenticateWithAdbFallback(adbBinary, deviceId, maestroEnv) {
  const loginEmail = String(maestroEnv.MAESTRO_LOGIN_EMAIL || "").trim();
  const loginPassword = String(maestroEnv.MAESTRO_LOGIN_PASSWORD || "").trim();
  tapRelativePosition(adbBinary, deviceId, 0.5, 0.56);
  sleepSync(900);
  inputTextWithAdb(adbBinary, deviceId, loginEmail);
  tapRelativePosition(adbBinary, deviceId, 0.5, 0.64);
  sleepSync(700);
  inputTextWithAdb(adbBinary, deviceId, loginPassword);
  runCommand(adbBinary, ["-s", deviceId, "shell", "input", "keyevent", "KEYCODE_BACK"], {
    stdio: "ignore",
  });
  sleepSync(500);
  tapRelativePosition(adbBinary, deviceId, 0.5, 0.76);
}

function createAuthenticatedFlowVariant(flowPath, anchorId) {
  const rawContent = fs.readFileSync(flowPath, "utf8");
  const parts = rawContent.split(/\r?\n---\r?\n/);
  if (parts.length !== 2) {
    throw new Error(`Flow ${flowPath} nao segue o formato esperado com cabecalho YAML e separador '---'.`);
  }

  const [header, body] = parts;
  const anchorIndex = body.indexOf(`id: ${anchorId}`);
  if (anchorIndex < 0) {
    throw new Error(`Anchor ${anchorId} nao encontrado em ${flowPath}.`);
  }

  const commandStart = body.lastIndexOf("\n- ", anchorIndex);
  if (commandStart < 0) {
    throw new Error(`Nao foi possivel localizar o inicio do comando do anchor ${anchorId} em ${flowPath}.`);
  }

  const variantDir = fs.mkdtempSync(path.join(os.tmpdir(), "tariel-maestro-auth-"));
  const variantPath = path.join(variantDir, path.basename(flowPath));
  const variantContent = `${header.trimEnd()}\n---\n${body.slice(commandStart + 1).trimStart()}`;

  fs.writeFileSync(variantPath, variantContent, "utf8");
  return variantPath;
}

function authenticateWithAdb(adbBinary, deviceId, maestroEnv, postLoginAnchorId) {
  const loginEmail = String(maestroEnv.MAESTRO_LOGIN_EMAIL || "").trim();
  const loginPassword = String(maestroEnv.MAESTRO_LOGIN_PASSWORD || "").trim();
  if (!loginEmail || !loginPassword) {
    throw new Error("Credenciais do smoke ausentes para autenticacao ADB.");
  }

  runCommand(adbBinary, ["-s", deviceId, "shell", "pm", "clear", "com.tarielia.inspetor"], { stdio: "ignore" });
  launchDevClientExperience(adbBinary, deviceId);
  sleepSync(20000);
  launchDevClientExperience(adbBinary, deviceId);
  sleepSync(5000);

  let emailBounds = null;
  try {
    emailBounds = waitForResourceId(
      adbBinary,
      deviceId,
      "login-email-input",
      ADB_AUTH_LOGIN_TIMEOUT_MS,
    );
  } catch (_error) {
    emailBounds = null;
  }

  if (!emailBounds) {
    authenticateWithAdbFallback(adbBinary, deviceId, maestroEnv);
    sleepSync(1500);
    return;
  }

  tapBoundsCenter(adbBinary, deviceId, emailBounds);
  sleepSync(800);
  inputTextWithAdb(adbBinary, deviceId, loginEmail);

  const passwordBounds = waitForResourceId(adbBinary, deviceId, "login-password-input", 10000);
  tapBoundsCenter(adbBinary, deviceId, passwordBounds);
  sleepSync(500);
  inputTextWithAdb(adbBinary, deviceId, loginPassword);
  runCommand(adbBinary, ["-s", deviceId, "shell", "input", "keyevent", "KEYCODE_BACK"], {
    stdio: "ignore",
  });
  sleepSync(400);

  const submitBounds = waitForResourceId(adbBinary, deviceId, "login-submit-button", 10000);
  tapBoundsCenter(adbBinary, deviceId, submitBounds);
  sleepSync(1500);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  const repoRoot = path.resolve(__dirname, "..");
  const adbBinary = findAdbBinary();
  if (shouldEnsureLocalEmulator(adbBinary, options.deviceId)) {
    ensureLocalEmulator(repoRoot);
  }
  const flowPath = resolveFlowPath(repoRoot, options.flow);
  const maestro = findMaestroRunner();
  const maestroEnv = enrichMaestroEnvForFlow(
    repoRoot,
    flowPath,
    buildMaestroEnv(),
  );
  const deviceId = resolveDeviceId(adbBinary, options.deviceId);

  if (!(await testHttpHealth())) {
    if (options.skipApiStart) {
      throw new Error(`API local indisponivel em ${HEALTH_URL} e --skip-api-start foi usado.`);
    }

    console.log("Subindo API local do mobile...");
    startMobileApiInBackground(repoRoot);
    const healthy = await waitForHealth();
    if (!healthy) {
      throw new Error(`API local nao respondeu a tempo em ${HEALTH_URL}.`);
    }
  }

  console.log(`Preparando dispositivo ${deviceId}...`);
  prepareVisibleDevice(adbBinary, deviceId);

  if (options.appMode === PREVIEW_APP_MODE) {
    installPreviewBuild(repoRoot, deviceId);
  } else {
    console.log(
      `Reiniciando Metro local do mobile em ${METRO_URL} com API ${LOCAL_MOBILE_API_BASE_URL}...`,
    );
    startMobileMetroInBackground(repoRoot);
    if (!(await waitForReachableUrl(METRO_URL))) {
      throw new Error(`Metro local nao respondeu a tempo em ${METRO_URL}.`);
    }
  }

  let effectiveFlowPath = flowPath;
  if (shouldUseAdbAuthenticatedFlow(repoRoot, flowPath, options.appMode)) {
    const anchorId = resolveAdbAuthAnchor(repoRoot, flowPath);
    console.log(
      `Autenticando shell por ADB antes do Maestro (${normalizeFlowForLookup(repoRoot, flowPath)} -> ${anchorId}).`,
    );
    authenticateWithAdb(adbBinary, deviceId, maestroEnv, anchorId);
    effectiveFlowPath = createAuthenticatedFlowVariant(flowPath, anchorId);
  }

  console.log(`Rodando Maestro: ${normalizeFlowForLookup(repoRoot, effectiveFlowPath)}`);
  runCommand(maestro.command, [...maestro.prefixArgs, "test", "--device", deviceId, effectiveFlowPath], {
    env: maestroEnv,
  });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
