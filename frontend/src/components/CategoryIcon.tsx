/** The icon of a category, decoration only: the name beside it says the same. */
export function CategoryIcon({ icon }: { icon?: string }) {
  return icon ? (
    <span className="category-icon" aria-hidden="true">
      {icon}
    </span>
  ) : null;
}
