import { CATEGORIES, type Category } from "@/lib/types";

function labelFor(category: Category): string {
  return CATEGORIES.find((c) => c.value === category)?.label ?? category;
}

export default function CategoryTag({ category }: { category: Category }) {
  return <span className="text-sm text-muted">{labelFor(category)}</span>;
}
