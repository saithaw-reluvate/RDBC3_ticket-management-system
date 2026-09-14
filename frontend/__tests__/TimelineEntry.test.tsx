import { render, screen } from "@testing-library/react";
import TimelineEntry from "@/components/TimelineEntry";

describe("TimelineEntry", () => {
  it("renders the event variant with a status transition", () => {
    render(
      <ul>
        <TimelineEntry
          variant="event"
          eventType="STATUS_CHANGED"
          oldValue="OPEN"
          newValue="IN_PROGRESS"
          timestamp="2026-01-01T00:00:00Z"
        />
      </ul>
    );
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getByText("In progress")).toBeInTheDocument();
  });

  it("renders the response variant", () => {
    render(
      <ul>
        <TimelineEntry variant="response" message="We're looking into this." timestamp="2026-01-01T00:00:00Z" />
      </ul>
    );
    expect(screen.getByText("We're looking into this.")).toBeInTheDocument();
  });

  it("renders the internal-note variant with a distinct tag", () => {
    render(
      <ul>
        <TimelineEntry
          variant="internal-note"
          message="Escalating to infra."
          timestamp="2026-01-01T00:00:00Z"
          author="admin1"
        />
      </ul>
    );
    expect(screen.getByText("Escalating to infra.")).toBeInTheDocument();
    expect(screen.getByText(/internal note/i)).toBeInTheDocument();
  });

  it("renders the attachment variant", () => {
    render(
      <ul>
        <TimelineEntry variant="attachment" filename="screenshot.png" timestamp="2026-01-01T00:00:00Z" />
      </ul>
    );
    expect(screen.getByText(/screenshot\.png/)).toBeInTheDocument();
  });
});
