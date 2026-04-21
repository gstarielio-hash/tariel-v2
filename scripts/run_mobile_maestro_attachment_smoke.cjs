#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const APP_ID = "com.tarielia.inspetor";
const DEFAULT_MAESTRO_FLOW = "android/maestro/attachments-smoke.yaml";
const DEFAULT_MAESTRO_LOGIN_EMAIL = "inspetor@tariel.ia";
const DEFAULT_MAESTRO_LOGIN_PASSWORD = "Dev@123456";
const EMULATOR_IMAGE_FILENAME = "tariel-attachment-image.png";
const EMULATOR_DOCUMENT_FILENAME = "tariel-attachment-document.pdf";
const EMULATOR_IMAGE_DESTINATION = `/sdcard/Pictures/${EMULATOR_IMAGE_FILENAME}`;
const EMULATOR_DOCUMENT_DESTINATION = `/sdcard/Download/${EMULATOR_DOCUMENT_FILENAME}`;

function hasGraphicalDisplay() {
  if (process.platform === "linux") {
    return Boolean(
      (process.env.DISPLAY || "").trim() ||
        (process.env.WAYLAND_DISPLAY || "").trim(),
    );
  }
  return true;
}

function runningInCi() {
  return ["1", "true", "yes", "on"].includes(
    String(process.env.CI || "").trim().toLowerCase(),
  );
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
  return false;
}

function printHelp() {
  console.log(`
Uso:
  node scripts/run_mobile_maestro_attachment_smoke.cjs [--device <id>] [--flow <path>] [--skip-api-start]

Opcoes:
  --device, --device-id, --udid  Serial/UDID do dispositivo Android (opcional).
  --flow                         Flow Maestro a executar. Padrao: ${DEFAULT_MAESTRO_FLOW}
  --skip-api-start               Reaproveita uma API local ja em execucao.
  -h, --help                     Mostra esta ajuda.

Exemplos:
  node scripts/run_mobile_maestro_attachment_smoke.cjs
  node scripts/run_mobile_maestro_attachment_smoke.cjs --device emulator-5554

Credenciais padrao do smoke:
  MAESTRO_LOGIN_EMAIL=${DEFAULT_MAESTRO_LOGIN_EMAIL}
  MAESTRO_LOGIN_PASSWORD=${DEFAULT_MAESTRO_LOGIN_PASSWORD}
`);
}

function parseArgs(argv) {
  const options = {
    deviceId: process.env.ANDROID_SERIAL || "",
    flow: DEFAULT_MAESTRO_FLOW,
    skipApiStart: false,
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

    if (arg.startsWith("--flow=")) {
      options.flow = arg.slice("--flow=".length).trim() || DEFAULT_MAESTRO_FLOW;
      continue;
    }

    if (arg.startsWith("--device=")) {
      options.deviceId = arg.slice("--device=".length).trim();
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

    if (arg === "--device" || arg === "--device-id" || arg === "--udid") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error(`Valor ausente para ${arg}`);
      }
      options.deviceId = value.trim();
      index += 1;
      continue;
    }

    throw new Error(`Argumento nao reconhecido: ${arg}`);
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

function runCommand(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    env: options.env,
    stdio: options.stdio || "inherit",
    encoding: options.encoding,
    shell: false,
  });

  if (result.error) {
    throw new Error(
      `Falha ao executar comando: ${command} (${result.error.message})`,
    );
  }

  if ((result.status ?? 0) !== 0) {
    throw new Error(
      `Comando retornou erro (${result.status ?? 1}): ${command} ${args.join(" ")}`,
    );
  }

  return result;
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
    throw new Error(
      `Falha ao executar comando: ${command} (${result.error.message})`,
    );
  }

  if ((result.status ?? 0) !== 0) {
    const stderr = String(result.stderr || "").trim();
    throw new Error(
      stderr ||
        `Comando retornou erro (${result.status ?? 1}): ${command} ${args.join(" ")}`,
    );
  }

  try {
    return JSON.parse(String(result.stdout || ""));
  } catch (error) {
    throw new Error(
      `Nao foi possivel ler JSON de ${command}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

function findAdbBinary() {
  const home = process.env.HOME || os.homedir() || "";
  const adbBinary = process.platform === "win32" ? "adb.exe" : "adb";
  const fileCandidates = [
    process.env.ADB_PATH,
    process.env.ANDROID_HOME &&
      path.join(process.env.ANDROID_HOME, "platform-tools", adbBinary),
    process.env.ANDROID_SDK_ROOT &&
      path.join(process.env.ANDROID_SDK_ROOT, "platform-tools", adbBinary),
    process.env.LOCALAPPDATA &&
      path.join(
        process.env.LOCALAPPDATA,
        "Android",
        "Sdk",
        "platform-tools",
        "adb.exe",
      ),
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

function parseConnectedDevices(adbBinary) {
  const result = spawnSync(adbBinary, ["devices"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
  });

  if (result.error || result.status !== 0) {
    throw new Error("Nao foi possivel listar dispositivos com adb devices.");
  }

  return String(result.stdout || "")
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.startsWith("List of devices attached"))
    .map((line) => line.split(/\s+/))
    .filter(([, state]) => state === "device")
    .map(([serial]) => serial);
}

function resolveDeviceId(adbBinary, preferredDevice) {
  if (preferredDevice) {
    return preferredDevice;
  }

  const connectedDevices = parseConnectedDevices(adbBinary);
  const emulators = connectedDevices.filter((serial) =>
    /^emulator-\d+$/.test(serial),
  );
  if (emulators.length > 0) {
    return emulators[0];
  }
  if (connectedDevices.length === 1) {
    return connectedDevices[0];
  }
  if (connectedDevices.length === 0) {
    throw new Error(
      "Nenhum dispositivo Android conectado. Conecte um aparelho ou suba um emulador.",
    );
  }

  throw new Error(
    `Mais de um dispositivo detectado (${connectedDevices.join(", ")}). Informe --device <id>.`,
  );
}

function shouldEnsureLocalEmulator(preferredDevice) {
  return !preferredDevice || /^emulator-\d+$/.test(preferredDevice);
}

function ensureLocalEmulator(repoRoot) {
  if (process.platform === "win32") {
    return;
  }

  const scriptPath = path.join(
    repoRoot,
    "scripts",
    "dev",
    "run_android_emulator_stack.sh",
  );
  if (!fs.existsSync(scriptPath)) {
    return;
  }

  const visualMode = mobileVisualEnabled();
  const args = ["--mode", "boot"];
  if (!visualMode) {
    args.push("--headless");
  }

  runCommand(scriptPath, args, { stdio: "inherit" });
}

function ensureAppInstalled(adbBinary, deviceId) {
  const result = spawnSync(
    adbBinary,
    ["-s", deviceId, "shell", "pm", "list", "packages", APP_ID],
    {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
    },
  );

  if (result.error || result.status !== 0) {
    throw new Error(`Nao foi possivel verificar o app ${APP_ID} no dispositivo.`);
  }

  if (!String(result.stdout || "").includes(APP_ID)) {
    throw new Error(
      `App ${APP_ID} nao esta instalado no dispositivo ${deviceId}. Rode a build preview/dev antes do smoke.`,
    );
  }
}

function copyFixtures(repoRoot) {
  const tempDir = fs.mkdtempSync(
    path.join(os.tmpdir(), "tariel-maestro-attachments-"),
  );
  const imageSource = path.join(repoRoot, "android", "assets", "icon.png");
  const documentSource = path.join(
    repoRoot,
    "docs",
    "portfolio_empresa_nr13_material_real",
    "nr13_integridade_caldeira",
    "pacote_referencia",
    "pdf",
    "nr13_integridade_caldeira_referencia_sintetica.pdf",
  );

  if (!fs.existsSync(imageSource)) {
    throw new Error(`Imagem fixture nao encontrada em ${imageSource}`);
  }
  if (!fs.existsSync(documentSource)) {
    throw new Error(`Documento fixture nao encontrado em ${documentSource}`);
  }

  const imageFixturePath = path.join(tempDir, EMULATOR_IMAGE_FILENAME);
  const documentFixturePath = path.join(tempDir, EMULATOR_DOCUMENT_FILENAME);

  fs.copyFileSync(imageSource, imageFixturePath);
  fs.copyFileSync(documentSource, documentFixturePath);

  return {
    imageFixturePath,
    documentFixturePath,
  };
}

function pushFixture(adbBinary, deviceId, localPath, remotePath) {
  runCommand(adbBinary, ["-s", deviceId, "shell", "mkdir", "-p", path.posix.dirname(remotePath)]);
  runCommand(adbBinary, ["-s", deviceId, "push", localPath, remotePath]);
  runCommand(
    adbBinary,
    [
      "-s",
      deviceId,
      "shell",
      "am",
      "broadcast",
      "-a",
      "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
      "-d",
      `file://${remotePath}`,
    ],
    { stdio: "ignore" },
  );
}

function grantPermissionBestEffort(adbBinary, deviceId, permission) {
  spawnSync(
    adbBinary,
    ["-s", deviceId, "shell", "pm", "grant", APP_ID, permission],
    {
      stdio: "ignore",
      shell: false,
    },
  );
}

function seedAttachmentCase(repoRoot) {
  const pythonBinary = findPythonBinary(repoRoot);
  const seedScriptPath = path.join(
    repoRoot,
    "web",
    "scripts",
    "seed_mobile_attachment_smoke_data.py",
  );
  return runJsonCommand(pythonBinary, [seedScriptPath], { cwd: repoRoot });
}

function buildMaestroEnv(seedPayload) {
  return {
    ...process.env,
    MAESTRO_LOGIN_EMAIL:
      process.env.MAESTRO_LOGIN_EMAIL ||
      seedPayload.inspetor_email ||
      DEFAULT_MAESTRO_LOGIN_EMAIL,
    MAESTRO_LOGIN_PASSWORD:
      process.env.MAESTRO_LOGIN_PASSWORD || DEFAULT_MAESTRO_LOGIN_PASSWORD,
    MAESTRO_TARGET_LAUDO_ID: String(seedPayload.laudo_id),
    MAESTRO_ATTACHMENT_DOCUMENT_FILENAME: EMULATOR_DOCUMENT_FILENAME,
    MAESTRO_ATTACHMENT_CASE_PREVIEW: String(seedPayload.preview || ""),
    MAESTRO_CHAT_EVIDENCE_TEXT:
      process.env.MAESTRO_CHAT_EVIDENCE_TEXT ||
      "Ponto de ancoragem com corrosao aparente e sem placa de identificacao.",
    MAESTRO_CHAT_PDF_REQUEST:
      process.env.MAESTRO_CHAT_PDF_REQUEST ||
      "faca um relatorio em pdf com base nisso",
    MAESTRO_CHAT_PDF_SUCCESS_TEXT:
      process.env.MAESTRO_CHAT_PDF_SUCCESS_TEXT ||
      "Relatório técnico do chat livre gerado em PDF com base nas mensagens e evidências registradas.",
  };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  const repoRoot = path.resolve(__dirname, "..");
  if (shouldEnsureLocalEmulator(options.deviceId)) {
    ensureLocalEmulator(repoRoot);
  }

  const adbBinary = findAdbBinary();
  runCommand(adbBinary, ["start-server"], { stdio: "ignore" });
  const deviceId = resolveDeviceId(adbBinary, options.deviceId);
  runCommand(adbBinary, ["-s", deviceId, "wait-for-device"], {
    stdio: "ignore",
  });

  ensureAppInstalled(adbBinary, deviceId);

  const seedPayload = seedAttachmentCase(repoRoot);
  console.log(
    `Seed de anexos pronto: laudo ${seedPayload.laudo_id} em ${seedPayload.status_revisao}.`,
  );

  const fixtures = copyFixtures(repoRoot);
  console.log(`Enviando fixtures para ${deviceId}...`);
  pushFixture(
    adbBinary,
    deviceId,
    fixtures.imageFixturePath,
    EMULATOR_IMAGE_DESTINATION,
  );
  pushFixture(
    adbBinary,
    deviceId,
    fixtures.documentFixturePath,
    EMULATOR_DOCUMENT_DESTINATION,
  );
  grantPermissionBestEffort(
    adbBinary,
    deviceId,
    "android.permission.CAMERA",
  );

  const smokeScriptPath = path.join(
    repoRoot,
    "scripts",
    "run_mobile_maestro_smoke.cjs",
  );
  const smokeArgs = [
    smokeScriptPath,
    "--device",
    deviceId,
    "--flow",
    options.flow || DEFAULT_MAESTRO_FLOW,
  ];
  if (options.skipApiStart) {
    smokeArgs.push("--skip-api-start");
  }

  runCommand("node", smokeArgs, {
    cwd: repoRoot,
    env: buildMaestroEnv(seedPayload),
  });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
