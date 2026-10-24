// Component tests: render real React components into jsdom and check output and
// interactions, using @testing-library/react.
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ConnectionStatus from "../components/ConnectionStatus.jsx";
import StatsBar from "../components/StatsBar.jsx";
import Toolbar from "../components/Toolbar.jsx";
import DeviceRow from "../components/DeviceRow.jsx";
import DeviceList from "../components/DeviceList.jsx";

const keyboard = {
  description: "HID Keyboard Device",
  manufacturer: "(Standard keyboards)",
  class_name: "Keyboard",
  hardware_ids: ["HID\\VID_8087"],
  instance_id: "HID\\INTC816\\1",
  status: "Ok",
};
const net = {
  description: "Ethernet Controller",
  class_name: "Net",
  instance_id: "PCI\\VEN_8086\\3",
  status: "NotStarted",
};

describe("ConnectionStatus", () => {
  it("renders the connected label", () => {
    render(<ConnectionStatus status="connected" demo={false} />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });
  it("renders a demo label in demo mode", () => {
    render(<ConnectionStatus status="disconnected" demo={true} />);
    expect(screen.getByText(/Demo mode/)).toBeInTheDocument();
  });
});

describe("StatsBar", () => {
  // Find the value shown on the stat card with the given label.
  function valueFor(label) {
    const card = screen.getByText(label).closest(".stat");
    return card.querySelector(".stat-value").textContent;
  }

  it("shows totals and problem counts per card", () => {
    render(<StatsBar devices={[keyboard, net]} />);
    // 2 devices total, 1 healthy (Ok), 1 problem (NotStarted), 2 classes.
    expect(valueFor("Devices")).toBe("2");
    expect(valueFor("Healthy")).toBe("1");
    expect(valueFor("Problems")).toBe("1");
    expect(valueFor("Classes")).toBe("2");
  });
});

describe("Toolbar", () => {
  it("lists the available classes and reports counts", () => {
    render(
      <Toolbar
        devices={[keyboard, net]}
        classFilter=""
        onClassFilter={() => {}}
        search=""
        onSearch={() => {}}
        shown={2}
        total={2}
      />
    );
    expect(screen.getByText("Keyboard")).toBeInTheDocument();
    expect(screen.getByText("Net")).toBeInTheDocument();
    expect(screen.getByText("2 / 2")).toBeInTheDocument();
  });

  it("calls onSearch as the user types", async () => {
    const onSearch = vi.fn();
    render(
      <Toolbar
        devices={[keyboard]}
        classFilter=""
        onClassFilter={() => {}}
        search=""
        onSearch={onSearch}
        shown={1}
        total={1}
      />
    );
    await userEvent.type(screen.getByLabelText("Search devices"), "a");
    expect(onSearch).toHaveBeenCalled();
  });
});

describe("DeviceRow", () => {
  it("shows the name, class and status, and flags keyboards", () => {
    render(<DeviceRow device={keyboard} />);
    expect(screen.getByText("HID Keyboard Device")).toBeInTheDocument();
    expect(screen.getByText("Keyboard")).toBeInTheDocument();
    expect(screen.getByText("Ok")).toBeInTheDocument();
    expect(screen.getByText("keyboard")).toBeInTheDocument(); // the tag
  });

  it("expands to show details when clicked", async () => {
    render(<DeviceRow device={keyboard} />);
    // Details (e.g. the instance_id row) are hidden until expanded.
    expect(screen.queryByText("instance_id")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByText("instance_id")).toBeInTheDocument();
  });
});

describe("DeviceList", () => {
  it("renders one row per device", () => {
    render(<DeviceList devices={[keyboard, net]} />);
    expect(screen.getByText("HID Keyboard Device")).toBeInTheDocument();
    expect(screen.getByText("Ethernet Controller")).toBeInTheDocument();
  });

  it("shows an empty message when nothing matches", () => {
    render(<DeviceList devices={[]} />);
    expect(screen.getByText(/No devices match/)).toBeInTheDocument();
  });
});
