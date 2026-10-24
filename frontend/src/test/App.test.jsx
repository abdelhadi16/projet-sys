// Integration test for the whole App: tabs, demo mode, and the wiring each view
// does. App opens WebSockets and fetches on mount, which jsdom doesn't provide,
// so we stub both with harmless fakes.
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import App from "../App.jsx";

// Minimal WebSocket stand-in so connect/cleanup can run without error.
class FakeWebSocket {
  constructor() {
    this.readyState = 0;
  }
  send() {}
  close() {}
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeWebSocket);
  // No backend in the test: a promise that never settles keeps the initial REST
  // load pending so no state update fires after the test (avoids act warnings).
  // Every path under test runs in demo mode anyway.
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
});

describe("App", () => {
  it("renders the header with both tabs", () => {
    render(<App />);
    expect(screen.getByText("OS")).toBeInTheDocument();
    expect(screen.getByText("Project")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Devices" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Keyboard" })).toBeInTheDocument();
  });

  it("shows the device snapshot on the Devices tab in demo mode", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Demo mode"));
    expect(screen.getByText(/Demo mode \(no backend\)/)).toBeInTheDocument();
    // "Devices" is both a tab button and a stat label, so pick the stat card.
    const devicesCard = screen
      .getAllByText("Devices")
      .map((el) => el.closest(".stat"))
      .find(Boolean);
    expect(within(devicesCard).getByText("175")).toBeInTheDocument();
  });

  it("switches to the Keyboard tab and shows the starter rule in demo mode", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Demo mode"));
    fireEvent.click(screen.getByRole("button", { name: "Keyboard" }));

    // The keyboard view shows its panels and the demo starter rule.
    expect(screen.getByText("Live key events")).toBeInTheDocument();
    expect(screen.getByText("Rules")).toBeInTheDocument();
    expect(screen.getByText("block-win-key")).toBeInTheDocument();
  });
});
