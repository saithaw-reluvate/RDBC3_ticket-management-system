import { CATEGORIES, type Category } from "@/lib/types";

export default function CategorySelect({
  id,
  name,
  value,
  onChange,
  required = false,
  ariaDescribedBy,
  ariaInvalid,
}: {
  id: string;
  name?: string;
  value: Category | "";
  onChange: (value: Category) => void;
  required?: boolean;
  ariaDescribedBy?: string;
  ariaInvalid?: boolean;
}) {
  return (
    <div className="relative">
      <select
        id={id}
        name={name}
        value={value}
        required={required}
        aria-describedby={ariaDescribedBy}
        aria-invalid={ariaInvalid}
        onChange={(event) => onChange(event.target.value as Category)}
        className="w-full appearance-none border-0 border-b border-rule bg-transparent py-2 pr-8 text-base focus:border-oxide focus:outline-none"
      >
        <option value="" disabled>
          Select a category
        </option>
        {CATEGORIES.map((category) => (
          <option key={category.value} value={category.value}>
            {category.label}
          </option>
        ))}
      </select>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute right-1 top-1/2 -translate-y-1/2 text-faint"
      >
        {"▾"}
      </span>
    </div>
  );
}
