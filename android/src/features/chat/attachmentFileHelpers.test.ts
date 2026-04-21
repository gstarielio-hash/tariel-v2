import {
  chaveAnexo,
  inferirExtensaoAnexo,
  montarAnexoDocumentoLocal,
  montarAnexoDocumentoMesa,
  montarAnexoImagem,
  nomeArquivoSeguro,
} from "./attachmentFileHelpers";

describe("attachmentFileHelpers", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("sanitiza nomes e resolve extensao/chave do anexo", () => {
    expect(nomeArquivoSeguro(" laudo:/teste?.pdf ", "fallback")).toBe(
      "laudo-teste-.pdf",
    );
    expect(
      inferirExtensaoAnexo({ nome: "arquivo-final.PDF", mime_type: "" } as any),
    ).toBe(".pdf");
    expect(
      chaveAnexo(
        {
          id: 4,
          url: "https://x",
          nome: "arquivo",
          nome_original: "orig",
          label: "lbl",
        } as any,
        "fallback",
      ),
    ).toBe("4:https://x:arquivo:orig:lbl");
  });

  it("monta anexos de imagem e documento", () => {
    jest.spyOn(Date, "now").mockReturnValue(100);

    expect(
      montarAnexoImagem(
        {
          base64: "abc",
          mimeType: "image/png",
          fileName: "",
          uri: "file://img.png",
        } as any,
        "Resumo",
      ),
    ).toMatchObject({
      kind: "image",
      label: "evidencia-100.png",
      resumo: "Resumo",
      previewUri: "file://img.png",
      fileUri: "file://img.png",
      mimeType: "image/png",
    });

    expect(
      montarAnexoDocumentoLocal(
        {
          name: "laudo.pdf",
          uri: "file://laudo.pdf",
          mimeType: "application/pdf",
        } as any,
        "Resumo doc",
      ),
    ).toEqual({
      kind: "document",
      label: "laudo.pdf",
      resumo: "Resumo doc",
      textoDocumento: "",
      nomeDocumento: "laudo.pdf",
      chars: 0,
      truncado: false,
      fileUri: "file://laudo.pdf",
      mimeType: "application/pdf",
    });

    expect(
      montarAnexoDocumentoMesa({
        name: "mesa.docx",
        uri: "file://mesa.docx",
        mimeType: "",
      } as any),
    ).toMatchObject({
      kind: "document",
      resumo: "Documento pronto para seguir direto para a mesa avaliadora.",
      mimeType: "application/octet-stream",
    });
  });

  it("falha ao montar imagem sem base64", () => {
    expect(() =>
      montarAnexoImagem({ uri: "file://img.jpg" } as any, "Resumo"),
    ).toThrow("Não foi possível preparar a imagem selecionada.");
  });
});
