jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  API_BASE_URL,
  construirHeaders,
  fetchComObservabilidade,
  pingApi,
  readRuntimeEnv,
  resolverUrlArquivoApi,
} from "./apiCore";

describe("apiCore", () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });
  });

  it("preserva URLs absolutas de arquivo", () => {
    expect(resolverUrlArquivoApi("https://cdn.tariel.dev/arquivo.pdf")).toBe(
      "https://cdn.tariel.dev/arquivo.pdf",
    );
  });

  it("resolve caminhos relativos com a base da API", () => {
    expect(resolverUrlArquivoApi("/uploads/laudo.pdf")).toBe(
      `${API_BASE_URL}/uploads/laudo.pdf`,
    );
    expect(resolverUrlArquivoApi("uploads/laudo.pdf")).toBe(
      `${API_BASE_URL}/uploads/laudo.pdf`,
    );
  });

  it("normaliza URLs protocol-relative", () => {
    expect(resolverUrlArquivoApi("//cdn.tariel.dev/imagem.png")).toBe(
      "https://cdn.tariel.dev/imagem.png",
    );
  });

  it("injeta headers canônicos de correlação e trace no runtime mobile", () => {
    const headers = construirHeaders("token-123");

    expect(headers.get("Authorization")).toBe("Bearer token-123");
    expect(headers.get("X-Correlation-ID")).toBeTruthy();
    expect(headers.get("X-Request-Id")).toBeTruthy();
    expect(headers.get("X-Client-Request-Id")).toBeTruthy();
    expect(headers.get("X-Mesa-Client-Trace-Id")).toBeTruthy();
    expect(headers.get("traceparent")).toMatch(
      /^00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]$/,
    );
  });

  it("abandona requests travadas quando o timeout expira", async () => {
    jest.useFakeTimers();
    fetchMock.mockImplementation((_url: string, init?: RequestInit) => {
      const signal = init?.signal;
      return new Promise<Response>((_resolve, reject) => {
        if (!signal) {
          return;
        }
        if (signal.aborted) {
          reject(signal.reason ?? new Error("aborted"));
          return;
        }
        signal.addEventListener(
          "abort",
          () => {
            reject(signal.reason ?? new Error("aborted"));
          },
          { once: true },
        );
      });
    });

    try {
      const pending = fetchComObservabilidade(
        "health_check",
        `${API_BASE_URL}/health`,
        undefined,
        undefined,
        { timeoutMs: 25 },
      );

      jest.advanceTimersByTime(30);
      await Promise.resolve();

      await expect(pending).rejects.toThrow("timed out");
    } finally {
      jest.useRealTimers();
    }
  });

  it("faz o ping da API cair para offline quando o health check trava", async () => {
    jest.useFakeTimers();
    fetchMock.mockImplementation((_url: string, init?: RequestInit) => {
      const signal = init?.signal;
      return new Promise<Response>((_resolve, reject) => {
        if (!signal) {
          return;
        }
        if (signal.aborted) {
          reject(signal.reason ?? new Error("aborted"));
          return;
        }
        signal.addEventListener(
          "abort",
          () => {
            reject(signal.reason ?? new Error("aborted"));
          },
          { once: true },
        );
      });
    });

    try {
      const pending = pingApi();

      jest.advanceTimersByTime(6_100);
      await Promise.resolve();

      await expect(pending).resolves.toBe(false);
    } finally {
      jest.useRealTimers();
    }
  });

  it("lê overrides da env de runtime quando disponíveis", () => {
    const envAnterior = process.env.EXPO_PUBLIC_API_BASE_URL;
    process.env.EXPO_PUBLIC_API_BASE_URL = "http://10.100.2.40:8000";

    try {
      expect(readRuntimeEnv("EXPO_PUBLIC_API_BASE_URL")).toBe(
        "http://10.100.2.40:8000",
      );
    } finally {
      if (typeof envAnterior === "string") {
        process.env.EXPO_PUBLIC_API_BASE_URL = envAnterior;
      } else {
        delete process.env.EXPO_PUBLIC_API_BASE_URL;
      }
    }
  });
});
