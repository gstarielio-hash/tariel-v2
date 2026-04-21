import { createHmac, randomInt } from "node:crypto";

const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function generateTotpSecret(length = 32) {
  if (!Number.isInteger(length) || length < 16) {
    throw new Error("Comprimento minimo do segredo TOTP e 16.");
  }

  return Array.from({ length }, () => BASE32_ALPHABET[randomInt(BASE32_ALPHABET.length)] ?? "A").join("");
}

export function normalizeTotpSecret(secret: string) {
  const normalized = String(secret ?? "")
    .trim()
    .toUpperCase()
    .split("")
    .filter((character) => BASE32_ALPHABET.includes(character))
    .join("");

  if (!normalized) {
    throw new Error("Segredo TOTP invalido.");
  }

  return normalized;
}

export function normalizeTotpCode(code: string) {
  return String(code ?? "")
    .split("")
    .filter((character) => /\d/.test(character))
    .join("")
    .slice(0, 8);
}

export function verifyTotp(
  secret: string,
  code: string,
  options?: {
    atTime?: number;
    stepSeconds?: number;
    digits?: number;
    window?: number;
  },
) {
  const digits = options?.digits ?? 6;
  const codeNormalized = normalizeTotpCode(code);

  if (codeNormalized.length !== digits) {
    return false;
  }

  const stepSeconds = options?.stepSeconds ?? 30;
  const timestamp = Math.trunc(options?.atTime ?? Date.now() / 1000);
  const counter = Math.trunc(timestamp / stepSeconds);
  const window = Math.abs(options?.window ?? 1);

  for (let delta = -window; delta <= window; delta += 1) {
    if (hotp(secret, counter + delta, digits) === codeNormalized) {
      return true;
    }
  }

  return false;
}

export function currentTotp(
  secret: string,
  options?: {
    atTime?: number;
    stepSeconds?: number;
    digits?: number;
  },
) {
  const digits = options?.digits ?? 6;
  const stepSeconds = options?.stepSeconds ?? 30;
  const timestamp = Math.trunc(options?.atTime ?? Date.now() / 1000);

  return hotp(secret, Math.trunc(timestamp / stepSeconds), digits);
}

export function buildTotpOtpauthUri(secret: string, accountName: string, issuer = "Tariel Admin-CEO") {
  const secretNormalized = normalizeTotpSecret(secret);
  const account = encodeURIComponent(String(accountName ?? "").trim() || "admin@tariel.ia");
  const issuerNormalized = encodeURIComponent(String(issuer ?? "").trim() || "Tariel Admin-CEO");

  return `otpauth://totp/${issuerNormalized}:${account}?secret=${secretNormalized}&issuer=${issuerNormalized}`;
}

function hotp(secret: string, counter: number, digits = 6) {
  const key = decodeBase32Secret(secret);
  const counterBuffer = Buffer.alloc(8);

  counterBuffer.writeBigUInt64BE(BigInt(Math.max(counter, 0)));

  const digest = createHmac("sha1", key).update(counterBuffer).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const binary = (digest.readUInt32BE(offset) & 0x7fffffff) % 10 ** digits;

  return String(binary).padStart(digits, "0");
}

function decodeBase32Secret(secret: string) {
  const normalized = normalizeTotpSecret(secret);
  let bits = "";

  for (const character of normalized) {
    const index = BASE32_ALPHABET.indexOf(character);

    if (index < 0) {
      throw new Error("Segredo TOTP invalido.");
    }

    bits += index.toString(2).padStart(5, "0");
  }

  const bytes: number[] = [];

  for (let offset = 0; offset + 8 <= bits.length; offset += 8) {
    bytes.push(Number.parseInt(bits.slice(offset, offset + 8), 2));
  }

  return Buffer.from(bytes);
}
