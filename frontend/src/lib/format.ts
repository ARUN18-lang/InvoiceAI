export function formatMoney(amount: number | null | undefined, currency: string | null | undefined) {
  if (amount == null || Number.isNaN(amount)) return "—";
  const c = currency || "INR";
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: c, maximumFractionDigits: 2 }).format(
      amount
    );
  } catch {
    return `${c} ${amount.toFixed(2)}`;
  }
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(d);
}

export function categoryLabel(cat: string | null | undefined) {
  if (!cat) return "Uncategorized";
  return cat.replace(/_/g, " ");
}
