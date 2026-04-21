import { Image } from "react-native";
import { render } from "@testing-library/react-native";

import { MessageAttachmentCard } from "./MessageCards";

jest.mock("@expo/vector-icons", () => {
  const React = require("react");
  const { Text } = require("react-native");
  return {
    MaterialCommunityIcons: ({
      name,
      ...props
    }: {
      name: string;
      [key: string]: unknown;
    }) => React.createElement(Text, props, name),
  };
});

describe("MessageAttachmentCard", () => {
  it("renderiza imagem com preview maior e resize contain", () => {
    const { UNSAFE_getByType } = render(
      <MessageAttachmentCard
        accessToken="token-123"
        attachment={{
          id: 8,
          nome: "painel.png",
          mime_type: "image/png",
          categoria: "imagem",
          eh_imagem: true,
          url: "/app/api/laudo/80/mesa/anexos/8",
        }}
        onPress={jest.fn()}
        opening={false}
      />,
    );

    const preview = UNSAFE_getByType(Image);
    expect(preview.props.resizeMode).toBe("contain");
    expect(preview.props.source).toMatchObject({
      uri: expect.stringContaining("/app/api/laudo/80/mesa/anexos/8"),
      headers: {
        Authorization: "Bearer token-123",
      },
    });
  });
});
