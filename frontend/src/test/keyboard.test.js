// Unit tests for the keyboard helpers + the demo rule engine. The engine mirrors
// decide_action() in takekbctrl.py, so these also check the frontend's
// understanding of the rules contract.
import { describe, it, expect } from "vitest";
import {
  eventKey,
  formatModifiers,
  displayCharacter,
  formatTime,
  describeRule,
  decideVerdict,
  makeDemoKeyEvent,
  demoStarterRules,
} from "../lib/keyboard.js";

const context = { window_title: "x", process_name: "notepad.exe", process_id: 1 };

describe("formatModifiers", () => {
  it("joins modifiers with pretty names, empty when none", () => {
    expect(formatModifiers([])).toBe("");
    expect(formatModifiers(["SHIFT", "CTRL"])).toBe("Shift+Ctrl");
    expect(formatModifiers(["CAPS_LOCK"])).toBe("Caps");
  });
});

describe("displayCharacter", () => {
  it("shows symbols for whitespace and passes normal chars", () => {
    expect(displayCharacter(" ")).toBe("␣");
    expect(displayCharacter("\n")).toBe("⏎");
    expect(displayCharacter("\t")).toBe("⇥");
    expect(displayCharacter("a")).toBe("a");
    expect(displayCharacter("")).toBe("");
  });
});

describe("formatTime", () => {
  it("formats POSIX seconds as HH:MM:SS.mmm", () => {
    const d = new Date(2026, 0, 2, 13, 5, 9, 123);
    expect(formatTime(d.getTime() / 1000)).toBe("13:05:09.123");
    expect(formatTime(0)).toBe("");
  });
});

describe("eventKey", () => {
  it("combines timestamp, key code and type", () => {
    const log = { enriched_event: { decoded: { raw: { timestamp: 10.5, key_code: 65, event_type: "PRESS" } } } };
    expect(eventKey(log)).toBe("10.5-65-PRESS");
  });
});

describe("describeRule", () => {
  it("summarises block and modify rules", () => {
    expect(
      describeRule({ action: "BLOCK", match_key: ["LWIN", "RWIN"], match_modifiers: [], match_process: "notepad.exe" })
    ).toBe("BLOCK LWIN, RWIN (when in notepad.exe)");
    expect(
      describeRule({ action: "MODIFY", match_key: ["A"], match_modifiers: ["CTRL"], match_process: null, replacement_key: 66 })
    ).toBe("MODIFY A with Ctrl -> key 66");
  });
});

describe("decideVerdict", () => {
  it("always PASSes in observe-only mode", () => {
    const v = decideVerdict({ key_name: "LWIN", modifiers: [] }, context, demoStarterRules(), true);
    expect(v.action).toBe("PASS");
    expect(v.rule_id).toBe("observe_only");
  });

  it("blocks a matching key when blocking is on", () => {
    const v = decideVerdict({ key_name: "LWIN", modifiers: [] }, context, demoStarterRules(), false);
    expect(v.action).toBe("BLOCK");
    expect(v.rule_id).toBe("block-win-key");
  });

  it("PASSes a key that matches no rule", () => {
    const v = decideVerdict({ key_name: "A", modifiers: [] }, context, demoStarterRules(), false);
    expect(v.action).toBe("PASS");
    expect(v.rule_id).toBeNull();
  });

  it("ignores disabled rules", () => {
    const rules = [{ ...demoStarterRules()[0], enabled: false }];
    expect(decideVerdict({ key_name: "LWIN", modifiers: [] }, context, rules, false).action).toBe("PASS");
  });

  it("respects priority (highest matching rule wins)", () => {
    const rules = [
      { id: "low", enabled: true, priority: 1, match_key: ["A"], match_modifiers: [], action: "BLOCK", replacement_key: null },
      { id: "high", enabled: true, priority: 9, match_key: ["A"], match_modifiers: [], action: "MODIFY", replacement_key: 66 },
    ];
    const v = decideVerdict({ key_name: "A", modifiers: [] }, context, rules, false);
    expect(v.rule_id).toBe("high");
    expect(v.action).toBe("MODIFY");
  });

  it("requires all modifiers to be held", () => {
    const rules = [
      { id: "ctrl-a", enabled: true, priority: 0, match_key: ["A"], match_modifiers: ["CTRL"], action: "BLOCK", replacement_key: null },
    ];
    expect(decideVerdict({ key_name: "A", modifiers: [] }, context, rules, false).action).toBe("PASS");
    expect(decideVerdict({ key_name: "A", modifiers: ["CTRL"] }, context, rules, false).action).toBe("BLOCK");
  });
});

describe("makeDemoKeyEvent", () => {
  it("produces a LogEntry-shaped object", () => {
    const log = makeDemoKeyEvent(0, demoStarterRules(), false);
    expect(log).toHaveProperty("enriched_event.decoded.raw.key_code");
    expect(log).toHaveProperty("enriched_event.context.process_name");
    expect(log).toHaveProperty("verdict.action");
    expect(log).toHaveProperty("logged_at");
  });
});
