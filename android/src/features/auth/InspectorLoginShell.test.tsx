jest.mock("./LoginScreen", () => ({
  LoginScreen: jest.fn(() => null),
}));

import { render } from "@testing-library/react-native";
import * as loginScreenModule from "./LoginScreen";
import { InspectorLoginShell } from "./InspectorLoginShell";

describe("InspectorLoginShell", () => {
  it("renderiza a tela de login com os props já montados", () => {
    render(<InspectorLoginShell loginScreenProps={{} as never} />);
    const mockedLoginScreen = jest.mocked(loginScreenModule.LoginScreen);

    expect(mockedLoginScreen).toHaveBeenCalledTimes(1);
  });
});
