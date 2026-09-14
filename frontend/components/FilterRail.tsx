import { CATEGORIES, PRIORITIES, STATUSES, type Category, type Priority, type Status } from "@/lib/types";

const STATUS_LABELS: Record<Status, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  RESOLVED: "Resolved",
};

const PRIORITY_LABELS: Record<Priority, string> = {
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

export interface QueueFilters {
  status: Status | "";
  priority: Priority | "";
  category: Category | "";
}

function FacetGroup<T extends string>({
  title,
  value,
  options,
  onSelect,
}: {
  title: string;
  value: T | "";
  options: { value: T; label: string }[];
  onSelect: (value: T | "") => void;
}) {
  return (
    <fieldset>
      <legend className="eyebrow mb-2">{title}</legend>
      <ul className="flex flex-col gap-1">
        <li>
          <button
            type="button"
            aria-pressed={value === ""}
            onClick={() => onSelect("")}
            className={`text-sm ${value === "" ? "font-medium text-ink" : "text-muted"}`}
          >
            All
          </button>
        </li>
        {options.map((option) => (
          <li key={option.value}>
            <button
              type="button"
              aria-pressed={value === option.value}
              onClick={() => onSelect(option.value)}
              className={`text-sm ${value === option.value ? "font-medium text-ink" : "text-muted"}`}
            >
              {option.label}
            </button>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}

export default function FilterRail({
  filters,
  onChange,
  onClear,
}: {
  filters: QueueFilters;
  onChange: (filters: QueueFilters) => void;
  onClear: () => void;
}) {
  const hasActiveFilters = filters.status || filters.priority || filters.category;

  return (
    <nav aria-label="Filter tickets" className="flex flex-col gap-6">
      <FacetGroup
        title="Status"
        value={filters.status}
        options={STATUSES.map((value) => ({ value, label: STATUS_LABELS[value] }))}
        onSelect={(status) => onChange({ ...filters, status })}
      />
      <FacetGroup
        title="Priority"
        value={filters.priority}
        options={PRIORITIES.map((value) => ({ value, label: PRIORITY_LABELS[value] }))}
        onSelect={(priority) => onChange({ ...filters, priority })}
      />
      <FacetGroup
        title="Category"
        value={filters.category}
        options={CATEGORIES.map((c) => ({ value: c.value, label: c.label }))}
        onSelect={(category) => onChange({ ...filters, category })}
      />
      {hasActiveFilters && (
        <button type="button" onClick={onClear} className="eyebrow self-start underline decoration-rule">
          Clear all filters
        </button>
      )}
    </nav>
  );
}
