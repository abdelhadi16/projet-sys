// Unit tests for the demo hotplug logic.
import { describe, it, expect } from "vitest";
import { demoInitialDevices, toggleDemoUsb } from "../lib/demo.js";

describe("demoInitialDevices", () => {
  it("returns a non-empty list of real-shaped devices", () => {
    const list = demoInitialDevices();
    expect(list.length).toBeGreaterThan(0);
    // Each device should at least have an instance_id and status.
    expect(list[0]).toHaveProperty("instance_id");
    expect(list[0]).toHaveProperty("status");
  });

  it("returns a fresh copy each call (no shared mutation)", () => {
    const a = demoInitialDevices();
    const b = demoInitialDevices();
    expect(a).not.toBe(b);
    expect(a[0]).not.toBe(b[0]);
  });
});

describe("toggleDemoUsb", () => {
  it("adds the demo USB when it is absent", () => {
    const start = demoInitialDevices();
    const after = toggleDemoUsb(start);
    expect(after.length).toBe(start.length + 1);
    expect(after.some((d) => d.instance_id.includes("DEMO1234"))).toBe(true);
  });

  it("removes the demo USB when it is present (plug then unplug)", () => {
    const start = demoInitialDevices();
    const plugged = toggleDemoUsb(start);
    const unplugged = toggleDemoUsb(plugged);
    expect(unplugged.length).toBe(start.length);
    expect(unplugged.some((d) => d.instance_id.includes("DEMO1234"))).toBe(false);
  });
});
