import { render, screen } from "@testing-library/react";
import CategorySelect from "@/components/CategorySelect";
import { CATEGORIES } from "@/lib/types";

describe("CategorySelect", () => {
  it("is required", () => {
    render(<CategorySelect id="category" value="" onChange={() => {}} required />);
    expect(screen.getByRole("combobox")).toBeRequired();
  });

  it("renders exactly the seven approved values", () => {
    render(<CategorySelect id="category" value="" onChange={() => {}} />);
    const options = screen.getAllByRole("option").filter((option) => (option as HTMLOptionElement).value !== "");
    expect(options).toHaveLength(7);
    const values = options.map((option) => (option as HTMLOptionElement).value);
    expect(values).toEqual(CATEGORIES.map((c) => c.value));
  });

  it("renders each category's label", () => {
    render(<CategorySelect id="category" value="" onChange={() => {}} />);
    for (const category of CATEGORIES) {
      expect(screen.getByRole("option", { name: category.label })).toBeInTheDocument();
    }
  });
});
