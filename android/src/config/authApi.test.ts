jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  loginInspectorMobile,
  obterUrlLoginSocialMobile,
  obterUrlRecuperacaoSenhaMobile,
} from "./authApi";

function criarResposta(
  body: string,
  init?: { status?: number; contentType?: string },
) {
  const status = init?.status ?? 200;
  const headers = new Headers();
  headers.set("content-type", init?.contentType ?? "application/json");
  return {
    ok: status >= 200 && status < 300,
    status,
    headers,
    text: async () => body,
  } as Response;
}

describe("authApi", () => {
  const fetchMock = jest.fn();
  const envOriginal = { ...process.env };

  beforeEach(() => {
    fetchMock.mockReset();
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });
    process.env = { ...envOriginal };
    delete process.env.EXPO_PUBLIC_AUTH_FORGOT_PASSWORD_URL;
    delete process.env.EXPO_PUBLIC_AUTH_GOOGLE_URL;
    delete process.env.EXPO_PUBLIC_AUTH_MICROSOFT_URL;
    delete process.env.EXPO_PUBLIC_AUTH_WEB_BASE_URL;
  });

  afterAll(() => {
    process.env = envOriginal;
  });

  it("monta a URL de recuperação com email opcional", () => {
    expect(obterUrlRecuperacaoSenhaMobile()).toBe(
      "http://127.0.0.1:8000/app/login",
    );
    expect(obterUrlRecuperacaoSenhaMobile("inspetor@tariel.dev")).toBe(
      "http://127.0.0.1:8000/app/login?email=inspetor%40tariel.dev",
    );
  });

  it("monta URLs de login social com fallbacks públicos corretos", () => {
    expect(obterUrlLoginSocialMobile("Google")).toBe(
      "http://127.0.0.1:8000/app/login?provider=google",
    );
    expect(obterUrlLoginSocialMobile("Microsoft")).toBe(
      "http://127.0.0.1:8000/app/login?provider=microsoft",
    );
  });

  it("honra a base pública ativa da sessão de desenvolvimento", () => {
    process.env.EXPO_PUBLIC_API_BASE_URL = "http://10.100.2.40:8000";

    expect(obterUrlRecuperacaoSenhaMobile()).toBe(
      "http://10.100.2.40:8000/app/login",
    );
    expect(obterUrlLoginSocialMobile("Google")).toBe(
      "http://10.100.2.40:8000/app/login?provider=google",
    );
  });

  it("retorna login válido quando a API responde com access_token", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          access_token: "token-123",
          token_type: "bearer",
          usuario: { email: "inspetor@tariel.dev" },
        }),
      ),
    );

    await expect(
      loginInspectorMobile("inspetor@tariel.dev", "segredo", true),
    ).resolves.toMatchObject({
      access_token: "token-123",
    });
  });

  it("propaga erro legível quando o login falha", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(JSON.stringify({ detail: "Credenciais inválidas" }), {
        status: 401,
      }),
    );

    await expect(
      loginInspectorMobile("inspetor@tariel.dev", "errada", false),
    ).rejects.toThrow("Credenciais inválidas");
  });

  it("traduz timeout de login para mensagem operacional legível", async () => {
    fetchMock.mockRejectedValue(new Error("Request timed out after 15000ms."));

    await expect(
      loginInspectorMobile("inspetor@tariel.dev", "segredo", true),
    ).rejects.toThrow("Tempo limite excedido ao autenticar no app.");
  });
});
