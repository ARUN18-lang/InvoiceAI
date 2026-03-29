import { Link } from "react-router-dom";
import { Calendar, Loader2 } from "lucide-react";
import type { InvoiceRecord } from "@/lib/api";
import { categoryLabel, formatDate, formatMoney } from "@/lib/format";

function initials(name: string | null | undefined) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || "?";
}

export function InvoiceCard({ invoice }: { invoice: InvoiceRecord }) {
  const status = invoice.status ?? "completed";
  const title =
    status === "processing"
      ? invoice.original_filename || "Processing invoice"
      : status === "failed"
        ? invoice.original_filename || "Failed invoice"
        : invoice.vendor_name || "Unknown vendor";
  const subtitle =
    status === "processing"
      ? "Extracting text and digitizing…"
      : status === "failed"
        ? invoice.processing_error || "Processing failed"
        : [invoice.invoice_number, categoryLabel(invoice.category)].filter(Boolean).join(" · ") || "No invoice number";

  return (
    <Link
      to={`/invoices/${invoice.id}`}
      aria-busy={status === "processing"}
      className={`group block rounded-xl border p-5 shadow-card transition-colors hover:bg-[#1f1f1f] ${
        status === "failed"
          ? "border-red-500/30 bg-raised hover:border-red-500/45"
          : status === "processing"
            ? "border-accent/25 bg-raised hover:border-accent/40"
            : "border-line-strong bg-raised hover:border-accent/35"
      }`}
    >
      <div className="flex gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-line-strong bg-surface text-sm font-semibold text-neutral-100">
          {status === "processing" ? (
            <Loader2 className="h-6 w-6 animate-spin text-accent" strokeWidth={2.25} aria-hidden />
          ) : (
            initials(title)
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-white group-hover:text-white">{title}</h3>
          <p
            className={`mt-1 truncate text-sm ${status === "failed" ? "text-red-300/90" : "text-muted"}`}
            title={status === "failed" ? invoice.processing_error ?? undefined : undefined}
          >
            {subtitle}
          </p>
          <p className="mt-3 text-sm font-medium text-white/90">
            {status === "completed" ? formatMoney(invoice.total_amount, invoice.currency) : "—"}
          </p>
          <p className="mt-4 flex items-center gap-1.5 text-xs text-muted">
            <Calendar className="h-3.5 w-3.5" strokeWidth={2} />
            Created {formatDate(invoice.created_at)}
          </p>
        </div>
      </div>
    </Link>
  );
}
