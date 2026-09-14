import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Composer from "@/components/Composer";

describe("Composer", () => {
  it("defaults to public mode with the customer-visible banner and copy", () => {
    render(<Composer reporterName="Jane" onSubmit={jest.fn()} />);
    expect(screen.getByText(/visible to the customer.*jane will be emailed/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send reply" })).toBeInTheDocument();
    expect(screen.getByText(/fresh tracking link is included/i)).toBeInTheDocument();
  });

  it("switches to internal mode: banner, button label and footer all change", async () => {
    const user = userEvent.setup();
    render(<Composer reporterName="Jane" onSubmit={jest.fn()} />);

    await user.click(screen.getByRole("button", { name: "Internal note" }));

    expect(screen.getByText(/visible to staff only/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add internal note" })).toBeInTheDocument();
    expect(screen.getByText(/no email is sent/i)).toBeInTheDocument();
  });

  it("marks the active mode button with aria-pressed", async () => {
    const user = userEvent.setup();
    render(<Composer reporterName="Jane" onSubmit={jest.fn()} />);

    expect(screen.getByRole("button", { name: "Public reply" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Internal note" })).toHaveAttribute("aria-pressed", "false");

    await user.click(screen.getByRole("button", { name: "Internal note" }));

    expect(screen.getByRole("button", { name: "Public reply" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Internal note" })).toHaveAttribute("aria-pressed", "true");
  });

  it("submits the message and mode, then clears the field", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<Composer reporterName="Jane" onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("Message"), "We're on it.");
    await user.click(screen.getByRole("button", { name: "Send reply" }));

    expect(onSubmit).toHaveBeenCalledWith("We're on it.", false);
  });
});
