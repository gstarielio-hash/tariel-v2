import { randomInt } from "node:crypto";

import { hash } from "@node-rs/argon2";

const SPECIAL_CHARACTERS = "!@#$%&*+-_=.";
const PASSWORD_ALPHABET = `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789${SPECIAL_CHARACTERS}`;

export async function hashPassword(password: string) {
  const normalized = String(password ?? "");

  if (!normalized) {
    throw new Error("Senha vazia não é permitida.");
  }

  return hash(normalized, {
    // Argon2id is the library default and matches the legacy Python policy.
  });
}

export function generateStrongPassword(length = 14) {
  if (length < 12) {
    throw new Error("Comprimento mínimo é 12.");
  }

  if (length > 128) {
    throw new Error("Comprimento máximo é 128.");
  }

  const password = [
    pickCharacter("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    pickCharacter("abcdefghijklmnopqrstuvwxyz"),
    pickCharacter("0123456789"),
    pickCharacter(SPECIAL_CHARACTERS),
  ];

  while (password.length < length) {
    password.push(pickCharacter(PASSWORD_ALPHABET));
  }

  for (let index = password.length - 1; index > 0; index -= 1) {
    const target = randomInt(index + 1);
    const current = password[index];

    password[index] = password[target] ?? current;
    password[target] = current;
  }

  return password.join("");
}

function pickCharacter(source: string) {
  return source[randomInt(source.length)] ?? source[0] ?? "";
}
