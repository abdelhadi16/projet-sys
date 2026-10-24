// Component tests for the Keyboard-tab components.
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EventRow from "../components/EventRow.jsx";
import ModeSwitch from "../components/ModeSwitch.jsx";
import RuleEditor from "../components/RuleEditor.jsx";

// A LogEntry matching takekbctrl.LogEntry.to_dict().
function sampleLog(overrides = {}) {
  return {
    enriched_event: {
      decoded: {
        raw: { key_code: 65, scan_code: 30, event_type: "PRESS", timestamp: 100, is_injected: false },
        key_name: "A",
        character: "a",
        modifiers: ["SHIFT"],
      },
      context: { window_title: "Notepad", process_name: "notepad.exe", process_id: 5 },
    },
    verdict: { action: "BLOCK", rule_id: "r1", replacement_key: null },
    logged_at: 100,
    ...overrides,
  };
}

describe("EventRow", () => {
  it("shows key, process and verdict", () => {
    render(<EventRow log={sampleLog()} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("notepad.exe", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("BLOCK")).toBeInTheDocument();
  });
});

describe("ModeSwitch", () => {
  it("calls onChange with the flipped value", async () => {
    const onChange = vi.fn();
    render(<ModeSwitch observeOnly={true} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onChange).toHaveBeenCalledWith(false);
  });

  it("shows 'Blocking' when observe-only is off", () => {
    render(<ModeSwitch observeOnly={false} onChange={() => {}} />);
    expect(screen.getByText("Blocking")).toBeInTheDocument();
  });
});

describe("RuleEditor", () => {
  const rule = {
    id: "block-win-key",
    enabled: true,
    priority: 10,
    match_key: ["LWIN"],
    match_modifiers: [],
    match_process: null,
    action: "BLOCK",
    replacement_key: null,
  };

  it("lists rules", () => {
    render(<RuleEditor rules={[rule]} onCreate={() => {}} onUpdate={() => {}} onDelete={() => {}} />);
    expect(screen.getByText("block-win-key")).toBeInTheDocument();
  });

  it("calls onDelete when Delete is clicked", async () => {
    const onDelete = vi.fn();
    render(<RuleEditor rules={[rule]} onCreate={() => {}} onUpdate={() => {}} onDelete={onDelete} />);
    await userEvent.click(screen.getByText("Delete"));
    expect(onDelete).toHaveBeenCalledWith("block-win-key");
  });

  it("toggles enabled via onUpdate when Disable is clicked", async () => {
    const onUpdate = vi.fn();
    render(<RuleEditor rules={[rule]} onCreate={() => {}} onUpdate={onUpdate} onDelete={() => {}} />);
    await userEvent.click(screen.getByText("Disable"));
    expect(onUpdate).toHaveBeenCalledWith("block-win-key", expect.objectContaining({ enabled: false }));
  });

  it("creates a new rule through the add form", async () => {
    const onCreate = vi.fn();
    render(<RuleEditor rules={[]} onCreate={onCreate} onUpdate={() => {}} onDelete={() => {}} />);
    await userEvent.click(screen.getByText("+ Add rule"));
    await userEvent.type(screen.getByPlaceholderText(/block-win-key/), "my-rule");
    await userEvent.click(screen.getByText("Save rule"));
    expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ id: "my-rule" }));
  });
});
