import { render, screen } from "@testing-library/react";
import FormField from "@/components/FormField";

describe("FormField", () => {
  it("renders the details error message", () => {
    render(
      <FormField id="email" label="Email address" error="Enter a valid email address.">
        {({ describedBy, invalid }) => (
          <input id="email" aria-describedby={describedBy} aria-invalid={invalid} />
        )}
      </FormField>
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email address.");
  });

  it("wires the control's aria-describedby to the error message id", () => {
    render(
      <FormField id="email" label="Email address" error="Enter a valid email address.">
        {({ describedBy, invalid }) => (
          <input id="email" aria-describedby={describedBy} aria-invalid={invalid} />
        )}
      </FormField>
    );
    const input = screen.getByLabelText("Email address");
    const errorMessage = screen.getByRole("alert");
    expect(input).toHaveAttribute("aria-describedby", errorMessage.id);
    expect(input).toHaveAttribute("aria-invalid", "true");
  });

  it("wires helper text instead when there is no error", () => {
    render(
      <FormField id="email" label="Email address" helperText="We'll only use this to send updates.">
        {({ describedBy, invalid }) => (
          <input id="email" aria-describedby={describedBy} aria-invalid={invalid} />
        )}
      </FormField>
    );
    const input = screen.getByLabelText("Email address");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "false");
    expect(input.getAttribute("aria-describedby")).toBe(
      screen.getByText("We'll only use this to send updates.").id
    );
  });
});
