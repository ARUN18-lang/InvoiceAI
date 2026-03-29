import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchInvoice, type InvoiceRecord } from "@/lib/api";
import { categoryLabel, formatDate, formatMoney } from "@/lib/format";
import { ArrowLeft, AlertTriangle, Loader2 } from "lucide-react";

export function InvoiceDetailPage() {
  const { current } = useWorkspace();
  const { id } = useParams<{ id: string }>();
  const [invoice, setInvoice] = useState<InvoiceRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || !current?.id) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchInvoice(id);
        if (!cancelled) setInvoice(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Not found");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, current?.id]);

  useEffect(() => {
    if (!id || !current?.id) return;
    const st = invoice?.status ?? "completed";
    if (st !== "processing") return;
    const t = setInterval(() => {
      void (async () => {
        try {
          const data = await fetchInvoice(id);
          setInvoice(data);
          setError(null);
        } catch {
          /* keep showing last good state */
        }
      })();
    }, 3000);
    return () => clearInterval(t);
  }, [id, current?.id, invoice?.status]);

  if (!id) {
    return <p className="p-8 text-muted">Missing id</p>;
  }

  const status = invoice?.status ?? "completed";

  return (
    <div>
      <PageHeader
        breadcrumb="Home · Invoices"
        title={
          status === "processing"
            ? invoice?.original_filename || "Processing"
            : status === "failed"
              ? invoice?.original_filename || "Failed"
              : invoice?.vendor_name || "Invoice"
        }
        subtitle={
          status === "processing"
            ? "Extracting text and digitizing…"
            : status === "failed"
              ? "Could not complete digitization"
              : invoice?.invoice_number
                ? `Invoice #${invoice.invoice_number}`
                : "Digitized invoice details"
        }
        action={
          <Link to="/invoices">
            <Button variant="secondary" className="gap-2">
              <ArrowLeft className="h-4 w-4" strokeWidth={2} />
              Back
            </Button>
          </Link>
        }
      />

      <div className="px-8 py-8">
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        {!invoice && !error ? <p className="text-sm text-muted">Loading…</p> : null}
        {invoice && status === "processing" ? (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-accent/25 bg-raised px-8 py-16 text-center shadow-card">
            <Loader2 className="h-10 w-10 animate-spin text-accent" strokeWidth={2} aria-hidden />
            <p className="max-w-md text-sm text-muted">
              This invoice is being processed in the background (PDF extraction and AI parsing). This page will refresh
              automatically.
            </p>
          </div>
        ) : null}
        {invoice && status === "failed" ? (
          <div className="rounded-xl border border-red-500/35 bg-raised p-6 shadow-card">
            <h2 className="text-sm font-semibold text-red-300">Processing failed</h2>
            <p className="mt-2 text-sm text-red-200/90">{invoice.processing_error || "Unknown error"}</p>
          </div>
        ) : null}
        {invoice && status === "completed" ? (
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              <section className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Summary</h2>
                <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs text-muted">Vendor</dt>
                    <dd className="mt-1 text-sm font-medium text-white">{invoice.vendor_name || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Category</dt>
                    <dd className="mt-1 text-sm font-medium text-white">{categoryLabel(invoice.category)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Invoice date</dt>
                    <dd className="mt-1 text-sm font-medium text-white">{formatDate(invoice.invoice_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Due date</dt>
                    <dd className="mt-1 text-sm font-medium text-white">{formatDate(invoice.due_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Total</dt>
                    <dd className="mt-1 text-lg font-semibold text-white">
                      {formatMoney(invoice.total_amount, invoice.currency)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Tax</dt>
                    <dd className="mt-1 text-sm font-medium text-white">
                      {formatMoney(invoice.tax_amount, invoice.currency)}
                    </dd>
                  </div>
                </dl>
              </section>

              <section className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Line items</h2>
                {invoice.line_items.length === 0 ? (
                  <p className="mt-4 text-sm text-muted">No line items extracted.</p>
                ) : (
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-line text-xs uppercase text-muted">
                          <th className="pb-2 font-medium">Description</th>
                          <th className="pb-2 font-medium">Qty</th>
                          <th className="pb-2 font-medium">Unit</th>
                          <th className="pb-2 font-medium">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {invoice.line_items.map((row, idx) => (
                          <tr key={idx} className="border-b border-line">
                            <td className="py-3 pr-4 text-white/90">{row.description || "—"}</td>
                            <td className="py-3 text-muted">{row.quantity ?? "—"}</td>
                            <td className="py-3 text-muted">
                              {row.unit_price != null ? formatMoney(row.unit_price, invoice.currency) : "—"}
                            </td>
                            <td className="py-3 text-white">
                              {row.amount != null ? formatMoney(row.amount, invoice.currency) : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </div>

            <div className="space-y-6">
              <section className="rounded-xl border border-line-strong bg-raised p-6 shadow-card">
                <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted">
                  Validation
                  {!invoice.validation.is_valid ? (
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                  ) : null}
                </h2>
                <p className="mt-2 text-sm text-white/90">
                  {invoice.validation.is_valid ? "No blocking issues." : "Review flagged items."}
                </p>
                {invoice.validation.fraud_flags.length > 0 ? (
                  <ul className="mt-3 list-inside list-disc text-xs text-amber-200/90">
                    {invoice.validation.fraud_flags.map((f) => (
                      <li key={f}>{f.replace(/_/g, " ")}</li>
                    ))}
                  </ul>
                ) : null}
                {invoice.validation.issues.length > 0 ? (
                  <ul className="mt-4 space-y-2">
                    {invoice.validation.issues.map((issue, i) => (
                      <li
                        key={`${issue.code}-${i}`}
                        className="rounded-lg border border-line bg-surface px-3 py-2 text-xs text-muted"
                      >
                        <span className="font-medium text-white/90">{issue.severity}</span>
                        {": "}
                        {issue.message}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </section>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
