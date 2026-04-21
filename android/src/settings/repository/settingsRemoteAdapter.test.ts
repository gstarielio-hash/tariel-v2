import { createDefaultAppSettings } from "../schema/defaults";
import { mergeMobileUserIntoSettings } from "./settingsRemoteAdapter";

describe("mergeMobileUserIntoSettings", () => {
  it("mantem a referencia original quando a conta ja esta sincronizada", () => {
    const settings = {
      ...createDefaultAppSettings(),
      account: {
        ...createDefaultAppSettings().account,
        fullName: "Gabriel Silva",
        displayName: "Gabriel",
        email: "inspetor@example.com",
        phone: "11999999999",
        photoUri: "https://cdn.example.com/profile.jpg",
        photoHint: "Foto sincronizada com a conta",
      },
    };

    const resultado = mergeMobileUserIntoSettings(settings, {
      id: 1,
      email: "inspetor@example.com",
      nome_completo: "Gabriel Silva",
      telefone: "11999999999",
      foto_perfil_url: "https://cdn.example.com/profile.jpg",
      empresa_nome: "Tariel",
      empresa_id: 7,
      nivel_acesso: 1,
    });

    expect(resultado).toBe(settings);
  });
});
