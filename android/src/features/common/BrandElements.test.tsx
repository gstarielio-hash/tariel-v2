import { render } from "@testing-library/react-native";

import { BrandLaunchOverlay } from "./BrandElements";

jest.mock("expo-linear-gradient", () => {
  const React = require("react");
  const { View } = require("react-native");
  return {
    LinearGradient: ({ children, ...props }: Record<string, unknown>) =>
      React.createElement(View, props, children),
  };
});

describe("BrandLaunchOverlay", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("nao reinicia a intro quando o callback muda durante um rerender", () => {
    const onDoneInicial = jest.fn();
    const onDoneAtual = jest.fn();

    const { rerender } = render(
      <BrandLaunchOverlay
        accentColor="#f97316"
        animationsEnabled={false}
        onDone={onDoneInicial}
        visible
      />,
    );

    jest.advanceTimersByTime(100);

    rerender(
      <BrandLaunchOverlay
        accentColor="#f97316"
        animationsEnabled={false}
        onDone={onDoneAtual}
        visible
      />,
    );

    jest.advanceTimersByTime(80);

    expect(onDoneInicial).not.toHaveBeenCalled();
    expect(onDoneAtual).toHaveBeenCalledTimes(1);
  });
});
