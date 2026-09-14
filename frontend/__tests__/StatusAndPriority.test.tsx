import { render, screen } from "@testing-library/react";
import StatusBadge from "@/components/StatusBadge";
import PriorityMark from "@/components/PriorityMark";
import StatusTransition from "@/components/StatusTransition";

describe("StatusBadge", () => {
  it.each([
    ["OPEN", "Open"],
    ["IN_PROGRESS", "In progress"],
    ["RESOLVED", "Resolved"],
  ] as const)("renders a text label for %s, not colour alone", (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});

describe("PriorityMark", () => {
  it.each([
    ["HIGH", "High"],
    ["MEDIUM", "Medium"],
    ["LOW", "Low"],
  ] as const)("renders a text label for %s, not the mark alone", (priority, label) => {
    render(<PriorityMark priority={priority} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});

describe("StatusTransition", () => {
  it("renders the old value struck through and the new value plain", () => {
    render(<StatusTransition oldValue="OPEN" newValue="RESOLVED" />);
    const oldValue = screen.getByText("Open");
    expect(oldValue).toHaveClass("line-through");
    expect(screen.getByText("Resolved")).toBeInTheDocument();
  });
});
