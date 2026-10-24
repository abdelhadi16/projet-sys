// Unit tests for the pure device helpers. No DOM needed — plain input/output.
import { describe, it, expect } from "vitest";
import {
  deviceName,
  deviceClass,
  statusClass,
  isKeyboard,
  formatValue,
  uniqueClasses,
  filterDevices,
  summarize,
} from "../lib/format.js";

// A few small device fixtures shaped like DeviceInfo.to_dict() in task1ver2.py.
const keyboard = {
  friendly_name: "",
  description: "HID Keyboard Device",
  manufacturer: "(Standard keyboards)",
  class_name: "Keyboard",
  hardware_ids: ["HID\\VID_8087"],
  instance_id: "HID\\INTC816\\1",
  status: "Ok",
};
const mouse = {
  friendly_name: "USB Optical Mouse",
  manufacturer: "Logitech",
  class_name: "Mouse",
  instance_id: "USB\\VID_046D\\2",
  status: "Ok",
};
const badNet = {
  description: "Ethernet Controller",
  class_name: "Net",
  instance_id: "PCI\\VEN_8086\\3",
  status: "NotStarted",
};

describe("deviceName", () => {
  it("prefers friendly_name, then description, then instance_id", () => {
    expect(deviceName(mouse)).toBe("USB Optical Mouse");
    expect(deviceName(keyboard)).toBe("HID Keyboard Device"); // friendly empty
    expect(deviceName({ instance_id: "X\\1" })).toBe("X\\1");
  });
});

describe("deviceClass / isKeyboard", () => {
  it("reads the class name with a fallback", () => {
    expect(deviceClass(mouse)).toBe("Mouse");
    expect(deviceClass({})).toBe("(no class)");
  });
  it("detects keyboards case-insensitively", () => {
    expect(isKeyboard(keyboard)).toBe(true);
    expect(isKeyboard(mouse)).toBe(false);
  });
});

describe("statusClass", () => {
  it("maps statuses to css modifiers", () => {
    expect(statusClass("Ok")).toBe("ok");
    expect(statusClass("Disabled")).toBe("disabled");
    expect(statusClass("Error")).toBe("error");
    expect(statusClass("NotStarted")).toBe("notstarted");
    expect(statusClass("Whatever")).toBe("unknown");
  });
});

describe("formatValue", () => {
  it("formats lists, booleans and empties", () => {
    expect(formatValue(["a", "b"])).toBe("a, b");
    expect(formatValue(true)).toBe("Yes");
    expect(formatValue(false)).toBe("No");
    expect(formatValue(null)).toBe("—");
    expect(formatValue("")).toBe("—");
    expect(formatValue(42)).toBe("42");
  });
});

describe("uniqueClasses", () => {
  it("returns a sorted unique list of class names", () => {
    expect(uniqueClasses([keyboard, mouse, badNet, mouse])).toEqual([
      "Keyboard",
      "Mouse",
      "Net",
    ]);
  });
});

describe("filterDevices", () => {
  const all = [keyboard, mouse, badNet];

  it("returns everything with no filter", () => {
    expect(filterDevices(all)).toHaveLength(3);
  });

  it("filters by class", () => {
    expect(filterDevices(all, { classFilter: "Mouse" })).toEqual([mouse]);
  });

  it("searches name, instance id, manufacturer and hardware ids", () => {
    expect(filterDevices(all, { search: "logitech" })).toEqual([mouse]);
    expect(filterDevices(all, { search: "VID_8087" })).toEqual([keyboard]);
    expect(filterDevices(all, { search: "ethernet" })).toEqual([badNet]);
  });

  it("combines class and search", () => {
    expect(filterDevices(all, { classFilter: "Net", search: "usb" })).toEqual([]);
  });
});

describe("summarize", () => {
  it("counts totals, healthy, problems and classes", () => {
    const s = summarize([keyboard, mouse, badNet]);
    expect(s.total).toBe(3);
    expect(s.ok).toBe(2);
    expect(s.problems).toBe(1); // NotStarted counts as a problem
    expect(s.classes).toBe(3);
  });
});
